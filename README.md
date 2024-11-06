# ![k8sPulse Logo](https://res.cloudinary.com/dyknhuvxt/image/upload/c_scale,w_100/v1730740391/k8spulse_axrf38.png)

# k8sPulse v0.4.0 Release 🚀✨

**Release Date: November 5, 2024**

> **Note**: This is a breaking release with several exciting new features, including experimental zombie process detection.

## Breaking Changes ⚠️

### Experimental Zombie Process Detection 🧟‍♂️🔍

- Added the `--zombies` flag to enable **experimental zombie process detection** in non-running pods.
- This feature uses a **Bash script** along with `kubectl` for efficient zombie detection, outperforming the Python Kubernetes API client.
- Detects and reports zombie processes in containers, helping identify problematic workloads and improve cluster stability.

## What's New in v0.4.0 ✨

### 1. Experimental Zombie Process Detection 🧟‍♂️🔍

- Added the `--zombies` flag to enable **experimental zombie process detection** in non-running pods.
- This feature uses a **Bash script** along with `kubectl` for efficient zombie detection, outperforming the Python Kubernetes API client.
- Detects and reports zombie processes in containers, helping identify problematic workloads and improve cluster stability.

### 2. Enhanced OpenAI Integration 🤖🧠

- Improved the **OpenAI-powered recommendations** feature for more precise insights into Kubernetes cluster health.
- Now supports specifying the GPT model with the `--gpt-model` flag, giving users more control over the type of AI responses generated.

### 3. Improved CLI Experience 💻✨

- Better error handling and more informative console logs with **rich text formatting** to make the command line experience smoother and more intuitive.
- Updated installation instructions for easier setup across different platforms.

### 4. HTML Report Enhancements 📊🌐

- The generated HTML report now includes a new section for **Zombie Processes** if the `--zombies` flag is used.
- Improved layout and styling to make navigating through **unusual events**, **node issues**, and **zombie processes** easier.

## Installation 🛠️

To install **k8sPulse v0.4.0** using `pipx`, run the following command:

```sh
pipx install git+https://github.com/raestrada/k8sPulse.git@v0.4.0
```

## Example Usage 💡

Generate a report for the `production` environment every 10 minutes, use OpenAI for recommendations, commit the report to Git, use the `gpt-4o` model, and enable zombie process detection:

```sh
k8spulse --env-name production --interval 600 --use-ai --git-commit --gpt-model got-4o --zombies
```

## Feedback & Contributions 🤝

We value your feedback! Please report any issues or suggestions on our [GitHub repository](https://github.com/raestrada/k8sPulse). Contributions are welcome!

## License 📜

**k8sPulse** is open source and available under the MIT License.
