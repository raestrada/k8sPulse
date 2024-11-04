#!/bin/bash

# Functions to display colors in logs
red() {
  tput setaf 1; echo "$1"; tput sgr0
}
green() {
  tput setaf 2; echo "$1"; tput sgr0
}
yellow() {
  tput setaf 3; echo "$1"; tput sgr0
}
blue() {
  tput setaf 4; echo "$1"; tput sgr0
}

# Check if necessary tools are installed
check_dependencies() {
  local dependencies=("git" "yq" "jq" "awk" "sort" "uniq")

  for cmd in "${dependencies[@]}"; do
    if ! command -v $cmd &> /dev/null; then
      red "Error: $cmd is not installed. Please install $cmd to continue."
      exit 1
    fi
  done
}

# Check if the --git-commit argument is present
# Default values
GIT_COMMIT=false
ENV_NAME="staging"
INTERVAL=300
USE_AI=false

# Parse arguments
for arg in "$@"; do
  if [ "$arg" == "--git-commit" ]; then
    GIT_COMMIT=true
  elif [[ "$arg" == --env-name=* ]]; then
    ENV_NAME="${arg#*=}"
  elif [[ "$arg" == --interval=* ]]; then
    INTERVAL="${arg#*=}"
  elif [ "$arg" == "--use-ai" ]; then
    USE_AI=true
  fi
done

# HTML report file
REPORT_FILE="${ENV_NAME}_statistics.html"
# Rotating history file
HISTORY_FILE="${ENV_NAME}_statistics_history.log"

# Infinite loop running every five minutes
while true; do
  # Get all deployments and calculate the total
  total_deployments=$(kubectl get deployments --all-namespaces | tail -n +2 | wc -l)
  if [ -z "$total_deployments" ]; then
    red "Error fetching deployments. Check that kubectl is properly configured."
    sleep 300
    continue
  fi
  blue "Total deployments: $total_deployments"

  # Count deployments with at least one ready replica
  deployments_with_replicas=$(kubectl get deployments --all-namespaces | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); if (a[1] > 0) count++} END {print count}')
  if [ -z "$deployments_with_replicas" ]; then
    deployments_with_replicas=0
  fi
  green "Deployments with at least one replica: $deployments_with_replicas"

  # Count deployments with zero ready replicas
  deployments_with_zero_replicas=$(kubectl get deployments --all-namespaces | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); if (a[1] == 0) count++} END {print count}')
  if [ -z "$deployments_with_zero_replicas" ]; then
    deployments_with_zero_replicas=0
  fi
  red "Deployments with zero replicas: $deployments_with_zero_replicas"

  # Count deployments with the exact number of desired replicas
  deployments_with_exact_replicas=$(kubectl get deployments --all-namespaces | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); if (a[1] == a[2]) count++} END {print count}')
  if [ -z "$deployments_with_exact_replicas" ]; then
    deployments_with_exact_replicas=0
  fi
  yellow "Deployments with desired number of replicas: $deployments_with_exact_replicas"

  # Count pods in CrashLoopBackOff state
  pods_with_crashloopbackoff=$(kubectl get pods --all-namespaces | grep -c 'CrashLoopBackOff')
  if [ -z "$pods_with_crashloopbackoff" ]; then
    pods_with_crashloopbackoff=0
  fi
  yellow "Pods in CrashLoopBackOff state: $pods_with_crashloopbackoff"

  # Get the total number of pods
  total_pods=$(kubectl get pods --all-namespaces | tail -n +2 | wc -l)
  if [ -z "$total_pods" ]; then
    total_pods=0
  fi
  blue "Total pods: $total_pods"

  # Count pods that restarted recently (less than 10 minutes)
  pods_recently_restarted=$(kubectl get pods --all-namespaces | grep -oE '\([0-9]+m[0-9]*s? ago\)|\([0-9]+s ago\)' | awk -F'[ms]' '{minutes=$1; seconds=$2; if (minutes == "" && seconds < 600) count++; else if (minutes != "" && minutes < 10) count++} END {print count}')
  if [ -z "$pods_recently_restarted" ]; then
    pods_recently_restarted=0
  fi
  blue "Pods restarted less than 10 minutes ago: $pods_recently_restarted"

  # Check if metrics-server has at least one replica up
  metrics_server_replicas=$(kubectl get deployment metrics-server-v1.30.3 -n kube-system | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); print a[1]}')
  if [ -z "$metrics_server_replicas" ] || [ "$metrics_server_replicas" -eq 0 ]; then
    metrics_server_replicas=0
  else
    metrics_server_replicas=1
  fi
  green "Metrics-server with at least one replica: $metrics_server_replicas"

  # Check if kube-dns has at least one replica up
  kube_dns_replicas=$(kubectl get deployment kube-dns -n kube-system | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); print a[1]}')
  if [ -z "$kube_dns_replicas" ] || [ "$kube_dns_replicas" -eq 0 ]; then
    kube_dns_replicas=0
  else
    kube_dns_replicas=1
  fi
  green "Kube-dns with at least one replica: $kube_dns_replicas"

  # Check if castai-agent has at least one replica up
  castai_agent_replicas=$(kubectl get deployment castai-agent -n castai-agent | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); print a[1]}')
  if [ -z "$castai_agent_replicas" ] || [ "$castai_agent_replicas" -eq 0 ]; then
    castai_agent_replicas=0
  else
    castai_agent_replicas=1
  fi
  green "CAST AI Agent with at least one replica: $castai_agent_replicas"

  # Check if castai-workload-autoscaler has at least one replica up
  castai_workload_autoscaler_replicas=$(kubectl get deployment castai-workload-autoscaler -n castai-agent | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); print a[1]}')
  if [ -z "$castai_workload_autoscaler_replicas" ] || [ "$castai_workload_autoscaler_replicas" -eq 0 ]; then
    castai_workload_autoscaler_replicas=0
  else
    castai_workload_autoscaler_replicas=1
  fi
  green "CAST AI Workload Autoscaler with at least one replica: $castai_workload_autoscaler_replicas"

  # Check if castai-cluster-controller has at least one replica up
  castai_cluster_controller_replicas=$(kubectl get deployment castai-cluster-controller -n castai-agent | tail -n +2 | awk '{print $3}' | awk '{split($1, a, "/"); print a[1]}')
  if [ -z "$castai_cluster_controller_replicas" ] || [ "$castai_cluster_controller_replicas" -eq 0 ]; then
    castai_cluster_controller_replicas=0
  else
    castai_cluster_controller_replicas=1
  fi
  green "CAST AI Cluster Controller with at least one replica: $castai_cluster_controller_replicas"

  # Percentage calculations (rounding to avoid formatting issues with commas)
  percentage_with_replicas=$(awk -v a="$deployments_with_replicas" -v b="$total_deployments" 'BEGIN { printf "%d", (b > 0 ? (a/b)*100 : 0) }')
  percentage_with_zero_replicas=$(awk -v a="$deployments_with_zero_replicas" -v b="$total_deployments" 'BEGIN { printf "%d", (b > 0 ? (a/b)*100 : 0) }')
  percentage_with_exact_replicas=$(awk -v a="$deployments_with_exact_replicas" -v b="$total_deployments" 'BEGIN { printf "%d", (b > 0 ? (a/b)*100 : 0) }')
  percentage_with_crashloopbackoff=$(awk -v a="$pods_with_crashloopbackoff" -v b="$total_pods" 'BEGIN { printf "%d", (b > 0 ? (a/b)*100 : 0) }')
  percentage_recently_restarted=$(awk -v a="$pods_recently_restarted" -v b="$total_pods" 'BEGIN { printf "%d", (b > 0 ? (a/b)*100 : 0) }')
  percentage_metrics_server=$(awk -v a="$metrics_server_replicas" 'BEGIN { printf "%d", (a > 0 ? 100 : 100) }')
  percentage_kube_dns=$(awk -v a="$kube_dns_replicas" 'BEGIN { printf "%d", (a > 0 ? 100 : 100) }')

  green "Saving log history $HISTORY_FILE ..."
  # Save the current state in the rotating history file
  echo "$(date +%Y-%m-%dT%H:%M:%S)|$total_deployments|$deployments_with_replicas|$percentage_with_replicas|$deployments_with_zero_replicas|$percentage_with_zero_replicas|$deployments_with_exact_replicas|$percentage_with_exact_replicas|$pods_with_crashloopbackoff|$percentage_with_crashloopbackoff|$pods_recently_restarted|$percentage_recently_restarted|$metrics_server_replicas|$percentage_metrics_server|$kube_dns_replicas|$percentage_kube_dns" >> "$HISTORY_FILE"

  green "Rotating log hisdtory ..."
   # Keep only the last 24 hours of logs (288 lines, one every five minutes)
  tail -n 288 "$HISTORY_FILE" > "$HISTORY_FILE.tmp" && mv "$HISTORY_FILE.tmp" "$HISTORY_FILE"

  green "Generate report ..."

  # Crear el reporte HTML utilizando printf
  printf "<html>\n<head>\n<title>%s Statistics</title>\n<style>\n" "$ENV_NAME" > "$REPORT_FILE"
  printf "body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; padding: 20px; }\n" >> "$REPORT_FILE"
  printf "h2 { color: #4caf50; }\n" >> "$REPORT_FILE"
  printf ".card { background: #fff; padding: 20px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 8px; }\n" >> "$REPORT_FILE"
  printf ".gauge-row, .chart-container { display: flex; gap: 20px; justify-content: space-around; margin-top: 20px; }\n" >> "$REPORT_FILE"
  printf ".gauge-container { text-align: center; }\n" >> "$REPORT_FILE"
  printf ".chart { text-align: center; display: inline-block; margin: 20px; }\n" >> "$REPORT_FILE"
  printf "table { width: 100%%; border-collapse: collapse; margin-top: 20px; }\n" >> "$REPORT_FILE"
  printf "th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }\n" >> "$REPORT_FILE"
  printf "th { background-color: #4caf50; color: white; }\n" >> "$REPORT_FILE"
  printf ".events { max-height: 400px; overflow-y: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 20px; }\n" >> "$REPORT_FILE"
  printf ".event { margin-bottom: 10px; padding: 10px; border-radius: 5px; }\n" >> "$REPORT_FILE"
  printf ".event-warning { background-color: #fff3cd; color: #856404; }\n" >> "$REPORT_FILE"
  printf ".event-error { background-color: #f8d7da; color: #721c24; }\n" >> "$REPORT_FILE"
  printf ".status-indicator { width: 20px; height: 20px; border-radius: 50%%; display: inline-block; margin-right: 10px; }\n" >> "$REPORT_FILE"
  printf ".status-ok { background-color: green; }\n" >> "$REPORT_FILE"
  printf ".status-error { background-color: red; }\n" >> "$REPORT_FILE"
  printf "</style>\n<meta http-equiv=\"refresh\" content=\"60\">\n</head>\n<body>\n" >> "$REPORT_FILE"

  # Refresh timer and header
  printf "<h2>%s Statistics</h2>\n" "$ENV_NAME" >> "$REPORT_FILE"

  # Script para generar gráficos de Google
  printf "<script type=\"text/javascript\" src=\"https://www.gstatic.com/charts/loader.js\"></script>\n" >> "$REPORT_FILE"
  printf "<script type=\"text/javascript\">\n" >> "$REPORT_FILE"
  printf "google.charts.load('current', {packages:['gauge']});\n" >> "$REPORT_FILE"
  printf "google.charts.setOnLoadCallback(drawGauges);\n\n" >> "$REPORT_FILE"
  printf "function drawGauges() {\n" >> "$REPORT_FILE"
  printf "  var options_replicas = { width: 120, height: 120, minorTicks: 5, greenFrom: 70, greenTo: 100, yellowFrom: 40, yellowTo: 70, redFrom: 0, redTo: 40 };\n" >> "$REPORT_FILE"
  printf "  var options_other = { width: 120, height: 120, minorTicks: 5, greenFrom: 0, greenTo: 20, yellowFrom: 20, yellowTo: 70, redFrom: 70, redTo: 100 };\n\n" >> "$REPORT_FILE"
  printf "  var dataWithReplicas = google.visualization.arrayToDataTable([\n" >> "$REPORT_FILE"
  printf "    ['Label', 'Value'],\n" >> "$REPORT_FILE"
  printf "    ['With Replica', %d]\n" "$percentage_with_replicas" >> "$REPORT_FILE"
  printf "  ]);\n" >> "$REPORT_FILE"
  printf "  var dataZeroReplicas = google.visualization.arrayToDataTable([\n" >> "$REPORT_FILE"
  printf "    ['Label', 'Value'],\n" >> "$REPORT_FILE"
  printf "    ['No Replica', %d]\n" "$percentage_with_zero_replicas" >> "$REPORT_FILE"
  printf "  ]);\n" >> "$REPORT_FILE"
  printf "  var dataExactReplicas = google.visualization.arrayToDataTable([\n" >> "$REPORT_FILE"
  printf "    ['Label', 'Value'],\n" >> "$REPORT_FILE"
  printf "    ['Exact', %d]\n" "$percentage_with_exact_replicas" >> "$REPORT_FILE"
  printf "  ]);\n" >> "$REPORT_FILE"
  printf "  var dataCrashLoop = google.visualization.arrayToDataTable([\n" >> "$REPORT_FILE"
  printf "    ['Label', 'Value'],\n" >> "$REPORT_FILE"
  printf "    ['CrashLoop', %d]\n" "$percentage_with_crashloopbackoff" >> "$REPORT_FILE"
  printf "  ]);\n" >> "$REPORT_FILE"
  printf "  var dataRecentlyRestarted = google.visualization.arrayToDataTable([\n" >> "$REPORT_FILE"
  printf "    ['Label', 'Value'],\n" >> "$REPORT_FILE"
  printf "    ['Restarted', %d]\n" "$percentage_recently_restarted" >> "$REPORT_FILE"
  printf "  ]);\n\n" >> "$REPORT_FILE"
  printf "  var gaugeWithReplicas = new google.visualization.Gauge(document.getElementById('gauge_with_replicas'));\n" >> "$REPORT_FILE"
  printf "  gaugeWithReplicas.draw(dataWithReplicas, options_replicas);\n\n" >> "$REPORT_FILE"
  printf "  var gaugeZeroReplicas = new google.visualization.Gauge(document.getElementById('gauge_zero_replicas'));\n" >> "$REPORT_FILE"
  printf "  gaugeZeroReplicas.draw(dataZeroReplicas, options_other);\n\n" >> "$REPORT_FILE"
  printf "  var gaugeExactReplicas = new google.visualization.Gauge(document.getElementById('gauge_exact_replicas'));\n" >> "$REPORT_FILE"
  printf "  gaugeExactReplicas.draw(dataExactReplicas, options_replicas);\n\n" >> "$REPORT_FILE"
  printf "  var gaugeCrashLoop = new google.visualization.Gauge(document.getElementById('gauge_crashloop'));\n" >> "$REPORT_FILE"
  printf "  gaugeCrashLoop.draw(dataCrashLoop, options_other);\n\n" >> "$REPORT_FILE"
  printf "  var gaugeRecentlyRestarted = new google.visualization.Gauge(document.getElementById('gauge_recently_restarted'));\n" >> "$REPORT_FILE"
  printf "  gaugeRecentlyRestarted.draw(dataRecentlyRestarted, options_other);\n" >> "$REPORT_FILE"
  printf "}\n" >> "$REPORT_FILE"
  printf "</script>\n</head>\n<body>\n" >> "$REPORT_FILE"

  # Añadir la fila de gauges al reporte HTML
  printf "<div class='gauge-row'>\n" >> "$REPORT_FILE"

  green "Generate Gauges ..."

  # Añadir los indicadores de estado y su estado correspondiente
  printf "<div class='status-container'>\n" >> "$REPORT_FILE"
  printf "<div class='status-box'><div class='status-indicator %s'></div>Metrics-server: %s</div>\n" "$(awk -v a="$metrics_server_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')" "$(awk -v a="$metrics_server_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')" >> "$REPORT_FILE"
  printf "<div class='status-box'><div class='status-indicator %s'></div>Kube-dns: %s</div>\n" "$(awk -v a="$kube_dns_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')" "$(awk -v a="$kube_dns_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')" >> "$REPORT_FILE"
  printf "<div class='status-box'><div class='status-indicator %s'></div>CAST AI Agent: %s</div>\n" "$(awk -v a="$castai_agent_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')" "$(awk -v a="$castai_agent_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')" >> "$REPORT_FILE"
  printf "<div class='status-box'><div class='status-indicator %s'></div>CAST AI Workload Autoscaler: %s</div>\n" "$(awk -v a="$castai_workload_autoscaler_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')" "$(awk -v a="$castai_workload_autoscaler_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')" >> "$REPORT_FILE"
  printf "<div class='status-box'><div class='status-indicator %s'></div>CAST AI Cluster Controller: %s</div>\n" "$(awk -v a="$castai_cluster_controller_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')" "$(awk -v a="$castai_cluster_controller_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')" >> "$REPORT_FILE"
  printf "</div>\n" >> "$REPORT_FILE"

  # Añadir contenedores de gauge con sus valores
  printf "<div class='gauge-container'><div id='gauge_with_replicas'></div><div>With Replica: %d (%d%%)</div></div>\n" "$deployments_with_replicas" "$percentage_with_replicas" >> "$REPORT_FILE"
  printf "<div class='gauge-container'><div id='gauge_zero_replicas'></div><div>No Replica: %d (%d%%)</div></div>\n" "$deployments_with_zero_replicas" "$percentage_with_zero_replicas" >> "$REPORT_FILE"
  printf "<div class='gauge-container'><div id='gauge_exact_replicas'></div><div>Exact: %d (%d%%)</div></div>\n" "$deployments_with_exact_replicas" "$percentage_with_exact_replicas" >> "$REPORT_FILE"
  printf "<div class='gauge-container'><div id='gauge_crashloop'></div><div>CrashLoop: %d (%d%%)</div></div>\n" "$pods_with_crashloopbackoff" "$percentage_with_crashloopbackoff" >> "$REPORT_FILE"
  printf "<div class='gauge-container'><div id='gauge_recently_restarted'></div><div>Restarted: %d (%d%%)</div></div>\n" "$pods_recently_restarted" "$percentage_recently_restarted" >> "$REPORT_FILE"

  # Cerrar la fila de gauges
  printf "</div>\n" >> "$REPORT_FILE"

  # Añadir el placeholder de OpenAI si USE_AI es verdadero
  if [ "$USE_AI" = true ]; then
    printf "\n<div id='openai-recommendation-placeholder'></div>\n" >> "$REPORT_FILE"
  fi

  blue "Generating events ..."
  # Contenedor para eventos y problemas de nodos
  printf "<div class='events-nodes-container' style='display: flex; gap: 20px; width: 100%%; align-items: flex-start;'>\n" >> "$REPORT_FILE"

  # Sección de eventos
  printf "<div class='events' style='flex: 1; max-height: 400px; overflow-y: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><h3>Unusual Events</h3>\n" >> "$REPORT_FILE"

  unusual_events=$(kubectl get events --all-namespaces | \
    grep -v -E "^NAMESPACE|Normal" | \
    awk '{print $1, $2, $5, $6, substr($0, index($0,$7))}' | \
    sort -k4,4 -k5,5 | \
    awk '!seen[$4,$5]++ {count[$4,$5] = 1; time[$4,$5] = $2; namespace[$4,$5] = $4; kind[$4,$5] = $5; first_col[$4,$5] = $1; rest[$4,$5] = substr($0, index($0,$7))} seen[$4,$5]++ {count[$4,$5]++} \
    END {for (key in count) print count[key], time[key], namespace[key], kind[key], first_col[key], rest[key]}' | \
    sort -k1,1nr | \
    awk '{print "[" $1 "] [" $2 "] [" $3 "] [" $4 "] [" $5 "] " substr($0, index($0,$6))}' | \
    head -50)
  
  green "Events read ..."

  # Procesar eventos inusuales
  if [ -z "$unusual_events" ]; then
    printf "<div class='event' style='color:red;'>No unusual events found.</div>\n" >> "$REPORT_FILE"
  else
    while IFS= read -r event; do 
      count=$(echo "$event" | awk '{print $1}' | tr -d '[]')
      time=$(echo "$event" | awk '{print $2}' | tr -d '[]')
      kind=$(echo "$event" | awk '{print $3}' | tr -d '[]')
      first_col=$(echo "$event" | awk '{print $4}' | tr -d '[]')
      namespace=$(echo "$event" | awk '{print $5}' | tr -d '[]')
      message=$(echo "$event" | cut -d' ' -f6-)
      event_class="event event-$(echo $kind | tr '[:upper:]' '[:lower:]')"
      color=""
      case "$kind" in
        "Warning") color="red" ;;
        "Normal") color="green" ;;
        "Failed") color="orange" ;;
        "SuccessfulCreate") color="blue" ;;
        *) color="purple" ;;
      esac
      printf "<div class='%s' style='border: 2px solid %s; padding: 10px; margin: 5px; background-color: #f0f0f0;'>\n" "$event_class" "$color" >> "$REPORT_FILE"
      printf "<strong style='color: %s;'>[%s]</strong> <strong>[%s]</strong> <span style='font-weight: bold;'>(%s times)</span> <em>[%s]</em>: <em>%s</em>\n" "$color" "$kind" "$namespace" "$count" "$time" "$message" >> "$REPORT_FILE"
      printf "<br><small>First occurrence: [%s]</small>\n" "$first_col" >> "$REPORT_FILE"
      printf "</div>\n" >> "$REPORT_FILE"
    done <<< "$unusual_events"
  fi

  # Cerrar la sección de eventos
  printf "</div>\n" >> "$REPORT_FILE"


  blue "Get nodes ..."

  # Añadir la sección de nodos con problemas al reporte HTML
  printf "<div class='nodes' style='flex: 1; max-height: 400px; overflow-y: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><h3>Nodes with Issues</h3>\n" >> "$REPORT_FILE"
  nodes_with_issues=$(kubectl get nodes --no-headers | awk '$2 != "Ready" {print $1, $2}')
  if [ -z "$nodes_with_issues" ]; then
    printf "<div class='event' style='color:green;'>All nodes are healthy.</div>\n" >> "$REPORT_FILE"
  else
    while IFS= read -r node_issue; do
      node_name=$(echo "$node_issue" | awk '{print $1}')
      node_status=$(echo "$node_issue" | awk '{print $2}')

      # Obtener la descripción detallada del nodo en formato YAML y filtrar secciones no deseadas con yq
      node_description=$(kubectl get node "$node_name" -o yaml | yq 'del(.metadata.labels, .metadata.annotations, .metadata.creationTimestamp)')

      printf "<div class='event' style='border: 2px solid red; padding: 10px; margin: 5px; background-color: #f0f0f0;'>\n" >> "$REPORT_FILE"
      printf "<strong style='color: red;'>Node: [%s]</strong> - Status: <em>%s</em>\n" "$node_name" "$node_status" >> "$REPORT_FILE"

      # Botón para colapsar/expandir la descripción del nodo
      printf "<button onclick='toggleDescription(\"%s\")' style='margin-right: 10px; background: none; border: none; font-size: 1.2em; cursor: pointer;'>▶</button>\n" "$node_name" >> "$REPORT_FILE"

      # Agregar la descripción filtrada del nodo en un div colapsable, utilizando highlight.js para el formato
      printf "<div id='desc-%s' class='node-description' style='display: none; margin-top: 10px; padding: 10px; background-color: #e9e9e9; border-radius: 5px; font-size: 0.9em;'>\n" "$node_name" >> "$REPORT_FILE"
      printf "<pre><code class='yaml'>%s</code></pre>\n" "$node_description" >> "$REPORT_FILE"
      printf "</div>\n" >> "$REPORT_FILE"

      printf "</div>\n" >> "$REPORT_FILE"
    done <<< "$nodes_with_issues"
  fi

  # Cerrar la sección de nodos
  printf "</div>\n" >> "$REPORT_FILE"

  # Añadir el script JavaScript para colapsar/expandir la descripción del nodo
  printf "<script>\n" >> "$REPORT_FILE"
  printf "function toggleDescription(nodeId) {\n" >> "$REPORT_FILE"
  printf "  var descElement = document.getElementById('desc-' + nodeId);\n" >> "$REPORT_FILE"
  printf "  var buttonElement = descElement.previousElementSibling;\n" >> "$REPORT_FILE"
  printf "  if (descElement.style.display === 'none') {\n" >> "$REPORT_FILE"
  printf "    descElement.style.display = 'block';\n" >> "$REPORT_FILE"
  printf "    buttonElement.innerHTML = '▼'; // Cambiar el icono cuando se expande\n" >> "$REPORT_FILE"
  printf "  } else {\n" >> "$REPORT_FILE"
  printf "    descElement.style.display = 'none';\n" >> "$REPORT_FILE"
  printf "    buttonElement.innerHTML = '▶'; // Cambiar el icono cuando se colapsa\n" >> "$REPORT_FILE"
  printf "  }\n" >> "$REPORT_FILE"
  printf "}\n" >> "$REPORT_FILE"
  printf "</script>\n" >> "$REPORT_FILE"

  # Incluir highlight.js para resaltar el YAML con colores
  printf "<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.1/styles/default.min.css'>\n" >> "$REPORT_FILE"
  printf "<script src='https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.1/highlight.min.js'></script>\n" >> "$REPORT_FILE"
  printf "<script>hljs.highlightAll();</script>\n" >> "$REPORT_FILE"

  # Cerrar el contenedor de eventos y nodos
  printf "</div>\n" >> "$REPORT_FILE"

  green "Generate line charts ..."

  # Read the history file and prepare the data for the chart, limiting to a maximum of 100 points
  timestamps_series=()
  deployments_with_replicas_percentage_series=()
  deployments_with_zero_replicas_percentage_series=()
  deployments_with_exact_replicas_percentage_series=()
  pods_with_crashloopbackoff_percentage_series=()
  pods_recently_restarted_percentage_series=()
  metrics_server_percentage_series=()
  kube_dns_percentage_series=()

  count=0
  step=1

  # Read all lines and determine the step if there are more than 100 records
  total_lines=$(wc -l < "$HISTORY_FILE")
  if [ "$total_lines" -gt 100 ]; then
    step=$((total_lines / 100))
  fi

  # Build the data series
  while IFS='|' read -r timestamp total with_replicas percentage_with_replicas without_replicas percentage_without_replicas exact_replicas percentage_exact_replicas crashloopbackoff percentage_crashloopbackoff recently_restarted percentage_recently_restarted metrics_server metrics_server_percentage kube_dns kube_dns_percentage; do
    if (( count % step == 0 )); then
      timestamps_series+=("$timestamp")
      deployments_with_replicas_percentage_series+=("$percentage_with_replicas")
      deployments_with_zero_replicas_percentage_series+=("$percentage_without_replicas")
      deployments_with_exact_replicas_percentage_series+=("$percentage_exact_replicas")
      pods_with_crashloopbackoff_percentage_series+=("$percentage_crashloopbackoff")
      pods_recently_restarted_percentage_series+=("$percentage_recently_restarted")
      metrics_server_percentage_series+=($(awk -v val="$metrics_server_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : int(val)}'))
      kube_dns_percentage_series+=($(awk -v val="$kube_dns_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : int(val)}'))
    fi
    count=$((count + 1))
  done < "$HISTORY_FILE"

  green "Data series  built ..."

  # Limit the series to a maximum of 100 values
  timestamps_series="${timestamps_series[*]:0:100}"
  deployments_with_replicas_percentage_series="${deployments_with_replicas_percentage_series[*]:0:100}"
  deployments_with_zero_replicas_percentage_series="${deployments_with_zero_replicas_percentage_series[*]:0:100}"
  deployments_with_exact_replicas_percentage_series="${deployments_with_exact_replicas_percentage_series[*]:0:100}"
  pods_with_crashloopbackoff_percentage_series="${pods_with_crashloopbackoff_percentage_series[*]:0:100}"
  pods_recently_restarted_percentage_series="${pods_recently_restarted_percentage_series[*]:0:100}"
  metrics_server_percentage_series="${metrics_server_percentage_series[*]:0:100}"
  kube_dns_percentage_series="${kube_dns_percentage_series[*]:0:100}"

  # Replace spaces with commas to generate the final series
  deployments_with_replicas_percentage_series=$(echo "${deployments_with_replicas_percentage_series[*]}" | tr ' ' ',')
  deployments_with_zero_replicas_percentage_series=$(echo "${deployments_with_zero_replicas_percentage_series[*]}" | tr ' ' ',')
  deployments_with_exact_replicas_percentage_series=$(echo "${deployments_with_exact_replicas_percentage_series[*]}" | tr ' ' ',')
  pods_with_crashloopbackoff_percentage_series=$(echo "${pods_with_crashloopbackoff_percentage_series[*]}" | tr ' ' ',')
  pods_recently_restarted_percentage_series=$(echo "${pods_recently_restarted_percentage_series[*]}" | tr ' ' ',')
  metrics_server_percentage_series=$(echo "${metrics_server_percentage_series[*]}" | tr ' ' ',')
  kube_dns_percentage_series=$(echo "${kube_dns_percentage_series[*]}" | tr ' ' ',')

  # Reduce the number of X-axis labels to keep it clean
  # We’ll select only 5 representative dates for the X-axis
  timestamps_sample=$(echo $timestamps_series | tr ' ' ',' | awk -F, '{for (i=1; i<=NF; i+=int(NF/5)) printf "%s|", $i; if (NF > 0) print $NF}')

  # Generate the URL for the line chart with Image Charts
  chart_url="https://image-charts.com/chart?cht=lc&chs=600x300&chd=t:$deployments_with_replicas_percentage_series|$deployments_with_zero_replicas_percentage_series|$deployments_with_exact_replicas_percentage_series|$pods_with_crashloopbackoff_percentage_series|$pods_recently_restarted_percentage_series&chco=4CAF50,FF4444,FFA500,42A5F5,FFBB33&chxt=x,y&chxl=0:|$timestamps_sample&chdl=With+Replica|No+Replica|Exact|CrashLoopBackOff|Recently+Restarted&chdlp=b&chg=5,10"
  # Generate the URL for the line chart with Image Charts only for "With Replica"
  chart_url_2="https://image-charts.com/chart?cht=lc&chs=500x300&chd=t:$deployments_with_replicas_percentage_series&chco=4CAF50&chxt=x,y&chxl=0:|$timestamps_sample&chdl=With+Replica&chdlp=b&chg=5,10"
  # Generate the URL for the line chart with Image Charts only for "Metrics-server and Kube-dns"
  chart_url_3="https://image-charts.com/chart?cht=lc&chs=500x300&chd=t:$metrics_server_percentage_series,$kube_dns_percentage_series&chco=00FF00,0000FF&chxt=x,y&chxl=0:|$timestamps_sample&chdl=Metrics-server|Kube-dns&chdlp=b&chg=5,10"

  # Generate chart with Image Charts
  chart_urls=(
    "$chart_url"
    "$chart_url_2"
    "$chart_url_3"
  )

  green "Add charts to repoert ..."

  green "Add charts to report ..."

  # Añadir gráficos al reporte
  printf "<div class='chart-container'>\n" >> "$REPORT_FILE"
  for chart_url in "${chart_urls[@]}"; do
    printf "<div class='chart'><img src='%s' alt='Deployment and Pod Statistics'></div>\n" "$chart_url" >> "$REPORT_FILE"
  done
  printf "</div>\n" >> "$REPORT_FILE"

  green "Generate History Table ..."

  # Añadir tabla de historial al reporte
  printf "<h3>Last 24-Hour History</h3>\n" >> "$REPORT_FILE"
  printf "<table><tr><th>Time</th><th>Total Deployments</th><th>With Replica</th><th>No Replica</th><th>Exactly Desired</th><th>CrashLoopBackOff</th><th>Recently Restarted</th><th>Metrics-server</th><th>Kube-dns</th></tr>\n" >> "$REPORT_FILE"

  # Crear un archivo temporal para almacenar el historial en orden inverso
  temp_file=$(mktemp)

  # Volcar el contenido en orden inverso en el archivo temporal
  tail -r "$HISTORY_FILE" > "$temp_file"

  # Leer el archivo temporal y generar la tabla HTML
  while IFS='|' read -r timestamp total with_replicas percentage_with_replicas without_replicas percentage_without_replicas exact_replicas percentage_exact_replicas crashloopbackoff percentage_crashloopbackoff recently_restarted percentage_recently_restarted metrics_server metrics_server_percentage kube_dns kube_dns_percentage; do
    metrics_server_percentage=$(awk -v val="$metrics_server_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : val}')
    kube_dns_percentage=$(awk -v val="$kube_dns_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : val}')
    printf "<tr><td>%s</td><td>%s</td><td>%s (%s%%)</td><td>%s (%s%%)</td><td>%s (%s%%)</td><td>%s (%s%%)</td><td>%s (%s%%)</td><td>%s (%s%%)</td><td>%s (%s%%)</td></tr>\n" \
      "$timestamp" "$total" "$with_replicas" "$percentage_with_replicas" "$without_replicas" "$percentage_without_replicas" "$exact_replicas" "$percentage_exact_replicas" \
      "$crashloopbackoff" "$percentage_crashloopbackoff" "$recently_restarted" "$percentage_recently_restarted" "$metrics_server" "$metrics_server_percentage" "$kube_dns" "$kube_dns_percentage" >> "$REPORT_FILE"
  done < "$temp_file"

  # Eliminar el archivo temporal
  rm "$temp_file"

  printf "</table>\n" >> "$REPORT_FILE"

  # Guardar reporte en el archivo HTML
  green "Report saved to $REPORT_FILE"


  if [ "$USE_AI" = true ]; then
    # Subir el archivo HTML a OpenAI
    upload_response=$(curl -s https://api.openai.com/v1/files \
      -H "Authorization: Bearer $OPENAI_API_KEY" \
      -F purpose="assistants" \
      -F file="@$REPORT_FILE")

    # Obtener el file_id del archivo subido
    file_id=$(echo "$upload_response" | jq -r '.id')

    if [ -z "$file_id" ] || [ "$file_id" = "null" ]; then
      red "Error: No se pudo subir el archivo a OpenAI"
      exit 1
    fi
  
    # Crear un nuevo thread
    thread_response=$(curl -s https://api.openai.com/v1/threads \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $OPENAI_API_KEY" \
      -H "OpenAI-Beta: assistants=v2" \
      -d '{}')

    # Obtener el thread_id
    thread_id=$(echo "$thread_response" | jq -r '.id')

    if [ -z "$thread_id" ] || [ "$thread_id" = "null" ]; then
      red "Error: No se pudo crear un nuevo thread en OpenAI"
      exit 1
    fi

    yellow "Thread id: $thread_id, Filew Id: $file_id"
    green "Send Open AI message"
    message_response=$(curl -s https://api.openai.com/v1/threads/$thread_id/messages \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $OPENAI_API_KEY" \
      -H "OpenAI-Beta: assistants=v2" \
      -d '{
        "role": "user",
        "content": "Attached is a Kubernetes cluster report. Please analyze it and provide a concise and actionable recommendation to improve the overall health of the cluster. Focus on issues related to deployments, pods, metrics server, and CrashLoopBackOff. Only return the result in Markdown format, without using ``` or any other code block delimiters.",
        "attachments": [
          {
            "file_id": "'"$file_id"'",
            "tools": [{"type": "file_search"}]
          }
        ]
      }')

    # Obtener el message_id del mensaje enviado
    message_id=$(echo "$message_response" | jq -r '.id')

    if [ -z "$message_id" ] || [ "$message_id" = "null" ]; then
      red "Error: No se pudo enviar el mensaje a OpenAI"
      exit 1
    fi

    if [ "$USE_AI" = true ]; then
      # Crear el asistente usando GPT-4o
      assistant_response=$(curl -s "https://api.openai.com/v1/assistants" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" \
        -d '{
          "instructions": "You are an assistant that provides actionable recommendations based on Kubernetes cluster reports. Consider that Cast.ai its used to analyze resources taints issues that could be normal when using dynamic auto-scaling",
          "name": "Kubernetes Health Assistant",
          "tools": [
            {
              "type": "file_search"
            }
          ],
          "model": "gpt-4o"
        }')

      # Obtener el assistant_id del asistente creado
      assistant_id=$(echo "$assistant_response" | jq -r '.id')

      if [ -z "$assistant_id" ] || [ "$assistant_id" = "null" ]; then
        red "Error: No se pudo crear el asistente en OpenAI"
        exit 1
      fi
    fi

    if [ "$USE_AI" = true ]; then
      # Crear un run para el thread con el asistente
      run_response=$(curl -s "https://api.openai.com/v1/threads/$thread_id/runs" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        -H "OpenAI-Beta: assistants=v2" \
        -d '{
          "assistant_id": "'"$assistant_id"'"
        }')

      # Obtener el run_id del run creado
      run_id=$(echo "$run_response" | jq -r '.id')

      if [ -z "$run_id" ] || [ "$run_id" = "null" ]; then
        red "Error: No se pudo crear un run en OpenAI"
        exit 1
      fi
    fi

    recommendation=""

    # Iterar hasta que el run esté completo
    while true; do
      sleep 5  # Esperar unos segundos antes de intentar obtener la respuesta

      # Obtener el estado del run
      run_status_response=$(curl -s "https://api.openai.com/v1/threads/$thread_id/runs/$run_id" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2")

      # Verificar si el run está completo
      status=$(echo "$run_status_response" | jq -r '.status')

      if [ "$status" = "completed" ]; then
        break
      elif [ "$status" = "failed" ]; then
        red "Error: El run ha fallado."
        exit 1
      fi
    done

    # Obtener todos los mensajes del thread
    messages_response=$(curl -s "https://api.openai.com/v1/threads/$thread_id/messages" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $OPENAI_API_KEY" \
      -H "OpenAI-Beta: assistants=v2")

    # Obtener el contenido del último mensaje (suponiendo que el mensaje generado por el asistente es el último)
    recommendation=$(echo "$messages_response" | jq -r '.data[0].content[0].text.value')

    if [ -z "$recommendation" ] || [ "$recommendation" = "null" ]; then
      red "Error: No se pudo obtener la recomendación del asistente."
      exit 1
    fi

    recommendation_div="<div class='card' style='max-height: 200px; overflow-y: auto; overflow-x: hidden;'>
    <pre style='white-space: pre-wrap; word-wrap: break-word;'>
      <code class='markdown'>$recommendation</code>
    </pre>
  </div>"

    # Leer el archivo y reemplazar el placeholder
    while IFS= read -r line; do
        if [[ "$line" == *"<div id='openai-recommendation-placeholder'></div>"* ]]; then
            printf "%s\n" "$recommendation_div"
        else
            printf "%s\n" "$line"
        fi
    done < "$REPORT_FILE" > temp.html && mv temp.html "$REPORT_FILE"
  fi

  # Perform git add, commit, and push for all files if --git-commit is present
  if [ "$GIT_COMMIT" = true ]; then
    git add --all
    git commit -m "$ENV_NAME statistics update"
    git push
  fi
  # Wait five minutes before the next run
  yellow "Wait $INTERVAL ..."
  sleep $INTERVAL
done
