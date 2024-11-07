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
from k8spulse.charts import (
    generate_dial_gauge_chart,
    generate_line_chart,
    generate_resource_dial_gauge,
)
from k8spulse.db import (
    generate_index_html,
    save_report_history,
    load_report_history,
    render_html_report,
    prepare_history_data_for_template,
)
from k8spulse.openai_tools import get_openai_recommendation

from k8spulse.detector.resources import get_cluster_resource_metrics

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

        zombie_processes = detect_zombie_processes_in_pods() if zombies else []
        resource_metrics = get_cluster_resource_metrics()

        # Calculate and adjust percentages for CPU and memory
        cpu_used_percentage = (
            resource_metrics["total_cpu_used_mcores"]
            / resource_metrics["total_cpu_capacity_mcores"]
        ) * 100
        cpu_requested_percentage = (
            resource_metrics["total_cpu_requested_mcores"]
            / resource_metrics["total_cpu_capacity_mcores"]
        ) * 100

        memory_used_percentage = (
            resource_metrics["total_memory_used_mib"]
            / resource_metrics["total_memory_capacity_mib"]
        ) * 100
        memory_requested_percentage = (
            resource_metrics["total_memory_requested_mib"]
            / resource_metrics["total_memory_capacity_mib"]
        ) * 100

        # Correct percentages if they are improbably low
        if cpu_used_percentage < 1:
            cpu_used_percentage *= 100

        if cpu_requested_percentage < 1:
            cpu_requested_percentage *= 100

        if memory_used_percentage < 1:
            memory_used_percentage *= 100

        if memory_requested_percentage < 1:
            memory_requested_percentage *= 100

        # Save report history with added percentages
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_deployments": total_deployments,
            "deployments_with_replicas": deployments_with_replicas,
            "deployments_with_zero_replicas": deployments_with_zero_replicas,
            "deployments_with_recent_start": deployments_with_recent_start,
            "deployments_with_exact_replicas": deployments_with_exact_replicas,
            "deployments_with_crashloopbackoff": deployments_with_crashloopbackoff,
            "nodes_with_issues": nodes_with_issues,
            "zombie_processes": zombie_processes,
            # Add calculated percentages for CPU and memory usage
            "cpu_used_percentage": cpu_used_percentage,
            "cpu_requested_percentage": cpu_requested_percentage,
            "memory_used_percentage": memory_used_percentage,
            "memory_requested_percentage": memory_requested_percentage,
        }

        save_report_history(data)

        # Load history data for generating charts
        history_df = load_report_history(as_dataframe=True)

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
        )

        gauge_cluster_resource_metrics_cpu = generate_resource_dial_gauge(
            "cpu", resource_metrics
        )
        gauge_cluster_resource_metrics_memory = generate_resource_dial_gauge(
            "memory", resource_metrics
        )

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
            "gauge_cluster_resource_metrics_cpu": gauge_cluster_resource_metrics_cpu,
            "gauge_cluster_resource_metrics_memory": gauge_cluster_resource_metrics_memory,
            "line_chart_image": line_chart_image,
            "use_ai": use_ai,
            "history_data": prepare_history_data_for_template(),
            "openai_recommendation": recommendation,
            "zombies": zombies,
            "zombies_processes": zombie_processes,
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
