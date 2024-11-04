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
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
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
        if deployment.status.ready_replicas is not None and deployment.status.ready_replicas == deployment.spec.replicas:
            count += 1
    return count


def get_deployments_with_zero_replicas():
    console.log("[cyan]Counting deployments with zero replicas...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = 0
    for deployment in deployments.items:
        if not deployment.status.ready_replicas or deployment.status.ready_replicas == 0:
            count += 1
    return count

from datetime import datetime, timedelta

from datetime import datetime, timedelta

def get_deployments_with_recent_restarts():
    console.log("[cyan]Counting deployments with pods recently restarted (last 10 minutes)...[/cyan]")
    core_v1 = client.CoreV1Api()
    now = datetime.now(timezone.utc)  # Cambiado a un objeto datetime con zona horaria UTC
    ten_minutes_ago = now - timedelta(minutes=10)

    pods = core_v1.list_pod_for_all_namespaces()
    deployment_names = set()  # Usaremos un conjunto para evitar duplicados

    for pod in pods.items:
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if container_status.restart_count > 0 and container_status.state.terminated:
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
                                        deployment_name = owner.name.rsplit("-", 1)[0]  # Obtener el nombre del deployment sin el sufijo del ReplicaSet
                                        deployment_names.add(deployment_name)

    return len(deployment_names)


def get_pods_with_crashloopbackoff():
    console.log("[cyan]Counting pods in CrashLoopBackOff state...[/cyan]")
    core_v1 = client.CoreV1Api()
    pods = core_v1.list_pod_for_all_namespaces()
    count = 0
    for pod in pods.items:
        for container_status in pod.status.container_statuses or []:
            if container_status.state.waiting and container_status.state.waiting.reason == "CrashLoopBackOff":
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
                nodes_with_issues.append({
                    'name': node.metadata.name,
                    'status': condition.status,
                    'description': yaml.dump(node.to_dict())
                })
    return nodes_with_issues

def get_unusual_events():
    console.log("[cyan]Fetching unusual events from Kubernetes...[/cyan]")
    core_v1 = client.CoreV1Api()
    events = core_v1.list_event_for_all_namespaces()
    event_summary = defaultdict(lambda: {'count': 0, 'namespace': '', 'reason': '', 'first_timestamp': '', 'last_timestamp': '', 'message': ''})
    
    for event in events.items:
        if event.type != "Normal":
            key = (event.metadata.namespace, event.reason, event.message)
            event_summary[key]['count'] += 1
            event_summary[key]['namespace'] = event.metadata.namespace
            event_summary[key]['reason'] = event.reason
            event_summary[key]['message'] = event.message
            event_summary[key]['first_timestamp'] = event.first_timestamp
            event_summary[key]['last_timestamp'] = event.last_timestamp

    # Sorting events by count (descending)
    sorted_events = sorted(event_summary.values(), key=lambda x: x['count'], reverse=True)
    return sorted_events[:50]

def get_semaphore_status():
    console.log("[cyan]Fetching status of Kubernetes services...[/cyan]")
    apps_v1 = client.AppsV1Api()
    statuses = {
        'metrics_server_status': False,
        'kube_dns_status': False,
        'cast_ai_agent_status': False,
        'cast_ai_workload_autoscaler_status': False,
        'cast_ai_cluster_controller_status': False
    }
    
    # Metrics Server
    try:
        metrics_server = apps_v1.read_namespaced_deployment(name='metrics-server-v1.30.3', namespace='kube-system')
        if metrics_server.status.ready_replicas and metrics_server.status.ready_replicas > 0:
            statuses['metrics_server_status'] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching metrics-server status[/red]")

    # Kube-DNS
    try:
        kube_dns = apps_v1.read_namespaced_deployment(name='kube-dns', namespace='kube-system')
        if kube_dns.status.ready_replicas and kube_dns.status.ready_replicas > 0:
            statuses['kube_dns_status'] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching kube-dns status[/red]")

    # CAST AI Agent
    try:
        cast_ai_agent = apps_v1.read_namespaced_deployment(name='castai-agent', namespace='castai-agent')
        if cast_ai_agent.status.ready_replicas and cast_ai_agent.status.ready_replicas > 0:
            statuses['cast_ai_agent_status'] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-agent status[/red]")

    # CAST AI Workload Autoscaler
    try:
        cast_ai_workload_autoscaler = apps_v1.read_namespaced_deployment(name='castai-workload-autoscaler', namespace='castai-agent')
        if cast_ai_workload_autoscaler.status.ready_replicas and cast_ai_workload_autoscaler.status.ready_replicas > 0:
            statuses['cast_ai_workload_autoscaler_status'] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-workload-autoscaler status[/red]")

    # CAST AI Cluster Controller
    try:
        cast_ai_cluster_controller = apps_v1.read_namespaced_deployment(name='castai-cluster-controller', namespace='castai-agent')
        if cast_ai_cluster_controller.status.ready_replicas and cast_ai_cluster_controller.status.ready_replicas > 0:
            statuses['cast_ai_cluster_controller_status'] = True
    except client.exceptions.ApiException:
        console.log("[red]Error fetching castai-cluster-controller status[/red]")

    return statuses

# Function to generate gauge chart images and encode them in base64
def generate_dial_gauge_chart(value, title, min_value=0, max_value=100):
    # Calcular el porcentaje real basado en el valor y el valor máximo
    percentage = (value - min_value) / (max_value - min_value) * 100
    percentage = min(max(percentage, 0), 100)  # Limitar el porcentaje entre 0 y 100

    console.log(f"[cyan]Generating dial gauge chart for {title} with {percentage}%...[/cyan]")
    
    fig, ax = plt.subplots(figsize=(5, 2.5), subplot_kw={'aspect': 'equal'})  # Restore original figure size

    # Determine wedge parameters based on percentage
    theta = percentage / 100 * 180  # Scale to half-circle (0° to 180°)
    wedge = Wedge(center=(0, 0), r=1, theta1=0, theta2=theta, facecolor='#4CAF50' if percentage >= 80 else '#FF4444', edgecolor='black')

    # Add the wedge and background to the plot
    ax.add_patch(wedge)
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis('off')  # Hide the axes

    # Add title and percentage labels
    plt.text(0, -1.3, title, ha='center', va='center', fontsize=12)  # Restore original font size for title
    plt.text(0, 0.2, f"{percentage:.0f}%", ha='center', va='center', fontsize=14, fontweight='bold')  # Mostrar el porcentaje

    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded_image

# Function to generate line chart based on history data
def generate_line_chart(history_df):
    console.log("[cyan]Generating line chart for Kubernetes metrics over time...[/cyan]")
    if 'timestamp' not in history_df.columns:
        console.log("[red]Error: 'timestamp' column not found in history data. Cannot generate line chart.[/red]")
        return ""
    fig, ax = plt.subplots()
    history_df.plot(x='timestamp', y=['deployments_with_replicas', 'deployments_with_zero_replicas', 'pods_with_crashloopbackoff'], ax=ax)
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.title('Kubernetes Metrics Over Time')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded_image

def save_report_history(history_file, data):
    console.log("[cyan]Saving report history...[/cyan]")
    columns = ['timestamp', 'total_deployments', 'deployments_with_replicas', 'deployments_with_zero_replicas', 'deployments_with_exact_replicas', 'pods_with_crashloopbackoff', 'deployments_with_recent_start', 'nodes_with_issues']
    if not os.path.exists(history_file):
        with open(history_file, 'w') as f:
            f.write(','.join(columns) + '\n')
    with open(history_file, 'a') as f:
        f.write(f"{data['timestamp']},{data['total_deployments']},{data['deployments_with_replicas']},{data['deployments_with_zero_replicas']},{data['deployments_with_exact_replicas']},{data['pods_with_crashloopbackoff']},{data['deployments_with_recent_start']},{len(data['nodes_with_issues'])}\n")

def load_report_history(history_file):
    console.log("[cyan]Loading report history...[/cyan]")
    if not os.path.exists(history_file):
        # Return an empty DataFrame with expected columns if the history file doesn't exist
        return pd.DataFrame(columns=[
            'timestamp', 'total_deployments', 'deployments_with_replicas', 
            'deployments_with_zero_replicas', 'deployments_with_exact_replicas', 
            'pods_with_crashloopbackoff', 'deployments_with_recent_start', 'nodes_with_issues'
        ])
    return pd.read_csv(history_file)

# Convert the DataFrame to a list of dictionaries to be passed to the HTML template
def prepare_history_data_for_template(history_file):
    history_df = load_report_history(history_file)
    history_data = history_df.to_dict(orient='records')
    return history_data

# Render the HTML report
def render_html_report(template_name, context):
    console.log("[cyan]Rendering HTML report...[/cyan]")
    template = env.get_template(template_name)
    return template.render(context)

# Main script logic using Click
@click.command()
@click.option('--env-name', default='staging', help='Environment name for the report.')
@click.option('--interval', default=300, help='Interval in seconds between report generations.')
@click.option('--use-ai', is_flag=True, help='Use OpenAI to generate recommendations.')
@click.option('--git-commit', is_flag=True, help='Commit and push the generated report to Git repository.')
def cli(env_name, interval, use_ai, git_commit):
    template_name = 'report_template.html'
    docs_dir = os.path.join(os.getcwd(), 'docs')
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
        pods_with_crashloopbackoff = get_pods_with_crashloopbackoff()
        nodes_with_issues = get_nodes_with_issues()
        unusual_events = get_unusual_events()
        semaphore_statuses = get_semaphore_status()

        # Save report history
        data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_deployments': total_deployments,
            'deployments_with_replicas': deployments_with_replicas,
            'deployments_with_zero_replicas': deployments_with_zero_replicas,
            'deployments_with_recent_start': deployments_with_recent_start,
            'deployments_with_exact_replicas': deployments_with_exact_replicas,
            'pods_with_crashloopbackoff': pods_with_crashloopbackoff,
            'nodes_with_issues': nodes_with_issues
        }
        save_report_history(history_file, data)
        
        # Load history data for generating charts
        history_df = load_report_history(history_file)
        
        # Generate charts using dial gauges
        gauge_chart_deployments_with_replicas = generate_dial_gauge_chart(deployments_with_replicas, 'With Replicas', max_value=total_deployments)
        gauge_chart_deployments_zero_replicas = generate_dial_gauge_chart(deployments_with_zero_replicas, 'Zero Replicas', max_value=total_deployments)
        gauge_chart_exact_replicas = generate_dial_gauge_chart(deployments_with_exact_replicas, 'Exact Replicas', max_value=total_deployments)  # Example calculation
        gauge_chart_crashloopbackoff = generate_dial_gauge_chart(pods_with_crashloopbackoff, 'CrashLoopBackOff')
        gauge_chart_recently_restarted = generate_dial_gauge_chart(deployments_with_recent_start, 'Restarted')  # Placeholder
        line_chart_image = generate_line_chart(history_df)

        context = {
            'env_name': env_name,
            'timestamp': data['timestamp'],
            'total_deployments': total_deployments,
            'deployments_with_replicas': deployments_with_replicas,
            'deployments_with_zero_replicas': deployments_with_zero_replicas,
            'deployments_with_recent_start': deployments_with_recent_start,
            'deployments_with_exact_replicas': deployments_with_exact_replicas,
            'pods_with_crashloopbackoff': pods_with_crashloopbackoff,
            'nodes_with_issues': nodes_with_issues,
            'unusual_events': unusual_events,
            **semaphore_statuses,  # Merge semaphore statuses into the context
            'gauge_chart_deployments_with_replicas': gauge_chart_deployments_with_replicas,
            'gauge_chart_deployments_zero_replicas': gauge_chart_deployments_zero_replicas,
            'gauge_chart_exact_replicas': gauge_chart_exact_replicas,
            'gauge_chart_crashloopbackoff': gauge_chart_crashloopbackoff,
            'gauge_chart_recently_restarted': gauge_chart_recently_restarted,
            'line_chart_image': line_chart_image,
            'use_ai': use_ai,
            'history_data': prepare_history_data_for_template(history_file), 
        }
        
        # Generate HTML report
        rendered_html = render_html_report(template_name, context)
        with open(report_file, 'w') as f:
            f.write(rendered_html)
        
        console.log(f"[green]Report saved to {report_file}[/green]")
        
        # Commit and push to git if enabled
        if git_commit:
            console.log("[cyan]Committing and pushing the report to Git repository...[/cyan]")
            subprocess.run(["git", "add", report_file])
            subprocess.run(["git", "commit", "-m", f"{env_name} statistics update"])
            subprocess.run(["git", "push"])
        
        console.log(f"[green]Waiting for {interval} seconds before the next cycle...[/green]")
        time.sleep(interval)

if __name__ == "__main__":
    cli()
