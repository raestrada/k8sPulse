# ![k8sPulse Logo](https://res.cloudinary.com/dyknhuvxt/image/upload/c_scale,w_100/v1730740391/k8spulse_axrf38.png)[k8sPulse Home](https://github.com/raestrada/k8sPulse)

# k8sPulse Documentation 🚀

## Overview

**k8sPulse** is an open-source Kubernetes monitoring tool designed for emergency scenarios when you only have `kubectl` access. It leverages the Python Kubernetes native client and OpenAI to provide intelligent recommendations on cluster health.

## Installation Guide 🔧

### Prerequisites 📋

To use **k8sPulse**, you'll need `pipx` installed to easily manage the tool as an isolated package.

### Installing k8sPulse with pipx 📦

To install **k8sPulse** using `pipx`, run the following command:

```sh
pipx install git+https://github.com/raestrada/k8sPulse.git@v0.3.0
```

This command installs the latest tagged version (`v0.3.0`) of **k8sPulse**.

### Installing pipx 🐍

#### On Linux and macOS 🐧🍏

To install `pipx` on Linux or macOS, run:

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Ensure `python3` and `pip` are installed on your system.

#### On Windows 🪟

To install `pipx` on Windows, you can use the following command in PowerShell:

```sh
python -m pip install --user pipx
python -m pipx ensurepath
```

After installing `pipx`, close and reopen your terminal or run `refreshenv` if you're using the Windows Command Prompt.

## Usage 🚀

Once **k8sPulse** is installed, you can use the following commands and options to generate reports and monitor your Kubernetes cluster:

### Generating a Report 📊

To generate a report with default settings, use:

```sh
k8spulse
```

This command will generate a Kubernetes cluster report for the default `staging` environment.

### Available Options ⚙️

- `--env-name`  
  **Description**: Specify the environment name for the report.  
  **Default Value**: `staging`  
  **Usage**:
  
  ```sh
  k8spulse --env-name production
  ```

- `--interval`  
  **Description**: Set the interval (in seconds) between report generations.  
  **Default Value**: `300` (5 minutes)  
  **Usage**:
  
  ```sh
  k8spulse --interval 600
  ```

- `--use-ai`  
  **Description**: Use OpenAI to generate recommendations based on the report.  
  **Usage**:
  
  ```sh
  k8spulse --use-ai
  ```

- `--git-commit`  
  **Description**: Automatically commit and push the generated report to the Git repository.  
  **Usage**:
  
  ```sh
  k8spulse --git-commit
  ```

- `--gpt-model`  
  **Description**: Specify which GPT model to use for recommendations.  
  **Default Value**: `gpt-4o`  
  **Usage**:
  
  ```sh
  k8spulse --gpt-model got-4o
  ```

- `--zombies`  
  **Description**: Enable **experimental** zombie process detection in non-running pods using a Bash script and `kubectl`. This approach provides better performance compared to using the Python Kubernetes API client.  
  **Usage**:
  
  ```sh
  k8spulse --zombies
  ```

## Example 💡

Below is an example of using multiple options together:

```sh
k8spulse --env-name production --interval 600 --use-ai --git-commit --gpt-model got-4o --zombies
```

This command generates a report for the `production` environment every 10 minutes, uses OpenAI for recommendations, commits the report to Git, uses the `got-4o` GPT model, and enables zombie process detection.

## Generating the HTML Report 📄

After generating a report, you can view it by opening the generated `staging_statistics.html` file in your browser. The report provides a visual overview of the Kubernetes cluster, including gauges, unusual events, detailed insights, and zombie process detection if enabled.

## Contributing 🤝

We welcome contributions to **k8sPulse**! To get started, visit our [GitHub repository](https://github.com/raestrada/k8sPulse) and check out the contributing guidelines.

## License 📜

**k8sPulse** is open source and available under the MIT License.
