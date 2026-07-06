import json
import os
from datetime import datetime, timezone
from pathlib import Path

from init_db import DEFAULT_DB_PATH, NEURO_COMMON_TEMPLATE, connect
from template_fixes_010 import build_corrected_neuro_common_schema, build_corrected_neuro_common_copy_format
from template_schema import normalize_copy_format, validate_copy_format_references


MIGRATION_VERSION = "011"
MIGRATION_NAME = "unify neuro_common swallow/treatment fields with genesis spec"

RENAMED_ANTIHYPERTENSIVE_OTHER_LINE_TEXT = "その他の降圧薬：{{treatment.antihypertensive_other}}"


def build_aligned_neuro_common_copy_format():
    # build_corrected_neuro_common_schema() already reflects the genesis (init_db.py)
    # field spec for thickened_water_level / dysphagia_diet_level / antihypertensive_other
    # (migration 010's inserts for these are no-ops once genesis already provides them,
    # see has_field() in template_fixes_010.py). Only the copy_format still needs a
    # targeted fix: migration 010 labels the antihypertensive-other line "その他の降圧薬"
    # while the genesis spec (init_db.py::build_neuro_common_copy_format) uses "降圧薬その他".
    # Keep it as its own showIf-gated line (not concatenated onto the antihypertensive
    # line) so a blank value never renders as an unlabeled "__" glued to another field's
    # value. Reuse migration 010's copy_format wholesale and adjust just this one line,
    # so every other line (JCS, eye, motor, NIHSS, ...) is untouched.
    base = build_corrected_neuro_common_copy_format()
    lines = []
    for line in base["lines"]:
        if isinstance(line, dict) and line.get("text") == RENAMED_ANTIHYPERTENSIVE_OTHER_LINE_TEXT:
            lines.append({**line, "text": "降圧薬その他：{{treatment.antihypertensive_other}}。"})
            continue
        lines.append(line)
    return normalize_copy_format({"format": "text-v1", "lines": lines})


def get_db_path():
    return Path(os.environ.get("NASUKERU_DB_PATH", DEFAULT_DB_PATH)).expanduser()


def migration_applied(conn):
    return conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (MIGRATION_VERSION,)).fetchone() is not None


def current_template_definition(conn, template_id):
    return conn.execute(
        """
        SELECT t.current_version_id,
               COALESCE(v.schema_json, t.schema_json) AS schema_json,
               v.copy_format_json AS copy_format_json
        FROM templates t
        LEFT JOIN template_versions v ON v.id = t.current_version_id
        WHERE t.id = ?
        """,
        (template_id,),
    ).fetchone()


def publish_system_version(conn, template_id, schema, copy_format, summary, reason, now):
    validate_copy_format_references(schema, copy_format)
    current = current_template_definition(conn, template_id)
    if current is None:
        return None
    current_schema = json.loads(current[1])
    current_copy_format = json.loads(current[2]) if current[2] else None
    if current_schema == schema and current_copy_format == copy_format:
        return current[0]

    version_number = conn.execute(
        "SELECT COALESCE(MAX(version_number), 0) + 1 FROM template_versions WHERE template_id = ?",
        (template_id,),
    ).fetchone()[0]
    cursor = conn.execute(
        """
        INSERT INTO template_versions
          (template_id, version_number, schema_json, copy_format_json,
           change_summary, change_reason, created_by, created_at,
           approved_by, approved_at, base_version_id, status)
        VALUES (?, ?, ?, ?, ?, ?, 'system', ?, 'system', ?, ?, 'published')
        """,
        (
            template_id, version_number, json.dumps(schema, ensure_ascii=False),
            json.dumps(copy_format, ensure_ascii=False), summary, reason,
            now, now, current[0],
        ),
    )
    version_id = cursor.lastrowid
    conn.execute(
        "UPDATE templates SET schema_json = ?, current_version_id = ?, updated_at = ?, status = 'published' WHERE id = ?",
        (json.dumps(schema, ensure_ascii=False), version_id, now, template_id),
    )
    conn.execute(
        "UPDATE template_versions SET status = 'retired' WHERE template_id = ? AND status = 'published' AND id <> ?",
        (template_id, version_id),
    )
    conn.execute(
        """
        INSERT INTO template_audit_logs
          (template_id, version_id, action, actor_name, acted_at, before_json, after_json, diff_json, reason)
        VALUES (?, ?, 'migrate', 'system', ?, ?, ?, ?, ?)
        """,
        (
            template_id, version_id, now,
            json.dumps({"schema": current_schema, "copy_format": current_copy_format}, ensure_ascii=False),
            json.dumps({"schema": schema, "copy_format": copy_format}, ensure_ascii=False),
            json.dumps({"migration": MIGRATION_VERSION}, ensure_ascii=False), reason,
        ),
    )
    return version_id


def apply_neuro_common_alignment(db_path=None):
    db_path = Path(db_path) if db_path is not None else get_db_path()
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        if migration_applied(conn):
            return False
        publish_system_version(
            conn, NEURO_COMMON_TEMPLATE["id"], build_corrected_neuro_common_schema(),
            build_aligned_neuro_common_copy_format(),
            "Unify swallow/treatment conditional fields with genesis spec",
            "Align thickened water options, dysphagia diet level type, and antihypertensive-other "
            "wording/placement across freshly seeded and previously migrated databases", now,
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (MIGRATION_VERSION, MIGRATION_NAME, now),
        )
    return True


def main():
    applied = apply_neuro_common_alignment()
    print("Applied neuro_common alignment migration 011" if applied else "Neuro_common alignment migration 011 already applied")


if __name__ == "__main__":
    main()
