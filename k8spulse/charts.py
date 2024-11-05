import base64
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
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
