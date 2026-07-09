import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory

from template_schema import (
    SchemaValidationError,
    collect_duplicate_section_conditions,
    collect_unreferenced_fields,
    detect_high_risk_changes,
    normalize_copy_format,
    normalize_schema,
    schema_format as get_schema_format,
    validate_template_id,
    validate_template_payload,
    validate_copy_format_references,
)


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = Path(__file__).with_name("nasukeru.db")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024


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
    if "base_version_id" in row.keys():
        version["base_version_id"] = row["base_version_id"]
    if "status" in row.keys():
        version["status"] = row["status"]
    if include_schema:
        schema = parse_json_value(row["schema_json"])
        schema = normalize_db_template_schema(schema)
        copy_format = parse_json_value(row["copy_format_json"])
        version["schema"] = schema
        version["copy_format"] = copy_format
        version["warnings"] = collect_template_warnings(schema, copy_format)
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


def require_optional_text(payload, field, fallback=""):
    value = payload.get(field, fallback)
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise TemplateValidationError(f"{field} must be a string")
    return value.strip()


def require_base_version_id(payload):
    if "base_version_id" not in payload:
        raise TemplateValidationError("base_version_id is required")
    value = payload.get("base_version_id")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TemplateValidationError("base_version_id must be a positive integer or null")
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
    if "schema_json" in row.keys() and row["schema_json"] is not None:
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
          v.schema_json AS schema_json
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
          v.schema_json AS current_schema_json,
          v.copy_format_json AS current_copy_format_json,
          latest.schema_json AS latest_schema_json,
          latest.copy_format_json AS latest_copy_format_json
        FROM templates t
        LEFT JOIN template_versions v ON v.id = t.current_version_id
        LEFT JOIN template_versions latest ON latest.id = (
            SELECT tv.id
            FROM template_versions tv
            WHERE tv.template_id = t.id
            ORDER BY tv.version_number DESC
            LIMIT 1
        )
        WHERE t.id = ?
        """,
        (template_id,),
    ).fetchone()


def fetch_template_version_state(conn, template_id, version_id):
    return conn.execute(
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
          approved_at,
          base_version_id,
          status
        FROM template_versions
        WHERE template_id = ? AND id = ?
        """,
        (template_id, version_id),
    ).fetchone()


def validate_version_definition(row):
    schema = normalize_db_template_schema(parse_json_value(row["schema_json"]))
    try:
        copy_format = normalize_copy_format(parse_json_value(row["copy_format_json"]))
        validate_copy_format_references(schema, copy_format)
    except SchemaValidationError as error:
        raise TemplateValidationError(str(error)) from error
    return schema, copy_format


def collect_template_warnings(schema, copy_format):
    return collect_unreferenced_fields(schema, copy_format) + collect_duplicate_section_conditions(schema)


def unreferenced_confirmation_response(unreferenced_fields):
    return jsonify(
        {
            "ok": False,
            "error": "unreferenced fields require confirmation",
            "unreferenced_fields": unreferenced_fields,
        }
    ), 409


def require_unreferenced_confirmation(payload, schema, copy_format):
    unreferenced_fields = collect_unreferenced_fields(schema, copy_format)
    if unreferenced_fields and payload.get("confirm_unreferenced") is not True:
        return unreferenced_fields
    return []


def admin_template_detail_from_row(row):
    schema_json = row["current_schema_json"] or row["latest_schema_json"]
    copy_format_json = row["current_copy_format_json"] if row["current_schema_json"] is not None else row["latest_copy_format_json"]
    schema = parse_json_value(schema_json)
    schema = normalize_db_template_schema(schema)
    copy_format = parse_json_value(copy_format_json)
    return {
        **template_summary_from_row(row),
        "schema": schema,
        "copy_format": copy_format,
        "schema_format": get_schema_format(schema),
        "warnings": collect_template_warnings(schema, copy_format),
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
    app.logger.warning("database not ready: %s", error)
    return jsonify({"ok": False, "error": "database not ready"}), 503


@app.errorhandler(sqlite3.Error)
def handle_database_error(error):
    app.logger.exception("database error")
    return jsonify({"ok": False, "error": "database error"}), 500


@app.errorhandler(413)
def handle_payload_too_large(error):
    return jsonify({"ok": False, "error": "payload too large"}), 413


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
              v.schema_json AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE (? = 1 OR t.is_active = 1)
              AND t.current_version_id IS NOT NULL
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
              v.schema_json AS schema_json
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
    warnings = collect_template_warnings(validated["schema"], validated["copy_format"])
    unreferenced_fields = require_unreferenced_confirmation(payload, validated["schema"], validated["copy_format"])
    if unreferenced_fields:
        return unreferenced_confirmation_response(unreferenced_fields)
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
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, NULL, 'draft')
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
               change_summary, change_reason, created_by, created_at, approved_by, approved_at, base_version_id, status)
            VALUES (?, 1, ?, ?, ?, ?, 'local', ?, NULL, NULL, NULL, 'draft')
            """,
            (
                validated["id"],
                schema_json,
                copy_format_json,
                change_summary,
                validated["change_reason"],
                timestamp,
            ),
        )
        version_id = cursor.lastrowid
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
    response = {"ok": True, "template": summary, "version_id": version_id, "status": "draft"}
    if warnings:
        response["warnings"] = warnings
    return jsonify(response), 201


@app.post("/api/templates/<template_id>/versions")
def create_template_version(template_id):
    payload = require_json_body()
    base_version_id = require_base_version_id(payload)
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
    warnings = collect_template_warnings(validated["schema"], validated["copy_format"])
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
        before_schema = None
        before_copy_format = None
        if template["current_schema_json"] is not None:
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
               change_summary, change_reason, created_by, created_at, approved_by, approved_at, base_version_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'local', ?, NULL, NULL, ?, 'draft')
            """,
            (
                template_id,
                version_number,
                schema_json,
                copy_format_json,
                validated["change_summary"],
                validated["change_reason"],
                timestamp,
                base_version_id,
            ),
        )
        version_id = cursor.lastrowid
        insert_audit_log(
            conn,
            template_id,
            version_id,
            "create_draft",
            timestamp,
            validated["change_reason"],
            before={
                "schema": before_schema,
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
            "status": "draft",
            "high_risk_changes": high_risk_changes,
            "warnings": warnings,
        }
    ), 201


@app.post("/api/templates/<template_id>/versions/<int:version_id>/publish")
def publish_template_version(template_id, version_id):
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
            raise TemplateStateError("deleted template cannot be published")
        target = fetch_template_version_state(conn, template_id, version_id)
        if target is None:
            return jsonify({"ok": False, "error": "template version not found"}), 404
        if target["status"] != "draft":
            raise TemplateStateError("only draft versions can be published")
        if target["base_version_id"] != template["current_version_id"]:
            raise TemplateStateError("draft was created from an outdated published version")

        target_schema, target_copy_format = validate_version_definition(target)
        before_schema = None
        before_copy_format = None
        high_risk_changes = []
        if template["current_schema_json"] is not None:
            before_schema = normalize_db_template_schema(parse_json_value(template["current_schema_json"]))
            before_copy_format = parse_json_value(template["current_copy_format_json"])
            high_risk_changes = detect_high_risk_changes(
                before_schema,
                target_schema,
                before_copy_format,
                target_copy_format,
            )
        if high_risk_changes and payload.get("confirm_high_risk") is not True:
            conn.rollback()
            return jsonify(
                {
                    "ok": False,
                    "error": "high risk changes require confirmation",
                    "high_risk_changes": high_risk_changes,
                }
            ), 409
        unreferenced_fields = require_unreferenced_confirmation(payload, target_schema, target_copy_format)
        if unreferenced_fields:
            conn.rollback()
            return unreferenced_confirmation_response(unreferenced_fields)

        conn.execute(
            """
            UPDATE template_versions
            SET status = 'published', approved_by = 'local', approved_at = ?
            WHERE id = ? AND template_id = ?
            """,
            (timestamp, version_id, template_id),
        )
        schema_json = json_dumps(target_schema)
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?, status = 'published'
            WHERE id = ?
            """,
            (schema_json, version_id, timestamp, template_id),
        )
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'retired'
            WHERE template_id = ? AND status = 'published' AND id <> ?
            """,
            (template_id, version_id),
        )
        insert_audit_log(
            conn,
            template_id,
            version_id,
            "publish",
            timestamp,
            reason,
            before={
                "schema": parse_json_value(template["current_schema_json"]),
                "copy_format": before_copy_format,
                "current_version_id": template["current_version_id"],
            },
            after={
                "schema": target_schema,
                "copy_format": target_copy_format,
                "current_version_id": version_id,
            },
            diff={"high_risk_changes": high_risk_changes},
        )
        summary = fetch_template_summary(conn, template_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"ok": True, "template": summary, "high_risk_changes": high_risk_changes})


@app.post("/api/templates/<template_id>/versions/<int:version_id>/rollback")
def rollback_template_version(template_id, version_id):
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
            raise TemplateStateError("deleted template cannot be rolled back")
        source = fetch_template_version_state(conn, template_id, version_id)
        if source is None:
            return jsonify({"ok": False, "error": "template version not found"}), 404
        if template["current_version_id"] == version_id:
            raise TemplateStateError("template is already using this version")

        source_schema, source_copy_format = validate_version_definition(source)
        before_schema = normalize_db_template_schema(parse_json_value(template["current_schema_json"]))
        before_copy_format = parse_json_value(template["current_copy_format_json"])
        high_risk_changes = detect_high_risk_changes(
            before_schema,
            source_schema,
            before_copy_format,
            source_copy_format,
        )
        if high_risk_changes and payload.get("confirm_high_risk") is not True:
            conn.rollback()
            return jsonify(
                {
                    "ok": False,
                    "error": "high risk changes require confirmation",
                    "high_risk_changes": high_risk_changes,
                }
            ), 409
        unreferenced_fields = require_unreferenced_confirmation(payload, source_schema, source_copy_format)
        if unreferenced_fields:
            conn.rollback()
            return unreferenced_confirmation_response(unreferenced_fields)

        version_number = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM template_versions
            WHERE template_id = ?
            """,
            (template_id,),
        ).fetchone()[0]
        schema_json = json_dumps(source_schema)
        copy_format_json = json_dumps(source_copy_format) if source_copy_format is not None else None
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'local', ?, 'local', ?, 'published')
            """,
            (
                template_id,
                version_number,
                schema_json,
                copy_format_json,
                f"Rollback to v{source['version_number']}",
                reason,
                timestamp,
                timestamp,
            ),
        )
        new_version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?, status = 'published'
            WHERE id = ?
            """,
            (schema_json, new_version_id, timestamp, template_id),
        )
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'retired'
            WHERE template_id = ? AND status = 'published' AND id <> ?
            """,
            (template_id, new_version_id),
        )
        insert_audit_log(
            conn,
            template_id,
            new_version_id,
            "rollback_publish",
            timestamp,
            reason,
            before={
                "schema": parse_json_value(template["current_schema_json"]),
                "copy_format": before_copy_format,
                "current_version_id": template["current_version_id"],
            },
            after={
                "schema": source_schema,
                "copy_format": source_copy_format,
                "current_version_id": new_version_id,
            },
            diff={
                "source_version_id": version_id,
                "high_risk_changes": high_risk_changes,
            },
        )
        summary = fetch_template_summary(conn, template_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify(
        {
            "ok": True,
            "template": summary,
            "source_version_id": version_id,
            "version_id": new_version_id,
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
              v.schema_json AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ? AND t.is_active = 1 AND t.current_version_id IS NOT NULL
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
              approved_at,
              base_version_id,
              status
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
              approved_at,
              base_version_id,
              status
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


def require_list(payload, key):
    value = payload.get(key)
    if not isinstance(value, list):
        raise TemplateValidationError(f"{key} must be an array")
    return value


def require_discovery_text(item, key, path):
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TemplateValidationError(f"{path}.{key} is required")
    return value.strip()


def require_discovery_id(value, field):
    try:
        return validate_template_id(value)
    except SchemaValidationError as error:
        raise TemplateValidationError(f"{field}: {error}") from error


def validate_discovery_target(conn, target_type, target_id, field):
    if target_type not in {"template", "group"}:
        raise TemplateValidationError(f"{field}.target_type must be template or group")
    require_discovery_id(target_id, f"{field}.target_id")
    if target_type == "template":
        row = conn.execute(
            "SELECT id FROM templates WHERE id = ? AND is_active = 1 AND current_version_id IS NOT NULL",
            (target_id,),
        ).fetchone()
        if row is None:
            raise TemplateValidationError(f"{field}.target_id references unknown published template: {target_id}")
        return
    row = conn.execute(
        "SELECT id FROM template_groups WHERE id = ? AND is_active = 1",
        (target_id,),
    ).fetchone()
    if row is None:
        raise TemplateValidationError(f"{field}.target_id references unknown active group: {target_id}")


def discovery_quick_from_row(row):
    return {
        "id": row["id"],
        "label": row["label"],
        "sub": row["sub"],
        "action": row["action"],
        "display_order": row["display_order"],
        "target": {
            "type": row["target_type"] or "template",
            "id": row["target_id"] or row["action"],
        },
    }


def discovery_keyword_from_row(row):
    return {
        "id": row["id"],
        "keyword": row["keyword"],
        "template_action": row["template_action"],
        "display_order": row["display_order"],
        "target": {
            "type": row["target_type"] or "template",
            "id": row["target_id"] or row["template_action"],
        },
    }


def discovery_group_from_row(row, items):
    return {
        "id": row["id"],
        "label": row["label"],
        "sub": row["sub"],
        "display_order": row["display_order"],
        "is_active": bool(row["is_active"]),
        "items": items.get(row["id"], []),
    }


@app.get("/api/admin/discovery")
def get_admin_discovery():
    with connect() as conn:
        quick_rows = conn.execute(
            """
            SELECT id, label, sub, action, target_type, target_id, display_order
            FROM quick_templates
            ORDER BY display_order, label
            """
        ).fetchall()
        keyword_rows = conn.execute(
            """
            SELECT id, keyword, template_action, target_type, target_id, display_order
            FROM search_keywords
            ORDER BY display_order, keyword
            """
        ).fetchall()
        group_rows = conn.execute(
            """
            SELECT id, label, sub, display_order, is_active
            FROM template_groups
            ORDER BY display_order, label
            """
        ).fetchall()
        item_rows = conn.execute(
            """
            SELECT group_id, template_id
            FROM template_group_items
            ORDER BY group_id, display_order, template_id
            """
        ).fetchall()
        template_rows = conn.execute(
            """
            SELECT id, label, full, is_active, current_version_id
            FROM templates
            ORDER BY display_order, label
            """
        ).fetchall()

    group_items = {}
    for row in item_rows:
        group_items.setdefault(row["group_id"], []).append(row["template_id"])

    return jsonify(
        {
            "quick_templates": [discovery_quick_from_row(row) for row in quick_rows],
            "search_keywords": [discovery_keyword_from_row(row) for row in keyword_rows],
            "template_groups": [discovery_group_from_row(row, group_items) for row in group_rows],
            "templates": [
                {
                    "id": row["id"],
                    "label": row["label"],
                    "full": row["full"],
                    "is_active": bool(row["is_active"]),
                    "current_version_id": row["current_version_id"],
                }
                for row in template_rows
            ],
        }
    )


@app.post("/api/admin/discovery/quick-templates")
def save_admin_quick_templates():
    require_local_post_guard()
    payload = require_json_body()
    items = require_list(payload, "items")
    normalized = []
    with connect() as conn:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise TemplateValidationError(f"items[{index}] must be an object")
            path = f"items[{index}]"
            label = require_discovery_text(item, "label", path)
            sub = require_optional_text(item, "sub")
            target = item.get("target") if isinstance(item.get("target"), dict) else {}
            target_type = require_optional_text(target, "type", "template")
            target_id = require_discovery_text(target, "id", f"{path}.target")
            validate_discovery_target(conn, target_type, target_id, path)
            action = require_optional_text(item, "action") or target_id
            normalized.append((label, sub, action, target_type, target_id, index + 1))
        conn.execute("DELETE FROM quick_templates")
        conn.executemany(
            """
            INSERT INTO quick_templates (label, sub, action, target_type, target_id, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            normalized,
        )
    return jsonify({"ok": True, "count": len(normalized)})


@app.post("/api/admin/discovery/search-keywords")
def save_admin_search_keywords():
    require_local_post_guard()
    payload = require_json_body()
    items = require_list(payload, "items")
    normalized = []
    with connect() as conn:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise TemplateValidationError(f"items[{index}] must be an object")
            path = f"items[{index}]"
            keyword = require_discovery_text(item, "keyword", path)
            target = item.get("target") if isinstance(item.get("target"), dict) else {}
            target_type = require_optional_text(target, "type", "template")
            target_id = require_discovery_text(target, "id", f"{path}.target")
            validate_discovery_target(conn, target_type, target_id, path)
            template_action = require_optional_text(item, "template_action") or target_id
            normalized.append((keyword, template_action, target_type, target_id, index + 1))
        conn.execute("DELETE FROM search_keywords")
        conn.executemany(
            """
            INSERT INTO search_keywords (keyword, template_action, target_type, target_id, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            normalized,
        )
    return jsonify({"ok": True, "count": len(normalized)})


@app.post("/api/admin/discovery/template-groups")
def save_admin_template_groups():
    require_local_post_guard()
    payload = require_json_body()
    groups = require_list(payload, "groups")
    now = now_iso()
    normalized_groups = []
    normalized_items = []
    seen_group_ids = set()
    with connect() as conn:
        template_ids = {
            row["id"]
            for row in conn.execute("SELECT id FROM templates WHERE is_active = 1 AND current_version_id IS NOT NULL").fetchall()
        }
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise TemplateValidationError(f"groups[{group_index}] must be an object")
            path = f"groups[{group_index}]"
            group_id = require_discovery_id(group.get("id"), f"{path}.id")
            if group_id in seen_group_ids:
                raise TemplateValidationError(f"{path}.id is duplicated: {group_id}")
            seen_group_ids.add(group_id)
            label = require_discovery_text(group, "label", path)
            sub = require_optional_text(group, "sub")
            is_active = bool(group.get("is_active", True))
            items = group.get("items", [])
            if not isinstance(items, list):
                raise TemplateValidationError(f"{path}.items must be an array")
            normalized_groups.append((group_id, label, sub, group_index + 1, 1 if is_active else 0, now, now))
            for item_index, template_id in enumerate(items):
                template_id = require_discovery_id(template_id, f"{path}.items[{item_index}]")
                if template_id not in template_ids:
                    raise TemplateValidationError(f"{path}.items[{item_index}] references unknown published template: {template_id}")
                normalized_items.append((group_id, template_id, item_index + 1))

        conn.execute("DELETE FROM template_group_items")
        conn.execute("DELETE FROM template_groups")
        conn.executemany(
            """
            INSERT INTO template_groups
              (id, label, sub, display_order, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            normalized_groups,
        )
        conn.executemany(
            """
            INSERT INTO template_group_items (group_id, template_id, display_order)
            VALUES (?, ?, ?)
            """,
            normalized_items,
        )
    return jsonify({"ok": True, "count": len(normalized_groups)})


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
              v.schema_json AS schema_json,
              v.copy_format_json AS copy_format_json
            FROM template_group_items gi
            JOIN templates t ON t.id = gi.template_id
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE gi.group_id = ? AND t.is_active = 1 AND t.current_version_id IS NOT NULL
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
        app.logger.warning("database not ready: %s", error)
        return jsonify({"ok": False, "database": "missing"}), 503
    except sqlite3.Error as error:
        app.logger.exception("database health check failed")
        return jsonify({"ok": False, "database": "error"}), 500
    return jsonify({"ok": True, "database": "connected", "db_path": str(get_db_path()), "counts": counts})


def env_flag(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    if not get_db_path().exists():
        raise SystemExit("DB not found. Run: py -3.10 server/init_db.py")
    host = os.environ.get("NASUKERU_HOST", "127.0.0.1")
    port = int(os.environ.get("NASUKERU_PORT", "8000"))
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if host not in local_hosts and not env_flag("NASUKERU_ALLOW_EXTERNAL"):
        logging.warning("Refusing non-local bind host %s without NASUKERU_ALLOW_EXTERNAL=1", host)
        raise SystemExit("External bind is disabled. Set NASUKERU_ALLOW_EXTERNAL=1 to allow it.")
    if host not in local_hosts:
        logging.warning("Nasukeru is binding to non-local host %s. Do not expose without proper network controls.", host)
    app.run(host=host, port=port, debug=env_flag("NASUKERU_DEBUG"))
