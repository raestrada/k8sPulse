from kubernetes import client, config
from datetime import datetime, timezone, timedelta
import re
import pandas as pd
import numpy as np
from rich.console import Console
from collections import defaultdict

console = Console()

config.load_kube_config()


# Functions to gather Kubernetes statistics
def get_deployments_count():
    console.log("[cyan]Fetching deployments with more than 0 replicas...[/cyan]")
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = sum(
        1
        for deployment in deployments.items
        if deployment.spec.replicas and deployment.spec.replicas > 0
    )
    return count


# Function to gather deployments with at least one replica defined and at least one ready replica
def get_deployments_with_replicas():
    console.log(
        "[cyan]Counting deployments with at least one replica defined and ready...[/cyan]"
    )
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = sum(
        1
        for deployment in deployments.items
        if deployment.spec.replicas
        and deployment.spec.replicas > 0
        and deployment.status.ready_replicas
        and deployment.status.ready_replicas > 0
    )
    return count


# Function to gather deployments with at least one replica defined and exactly all replicas ready
def get_deployments_with_exact_replicas():
    console.log(
        "[cyan]Counting deployments with exactly desired replicas ready...[/cyan]"
    )
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = sum(
        1
        for deployment in deployments.items
        if deployment.spec.replicas
        and deployment.spec.replicas > 0
        and deployment.status.ready_replicas is not None
        and deployment.status.ready_replicas == deployment.spec.replicas
    )
    return count


# Function to gather deployments with zero replicas ready but with at least one replica defined
def get_deployments_with_zero_replicas():
    console.log(
        "[cyan]Counting deployments with zero ready replicas but having at least one defined...[/cyan]"
    )
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_deployment_for_all_namespaces()
    count = sum(
        1
        for deployment in deployments.items
        if deployment.spec.replicas
        and deployment.spec.replicas > 0
        and (
            not deployment.status.ready_replicas
            or deployment.status.ready_replicas == 0
        )
    )
    return count


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
    console.log(
        "[cyan]Counting deployments with pods in CrashLoopBackOff state...[/cyan]"
    )
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
                    app_label = labels.get("app") or labels.get(
                        "app.kubernetes.io/name"
                    )
                    if app_label:
                        deployments_in_crashloop.add(
                            (pod.metadata.namespace, app_label)
                        )

    # Check for matching deployments
    count = 0
    for namespace, app_label in deployments_in_crashloop:
        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        for deployment in deployments.items:
            if (
                deployment.metadata.labels.get("app") == app_label
                or deployment.metadata.labels.get("app.kubernetes.io/name") == app_label
            ):
                count += 1

    return count

# Function to gather deployments and pods by node pool using pandas and enhanced dynamic prefix analysis
import re
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
from kubernetes import client
from rich.console import Console

console = Console()
core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def get_node_pool_summary():
    console.log("[cyan]Fetching node pool summary...[/cyan]")

    # Get all nodes
    nodes = core_v1.list_node()
    node_names = [node.metadata.name for node in nodes.items]

    # Create a DataFrame to store node names
    node_df = pd.DataFrame(node_names, columns=["node_name"])

    # Extract candidate prefixes from node names
    def extract_candidate_prefixes(name):
        """Extract possible prefixes by splitting by `-` or `_` and filtering out hash-like sequences."""
        parts = re.split(r'[-_]', name)
        filtered_parts = [part for part in parts if not re.match(r'^[a-f0-9]{6,}$', part)]
        return ["-".join(filtered_parts[:i+1]) for i in range(len(filtered_parts))]

    # Generate all candidate prefixes for each node and create a flat list
    all_prefixes = []
    for name in node_names:
        all_prefixes.extend(extract_candidate_prefixes(name))

    # Create a DataFrame with prefix counts
    prefix_df = pd.DataFrame(all_prefixes, columns=["prefix"])
    prefix_counts = prefix_df["prefix"].value_counts().reset_index()
    prefix_counts.columns = ["prefix", "count"]

    # Set a tolerance to consider a prefix as valid (at least 2 occurrences or 1% of nodes)
    tolerance = max(2, len(node_names) * 0.01)
    valid_prefixes = prefix_counts[prefix_counts["count"] >= tolerance]["prefix"].tolist()

    # Assign the most appropriate valid prefix to each node
    node_pools = {}
    for _, row in node_df.iterrows():
        name = row["node_name"]
        candidate_prefixes = extract_candidate_prefixes(name)
        # Find the longest valid prefix from the candidates
        assigned_prefix = "unknown"
        for prefix in sorted(candidate_prefixes, key=len, reverse=True):
            if prefix in valid_prefixes:
                assigned_prefix = prefix
                break
        node_pools[name] = assigned_prefix

    # Initialize dictionaries to store deployment and pod counts per node pool
    deployments_per_node_pool = defaultdict(int)
    pods_per_node_pool = defaultdict(int)

    # Get all pods and determine their node pool
    pods = core_v1.list_pod_for_all_namespaces()
    pod_to_deployment = {}  # Mapping from pods to deployments

    for pod in pods.items:
        node_name = pod.spec.node_name
        if node_name and node_name in node_pools:
            node_pool = node_pools[node_name]
            pods_per_node_pool[node_pool] += 1

            # Store the deployment name for this pod if it exists
            owner_references = pod.metadata.owner_references
            if owner_references:
                for owner in owner_references:
                    if owner.kind == "ReplicaSet":
                        deployment_name = owner.name.rsplit("-", 1)[0]  # Extract deployment name from replicaset
                        pod_to_deployment[pod.metadata.name] = deployment_name

    # Get all deployments and determine their node pool using pod association
    deployments = apps_v1.list_deployment_for_all_namespaces()

    for deployment in deployments.items:
        deployment_name = deployment.metadata.name
        assigned_pool = "unknown"

        # Determine the node pool based on associated pods
        associated_pods = [pod_name for pod_name, dep_name in pod_to_deployment.items() if dep_name == deployment_name]
        associated_node_pools = [node_pools.get(pod.spec.node_name, "unknown") for pod in pods.items if pod.metadata.name in associated_pods]

        if associated_node_pools:
            # Determine the most common node pool among the associated pods
            assigned_pool = pd.Series(associated_node_pools).mode()[0]

        deployments_per_node_pool[assigned_pool] += 1

    # Output summary
    console.print("\n[bold green]Node Pool Summary:[/bold green]")
    for node_pool in set(node_pools.values()):
        console.print(
            f"[yellow]{node_pool}[/yellow]: [blue]{deployments_per_node_pool[node_pool]} deployments, {pods_per_node_pool[node_pool]} pods[/blue]"
        )

    # Return the summary data if needed elsewhere
    return {
        "deployments_per_node_pool": dict(deployments_per_node_pool),
        "pods_per_node_pool": dict(pods_per_node_pool),
    }
