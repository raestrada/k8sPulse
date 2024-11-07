import os
import sqlite3
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()

# SQLite Database setup
db_file = "k8spulse.sqlite"

# HTML Template directory setup
template_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(template_dir))

# Initialize the database
with sqlite3.connect(db_file) as conn:
    cursor = conn.cursor()

    # Crear la tabla report_history si no existe
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS report_history (
            id INTEGER PRIMARY KEY,
            timestamp TEXT UNIQUE,
            total_deployments INTEGER,
            deployments_with_replicas INTEGER,
            deployments_with_zero_replicas INTEGER,
            deployments_with_exact_replicas INTEGER,
            deployments_with_crashloopbackoff INTEGER,
            deployments_with_recent_start INTEGER
        )
    """
    )

    # Usar ALTER TABLE para agregar las nuevas columnas si no existen
    try:
        cursor.execute(
            "ALTER TABLE report_history ADD COLUMN cpu_used_percentage REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    try:
        cursor.execute(
            "ALTER TABLE report_history ADD COLUMN cpu_requested_percentage REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    try:
        cursor.execute(
            "ALTER TABLE report_history ADD COLUMN memory_used_percentage REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    try:
        cursor.execute(
            "ALTER TABLE report_history ADD COLUMN memory_requested_percentage REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    # Crear las tablas node_issues y zombie_processes si no existen
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS node_issues (
            id INTEGER PRIMARY KEY,
            report_id INTEGER,
            name TEXT,
            status TEXT,
            description TEXT,
            FOREIGN KEY (report_id) REFERENCES report_history(id)
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS zombie_processes (
            id INTEGER PRIMARY KEY,
            report_id INTEGER,
            namespace TEXT,
            pod TEXT,
            container TEXT,
            pid INTEGER,
            process_name TEXT,
            FOREIGN KEY (report_id) REFERENCES report_history(id)
        )
    """
    )
    conn.commit()


def load_report_history(as_dataframe=False):
    console.log("[cyan]Loading report history...[/cyan]")
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM report_history WHERE timestamp >= datetime('now', '-1 day') ORDER BY timestamp DESC;"
        )
        rows = cursor.fetchall()

        # Convert rows to a list of dictionaries
        history_list = []
        for row in rows:
            report_id = row[0]
            history_list.append(
                {
                    "timestamp": row[1],
                    "total_deployments": int(row[2]),
                    "deployments_with_replicas": int(row[3]),
                    "deployments_with_zero_replicas": int(row[4]),
                    "deployments_with_exact_replicas": int(row[5]),
                    "deployments_with_crashloopbackoff": int(row[6]),
                    "deployments_with_recent_start": int(row[7]),
                    "cpu_used_percentage": float(row[8]),
                    "cpu_requested_percentage": float(row[9]),
                    "memory_used_percentage": float(row[10]),
                    "memory_requested_percentage": float(row[11]),
                    "nodes_with_issues": load_node_issues(report_id),
                    "zombie_processes": load_zombie_processes(report_id),
                }
            )

        # If a pandas DataFrame is requested
        if as_dataframe:
            return pd.DataFrame(history_list)

        # Otherwise, return the list of dictionaries
        return history_list


def load_node_issues(report_id):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, status, description FROM node_issues WHERE report_id = ?",
            (report_id,),
        )
        rows = cursor.fetchall()
        return [
            {"name": row[0], "status": row[1], "description": row[2]} for row in rows
        ]


def load_zombie_processes(report_id):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT namespace, pod, container, pid, process_name FROM zombie_processes WHERE report_id = ?",
            (report_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "namespace": row[0],
                "pod": row[1],
                "container": row[2],
                "pid": row[3],
                "process_name": row[4],
            }
            for row in rows
        ]


def prepare_history_data_for_template():
    console.log("[cyan]Preparing history data for the template...[/cyan]")
    history = load_report_history()  # Should return a list of dictionaries.

    if len(history) == 0:
        console.log("[yellow]No history data found.[/yellow]")
        return []

    # Asegúrate de que cada valor sea del tipo correcto.
    for entry in history:
        entry["total_deployments"] = int(entry.get("total_deployments", 0))
        entry["deployments_with_replicas"] = int(
            entry.get("deployments_with_replicas", 0)
        )
        entry["deployments_with_zero_replicas"] = int(
            entry.get("deployments_with_zero_replicas", 0)
        )
        entry["deployments_with_exact_replicas"] = int(
            entry.get("deployments_with_exact_replicas", 0)
        )
        entry["deployments_with_crashloopbackoff"] = int(
            entry.get("deployments_with_crashloopbackoff", 0)
        )
        entry["deployments_with_recent_start"] = int(
            entry.get("deployments_with_recent_start", 0)
        )
        entry["cpu_used_percentage"] = float(entry.get("cpu_used_percentage", 0))
        entry["cpu_requested_percentage"] = float(
            entry.get("cpu_requested_percentage", 0)
        )
        entry["memory_used_percentage"] = float(entry.get("memory_used_percentage", 0))
        entry["memory_requested_percentage"] = float(
            entry.get("memory_requested_percentage", 0)
        )

    return history


# Render the HTML report
def render_html_report(template_name, context):
    console.log("[cyan]Rendering HTML report...[/cyan]")
    template = env.get_template(template_name)
    return template.render(context)


def save_report_history(data):
    console.log("[cyan]Saving report history...[/cyan]")
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO report_history (
                timestamp, total_deployments, deployments_with_replicas, deployments_with_zero_replicas,
                deployments_with_exact_replicas, deployments_with_crashloopbackoff, deployments_with_recent_start,
                cpu_used_percentage, cpu_requested_percentage, memory_used_percentage, memory_requested_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["timestamp"],
                int(data["total_deployments"]),
                int(data["deployments_with_replicas"]),
                int(data["deployments_with_zero_replicas"]),
                int(data["deployments_with_exact_replicas"]),
                int(data["deployments_with_crashloopbackoff"]),
                int(data["deployments_with_recent_start"]),
                float(data.get("cpu_used_percentage", 0)),
                float(data.get("cpu_requested_percentage", 0)),
                float(data.get("memory_used_percentage", 0)),
                float(data.get("memory_requested_percentage", 0)),
            ),
        )
        report_id = cursor.lastrowid
        for node in data["nodes_with_issues"]:
            cursor.execute(
                """
                INSERT INTO node_issues (report_id, name, status, description) VALUES (?, ?, ?, ?)
            """,
                (report_id, node["name"], node["status"], node.get("description")),
            )
        for zombie in data["zombie_processes"]:
            cursor.execute(
                """
                INSERT INTO zombie_processes (report_id, namespace, pod, container, pid, process_name) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    report_id,
                    zombie["namespace"],
                    zombie["pod"],
                    zombie["container"],
                    zombie["pid"],
                    zombie["process_name"],
                ),
            )
        conn.commit()


# Define the directory where reports are saved
REPORTS_DIR = "docs"


# Function to get the list of generated reports
def get_reports_list():
    reports = []
    for filename in os.listdir(REPORTS_DIR):
        if filename.endswith(".html") and filename != "index.html":
            report_path = os.path.join(REPORTS_DIR, filename)
            # Extract the date from the filename or its metadata
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


# Function to generate the index.html file
def generate_index_html():
    template = env.get_template("index.html")  # Use the template `index.html`
    reports = get_reports_list()
    rendered_index = template.render(reports=reports)

    # Save index.html in the reports directory
    with open(os.path.join(REPORTS_DIR, "index.html"), "w") as f:
        f.write(rendered_index)
