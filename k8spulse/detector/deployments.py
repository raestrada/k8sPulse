from kubernetes import client, config
from datetime import datetime, timezone, timedelta
import time
from rich.console import Console

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
