from kubernetes import client, config
from rich.console import Console

console = Console()

def get_cluster_resource_metrics():
    # Load the configuration from the default environment
    config.load_kube_config()
    
    # Initialize APIs
    v1 = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()  # API para obtener las métricas

    total_cpu_capacity = 0
    total_memory_capacity = 0
    total_cpu_requested = 0
    total_memory_requested = 0
    total_cpu_used = 0
    total_memory_used = 0

    nodes = v1.list_node().items
    pods = v1.list_pod_for_all_namespaces().items
    
    # Calculate the total capacity of the cluster
    console.log("[cyan]Calculating total cluster capacity...[/cyan]")
    for node in nodes:
        cpu_capacity = node.status.capacity["cpu"]
        memory_capacity = node.status.capacity["memory"]
        
        # Convert CPU to millicores
        try:
            if "m" in cpu_capacity:
                total_cpu_capacity += int(cpu_capacity.replace("m", ""))
            elif cpu_capacity.isdigit():
                total_cpu_capacity += int(cpu_capacity) * 1000  # Assuming it's in cores, convert to millicores
            else:
                console.log(f"[red]Unexpected CPU capacity value: {cpu_capacity}[/red]")

        except ValueError:
            console.log(f"[red]Invalid CPU capacity value: {cpu_capacity}[/red]")

        # Convert memory to MiB
        try:
            if "Ki" in memory_capacity:
                total_memory_capacity += int(memory_capacity.replace("Ki", "")) / 1024
            elif "Mi" in memory_capacity:
                total_memory_capacity += int(memory_capacity.replace("Mi", ""))
            elif "Gi" in memory_capacity:
                total_memory_capacity += int(memory_capacity.replace("Gi", "")) * 1024
            elif "M" in memory_capacity:
                total_memory_capacity += int(memory_capacity.replace("M", ""))  # Assuming it's in MiB
            elif memory_capacity.isdigit():
                total_memory_capacity += int(memory_capacity) / (1024 * 1024)  # Assuming it's in bytes
            else:
                console.log(f"[red]Unexpected memory capacity unit: {memory_capacity}[/red]")
        except ValueError:
            console.log(f"[red]Invalid memory capacity value: {memory_capacity}[/red]")

    # Calculate requested and used resources by all pods in the cluster
    console.log("[cyan]Calculating requested and used resources...[/cyan]")
    for pod in pods:
        for container in pod.spec.containers:
            resources = container.resources
            requests = resources.requests if resources.requests else {}
            limits = resources.limits if resources.limits else {}
            
            # Sum requested resources (requests)
            if "cpu" in requests:
                cpu_requested = requests["cpu"]
                try:
                    if "m" in cpu_requested:
                        total_cpu_requested += int(cpu_requested.replace("m", ""))
                    elif cpu_requested.isdigit():
                        total_cpu_requested += int(cpu_requested) * 1000  # Assuming it's in cores
                    else:
                        console.log(f"[red]Unexpected CPU requested value: {cpu_requested}[/red]")
                except ValueError:
                    console.log(f"[red]Invalid CPU requested value: {cpu_requested}[/red]")
            
            if "memory" in requests:
                memory_requested = requests["memory"]
                try:
                    if "Ki" in memory_requested:
                        total_memory_requested += int(memory_requested.replace("Ki", "")) / 1024
                    elif "Mi" in memory_requested:
                        total_memory_requested += int(memory_requested.replace("Mi", ""))
                    elif "Gi" in memory_requested:
                        total_memory_requested += int(memory_requested.replace("Gi", "")) * 1024
                    elif "M" in memory_requested:
                        total_memory_requested += int(memory_requested.replace("M", ""))  # Assuming it's in MiB
                    elif memory_requested.isdigit():
                        total_memory_requested += int(memory_requested) / (1024 * 1024)  # Assuming it's in bytes
                    else:
                        console.log(f"[red]Unexpected memory requested unit: {memory_requested}[/red]")
                except ValueError:
                    console.log(f"[red]Invalid memory requested value: {memory_requested}[/red]")
    
    # Attempt to retrieve usage data using Metrics API
    try:
        console.log("[cyan]Fetching real-time usage metrics from Metrics Server...[/cyan]")
        metrics = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace="default",
            plural="pods"
        )

        for pod_metric in metrics["items"]:
            for container_metric in pod_metric["containers"]:
                # CPU usage
                if "cpu" in container_metric["usage"]:
                    cpu_used = container_metric["usage"]["cpu"]
                    if "n" in cpu_used:
                        total_cpu_used += int(cpu_used.replace("n", "")) / 1e6  # Convert nanocores to millicores
                    elif "m" in cpu_used:
                        total_cpu_used += int(cpu_used.replace("m", ""))
                    elif cpu_used.isdigit():
                        total_cpu_used += int(cpu_used) * 1000  # Assuming it's in cores

                # Memory usage
                if "memory" in container_metric["usage"]:
                    memory_used = container_metric["usage"]["memory"]
                    if "Ki" in memory_used:
                        total_memory_used += int(memory_used.replace("Ki", "")) / 1024
                    elif "Mi" in memory_used:
                        total_memory_used += int(memory_used.replace("Mi", ""))
                    elif "Gi" in memory_used:
                        total_memory_used += int(memory_used.replace("Gi", "")) * 1024
                    elif "M" in memory_used:
                        total_memory_used += int(memory_used.replace("M", ""))
                    elif memory_used.isdigit():
                        total_memory_used += int(memory_used) / (1024 * 1024)
                    else:
                        console.log(f"[yellow]Unexpected memory usage unit: {memory_used}[/yellow]")
    
    except client.exceptions.ApiException as e:
        console.log(f"[yellow]Metrics server not available or error fetching metrics: {str(e)}[/yellow]")

    # Log all gathered metrics for better debugging
    console.log(f"[blue]Total CPU Capacity: {total_cpu_capacity} mcores[/blue]")
    console.log(f"[blue]Total Memory Capacity: {total_memory_capacity} MiB[/blue]")
    console.log(f"[blue]Total CPU Requested: {total_cpu_requested} mcores[/blue]")
    console.log(f"[blue]Total Memory Requested: {total_memory_requested} MiB[/blue]")
    console.log(f"[blue]Total CPU Used: {total_cpu_used} mcores[/blue]")
    console.log(f"[blue]Total Memory Used: {total_memory_used} MiB[/blue]")

    # Ensure that percentages do not exceed 100% and handle improbably low values
    total_cpu_used = min(total_cpu_used, total_cpu_capacity)
    total_cpu_requested = min(total_cpu_requested, total_cpu_capacity)
    total_memory_used = min(total_memory_used, total_memory_capacity)
    total_memory_requested = min(total_memory_requested, total_memory_capacity)

    # Create the dictionary with all metrics
    metrics = {
        "total_cpu_capacity_mcores": total_cpu_capacity,
        "total_memory_capacity_mib": total_memory_capacity,
        "total_cpu_requested_mcores": total_cpu_requested,
        "total_memory_requested_mib": total_memory_requested,
        "total_cpu_used_mcores": total_cpu_used,
        "total_memory_used_mib": total_memory_used
    }
    
    console.log("[green]Cluster resource metrics calculated successfully.[/green]")
    return metrics
