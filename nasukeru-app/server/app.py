import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory

from template_schema import (
    SchemaValidationError,
    detect_high_risk_changes,
    normalize_schema,
    schema_format as get_schema_format,
    validate_template_payload,
)


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = Path(__file__).with_name("nasukeru.db")

app = Flask(__name__)


class DatabaseNotReady(RuntimeError):
    pass


class TemplateSchemaError(RuntimeError):
    pass


class TemplateValidationError(RuntimeError):
    pass


class TemplateStateError(RuntimeError):
    pass


class LocalGuardError(RuntimeError):
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
    schema = normalize_db_template_schema(schema)
    if get_schema_format(schema) != "stroke-v1":
        raise TemplateSchemaError("normal template API supports stroke-v1 only")
    return {
        "id": row["id"],
        "label": row["label"],
        "full": row["full"],
        "vitals": schema["vitals"],
        "symptoms": schema["symptoms"],
        "neuro": schema["neuro"],
        "rest": schema["rest"],
    }


def normal_template_from_row(row):
    schema = json.loads(row["schema_json"])
    schema = normalize_db_template_schema(schema)
    fmt = get_schema_format(schema)
    if fmt == "stroke-v1":
        return {
            **template_from_row(row),
            "category": row["category"] if "category" in row.keys() else "stroke",
            "schema_format": fmt,
        }
    return {
        "id": row["id"],
        "label": row["label"],
        "full": row["full"],
        "category": row["category"] if "category" in row.keys() else "",
        "schema_format": fmt,
        "schema": schema,
        "copy_format": parse_json_value(row["copy_format_json"]) if "copy_format_json" in row.keys() else None,
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
        schema = normalize_db_template_schema(schema)
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


def validate_db_template_schema(schema):
    try:
        normalize_schema(schema)
    except SchemaValidationError as error:
        raise TemplateSchemaError(str(error)) from error


def normalize_db_template_schema(schema):
    try:
        return normalize_schema(schema)
    except SchemaValidationError as error:
        raise TemplateSchemaError(str(error)) from error


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def require_json_body():
    payload = request.get_json(silent=True)
    if payload is None:
        raise TemplateValidationError("request body must be JSON")
    if not isinstance(payload, dict):
        raise TemplateValidationError("request body must be an object")
    return payload


def require_reason(payload, field="reason"):
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TemplateValidationError(f"{field} is required")
    return value.strip()


def require_positive_int(payload, field):
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TemplateValidationError(f"{field} must be a positive integer")
    return value


def allowed_local_origin(value):
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def require_local_post_guard():
    if request.method != "POST":
        return
    if request.headers.get("X-Nasukeru-Local") != "1":
        raise LocalGuardError("X-Nasukeru-Local: 1 header is required")
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    if not origin and not referer:
        raise LocalGuardError("Origin or Referer header is required")
    if not (allowed_local_origin(origin) or allowed_local_origin(referer)):
        raise LocalGuardError("Origin or Referer must be localhost, 127.0.0.1, or ::1")


def template_summary_from_row(row):
    summary = {
        "id": row["id"],
        "label": row["label"],
        "full": row["full"],
        "category": row["category"],
        "is_active": bool(row["is_active"]),
        "status": row["status"],
        "current_version_id": row["current_version_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if "current_version_number" in row.keys():
        summary["current_version_number"] = row["current_version_number"]
    if "schema_json" in row.keys():
        schema = parse_json_value(row["schema_json"])
        validate_db_template_schema(schema)
        summary["schema_format"] = get_schema_format(schema)
    return summary


def fetch_template_summary(conn, template_id):
    row = conn.execute(
        """
        SELECT
          t.id AS id,
          t.label,
          t.full,
          t.category,
          t.is_active,
          t.status,
          t.current_version_id,
          v.version_number AS current_version_number,
          t.created_at,
          t.updated_at,
          COALESCE(v.schema_json, t.schema_json) AS schema_json
        FROM templates t
        LEFT JOIN template_versions v ON v.id = t.current_version_id
        WHERE t.id = ?
        """,
        (template_id,),
    ).fetchone()
    return template_summary_from_row(row) if row else None


def fetch_template_state(conn, template_id):
    return conn.execute(
        """
        SELECT
          t.id,
          t.label,
          t.full,
          t.category,
          t.schema_json,
          t.is_active,
          t.status,
          t.current_version_id,
          v.version_number AS current_version_number,
          t.created_at,
          t.updated_at,
          COALESCE(v.schema_json, t.schema_json) AS current_schema_json,
          v.copy_format_json AS current_copy_format_json
        FROM templates t
        LEFT JOIN template_versions v ON v.id = t.current_version_id
        WHERE t.id = ?
        """,
        (template_id,),
    ).fetchone()


def admin_template_detail_from_row(row):
    schema = parse_json_value(row["current_schema_json"])
    schema = normalize_db_template_schema(schema)
    return {
        **template_summary_from_row(row),
        "schema": schema,
        "copy_format": parse_json_value(row["current_copy_format_json"]),
        "schema_format": get_schema_format(schema),
    }


def insert_audit_log(conn, template_id, version_id, action, acted_at, reason, before=None, after=None, diff=None):
    conn.execute(
        """
        INSERT INTO template_audit_logs
          (template_id, version_id, action, actor_name, acted_at,
           before_json, after_json, diff_json, reason, client_info)
        VALUES (?, ?, ?, 'local', ?, ?, ?, ?, ?, ?)
        """,
        (
            template_id,
            version_id,
            action,
            acted_at,
            json_dumps(before) if before is not None else None,
            json_dumps(after) if after is not None else None,
            json_dumps(diff) if diff is not None else None,
            reason,
            request.user_agent.string,
        ),
    )


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


@app.errorhandler(TemplateValidationError)
def handle_template_validation_error(error):
    return jsonify({"ok": False, "error": "template validation error", "detail": str(error)}), 400


@app.errorhandler(TemplateStateError)
def handle_template_state_error(error):
    return jsonify({"ok": False, "error": "template state error", "detail": str(error)}), 409


@app.errorhandler(LocalGuardError)
def handle_local_guard_error(error):
    return jsonify({"ok": False, "error": "local guard error", "detail": str(error)}), 403


@app.before_request
def guard_local_write_requests():
    if request.path.startswith("/api/templates") and request.method == "POST":
        require_local_post_guard()


@app.get("/")
def index():
    return send_from_directory(APP_ROOT, "index.html")


@app.get("/admin")
@app.get("/admin/")
def admin():
    return send_from_directory(APP_ROOT, "admin.html")


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
    include_inactive = request.args.get("include_inactive") == "1"
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
              t.id,
              t.label,
              t.full,
              t.category,
              COALESCE(v.schema_json, t.schema_json) AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE (? = 1 OR t.is_active = 1)
            ORDER BY t.display_order, t.label
            """,
            (1 if include_inactive else 0,),
        ).fetchall()
    return jsonify([normal_template_from_row(row) for row in rows])


@app.get("/api/admin/templates")
def get_admin_templates():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
              t.id,
              t.label,
              t.full,
              t.category,
              t.is_active,
              t.status,
              t.current_version_id,
              v.version_number AS current_version_number,
              t.created_at,
              t.updated_at,
              COALESCE(v.schema_json, t.schema_json) AS schema_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            ORDER BY t.display_order, t.label
            """
        ).fetchall()
    return jsonify(
        [
            {
                **template_summary_from_row(row),
                "current_version_number": row["current_version_number"],
            }
            for row in rows
        ]
    )


@app.get("/api/admin/templates/<template_id>")
def get_admin_template(template_id):
    with connect() as conn:
        row = fetch_template_state(conn, template_id)
    if row is None:
        return jsonify({"error": "template not found"}), 404
    return jsonify(admin_template_detail_from_row(row))


@app.post("/api/templates")
def create_template():
    payload = require_json_body()
    try:
        validated = validate_template_payload(payload, require_identity=True)
    except SchemaValidationError as error:
        raise TemplateValidationError(str(error)) from error

    timestamp = now_iso()
    schema_json = json_dumps(validated["schema"])
    copy_format_json = json_dumps(validated["copy_format"]) if validated["copy_format"] is not None else None
    change_summary = validated["change_summary"] or "Create template"
    conn = connect()
    try:
        conn.execute("BEGIN")
        if fetch_template_state(conn, validated["id"]) is not None:
            raise TemplateStateError("template id already exists")

        display_order = conn.execute(
            "SELECT COALESCE(MAX(display_order), 0) + 1 FROM templates"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO templates
              (id, label, full, category, schema_json, is_active, display_order,
               created_at, updated_at, current_version_id, status)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, NULL, 'published')
            """,
            (
                validated["id"],
                validated["label"],
                validated["full"],
                validated["category"],
                schema_json,
                display_order,
                timestamp,
                timestamp,
            ),
        )
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at)
            VALUES (?, 1, ?, ?, ?, ?, 'local', ?, 'local', ?)
            """,
            (
                validated["id"],
                schema_json,
                copy_format_json,
                change_summary,
                validated["change_reason"],
                timestamp,
                timestamp,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE templates
            SET current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (version_id, timestamp, validated["id"]),
        )
        insert_audit_log(
            conn,
            validated["id"],
            version_id,
            "create",
            timestamp,
            validated["change_reason"],
            after={
                "schema": validated["schema"],
                "copy_format": validated["copy_format"],
            },
        )
        summary = fetch_template_summary(conn, validated["id"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"ok": True, "template": summary}), 201


@app.post("/api/templates/<template_id>/versions")
def create_template_version(template_id):
    payload = require_json_body()
    base_version_id = require_positive_int(payload, "base_version_id")
    try:
        validated = validate_template_payload(
            payload,
            require_identity=False,
            require_change_summary=True,
        )
    except SchemaValidationError as error:
        raise TemplateValidationError(str(error)) from error

    timestamp = now_iso()
    schema_json = json_dumps(validated["schema"])
    copy_format_json = json_dumps(validated["copy_format"]) if validated["copy_format"] is not None else None
    high_risk_changes = []
    conn = connect()
    try:
        conn.execute("BEGIN")
        template = fetch_template_state(conn, template_id)
        if template is None:
            return jsonify({"ok": False, "error": "template not found"}), 404
        if not template["is_active"]:
            raise TemplateStateError("deleted template cannot be edited")
        if template["current_version_id"] != base_version_id:
            raise TemplateStateError("template has been updated; reload before saving")
        before_schema = normalize_db_template_schema(parse_json_value(template["current_schema_json"]))
        before_copy_format = parse_json_value(template["current_copy_format_json"])
        high_risk_changes = detect_high_risk_changes(
            before_schema,
            validated["schema"],
            before_copy_format,
            validated["copy_format"],
        )

        version_number = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM template_versions
            WHERE template_id = ?
            """,
            (template_id,),
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, 'local', ?, 'local', ?)
            """,
            (
                template_id,
                version_number,
                schema_json,
                copy_format_json,
                validated["change_summary"],
                validated["change_reason"],
                timestamp,
                timestamp,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (schema_json, version_id, timestamp, template_id),
        )
        insert_audit_log(
            conn,
            template_id,
            version_id,
            "update",
            timestamp,
            validated["change_reason"],
            before={
                "schema": parse_json_value(template["current_schema_json"]),
                "copy_format": parse_json_value(template["current_copy_format_json"]),
            },
            after={
                "schema": validated["schema"],
                "copy_format": validated["copy_format"],
            },
            diff={"high_risk_changes": high_risk_changes},
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify(
        {
            "ok": True,
            "template_id": template_id,
            "version_id": version_id,
            "version_number": version_number,
            "high_risk_changes": high_risk_changes,
        }
    ), 201


@app.post("/api/templates/<template_id>/delete")
def delete_template(template_id):
    payload = require_json_body()
    reason = require_reason(payload)
    timestamp = now_iso()
    conn = connect()
    try:
        conn.execute("BEGIN")
        template = fetch_template_state(conn, template_id)
        if template is None:
            return jsonify({"ok": False, "error": "template not found"}), 404
        if not template["is_active"]:
            raise TemplateStateError("template is already deleted")

        conn.execute(
            "UPDATE templates SET is_active = 0, updated_at = ? WHERE id = ?",
            (timestamp, template_id),
        )
        insert_audit_log(
            conn,
            template_id,
            template["current_version_id"],
            "delete",
            timestamp,
            reason,
            before=template_summary_from_row(template),
            after={"is_active": False},
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"ok": True, "template_id": template_id, "is_active": False})


@app.post("/api/templates/<template_id>/restore")
def restore_template(template_id):
    payload = require_json_body()
    reason = require_reason(payload)
    timestamp = now_iso()
    conn = connect()
    try:
        conn.execute("BEGIN")
        template = fetch_template_state(conn, template_id)
        if template is None:
            return jsonify({"ok": False, "error": "template not found"}), 404
        if template["is_active"]:
            raise TemplateStateError("template is already active")

        conn.execute(
            "UPDATE templates SET is_active = 1, updated_at = ? WHERE id = ?",
            (timestamp, template_id),
        )
        insert_audit_log(
            conn,
            template_id,
            template["current_version_id"],
            "restore",
            timestamp,
            reason,
            before={"is_active": False},
            after={"is_active": True},
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"ok": True, "template_id": template_id, "is_active": True})


@app.get("/api/templates/<template_id>")
def get_template(template_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.label,
              t.full,
              t.category,
              COALESCE(v.schema_json, t.schema_json) AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ? AND t.is_active = 1
            """,
            (template_id,),
        ).fetchone()
    if row is None:
        return jsonify({"error": "template not found"}), 404
    schema = parse_json_value(row["schema_json"])
    validate_db_template_schema(schema)
    return jsonify(normal_template_from_row(row))


@app.get("/api/templates/<template_id>/versions")
def get_template_versions(template_id):
    with connect() as conn:
        template = conn.execute(
            "SELECT id FROM templates WHERE id = ?",
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
            "SELECT id FROM templates WHERE id = ?",
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
            SELECT label, sub, action, target_type, target_id
            FROM quick_templates
            ORDER BY display_order, label
            """
        ).fetchall()
    return jsonify(
        [
            {
                "label": row["label"],
                "sub": row["sub"],
                "action": row["action"],
                "target": {
                    "type": row["target_type"] or "template",
                    "id": row["target_id"] or row["action"],
                },
            }
            for row in rows
        ]
    )


@app.get("/api/search-keywords")
def get_search_keywords():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT keyword, template_action, target_type, target_id
            FROM search_keywords
            ORDER BY display_order, keyword
            """
        ).fetchall()
    return jsonify(
        [
            {
                "keyword": row["keyword"],
                "template_action": row["template_action"],
                "target": {
                    "type": row["target_type"] or "template",
                    "id": row["target_id"] or row["template_action"],
                },
            }
            for row in rows
        ]
    )


@app.get("/api/template-groups/<group_id>")
def get_template_group(group_id):
    with connect() as conn:
        group = conn.execute(
            """
            SELECT id, label, sub
            FROM template_groups
            WHERE id = ? AND is_active = 1
            """,
            (group_id,),
        ).fetchone()
        if group is None:
            return jsonify({"error": "template group not found"}), 404
        rows = conn.execute(
            """
            SELECT
              t.id,
              t.label,
              t.full,
              t.category,
              COALESCE(v.schema_json, t.schema_json) AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM template_group_items gi
            JOIN templates t ON t.id = gi.template_id
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE gi.group_id = ? AND t.is_active = 1
            ORDER BY gi.display_order, t.display_order, t.label
            """,
            (group_id,),
        ).fetchall()
    return jsonify(
        {
            "id": group["id"],
            "label": group["label"],
            "sub": group["sub"],
            "templates": [normal_template_from_row(row) for row in rows],
        }
    )


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
