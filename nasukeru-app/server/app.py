import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, send_from_directory


APP_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).with_name("nasukeru.db")

app = Flask(__name__, static_folder=str(APP_ROOT), static_url_path="")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def template_from_row(row):
    schema = json.loads(row["schema_json"])
    return {
        "id": row["id"],
        "label": row["label"],
        "full": row["full"],
        "vitals": schema["vitals"],
        "symptoms": schema["symptoms"],
        "neuro": schema["neuro"],
        "rest": schema["rest"],
    }


@app.get("/")
def index():
    return send_from_directory(APP_ROOT, "index.html")


@app.get("/api/templates")
def get_templates():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, label, full, schema_json
            FROM templates
            WHERE is_active = 1
            ORDER BY display_order, label
            """
        ).fetchall()
    return jsonify([template_from_row(row) for row in rows])


@app.get("/api/rest-options")
def get_rest_options():
    with connect() as conn:
        rows = conn.execute(
            "SELECT label FROM rest_options ORDER BY display_order, label"
        ).fetchall()
    return jsonify([row["label"] for row in rows])


@app.get("/api/quick-templates")
def get_quick_templates():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT label, sub, action
            FROM quick_templates
            ORDER BY display_order, label
            """
        ).fetchall()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit("DB not found. Run: py -3.10 server/init_db.py")
    app.run(host="127.0.0.1", port=8000, debug=True)
