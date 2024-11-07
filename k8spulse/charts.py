import base64
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import numpy as np
from rich.console import Console

console = Console()


# Function to generate gauge chart images and encode them in base64
def generate_dial_gauge_chart(
    value,
    title,
    min_value=0,
    max_value=100,
    direction="direct",
    yellow_threshold=50,
    red_threshold=80,
):
    # Calculate the actual percentage based on value and limits
    percentage = (value - min_value) / (max_value - min_value) * 100
    percentage = min(max(percentage, 0), 100)  # Limit percentage between 0 and 100

    console.log(
        f"[cyan]Generating dial gauge chart for {title} with {percentage}%...[/cyan]"
    )

    green = "#4CAF50"
    yellow = "#FFC107"
    red = "#FF4444"

    # Set gauge colors based on thresholds and direction
    if direction == "inverse":
        # Inverse: less is better
        if percentage <= yellow_threshold:
            color = green
        elif percentage <= red_threshold:
            color = yellow
        else:
            color = red
    else:
        # Direct: more is better
        if percentage >= yellow_threshold:
            color = green
        elif percentage >= red_threshold:
            color = yellow
        else:
            color = red

    fig, ax = plt.subplots(
        figsize=(5, 2.5), subplot_kw={"aspect": "equal"}
    )  # Restore original figure size

    # Determine wedge parameters based on percentage
    theta = percentage / 100 * 180  # Scale to half-circle (0° to 180°)
    wedge = Wedge(
        center=(0, 0),
        r=1,
        theta1=0,
        theta2=theta,
        facecolor=color,
        edgecolor="black",
    )

    # Add the wedge and background to the plot
    ax.add_patch(wedge)
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")  # Hide the axes

    # Add title and percentage labels
    plt.text(
        0, -1.3, title, ha="center", va="center", fontsize=12
    )  # Restore original font size for title
    plt.text(
        0,
        0.2,
        f"{percentage:.0f}%",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
    )  # Display percentage

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", transparent=True)
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded_image


# Function to generate line chart based on history data
def generate_line_chart(history_df):
    console.log(
        "[cyan]Generating line chart for Kubernetes metrics over time...[/cyan]"
    )
    if "timestamp" not in history_df.columns:
        console.log(
            "[red]Error: 'timestamp' column not found in history data. Cannot generate line chart.[/red]"
        )
        return ""

    # Convert absolute values to percentages
    history_df["deployments_with_replicas_pct"] = (
        history_df["deployments_with_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_zero_replicas_pct"] = (
        history_df["deployments_with_zero_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_exact_replicas_pct"] = (
        history_df["deployments_with_exact_replicas"] / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_crashloopbackoff_pct"] = (
        history_df["deployments_with_crashloopbackoff"]
        / history_df["total_deployments"]
    ) * 100
    history_df["deployments_with_recent_start_pct"] = (
        history_df["deployments_with_recent_start"] / history_df["total_deployments"]
    ) * 100

    fig, ax = plt.subplots(figsize=(16, 6))  # Double the width by adjusting figsize
    history_df.plot(
        x="timestamp",
        y=[
            "deployments_with_replicas_pct",
            "deployments_with_zero_replicas_pct",
            "deployments_with_exact_replicas_pct",
            "deployments_with_crashloopbackoff_pct",
            "deployments_with_recent_start_pct",
        ],
        ax=ax,
    )

    plt.xlabel("Time")
    plt.ylabel("Percentage (%)")
    plt.title("Kubernetes Metrics Over Time (Percentage)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded_image


def generate_resource_dial_gauge(resource_type, metrics):
    console.log(f"[cyan]Generating dial gauge for {resource_type}...[/cyan]")

    if resource_type == "cpu":
        total = metrics["total_cpu_capacity_mcores"]
        used = metrics["total_cpu_used_mcores"]
        requested = metrics["total_cpu_requested_mcores"]
        title = "CPU Usage"
    elif resource_type == "memory":
        total = metrics["total_memory_capacity_mib"]
        used = metrics["total_memory_used_mib"]
        requested = metrics["total_memory_requested_mib"]
        title = "Memory Usage"
    else:
        console.log(
            "[red]Invalid resource type specified. Use 'cpu' or 'memory'.[/red]"
        )
        return ""

    # Calculate percentages
    used_percentage = (used / total) * 100
    requested_percentage = (requested / total) * 100

    # Log percentages before correction
    console.log(f"[yellow]Initial used percentage: {used_percentage}%[/yellow]")
    console.log(
        f"[yellow]Initial requested percentage: {requested_percentage}%[/yellow]"
    )

    # If any percentage is improbably low (< 1%), multiply by 100
    if used_percentage < 1:
        console.log(
            f"[red]Used percentage too low, correcting: {used_percentage}% -> {used_percentage * 100}%[/red]"
        )
        used_percentage *= 100

    if requested_percentage < 1:
        console.log(
            f"[red]Requested percentage too low, correcting: {requested_percentage}% -> {requested_percentage * 100}%[/red]"
        )
        requested_percentage *= 100

    # Set up the plot as a semicircle
    fig, ax = plt.subplots(figsize=(10, 5))  # Wider plot for a horizontal semicircle
    theta = np.linspace(0, np.pi, 100)  # Semicircle angles from 0 to pi

    # Set the background color to transparent
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    # Plot requested percentage in blue (entire semicircle)
    ax.fill_between(
        theta,
        0,
        1,
        where=(theta <= requested_percentage / 100 * np.pi),
        color="#90CAF9",
        edgecolor="black",
        linewidth=1.5,
        alpha=0.7,
        label="Requested",
    )

    # Plot used percentage in green (covers up to used part)
    ax.fill_between(
        theta,
        0,
        1,
        where=(theta <= used_percentage / 100 * np.pi),
        color="#4CAF50",
        edgecolor="black",
        linewidth=1.5,
        alpha=0.8,
        label="Used",
    )

    # Complete the rest of the semicircle in white
    ax.fill_between(
        theta,
        0,
        1,
        where=(theta > requested_percentage / 100 * np.pi),
        color="white",
        edgecolor="black",
        linewidth=1.5,
        alpha=0.5,
    )

    # Remove axes and ticks
    ax.axis("off")

    # Adjusted percentage labels
    # Add used percentage on the left side of the chart
    ax.text(
        0.1 * np.pi,
        0.5,
        f"U:{used_percentage:.0f}%",
        ha="left",
        va="center",
        fontsize=24,
        color="black",
        weight="bold",
        bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.5"),
    )

    # Add requested percentage on the right side of the chart
    ax.text(
        0.9 * np.pi,
        0.5,
        f"R:{requested_percentage:.0f}%",
        ha="right",
        va="center",
        fontsize=24,
        color="black",
        weight="bold",
        bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.5"),
    )

    # Add title below the gauge
    ax.text(0, -0.3, title, ha="center", fontsize=16, color="black", weight="bold")

    # Save the plot to a BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", transparent=True)
    buf.seek(0)

    # Encode the plot to base64
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    console.log(
        f"[green]Dial gauge for {resource_type} generated successfully.[/green]"
    )
    return encoded_image
