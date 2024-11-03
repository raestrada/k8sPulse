# Quick Emergency Kubernetes Report

**An Experimental Tool, 100% Made with ChatGPT**

> **Note**: This tool is a technical experiment created entirely with ChatGPT. It’s not optimized for speed or efficiency and does not replace real-time monitoring solutions like Grafana, New Relic, or Datadog. However, it’s designed as a fallback option for emergency scenarios, especially when advanced cloud-native scaling tools (e.g., CAST AI, Karpenter, GKE’s autoscaler) may fail. This report generator provides a simple way to retrieve critical insights from a Kubernetes cluster with only kubectl access.

---

## What is This?

"Quick Emergency Kubernetes Report" is a script to generate an HTML report summarizing key Kubernetes metrics (deployments, replicas, events, etc.). It requires only kubectl access to the cluster and can run locally or push changes to GitHub Pages for sharing in real time.

**Disclaimer:** Outside of an emergency, this script is inefficient and unnecessary. Use real-time tools for routine monitoring.

## Usage

### Requirements
- `kubectl` configured and connected to your Kubernetes cluster.
- `git` for the optional commit/push functionality.

### Running the Script Locally

To use the report generator locally, run:
```bash
./docs/generate.sh
```
By default, the script generates an HTML report called `staging_statistics.html` that can be opened in a browser. It updates every 5 minutes to keep metrics current.

### Enabling Emergency Mode with Git Commit

To set up Git commit functionality for emergency publication:
1. Run the script with the `--git-commit` flag:
   ```bash
   ./docs/generate.sh --git-commit
   ```
2. Set up a GitHub repository and configure GitHub Pages to serve from the `docs` folder:
   - In your repository, go to **Settings > Pages**.
   - Under **Source**, select the branch and set the folder to `/docs`.

3. The HTML report will now be published under your GitHub Pages URL.

#### Optional Flags

- **`--env-name`**: Specify an environment name (default: `staging`).
- **`--interval`**: Set the refresh interval in seconds (default: `300`).

### Sample Output

Below is an example screenshot of the report layout (scaled down for brevity):
<img src="https://res.cloudinary.com/dyknhuvxt/image/upload/v1730648635/Captura_de_pantalla_2024-11-03_a_la_s_12.43.41_s2modk.png" alt="Sample Report Screenshot" style="max-width: 600px; height: auto;">

---

## FAQ

### Why use this script?
While tools like Grafana and New Relic offer better functionality, they may not be accessible during critical failures. This script provides a quick, git-based workaround using only `kubectl` and `git`.

### Is this script optimized?
No, this is an experimental tool with limited functionality. It’s intended solely as an emergency fallback and has limitations in speed and efficiency.

---

Feel free to contribute any insights, but remember, this project is intended as an experiment in using AI for coding solutions!
# k8s-emergency-report
# k8s-emergency-report
