# ![k8sPulse Logo](https://res.cloudinary.com/dyknhuvxt/image/upload/v1730740391/k8spulse_axrf38.png) k8sPulse: Quick Emergency Kubernetes Report

**An Experimental Tool, 100% Made with ChatGPT**

> **Note**: k8sPulse is a technical experiment built entirely with ChatGPT. It’s not optimized for speed or efficiency and does not replace real-time monitoring solutions like Grafana, New Relic, or Datadog. Instead, it’s designed as a fallback option for emergency scenarios when advanced cloud-native scaling tools (e.g., CAST AI, Karpenter, GKE’s autoscaler) may fail. This tool provides critical insights into a Kubernetes cluster with only `kubectl` access.

---

## Overview

k8sPulse is an open-source monitoring tool for emergency scenarios, providing a quick Kubernetes cluster health overview when only `kubectl` is available. Leveraging the Python Kubernetes native client and OpenAI, it generates insightful and actionable recommendations to help resolve issues efficiently.

![k8sPulse Screenshot](https://res.cloudinary.com/dyknhuvxt/image/upload/v1730741959/Captura_de_pantalla_2024-11-04_a_la_s_14.39.08_flhkbc.png)

---

## Features

- **Fallback Kubernetes Monitoring:** Designed for emergencies where only `kubectl` access is possible.
- **OpenAI-Powered Recommendations:** Generates actionable cluster health suggestions using OpenAI's GPT models.
- **Native Kubernetes Python Client:** Uses Kubernetes Python client for direct and reliable cluster interaction.

## Installation Guide

### Requirements

- `kubeconfig` configured and connected to your Kubernetes cluster.
- `python3` to run cli.
- OpenAI API key for AI-powered recommendations (optional).

### Installing k8sPulse with pipx

To install **k8sPulse** using `pipx`, run:

```sh
pipx install git+https://github.com/raestrada/k8sPulse.git@v0.1.0
```

This command installs the latest tagged version (`v0.1.0`) of k8sPulse.

### Installing pipx

#### On Linux and macOS

To install `pipx` on Linux or macOS, run:

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Ensure `python3` and `pip` are installed on your system.

#### On Windows

To install `pipx` on Windows, use the following command in PowerShell:

```sh
python -m pip install --user pipx
python -m pipx ensurepath
```

After installing `pipx`, close and reopen your terminal or run `refreshenv` if using the Windows Command Prompt.

## Usage

Once installed, k8sPulse allows you to generate Kubernetes cluster reports and monitor your environment.

### Generating a Report

To generate a report with default settings, use:

```sh
k8spulse
```

This command generates a Kubernetes cluster report for the default `staging` environment.

### Available Options

- `--env-name`
  - **Description:** Specify the environment name for the report.
  - **Default Value:** `staging`
  - **Usage:**
    
    ```sh
    k8spulse --env-name production
    ```

- `--interval`
  - **Description:** Set the interval (in seconds) between report generations.
  - **Default Value:** `300` (5 minutes)
  - **Usage:**
    
    ```sh
    k8spulse --interval 600
    ```

- `--use-ai`
  - **Description:** Use OpenAI to generate recommendations based on the report.
  - **Usage:**
    
    ```sh
    k8spulse --use-ai
    ```

- `--git-commit`
  - **Description:** Automatically commit and push the generated report to the Git repository.
  - **Usage:**
    
    ```sh
    k8spulse --git-commit
    ```

- `--gpt-model`
  - **Description:** Specify which GPT model to use for recommendations.
  - **Default Value:** `got-4o`
  - **Usage:**
    
    ```sh
    k8spulse --gpt-model got-4o
    ```

### Enabling AI Recommendations

To receive AI-powered recommendations for Kubernetes cluster health:

1. Ensure you have an [OpenAI API key](https://platform.openai.com/account/api-keys) set as an environment variable:
   
   ```sh
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

2. Run the command with the `--use-ai` flag:
   
   ```sh
   k8spulse --use-ai
   ```

3. Recommendations will be generated and included in the HTML report.

## Generating the HTML Report

After generating a report, open the generated `staging_statistics.html` file in your browser. The report provides a visual overview of the Kubernetes cluster, including metrics, events, and insights.

### Index.html Generation for GitHub Pages

An `index.html` file is automatically generated to list all available reports. This allows easy hosting of reports using GitHub Pages for sharing and quick access.

#### Using GitHub Pages

1. Push the generated `index.html` and report files to your GitHub repository.
2. In your repository settings, go to **Settings > Pages**.
3. Under **Source**, select the branch and set the folder to `/docs`.
4. Your reports will now be accessible at your GitHub Pages URL.

## Contributing

Contributions are welcome! Visit our [GitHub repository](https://github.com/raestrada/k8sPulse) for more details on how to get started and our contributing guidelines.

## License

k8sPulse is open source and available under the MIT License.
