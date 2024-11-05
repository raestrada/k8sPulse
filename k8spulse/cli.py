import os
import time
import click
from jinja2 import Environment, FileSystemLoader
import yaml
import datetime
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import base64
from io import BytesIO
import openai
import pandas as pd
from kubernetes import client, config
from collections import defaultdict
from rich.console import Console
import subprocess

console = Console()

# HTML Template directory setup
template_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(template_dir))

# Load Kubernetes config
config.load_kube_config()


# Functions to gather Kubernetes statistics
def get_deployments_count():
    console.log("[cyan]Fetching total deployments count...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    return len(deployments.items)


def get_deployments_with_replicas():
    console.log("[cyan]Counting deployments with at least one replica...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = 0
    for deployment in deployments.items:
        if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
            count += 1
    return count


def get_deployments_with_exact_replicas():
    console.log("[cyan]Counting deployments with exactly desired replicas...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = 0
    for deployment in deployments.items:
        if (
            deployment.status.ready_replicas is not None
            and deployment.status.ready_replicas == deployment.spec.replicas
        ):
            count += 1
    return count


def get_deployments_with_zero_replicas():
    console.log("[cyan]Counting deployments with zero replicas...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = 0
    for deployment in deployments.items:
        if (
            not deployment.status.ready_replicas
            or deployment.status.ready_replicas == 0
        ):
            count += 1
    return count


from datetime import datetime, timedelta

from datetime import datetime, timedelta


def get_deployments_with_recent_restarts():
    console.log(
        "[cyan]Counting deployments with pods recently restarted (last 10 minutes)...[/cyan]"
    )
    core_v1 = client.CoreV1Api()
    now = datetime.now(
        timezone.utc
    )  # Cambiado a un objeto datetime con zona horaria UTC
    ten_minutes_ago = now - timedelta(minutes=10)

    pods = core_v1.list_pod_for_all_namespaces()
    deployment_names = set()  # Usaremos un conjunto para evitar duplicados

    for pod in pods.items:
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if (
                    container_status.restart_count > 0
                    and container_status.state.terminated
                ):
                    last_restart_time = container_status.state.terminated.finished_at
                    if last_restart_time:
                        # Asegurarse de que last_restart_time tenga información de zona horaria
                        last_restart_time = last_restart_time.astimezone(timezone.utc)
                        if last_restart_time >= ten_minutes_ago:
                            # Añadir el nombre del deployment relacionado al conjunto
                            owner_references = pod.metadata.owner_references
                            if owner_references:
                                for owner in owner_references:
                                    if owner.kind == "ReplicaSet":
                                        deployment_name = owner.name.rsplit("-", 1)[
                                            0
                                        ]  # Obtener el nombre del deployment sin el sufijo del ReplicaSet
                                        deployment_names.add(deployment_name)

    return len(deployment_names)


def get_deployments_with_crashloopbackoff():
    console.log("[cyan]Counting deployments with pods in CrashLoopBackOff state...[/cyan]")
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    # Get all pods
    pods = core_v1.list_pod_for_all_namespaces()

    # Track namespaces and labels of pods in CrashLoopBackOff
    deployments_in_crashloop = set()

    for pod in pods.items:
        for container_status in pod.status.container_statuses or []:
            if (
                container_status.state.waiting
                and container_status.state.waiting.reason == "CrashLoopBackOff"
            ):
                # Identify the deployment from pod metadata labels
                labels = pod.metadata.labels
                if labels:
                    # Assuming the label `app` or `app.kubernetes.io/name` identifies the deployment
                    app_label = labels.get('app') or labels.get('app.kubernetes.io/name')
                    if app_label:
                        deployments_in_crashloop.add((pod.metadata.namespace, app_label))

    # Check for matching deployments
    count = 0
    for namespace, app_label in deployments_in_crashloop:
        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        for deployment in deployments.items:
            if deployment.metadata.labels.get('app') == app_label or deployment.metadata.labels.get('app.kubernetes.io/name') == app_label:
                count += 1

    return count

def get_nodes_with_issues():
    console.log("[cyan]Identifying nodes with issues...[/cyan]")
    core_v1 = client.CoreV1Api()
    nodes = core_v1.list_node()
    nodes_with_issues = []
    for node in nodes.items:
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status != "True":
                nodes_with_issues.append(
                    {
                        "name": node.metadata.name,
                        "status": condition.status,
                        "description": yaml.dump(node.to_dict()),
                    }
                )
    return nodes_with_issues


def get_unusual_events():
    console.log("[cyan]Fetching unusual events from Kubernetes...[/cyan]")
    core_v1 = client.CoreV1Api()
    events = core_v1.list_event_for_all_namespaces()
    event_summary = defaultdict(
        lambda: {
            "count": 0,
            "namespace": "",
            "reason": "",
            "first_timestamp": "",
            "last_timestamp": "",
            "message": "",
        }
    )

    for event in events.items:
        if event.type != "Normal":
            key = (event.metadata.namespace, event.reason, event.message)
            event_summary[key]["count"] += 1
            event_summary[key]["namespace"] = event.metadata.namespace
            event_summary[key]["reason"] = event.reason
            event_summary[key]["message"] = event.message
            event_summary[key]["first_timestamp"] = event.first_timestamp
            event_summary[key]["last_timestamp"] = event.last_timestamp

    # Sorting events by count (descending)
    sorted_events = sorted(
        event_summary.values(), key=lambda x: x["count"], reverse=True
    )
    return sorted_events[:50]


def get_semaphore_status():
    console.log("[cyan]Fetching status of Kubernetes services...[/cyan]")
    apps_v1 = client.AppsV1Api()
    statuses = {
        "metrics_server_status": False,
        "kube_dns_status": False,
        "cast_ai_agent_status": False,
        "cast_ai_workload_autoscaler_status": False,
        "cast_ai_cluster_controller_status": False,
    }

    # Metrics Server
    try:
        deployments = apps_v1.list_namespaced_deployment(namespace="kube-system")
        metrics_server = next((
            deployment for deployment in deployments.items
            if deployment.metadata.name.startswith("metrics-server")
        ), None)
        if metrics_server and metrics_server.status.ready_replicas and metrics_server.status.ready_replicas > 0:
            statuses["metrics_server_status"] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching metrics-server status[/red]")

    # Kube-DNS
    try:
        kube_dns = apps_v1.read_namespaced_deployment(
            name="kube-dns", namespace="kube-system"
        )
        if kube_dns.status.ready_replicas and kube_dns.status.ready_replicas > 0:
            statuses["kube_dns_status"] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching kube-dns status[/red]")

    # CAST AI Agent
    try:
        cast_ai_agent = apps_v1.read_namespaced_deployment(
            name="castai-agent", namespace="castai-agent"
        )
        if (
            cast_ai_agent.status.ready_replicas
            and cast_ai_agent.status.ready_replicas > 0
        ):
            statuses["cast_ai_agent_status"] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-agent status[/red]")

    # CAST AI Workload Autoscaler
    try:
        cast_ai_workload_autoscaler = apps_v1.read_namespaced_deployment(
            name="castai-workload-autoscaler", namespace="castai-agent"
        )
        if (
            cast_ai_workload_autoscaler.status.ready_replicas
            and cast_ai_workload_autoscaler.status.ready_replicas > 0
        ):
            statuses["cast_ai_workload_autoscaler_status"] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-workload-autoscaler status[/red]")

    # CAST AI Cluster Controller
    try:
        cast_ai_cluster_controller = apps_v1.read_namespaced_deployment(
            name="castai-cluster-controller", namespace="castai-agent"
        )
        if (
            cast_ai_cluster_controller.status.ready_replicas
            and cast_ai_cluster_controller.status.ready_replicas > 0
        ):
            statuses["cast_ai_cluster_controller_status"] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-cluster-controller status[/red]")

    return statuses


# Function to generate gauge chart images and encode them in base64
def generate_dial_gauge_chart(value, title, min_value=0, max_value=100, direction="direct", yellow_threshold=50, red_threshold=80):
    # Calculate the actual percentage based on value and limits
    percentage = (value - min_value) / (max_value - min_value) * 100
    percentage = min(max(percentage, 0), 100)  # Limit percentage between 0 and 100

    console.log(
        f"[cyan]Generating dial gauge chart for {title} with {percentage}%...[/cyan]"
    )

    # Set gauge colors based on thresholds and direction
    if direction == "inverse":
        # Inverse: less is better
        if percentage <= yellow_threshold:
            color = "#4CAF50"
        elif percentage <= red_threshold:
            color = "#FFC107"
        else:
            color = "#FF4444"
    else:
        # Direct: more is better
        if percentage >= red_threshold:
            color = "#4CAF50"
        elif percentage >= yellow_threshold:
            color = "#FFC107"
        else:
            color = "#FF4444"

    fig, ax = plt.subplots(
        figsize=(5, 2.5), subplot_kw={"aspect": "equal"}
    )  # Restore original figure size

    # Determine wedge parameters based on percentage
    theta = percentage / 100 * 180  # Scale to half-circle (0° to 180°)
    wedge = Wedge(
        center=(0, 0),
        r=1,
        theta1=0,
        theta2=theta,
        facecolor=color,
        edgecolor="black",
    )

    # Add the wedge and background to the plot
    ax.add_patch(wedge)
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")  # Hide the axes

    # Add title and percentage labels
    plt.text(
        0, -1.3, title, ha="center", va="center", fontsize=12
    )  # Restore original font size for title
    plt.text(
        0,
        0.2,
        f"{percentage:.0f}%",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
    )  # Display percentage

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", transparent=True)
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded_image

# Function to generate line chart based on history data
def generate_line_chart(history_df):
    console.log(
        "[cyan]Generating line chart for Kubernetes metrics over time...[/cyan]"
    )
    if "timestamp" not in history_df.columns:
        console.log(
            "[red]Error: 'timestamp' column not found in history data. Cannot generate line chart.[/red]"
        )
        return ""

    # Convert absolute values to percentages
    history_df["deployments_with_replicas_pct"] = (
        history_df["deployments_with_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_zero_replicas_pct"] = (
        history_df["deployments_with_zero_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_exact_replicas_pct"] = (
        history_df["deployments_with_exact_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_crashloopbackoff_pct"] = (
        history_df["deployments_with_crashloopbackoff"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_recent_start_pct"] = (
        history_df["deployments_with_recent_start"] / history_df["total_deployments"]
    ) * 100

    fig, ax = plt.subplots(figsize=(16, 6))  # Double the width by adjusting figsize
    history_df.plot(
        x="timestamp",
        y=[
            "deployments_with_replicas_pct",
            "deployments_with_zero_replicas_pct",
            "deployments_with_exact_replicas_pct",
            "deployments_with_crashloopbackoff_pct",
            "deployments_with_recent_start_pct",
        ],
        ax=ax,
    )

    plt.xlabel("Time")
    plt.ylabel("Percentage (%)")
    plt.title("Kubernetes Metrics Over Time (Percentage)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded_image


def save_report_history(history_file, data):
    console.log("[cyan]Saving report history...[/cyan]")
    columns = [
        "timestamp",
        "total_deployments",
        "deployments_with_replicas",
        "deployments_with_zero_replicas",
        "deployments_with_exact_replicas",
        "deployments_with_crashloopbackoff",
        "deployments_with_recent_start",
        "nodes_with_issues",
    ]
    if not os.path.exists(history_file):
        with open(history_file, "w") as f:
            f.write(",".join(columns) + "\n")
    with open(history_file, "a") as f:
        f.write(
            f"{data['timestamp']},{data['total_deployments']},{data['deployments_with_replicas']},{data['deployments_with_zero_replicas']},{data['deployments_with_exact_replicas']},{data['deployments_with_crashloopbackoff']},{data['deployments_with_recent_start']},{len(data['nodes_with_issues'])}\n"
        )


def load_report_history(history_file):
    console.log("[cyan]Loading report history...[/cyan]")
    if not os.path.exists(history_file):
        # Return an empty DataFrame with expected columns if the history file doesn't exist
        return pd.DataFrame(
            columns=[
                "timestamp",
                "total_deployments",
                "deployments_with_replicas",
                "deployments_with_zero_replicas",
                "deployments_with_exact_replicas",
                "deployments_with_crashloopbackoff",
                "deployments_with_recent_start",
                "nodes_with_issues",
            ]
        )
    return pd.read_csv(history_file)


# Convert the DataFrame to a list of dictionaries to be passed to the HTML template
def prepare_history_data_for_template(history_file):
    history_df = load_report_history(history_file)
    history_data = history_df.to_dict(orient="records")
    return history_data


# Render the HTML report
def render_html_report(template_name, context):
    console.log("[cyan]Rendering HTML report...[/cyan]")
    template = env.get_template(template_name)
    return template.render(context)


def get_openai_recommendation(report_file_path, gpt_model):
    console.log("[cyan]Requesting recommendation from OpenAI...[/cyan]")

    # Initialize OpenAI client (it will automatically use the API key from environment variables)
    client = openai.OpenAI()

    # Step 1: Upload the report file to OpenAI
    with open(report_file_path, "rb") as report_file:
        uploaded_file = client.files.create(file=report_file, purpose="assistants")
    file_id = uploaded_file.id

    if not file_id:
        console.log("[red]Error: Failed to upload the report to OpenAI.[/red]")
        return ""

    # Step 2: Create a new thread
    thread_response = client.beta.threads.create()
    thread_id = thread_response.id

    if not thread_id:
        console.log("[red]Error: Failed to create a new thread in OpenAI.[/red]")
        return ""

    # Step 3: Send a message to the thread
    message_response = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Attached is a Kubernetes cluster report. Please analyze it and provide a concise and actionable recommendation to improve the overall health of the cluster. Focus on issues related to deployments, pods, metrics server, and CrashLoopBackOff. Only return the result in HTML to put in a innerHTML format with a good style, without using ``` or any other code block delimiters.",
        attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}],
    )
    message_id = message_response.id

    if not message_id:
        console.log("[red]Error: Failed to send a message to OpenAI.[/red]")
        return ""

    # Step 4: Create the assistant using GPT-4o
    assistant_response = client.beta.assistants.create(
        instructions="You are an assistant that provides actionable recommendations based on Kubernetes cluster reports. Consider that Cast.ai is used to analyze resources taints issues that could be normal when using dynamic auto-scaling.",
        name="Kubernetes Health Assistant",
        tools=[{"type": "file_search"}],
        model=gpt_model,
        temperature=0.7,
        top_p=1.0,
    )
    assistant_id = assistant_response.id

    if not assistant_id:
        console.log("[red]Error: Failed to create the assistant in OpenAI.[/red]")
        return ""

    # Step 5: Create a run for the thread with the assistant
    run_response = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )
    run_id = run_response.id

    if not run_id:
        console.log("[red]Error: Failed to create a run in OpenAI.[/red]")
        return ""

    # Step 6: Wait for the run to complete
    while True:
        time.sleep(5)  # Wait a few seconds before trying to get the response
        run_status_response = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        status = run_status_response.status

        if status == "completed":
            break
        elif status == "failed":
            console.log("[red]Error: The run has failed.[/red]")
            return ""

    # Step 7: Retrieve the final message from the assistant
    messages_response = client.beta.threads.messages.list(thread_id=thread_id)
    messages = messages_response.data

    # Extract the content from the last message
    recommendation = messages[0].content[0].text.value if messages else ""

    return recommendation


# Define el directorio donde se guardan los reportes
REPORTS_DIR = "docs"


# Función para obtener la lista de reportes generados
def get_reports_list():
    reports = []
    for filename in os.listdir(REPORTS_DIR):
        if filename.endswith(".html") and filename != "index.html":
            report_path = os.path.join(REPORTS_DIR, filename)
            # Extraer la fecha del nombre del archivo o de su metadata
            report_date = datetime.fromtimestamp(
                os.path.getmtime(report_path)
            ).strftime("%Y-%m-%d %H:%M:%S")
            reports.append(
                {
                    "name": filename.replace(".html", "")
                    .replace("_", " ")
                    .capitalize(),
                    "link": filename,
                    "date": report_date,
                }
            )
    return sorted(reports, key=lambda x: x["date"], reverse=True)


# Función para generar el archivo index.html
def generate_index_html():
    template = env.get_template("index.html")  # Usa el template `index.html`
    reports = get_reports_list()
    rendered_index = template.render(reports=reports)

    # Guardar el index.html en el directorio de reportes
    with open(os.path.join(REPORTS_DIR, "index.html"), "w") as f:
        f.write(rendered_index)


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
@click.option("--gpt-model", default="gpt-4o", help="GPT Model")
def cli(env_name, interval, use_ai, git_commit, gpt_model):
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
            deployments_with_replicas, "With Replicas", max_value=total_deployments, direction="direct", red_threshold=60, yellow_threshold=80
        )
        gauge_chart_deployments_zero_replicas = generate_dial_gauge_chart(
            deployments_with_zero_replicas, "Zero Replicas", max_value=total_deployments, direction="inverse", red_threshold=70, yellow_threshold=50
        )
        gauge_chart_exact_replicas = generate_dial_gauge_chart(
            deployments_with_exact_replicas,
            "Exact Replicas",
            max_value=total_deployments, direction="direct", red_threshold=50, yellow_threshold=65
        )  # Example calculation
        gauge_chart_crashloopbackoff = generate_dial_gauge_chart(
            deployments_with_crashloopbackoff, "CrashLoopBackOff", max_value=total_deployments, direction="inverse", red_threshold=50, yellow_threshold=30
        )
        gauge_chart_recently_restarted = generate_dial_gauge_chart(
            deployments_with_recent_start, "Restarted", direction="inverse", red_threshold=60, yellow_threshold=30
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
