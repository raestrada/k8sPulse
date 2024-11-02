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

# Check if git is configured
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
  red "Error: Not a Git repository. Please run this script inside a valid Git repository."
  exit 1
fi

# Check if the --git-commit argument is present
# Default values
GIT_COMMIT=false
ENV_NAME="staging"
INTERVAL=300

# Parse arguments
for arg in "$@"; do
  if [ "$arg" == "--git-commit" ]; then
    GIT_COMMIT=true
  elif [[ "$arg" == --env-name=* ]]; then
    ENV_NAME="${arg#*=}"
  elif [[ "$arg" == --interval=* ]]; then
    INTERVAL="${arg#*=}"
  fi
done

# HTML report file
REPORT_FILE="$ENV_NAME_statistics.html"
# Rotating history file
HISTORY_FILE="$ENV_NAME_statistics_history.log"

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

  green "Saving log history ..."
  # Save the current state in the rotating history file
  echo "$(date +%Y-%m-%dT%H:%M:%S)|$total_deployments|$deployments_with_replicas|$percentage_with_replicas|$deployments_with_zero_replicas|$percentage_with_zero_replicas|$deployments_with_exact_replicas|$percentage_with_exact_replicas|$pods_with_crashloopbackoff|$percentage_with_crashloopbackoff|$pods_recently_restarted|$percentage_recently_restarted|$metrics_server_replicas|$percentage_metrics_server|$kube_dns_replicas|$percentage_kube_dns" >> "$HISTORY_FILE"

  green "Rotating log hisdtory ..."
   # Keep only the last 24 hours of logs (288 lines, one every five minutes)
  tail -n 288 "$HISTORY_FILE" > "$HISTORY_FILE.tmp" && mv "$HISTORY_FILE.tmp" "$HISTORY_FILE"

  green "Generate report ..."
  # Generate HTML report with modern design and requested adjustments
  report="<html><head><title>$ENV_NAME Statistics</title><style>"
  report+="body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; padding: 20px; }"
  report+="h2 { color: #4caf50; }"
  report+=".card { background: #fff; padding: 20px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 8px; }"
  report+=".gauge-row, .chart-container { display: flex; gap: 20px; justify-content: space-around; margin-top: 20px; }"
  report+=".gauge-container { text-align: center; }"
  report+=".chart { text-align: center; display: inline-block; margin: 20px; }"
  report+="table { width: 100%; border-collapse: collapse; margin-top: 20px; }"
  report+="th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }"
  report+="th { background-color: #4caf50; color: white; }"
  report+=".events { max-height: 400px; overflow-y: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 20px; }"
  report+=".event { margin-bottom: 10px; padding: 10px; border-radius: 5px; }"
  report+=".event-warning { background-color: #fff3cd; color: #856404; }"
  report+=".event-error { background-color: #f8d7da; color: #721c24; }"
  report+="#refresh-timer { position: fixed; top: 20px; right: 20px; background: #4caf50; color: white; padding: 10px; border-radius: 8px; font-size: 16px; font-weight: bold; }"
  report+=".status-indicator { width: 20px; height: 20px; border-radius: 50%; display: inline-block; margin-right: 10px; }"
  report+=".status-ok { background-color: green; }"
  report+=".status-error { background-color: red; }"
  report+="</style><meta http-equiv=\"refresh\" content=\"60\">"
  report+="</head><body>"
  
  # Refresh timer and header
  report+="<div id='refresh-timer'>Next refresh in: <span id='refresh-counter'>60 s</span></div>"
  report+="<h2>$ENV_NAME Statistics</h2>"

  report+="<script type=\"text/javascript\" src=\"https://www.gstatic.com/charts/loader.js\"></script>"
  report+="<script type=\"text/javascript\">
            google.charts.load('current', {packages:['gauge']});
            google.charts.setOnLoadCallback(drawGauges);

            function drawGauges() {
              var options_replicas = { width: 120, height: 120, minorTicks: 5, greenFrom: 70, greenTo: 100, yellowFrom: 40, yellowTo: 70, redFrom: 0, redTo: 40 };
              var options_other = { width: 120, height: 120, minorTicks: 5, greenFrom: 0, greenTo: 20, yellowFrom: 20, yellowTo: 70, redFrom: 70, redTo: 100 };

              var dataWithReplicas = google.visualization.arrayToDataTable([
                ['Label', 'Value'],
                ['With Replica', $percentage_with_replicas]
              ]);
              var dataZeroReplicas = google.visualization.arrayToDataTable([
                ['Label', 'Value'],
                ['No Replica', $percentage_with_zero_replicas]
              ]);
              var dataExactReplicas = google.visualization.arrayToDataTable([
                ['Label', 'Value'],
                ['Exact', $percentage_with_exact_replicas]
              ]);
              var dataCrashLoop = google.visualization.arrayToDataTable([
                ['Label', 'Value'],
                ['CrashLoop', $percentage_with_crashloopbackoff]
              ]);
              var dataRecentlyRestarted = google.visualization.arrayToDataTable([
                ['Label', 'Value'],
                ['Restarted', $percentage_recently_restarted]
              ]);

              var gaugeWithReplicas = new google.visualization.Gauge(document.getElementById('gauge_with_replicas'));
              gaugeWithReplicas.draw(dataWithReplicas, options_replicas);

              var gaugeZeroReplicas = new google.visualization.Gauge(document.getElementById('gauge_zero_replicas'));
              gaugeZeroReplicas.draw(dataZeroReplicas, options_other);

              var gaugeExactReplicas = new google.visualization.Gauge(document.getElementById('gauge_exact_replicas'));
              gaugeExactReplicas.draw(dataExactReplicas, options_replicas);

              var gaugeCrashLoop = new google.visualization.Gauge(document.getElementById('gauge_crashloop'));
              gaugeCrashLoop.draw(dataCrashLoop, options_other);

              var gaugeRecentlyRestarted = new google.visualization.Gauge(document.getElementById('gauge_recently_restarted'));
              gaugeRecentlyRestarted.draw(dataRecentlyRestarted, options_other);
            }
          </script>"
  report+="</head><body>"

  report+="<div class='gauge-row'>"
  
  green "Generate Gauges ..."
  # Gauges with values and percentages
  report+="<div class='status-container'>"
  report+="<div class='status-box'><div class='status-indicator $(awk -v a="$metrics_server_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')'></div>Metrics-server: $(awk -v a="$metrics_server_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')</div>"
  report+="<div class='status-box'><div class='status-indicator $(awk -v a="$kube_dns_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')'></div>Kube-dns: $(awk -v a="$kube_dns_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')</div>"
  report+="<div class='status-box'><div class='status-indicator $(awk -v a="$castai_agent_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')'></div>CAST AI Agent: $(awk -v a="$castai_agent_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')</div>"
  report+="<div class='status-box'><div class='status-indicator $(awk -v a="$castai_workload_autoscaler_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')'></div>CAST AI Workload Autoscaler: $(awk -v a="$castai_workload_autoscaler_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')</div>"
  report+="<div class='status-box'><div class='status-indicator $(awk -v a="$castai_cluster_controller_replicas" 'BEGIN {print (a == 0 ? "status-error" : "status-ok") }')'></div>CAST AI Cluster Controller: $(awk -v a="$castai_cluster_controller_replicas" 'BEGIN {print (a == 0 ? "Error" : "OK") }')</div>"
  report+="</div>"
  report+="<div class='gauge-container'><div id='gauge_with_replicas'></div><div>With Replica: $deployments_with_replicas ($percentage_with_replicas%)</div></div>"
  report+="<div class='gauge-container'><div id='gauge_zero_replicas'></div><div>No Replica: $deployments_with_zero_replicas ($percentage_with_zero_replicas%)</div></div>"
  report+="<div class='gauge-container'><div id='gauge_exact_replicas'></div><div>Exact: $deployments_with_exact_replicas ($percentage_with_exact_replicas%)</div></div>"
  report+="<div class='gauge-container'><div id='gauge_crashloop'></div><div>CrashLoop: $pods_with_crashloopbackoff ($percentage_with_crashloopbackoff%)</div></div>"
  report+="<div class='gauge-container'><div id='gauge_recently_restarted'></div><div>Restarted: $pods_recently_restarted ($percentage_recently_restarted%)</div></div>"

  report+="</div>"

  green "Generate events section ..."
  # Event section with scroll
  report+="<div class='events'><h3>Unusual Events</h3>"
  unusual_events=$(kubectl get events --all-namespaces | grep -v "Normal" | awk '{print $1, $2, $5, substr($0, index($0,$6))}' | sort | uniq -c | sort -nr | head -50)
  green "Events read ..."

  if [ -z "$unusual_events" ]; then
    report+="<div class='event' style='color:red;'>No unusual events found.</div>"
  else
    while IFS= read -r event; do
      count=$(echo "$event" | awk '{print $1}')
      namespace=$(echo "$event" | awk '{print $2}')
      event_type=$(echo "$event" | awk '{print $3}')
      message=$(echo "$event" | cut -d' ' -f4-)
      event_class="event event-$(echo $event_type | tr '[:upper:]' '[:lower:]')"
      report+="<div class='$event_class'><strong>[$namespace]</strong> ($count times): $message</div>"
    done <<< "$unusual_events"
  fi
  report+="</div>"

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

  # Add charts to the report
  report+="<div class='chart-container'>"
  for chart_url in "${chart_urls[@]}"; do
    report+="<div class='chart'><img src='$chart_url' alt='Deployment and Pod Statistics'></div>"
  done
  report+="</div>"

  green "Generate History Table ..."
  # Generate history table
  report+="<h3>Last 24-Hour History</h3>"
  report+="<table><tr><th>Time</th><th>Total Deployments</th><th>With Replica</th><th>No Replica</th><th>Exactly Desired</th><th>CrashLoopBackOff</th><th>Recently Restarted</th><th>Metrics-server</th><th>Kube-dns</th></tr>"

  # Create a temporary file to store the history in reverse
  temp_file=$(mktemp)

  # Dump the content in reverse into the temporary file
  tail -r "$HISTORY_FILE" > "$temp_file"

  # Read the temporary file and generate the HTML table
  while IFS='|' read -r timestamp total with_replicas percentage_with_replicas without_replicas percentage_without_replicas exact_replicas percentage_exact_replicas crashloopbackoff percentage_crashloopbackoff recently_restarted percentage_recently_restarted metrics_server metrics_server_percentage kube_dns kube_dns_percentage; do
    metrics_server_percentage=$(awk -v val="$metrics_server_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : val}')
    kube_dns_percentage=$(awk -v val="$kube_dns_percentage" 'BEGIN {print (val == "" || val == "-") ? 100 : val}')
    report+="<tr><td>$timestamp</td><td>$total</td><td>$with_replicas ($percentage_with_replicas%)</td><td>$without_replicas ($percentage_without_replicas%)</td><td>$exact_replicas ($percentage_exact_replicas%)</td><td>$crashloopbackoff ($percentage_crashloopbackoff%)</td><td>$recently_restarted ($percentage_recently_restarted%)</td><td>$metrics_server ($metrics_server_percentage%)</td><td>$kube_dns ($kube_dns_percentage%)</td></tr>"
  done < "$temp_file"

  # Delete the temporary file
  rm "$temp_file"

  report+="</table>"

  npx prettier . --write

  # Save report to HTML file
  echo "$report" > "$REPORT_FILE"

  # Perform git add, commit, and push for all files if --git-commit is present
  if [ "$GIT_COMMIT" = true ]; then
    git add --all
    git commit -m "$ENV_NAME statistics update"
    git push
  fi

  # Wait five minutes before the next run
  sleep $INTERVAL
done
