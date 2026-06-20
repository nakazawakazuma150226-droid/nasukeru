import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, send_from_directory


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = Path(__file__).with_name("nasukeru.db")

app = Flask(__name__)


class DatabaseNotReady(RuntimeError):
    pass


class TemplateSchemaError(RuntimeError):
    pass


def get_db_path():
    return Path(os.environ.get("NASUKERU_DB_PATH", DEFAULT_DB_PATH)).expanduser()


def connect():
    db_path = get_db_path()
    if not db_path.exists():
        raise DatabaseNotReady(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def template_from_row(row):
    schema = json.loads(row["schema_json"])
    validate_template_schema(schema)
    return {
        "id": row["id"],
        "label": row["label"],
        "full": row["full"],
        "vitals": schema["vitals"],
        "symptoms": schema["symptoms"],
        "neuro": schema["neuro"],
        "rest": schema["rest"],
    }


def parse_json_value(value):
    if value is None:
        return None
    return json.loads(value)


def version_from_row(row, include_schema=False):
    version = {
        "id": row["id"],
        "template_id": row["template_id"],
        "version_number": row["version_number"],
        "change_summary": row["change_summary"],
        "change_reason": row["change_reason"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "approved_by": row["approved_by"],
        "approved_at": row["approved_at"],
    }
    if include_schema:
        schema = parse_json_value(row["schema_json"])
        validate_template_schema(schema)
        version["schema"] = schema
        version["copy_format"] = parse_json_value(row["copy_format_json"])
    return version


def audit_log_from_row(row):
    return {
        "id": row["id"],
        "template_id": row["template_id"],
        "version_id": row["version_id"],
        "action": row["action"],
        "actor_id": row["actor_id"],
        "actor_name": row["actor_name"],
        "acted_at": row["acted_at"],
        "before": parse_json_value(row["before_json"]),
        "after": parse_json_value(row["after_json"]),
        "diff": parse_json_value(row["diff_json"]),
        "reason": row["reason"],
        "client_info": row["client_info"],
    }


def validate_template_schema(schema):
    required = ("vitals", "symptoms", "neuro", "rest")
    missing = [key for key in required if key not in schema]
    if missing:
        raise TemplateSchemaError("template schema missing: " + ", ".join(missing))
    if "mmt" not in schema["neuro"]:
        raise TemplateSchemaError("template schema missing: neuro.mmt")


def count_rows(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


@app.errorhandler(DatabaseNotReady)
def handle_database_not_ready(error):
    return jsonify({"ok": False, "error": "database not ready", "detail": str(error)}), 503


@app.errorhandler(sqlite3.Error)
def handle_database_error(error):
    return jsonify({"ok": False, "error": "database error", "detail": str(error)}), 500


@app.errorhandler(TemplateSchemaError)
def handle_template_schema_error(error):
    return jsonify({"ok": False, "error": "template schema error", "detail": str(error)}), 500


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
            SELECT
              t.id,
              t.label,
              t.full,
              COALESCE(v.schema_json, t.schema_json) AS schema_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.is_active = 1
            ORDER BY t.display_order, t.label
            """
        ).fetchall()
    return jsonify([template_from_row(row) for row in rows])


@app.get("/api/templates/<template_id>")
def get_template(template_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.label,
              t.full,
              COALESCE(v.schema_json, t.schema_json) AS schema_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ? AND t.is_active = 1
            """,
            (template_id,),
        ).fetchone()
    if row is None:
        return jsonify({"error": "template not found"}), 404
    return jsonify(template_from_row(row))


@app.get("/api/templates/<template_id>/versions")
def get_template_versions(template_id):
    with connect() as conn:
        template = conn.execute(
            "SELECT id FROM templates WHERE id = ? AND is_active = 1",
            (template_id,),
        ).fetchone()
        if template is None:
            return jsonify({"error": "template not found"}), 404
        rows = conn.execute(
            """
            SELECT
              id,
              template_id,
              version_number,
              change_summary,
              change_reason,
              created_by,
              created_at,
              approved_by,
            approved_at
            FROM template_versions
            WHERE template_id = ?
            ORDER BY version_number DESC
            """,
            (template_id,),
        ).fetchall()
    return jsonify([version_from_row(row) for row in rows])


@app.get("/api/templates/<template_id>/versions/<int:version_id>")
def get_template_version(template_id, version_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              id,
              template_id,
              version_number,
              schema_json,
              copy_format_json,
              change_summary,
              change_reason,
              created_by,
              created_at,
              approved_by,
              approved_at
            FROM template_versions
            WHERE template_id = ? AND id = ?
            """,
            (template_id, version_id),
        ).fetchone()
    if row is None:
        return jsonify({"error": "template version not found"}), 404
    return jsonify(version_from_row(row, include_schema=True))


@app.get("/api/templates/<template_id>/logs")
def get_template_logs(template_id):
    with connect() as conn:
        template = conn.execute(
            "SELECT id FROM templates WHERE id = ? AND is_active = 1",
            (template_id,),
        ).fetchone()
        if template is None:
            return jsonify({"error": "template not found"}), 404
        rows = conn.execute(
            """
            SELECT
              id,
              template_id,
              version_id,
              action,
              actor_id,
              actor_name,
              acted_at,
              before_json,
              after_json,
              diff_json,
              reason,
              client_info
            FROM template_audit_logs
            WHERE template_id = ?
            ORDER BY acted_at DESC, id DESC
            """,
            (template_id,),
        ).fetchall()
    return jsonify([audit_log_from_row(row) for row in rows])


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


@app.get("/api/migrations")
def get_migrations():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT version, name, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/health")
def health():
    try:
        with connect() as conn:
            counts = {
                "templates": count_rows(conn, "templates"),
                "template_versions": count_rows(conn, "template_versions"),
                "template_audit_logs": count_rows(conn, "template_audit_logs"),
                "quick_templates": count_rows(conn, "quick_templates"),
                "rest_options": count_rows(conn, "rest_options"),
                "search_keywords": count_rows(conn, "search_keywords"),
            }
    except DatabaseNotReady as error:
        return jsonify({"ok": False, "database": "missing", "detail": str(error)}), 503
    except sqlite3.Error as error:
        return jsonify({"ok": False, "database": "error", "detail": str(error)}), 500
    return jsonify({"ok": True, "database": "connected", "db_path": str(get_db_path()), "counts": counts})


def env_flag(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    if not get_db_path().exists():
        raise SystemExit("DB not found. Run: py -3.10 server/init_db.py")
    host = os.environ.get("NASUKERU_HOST", "127.0.0.1")
    port = int(os.environ.get("NASUKERU_PORT", "8000"))
    app.run(host=host, port=port, debug=env_flag("NASUKERU_DEBUG"))
