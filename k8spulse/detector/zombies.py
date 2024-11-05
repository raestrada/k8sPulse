import shutil
import subprocess
from rich.console import Console

console = Console()


def detect_zombie_processes_in_pods(interval=300):
    # Verificar si kubectl está instalado
    if not shutil.which("kubectl"):
        raise EnvironmentError("kubectl no está instalado o no se encuentra en el PATH.")

    # Definir el script bash en una variable raw
    bash_script = """
#!/bin/bash

# Colores para los logs
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[0;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# Parámetro de intervalo en segundos con valor por defecto de {interval} segundos
interval={interval}

# Obtener la fecha límite para filtrar pods
current_time=$(date +%s)
time_threshold=$((current_time - interval))

# Obtener todos los pods en estado Pending o que no están Running por más del intervalo especificado
echo -e "${{BLUE}}Obteniendo pods en estado Pending o no Running por más de $interval segundos...${{NC}}"
pods=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Running -o jsonpath='{{range .items[*]}}{{.metadata.namespace}} {{.metadata.name}} {{.status.startTime}}{{"\\n"}}{{end}}')

selected_pods=""
while IFS=$'\\n' read -r line; do
  namespace=$(echo "$line" | awk '{{print $1}}')
  pod_name=$(echo "$line" | awk '{{print $2}}')
  start_time=$(echo "$line" | awk '{{print $3}}')

  if [[ -n "$start_time" ]]; then
    # Convertir la fecha usando el formato correcto para macOS
    start_seconds=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$start_time" +%s 2>/dev/null)
    if [[ -z "$start_seconds" ]]; then
      echo -e "${{RED}}Error al convertir la fecha: $start_time${{NC}}"
      continue
    fi

    current_seconds=$(date +%s)
    diff_seconds=$((current_seconds - start_seconds))
    if (( diff_seconds > interval )); then
      selected_pods+="$namespace $pod_name\\n"
    fi
  else
    selected_pods+="$namespace $pod_name\\n"
  fi
done <<< "$pods"

if [[ -z "$selected_pods" ]]; then
  echo -e "${{GREEN}}No se encontraron pods en estado Pending o no Running por más de $interval segundos.${{NC}}"
  exit 0
fi

while IFS=$'\\n' read -r pod; do
  namespace=$(echo "$pod" | awk '{{print $1}}')
  pod_name=$(echo "$pod" | awk '{{print $2}}')
  
  if [[ -n "$namespace" && -n "$pod_name" ]]; then
    echo -e "${{YELLOW}}Verificando todos los procesos en los contenedores del pod: $pod_name en el namespace: $namespace...${{NC}}"
    
    # Obtener todos los contenedores del pod
    containers=$(kubectl get pod "$pod_name" -n "$namespace" -o jsonpath='{{.spec.containers[*].name}}')

    for container in $containers; do
      echo -e "${{BLUE}}Verificando contenedor: $container...${{NC}}"

      # Obtener la información relevante de /proc de todos los procesos y llevarla fuera para su análisis
      proc_info=$(kubectl exec -n "$namespace" -c "$container" "$pod_name" -- sh -c '
        for pid in /proc/[0-9]*; do
          if [ -f "$pid/status" ]; then
            echo "$pid"
            cat $pid/status | grep "^State:" || true
            cat $pid/status | grep "^Name:" || true
          fi
        done' 2>/dev/null)
      # Procesar la información fuera del contenedor
      echo "$proc_info" | while IFS= read -r line; do
        if [[ $line == /proc/* ]]; then
          current_pid=$line
        elif [[ $line == State:* ]]; then
          process_state=$(echo "$line" | awk '{{print $2}}')
        elif [[ $line == Name:* ]]; then
          process_name=$(echo "$line" | awk '{{print $2}}')
          
          # Si tenemos un proceso zombie, imprimimos la información
          #if [[ "$process_state" == "Z" ]]; then
            echo -e "${{RED}}Proceso zombie encontrado en el contenedor: $container del pod: $pod_name en el namespace: $namespace. PID: $current_pid, Nombre: $process_name, Estado: $process_state${{NC}}"
          #fi
        fi
      done
    done
  fi
done <<< "$(echo -e "$selected_pods")"
"""

    # Formatear el script con el valor del intervalo
    formatted_bash_script = bash_script.format(interval=interval)

    # Ejecutar el script Bash usando subprocess
    console.log("[cyan]Ejecutando script Bash para detectar procesos zombie...[/cyan]")
    result = subprocess.run(['bash', '-c', formatted_bash_script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Obtener la salida
    output = result.stdout
    errors = result.stderr

    # Manejo de errores
    if errors:
        console.log(f"[red]Errores durante la ejecución del script:[/red] {errors}")

    # Procesar la salida
    zombie_processes = []
    if output:
        for line in output.splitlines():
            if "Proceso zombie encontrado" in line:
                # Parsear la línea para extraer la información relevante
                parts = line.split(", ")
                process_info = {}
                for part in parts:
                    # Parsing each part to handle cases where there might not be enough values
                    try:
                      key, value = part.split(": ")[1].split("=", 1)
                      process_info[key.lower()] = value
                    except (ValueError, IndexError):
                      console.log("[red]Warning: Couldn't unpack part, skipping - Content: {}[/red]".format(part))

                zombie_processes.append(process_info)

    console.log(f"[green]Se encontraron {len(zombie_processes)} procesos zombies.[/green]")

    return zombie_processes
