import os
import requests
import yaml
from collections import defaultdict
from kubernetes import client, config
from rich.console import Console

console = Console()

# Load Kubernetes config
config.load_kube_config()


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
        metrics_server = next(
            (
                deployment
                for deployment in deployments.items
                if deployment.metadata.name.startswith("metrics-server")
            ),
            None,
        )
        if (
            metrics_server
            and metrics_server.status.ready_replicas
            and metrics_server.status.ready_replicas > 0
        ):
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

def get_latest_cast_events(limit=50):
    console.log("[cyan]Starting to fetch the latest Cast.AI events...[/cyan]")

    # Get the API key and Cluster ID from environment variables
    api_key = os.getenv("CAST_AI_API_KEY")
    cluster_id = os.getenv("CAST_AI_CLUSTER_ID")

    # Check if the API key is available
    if not api_key:
        console.log("[red]The environment variable 'CAST_AI_API_KEY' is not set. Aborting request.[/red]")
        raise ValueError("The environment variable 'CAST_AI_API_KEY' is not set.")
    
    # Check if the Cluster ID is available
    if not cluster_id:
        console.log("[red]The environment variable 'CAST_AI_CLUSTER_ID' is not set. Aborting request.[/red]")
        raise ValueError("The environment variable 'CAST_AI_CLUSTER_ID' is not set.")

    console.log(f"[green]Using cluster ID: {cluster_id}[/green]")

    # Construct the API URL
    url = f"https://api.cast.ai/v1/audit?page.limit={limit}&clusterId={cluster_id}"
    console.log(f"[blue]Constructed URL: {url}[/blue]")

    headers = {
        "accept": "application/json",
        "X-API-Key": api_key,
    }
    
    console.log("[cyan]Sending GET request to Cast.AI API...[/cyan]")

    try:
        # Make the request
        response = requests.get(url, headers=headers)

        # Log the response status code
        console.log(f"[yellow]Response status code: {response.status_code}[/yellow]")

        # Raise an HTTPError if the status code indicates an error
        response.raise_for_status()

        # Parse the response
        cast_events = response.json().get("items", [])
        
        # Log the number of events fetched
        console.log(f"[green]Successfully fetched {len(cast_events)} Cast.AI events.[/green]")

        return cast_events
    except requests.exceptions.RequestException as e:
        console.log(f"[red]Error fetching Cast.AI events: {e}[/red]")
        return []
