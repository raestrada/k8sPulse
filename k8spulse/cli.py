import os
import time
import click
from datetime import datetime
from rich.console import Console
import subprocess

from k8spulse.detector.deployments import (
    get_deployments_count,
    get_deployments_with_crashloopbackoff,
    get_deployments_with_exact_replicas,
    get_deployments_with_recent_restarts,
    get_deployments_with_replicas,
    get_deployments_with_zero_replicas,
)
from k8spulse.detector.status import (
    get_nodes_with_issues,
    get_semaphore_status,
    get_unusual_events,
)
from k8spulse.detector.zombies import detect_zombie_processes_in_pods
from k8spulse.charts import generate_dial_gauge_chart, generate_line_chart
from k8spulse.db import (
    generate_index_html,
    save_report_history,
    load_report_history,
    render_html_report,
    prepare_history_data_for_template,
)
from k8spulse.openai import get_openai_recommendation

console = Console()


# Main script logic using Click
@click.command()
@click.option("--env-name", default="staging", help="Environment name for the report.")
@click.option(
    "--interval", default=300, help="Interval in seconds between report generations."
)
@click.option("--use-ai", is_flag=True, help="Use OpenAI to generate recommendations.")
@click.option(
    "--git-commit",
    is_flag=True,
    help="Commit and push the generated report to Git repository.",
)
@click.option(
    "--zombies",
    is_flag=True,
    default=False,
    help="Detect Zombies.",
)
@click.option("--gpt-model", default="gpt-4o", help="GPT Model")
def cli(env_name, interval, use_ai, git_commit, gpt_model, zombies):
    template_name = "report_template.html"
    docs_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_file = os.path.join(docs_dir, f"{env_name}_statistics.html")
    history_file = os.path.join(docs_dir, f"{env_name}_statistics_history.csv")

    while True:
        console.log("[green]Starting Kubernetes monitoring cycle...[/green]")
        total_deployments = get_deployments_count()
        deployments_with_replicas = get_deployments_with_replicas()
        deployments_with_zero_replicas = get_deployments_with_zero_replicas()
        deployments_with_exact_replicas = get_deployments_with_exact_replicas()
        deployments_with_recent_start = get_deployments_with_recent_restarts()
        deployments_with_crashloopbackoff = get_deployments_with_crashloopbackoff()
        nodes_with_issues = get_nodes_with_issues()
        unusual_events = get_unusual_events()
        semaphore_statuses = get_semaphore_status()

        # Save report history
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_deployments": total_deployments,
            "deployments_with_replicas": deployments_with_replicas,
            "deployments_with_zero_replicas": deployments_with_zero_replicas,
            "deployments_with_recent_start": deployments_with_recent_start,
            "deployments_with_exact_replicas": deployments_with_exact_replicas,
            "deployments_with_crashloopbackoff": deployments_with_crashloopbackoff,
            "nodes_with_issues": nodes_with_issues,
        }
        save_report_history(history_file, data)

        # Load history data for generating charts
        history_df = load_report_history(history_file)

        # Generate charts using dial gauges
        gauge_chart_deployments_with_replicas = generate_dial_gauge_chart(
            deployments_with_replicas,
            "With Replicas",
            max_value=total_deployments,
            direction="direct",
            red_threshold=60,
            yellow_threshold=80,
        )
        gauge_chart_deployments_zero_replicas = generate_dial_gauge_chart(
            deployments_with_zero_replicas,
            "Zero Replicas",
            max_value=total_deployments,
            direction="inverse",
            red_threshold=70,
            yellow_threshold=50,
        )
        gauge_chart_exact_replicas = generate_dial_gauge_chart(
            deployments_with_exact_replicas,
            "Exact Replicas",
            max_value=total_deployments,
            direction="direct",
            red_threshold=50,
            yellow_threshold=65,
        )  # Example calculation
        gauge_chart_crashloopbackoff = generate_dial_gauge_chart(
            deployments_with_crashloopbackoff,
            "CrashLoopBackOff",
            max_value=total_deployments,
            direction="inverse",
            red_threshold=50,
            yellow_threshold=30,
        )
        gauge_chart_recently_restarted = generate_dial_gauge_chart(
            deployments_with_recent_start,
            "Restarted",
            direction="inverse",
            red_threshold=60,
            yellow_threshold=30,
        )  # Placeholder
        line_chart_image = generate_line_chart(history_df)

        if use_ai:
            # Generate recommendation using OpenAI
            console.log("[cyan]Generating OpenAI recommendation...[/cyan]")
            recommendation = get_openai_recommendation(report_file, gpt_model)
        else:
            recommendation = ""

        context = {
            "env_name": env_name,
            "timestamp": data["timestamp"],
            "total_deployments": total_deployments,
            "deployments_with_replicas": deployments_with_replicas,
            "deployments_with_zero_replicas": deployments_with_zero_replicas,
            "deployments_with_recent_start": deployments_with_recent_start,
            "deployments_with_exact_replicas": deployments_with_exact_replicas,
            "deployments_with_crashloopbackoff": deployments_with_crashloopbackoff,
            "nodes_with_issues": nodes_with_issues,
            "unusual_events": unusual_events,
            **semaphore_statuses,  # Merge semaphore statuses into the context
            "gauge_chart_deployments_with_replicas": gauge_chart_deployments_with_replicas,
            "gauge_chart_deployments_zero_replicas": gauge_chart_deployments_zero_replicas,
            "gauge_chart_exact_replicas": gauge_chart_exact_replicas,
            "gauge_chart_crashloopbackoff": gauge_chart_crashloopbackoff,
            "gauge_chart_recently_restarted": gauge_chart_recently_restarted,
            "line_chart_image": line_chart_image,
            "use_ai": use_ai,
            "history_data": prepare_history_data_for_template(history_file),
            "openai_recommendation": recommendation,
            "zombies": zombies,
            "zombies_processes": detect_zombie_processes_in_pods() if zombies else []
        }

        # Generate HTML report
        rendered_html = render_html_report(template_name, context)
        with open(report_file, "w") as f:
            f.write(rendered_html)

        console.log(f"[green]Report saved to {report_file}[/green]")
        console.log(f"[green]Generate index[/green]")
        generate_index_html()

        # Commit and push to git if enabled
        if git_commit:
            console.log(
                "[cyan]Committing and pushing the report to Git repository...[/cyan]"
            )
            subprocess.run(["git", "add", report_file])
            subprocess.run(["git", "commit", "-m", f"{env_name} statistics update"])
            subprocess.run(["git", "push"])

        console.log(
            f"[green]Waiting for {interval} seconds before the next cycle...[/green]"
        )
        time.sleep(interval)


if __name__ == "__main__":
    cli()
