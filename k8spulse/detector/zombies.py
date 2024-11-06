import re
import shutil
import subprocess
from rich.console import Console

console = Console()


def detect_zombie_processes_in_pods(interval=300):
    # Verify if kubectl is installed
    if not shutil.which("kubectl"):
        console.log(
            "[bold red]Error:[/bold red] kubectl is not installed or not found in PATH."
        )
        raise EnvironmentError("kubectl is not installed or not found in PATH.")

    console.log(
        "[bold blue]Starting zombie process detection in Kubernetes pods...[/bold blue]"
    )

    # Define the bash script in a raw variable
    bash_script = r"""
    #!/bin/bash

    # Interval in seconds
    interval=INTERVALPLACEHOLDER

    # Get the pods that are pending or not running for more than the specified interval
    current_time=$(date +%s)
    time_threshold=$((current_time - interval))

    pods=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Running -o jsonpath='{range .items[*]}{.metadata.namespace} {.metadata.name} {.status.startTime}{"\n"}{end}')

    selected_pods=""
    while IFS=$'\n' read -r line; do
      namespace=$(echo "$line" | awk '{print $1}')
      pod_name=$(echo "$line" | awk '{print $2}')
      start_time=$(echo "$line" | awk '{print $3}')

      if [[ -n "$start_time" ]]; then
        start_seconds=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$start_time" +%s 2>/dev/null)
        if [[ -z "$start_seconds" ]]; then
          continue
        fi

        current_seconds=$(date +%s)
        diff_seconds=$((current_seconds - start_seconds))
        if (( diff_seconds > interval )); then
          selected_pods+="$namespace $pod_name\n"
        fi
      else
        selected_pods+="$namespace $pod_name\n"
      fi
    done <<< "$pods"

    if [[ -z "$selected_pods" ]]; then
      exit 0
    fi

    while IFS=$'\n' read -r pod; do
      namespace=$(echo "$pod" | awk '{print $1}')
      pod_name=$(echo "$pod" | awk '{print $2}')

      if [[ -n "$namespace" && -n "$pod_name" ]]; then
        containers=$(kubectl get pod "$pod_name" -n "$namespace" -o jsonpath='{.spec.containers[*].name}')

        for container in $containers; do
          proc_info=$(kubectl exec -n "$namespace" -c "$container" "$pod_name" -- sh -c '
            for pid in /proc/[0-9]*; do
              if [ -f "$pid/status" ]; then
                echo "$pid"
                cat $pid/status | grep "^State:" || true
                cat $pid/status | grep "^Name:" || true
              fi
            done' 2>/dev/null)
          echo "$proc_info" | while IFS= read -r line; do
            if [[ $line == /proc/* ]]; then
              current_pid=$line
            elif [[ $line == State:* ]]; then
              process_state=$(echo "$line" | awk '{print $2}')
            elif [[ $line == Name:* ]]; then
              process_name=$(echo "$line" | awk '{print $2}')

              echo "Zombie process found: Namespace=$namespace, Pod=$pod_name, Container=$container, PID=$current_pid, Name=$process_name, State=$process_state"
            fi
          done
        done
      fi
    done <<< "$(echo -e "$selected_pods")"
    """

    console.log(
        "[bold blue]Running bash script to detect zombie processes...[/bold blue]"
    )  # Run the bash script using subprocess

    formatted_bash_script = bash_script.replace("INTERVALPLACEHOLDER", str(interval))
    result = subprocess.run(
        ["bash", "-c", formatted_bash_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Clean ANSI escape codes from the output
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    output = ansi_escape.sub("", result.stdout)

    # Run the bash script using subprocess
    result = subprocess.run(
        ["bash", "-c", bash_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Log the stderr output if there's any error
    if result.stderr:
        console.log(f"[bold red]Error:[/bold red] {result.stderr}")

    # Clean ANSI escape codes from the output
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    output = ansi_escape.sub("", result.stdout)

    # Process the cleaned output
    zombie_processes = []
    if output:
        for line in output.splitlines():
            if "Zombie process found" in line:
                # Extract relevant details
                parts = line.split(", ")
                process_info = {}
                for part in parts:
                    try:
                        key, value = part.split("=", 1)
                        process_info[key.lower().replace(" ", "_")] = value
                    except ValueError:
                        continue
                zombie_processes.append(process_info)

    # Log the detected zombie processes
    if zombie_processes:
        console.log("[bold yellow]Zombie processes detected:[/bold yellow]")
        for zp in zombie_processes:
            console.log(f"[yellow]{zp}[/yellow]")
    else:
        console.log("[bold green]No zombie processes found.[/bold green]")

    return zombie_processes
