import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, send_from_directory


APP_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).with_name("nasukeru.db")

app = Flask(__name__)


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


def count_rows(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


@app.get("/")
def index():
    return send_from_directory(APP_ROOT, "index.html")


@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(APP_ROOT / "assets", filename)


@app.get("/css/<path:filename>")
def css(filename):
    return send_from_directory(APP_ROOT / "css", filename)


@app.get("/js/<path:filename>")
def js(filename):
    return send_from_directory(APP_ROOT / "js", filename)


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


@app.get("/api/templates/<template_id>")
def get_template(template_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, label, full, schema_json
            FROM templates
            WHERE id = ? AND is_active = 1
            """,
            (template_id,),
        ).fetchone()
    if row is None:
        return jsonify({"error": "template not found"}), 404
    return jsonify(template_from_row(row))


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


@app.get("/api/search-keywords")
def get_search_keywords():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT keyword
            FROM search_keywords
            ORDER BY display_order, keyword
            """
        ).fetchall()
    return jsonify([row["keyword"] for row in rows])


@app.get("/api/health")
def health():
    with connect() as conn:
        counts = {
            "templates": count_rows(conn, "templates"),
            "quick_templates": count_rows(conn, "quick_templates"),
            "rest_options": count_rows(conn, "rest_options"),
            "search_keywords": count_rows(conn, "search_keywords"),
        }
    return jsonify({"ok": True, "database": "connected", "counts": counts})


def env_flag(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit("DB not found. Run: py -3.10 server/init_db.py")
    host = os.environ.get("NASUKERU_HOST", "127.0.0.1")
    port = int(os.environ.get("NASUKERU_PORT", "8000"))
    app.run(host=host, port=port, debug=env_flag("NASUKERU_DEBUG"))
