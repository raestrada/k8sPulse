import os
from datetime import datetime
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()

# HTML Template directory setup
template_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(template_dir))


def load_report_history(history_file):
    console.log("[cyan]Loading report history...[/cyan]")
    if not os.path.exists(history_file):
        # Return an empty DataFrame with expected columns if the history file doesn't exist
        return pd.DataFrame(
            columns=[
                "timestamp",
                "total_deployments",
                "deployments_with_replicas",
                "deployments_with_zero_replicas",
                "deployments_with_exact_replicas",
                "deployments_with_crashloopbackoff",
                "deployments_with_recent_start",
                "nodes_with_issues",
                "zombie_processes",
            ]
        )
    return pd.read_csv(history_file)


# Convert the DataFrame to a list of dictionaries to be passed to the HTML template
def prepare_history_data_for_template(history_file):
    history_df = load_report_history(history_file)
    history_df = history_df.set_index(
        "timestamp"
    )  # Establecer 'timestamp' como el índice
    history_df = history_df.sort_index(
        ascending=False
    )  # Ordenar de más reciente a más viejo
    history_data = history_df.reset_index().to_dict(
        orient="records"
    )  # Restaurar el índice para pasar al template
    return history_data


# Render the HTML report
def render_html_report(template_name, context):
    console.log("[cyan]Rendering HTML report...[/cyan]")
    template = env.get_template(template_name)
    return template.render(context)


def save_report_history(history_file, data):
    console.log("[cyan]Saving report history...[/cyan]")
    columns = [
        "timestamp",
        "total_deployments",
        "deployments_with_replicas",
        "deployments_with_zero_replicas",
        "deployments_with_exact_replicas",
        "deployments_with_crashloopbackoff",
        "deployments_with_recent_start",
        "nodes_with_issues",
        "zombie_processes",
    ]
    if not os.path.exists(history_file):
        with open(history_file, "w") as f:
            f.write(",".join(columns) + "\n")
    with open(history_file, "a") as f:
        f.write(
            f"{data['timestamp']},{data['total_deployments']},{data['deployments_with_replicas']},{data['deployments_with_zero_replicas']},{data['deployments_with_exact_replicas']},{data['deployments_with_crashloopbackoff']},{data['deployments_with_recent_start']},{len(data['nodes_with_issues'])},{len(data['zombie_processes'])}\n"
        )


# Define el directorio donde se guardan los reportes
REPORTS_DIR = "docs"


# Función para obtener la lista de reportes generados
def get_reports_list():
    reports = []
    for filename in os.listdir(REPORTS_DIR):
        if filename.endswith(".html") and filename != "index.html":
            report_path = os.path.join(REPORTS_DIR, filename)
            # Extraer la fecha del nombre del archivo o de su metadata
            report_date = datetime.fromtimestamp(
                os.path.getmtime(report_path)
            ).strftime("%Y-%m-%d %H:%M:%S")
            reports.append(
                {
                    "name": filename.replace(".html", "")
                    .replace("_", " ")
                    .capitalize(),
                    "link": filename,
                    "date": report_date,
                }
            )
    return sorted(reports, key=lambda x: x["date"], reverse=True)


# Función para generar el archivo index.html
def generate_index_html():
    template = env.get_template("index.html")  # Usa el template `index.html`
    reports = get_reports_list()
    rendered_index = template.render(reports=reports)

    # Guardar el index.html en el directorio de reportes
    with open(os.path.join(REPORTS_DIR, "index.html"), "w") as f:
        f.write(rendered_index)
