from kubernetes import client, config
from datetime import datetime, timezone, timedelta
import time
from rich.console import Console

console = Console()

config.load_kube_config()


def detect_zombie_processes_in_pods(interval=300):
    console.log("[cyan]Detecting zombie processes in non-running pods...[/cyan]")

    # Cargar la configuración del kubeconfig
    config.load_kube_config()
    core_v1 = client.CoreV1Api()

    # Lista para almacenar la información de los procesos zombies encontrados
    zombie_processes = []

    # Obtener el tiempo actual y el límite de tiempo
    current_time = int(time.time())
    time_threshold = current_time - interval

    # Obtener todos los pods que no están en estado Running
    pods = core_v1.list_pod_for_all_namespaces(field_selector="status.phase!=Running")

    for pod in pods.items:
        start_time = pod.status.start_time
        if not start_time:
            continue

        # Convertir el tiempo de inicio del pod a segundos desde el epoch
        start_timestamp = int(start_time.replace(tzinfo=timezone.utc).timestamp())
        diff_seconds = current_time - start_timestamp

        if diff_seconds > interval:
            namespace = pod.metadata.namespace
            pod_name = pod.metadata.name
            console.log(
                f"[yellow]Checking pod: {pod_name} in namespace: {namespace}...[/yellow]"
            )

            # Obtener los contenedores del pod
            for container in pod.spec.containers:
                container_name = container.name
                console.log(f"[blue]Checking container: {container_name}...[/blue]")

                try:
                    # Ejecutar el comando para listar procesos y encontrar zombies
                    exec_command = [
                        "sh",
                        "-c",
                        "for pid in /proc/[0-9]*; do "
                        'if [ -f "$pid/status" ]; then '
                        'echo "$pid"; '
                        'cat $pid/status | grep "^State:" || true; '
                        'cat $pid/status | grep "^Name:" || true; '
                        "fi; "
                        "done",
                    ]
                    resp = core_v1.connect_get_namespaced_pod_exec(
                        name=pod_name,
                        namespace=namespace,
                        container=container_name,
                        command=exec_command,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )

                    # Procesar la salida para detectar procesos zombies
                    current_pid = None
                    for line in resp.splitlines():
                        if line.startswith("/proc/"):
                            current_pid = line
                        elif line.startswith("State:"):
                            process_state = line.split()[1]
                        elif line.startswith("Name:"):
                            process_name = line.split()[1]
                            # Si el proceso es zombie, agregar la información a la lista
                            if process_state == "Z":
                                console.log(
                                    f"[red]Zombie process found in container: {container_name} of pod: {pod_name} "
                                    f"in namespace: {namespace}. PID: {current_pid}, Name: {process_name}, State: {process_state}[/red]"
                                )
                                zombie_processes.append(
                                    {
                                        "namespace": namespace,
                                        "pod_name": pod_name,
                                        "container_name": container_name,
                                        "process_name": process_name,
                                    }
                                )

                except client.exceptions.ApiException as e:
                    console.log(
                        f"[red]Error executing command in pod: {pod_name}, container: {container_name}. Error: {e}[/red]"
                    )

    return zombie_processes
