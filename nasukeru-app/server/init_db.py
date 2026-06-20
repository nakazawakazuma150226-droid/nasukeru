import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from template_schema import SchemaValidationError, normalize_schema, validate_template_id


DEFAULT_DB_PATH = Path(__file__).with_name("nasukeru.db")


STROKE_TYPES = [
    {
        "id": "mca",
        "label": "MCA",
        "full": "MCA領域梗塞（中大脳動脈）",
        "vitals": {"jcs": "", "t": "", "bp": "", "hr": "", "spo2": ""},
        "symptoms": {"headache": "", "dizzy": "", "nausea": ""},
        "neuro": {
            "pupil": "",
            "light": "",
            "eye": "",
            "barre": "",
            "mingazzini": "",
            "mmt": {"ru": "", "rl": "", "lu": "", "ll": ""},
            "nihss": "",
            "other": "",
        },
        "rest": "",
    },
    {
        "id": "aca",
        "label": "ACA",
        "full": "ACA領域梗塞（前大脳動脈）",
        "vitals": {"jcs": "", "t": "", "bp": "", "hr": "", "spo2": ""},
        "symptoms": {"headache": "", "dizzy": "", "nausea": ""},
        "neuro": {
            "pupil": "",
            "light": "",
            "eye": "",
            "barre": "",
            "mingazzini": "",
            "mmt": {"ru": "", "rl": "", "lu": "", "ll": ""},
            "nihss": "",
            "other": "",
        },
        "rest": "",
    },
    {
        "id": "pca",
        "label": "PCA",
        "full": "PCA領域梗塞（後大脳動脈）",
        "vitals": {"jcs": "", "t": "", "bp": "", "hr": "", "spo2": ""},
        "symptoms": {"headache": "", "dizzy": "", "nausea": ""},
        "neuro": {
            "pupil": "",
            "light": "",
            "eye": "",
            "barre": "",
            "mingazzini": "",
            "mmt": {"ru": "", "rl": "", "lu": "", "ll": ""},
            "nihss": "",
            "other": "",
        },
        "rest": "",
    },
    {
        "id": "lacunar",
        "label": "ラクナ",
        "full": "ラクナ梗塞／穿通枝梗塞",
        "vitals": {"jcs": "", "t": "", "bp": "", "hr": "", "spo2": ""},
        "symptoms": {"headache": "", "dizzy": "", "nausea": ""},
        "neuro": {
            "pupil": "",
            "light": "",
            "eye": "",
            "barre": "",
            "mingazzini": "",
            "mmt": {"ru": "", "rl": "", "lu": "", "ll": ""},
            "nihss": "",
            "other": "",
        },
        "rest": "",
    },
    {
        "id": "brainstem",
        "label": "脳幹",
        "full": "脳幹梗塞",
        "vitals": {"jcs": "", "t": "", "bp": "", "hr": "", "spo2": ""},
        "symptoms": {"headache": "", "dizzy": "", "nausea": ""},
        "neuro": {
            "pupil": "",
            "light": "",
            "eye": "",
            "barre": "",
            "mingazzini": "",
            "mmt": {"ru": "", "rl": "", "lu": "", "ll": ""},
            "nihss": "",
            "other": "",
        },
        "rest": "",
    },
]

REST_OPTIONS = ["ベッド上安静", "ベッド上フリー", "病棟内フリー", "院内フリー", "リハビリに準ずる"]
QUICK_TEMPLATES = [{"label": "脳梗塞", "sub": "5パターン専用テンプレ", "action": "stroke"}]
SEARCH_KEYWORDS = [
    {"keyword": "脳梗塞", "template_action": "stroke"},
    {"keyword": "脳卒中", "template_action": "stroke"},
    {"keyword": "stroke", "template_action": "stroke"},
]


def get_db_path():
    return Path(os.environ.get("NASUKERU_DB_PATH", DEFAULT_DB_PATH)).expanduser()


def connect(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def validate_template(template):
    try:
        validate_template_id(template.get("id"))
        normalize_schema(
            {
                "vitals": template.get("vitals"),
                "symptoms": template.get("symptoms"),
                "neuro": template.get("neuro"),
                "rest": template.get("rest"),
            }
        )
    except SchemaValidationError as error:
        raise ValueError(f"template {template.get('id', '<unknown>')} invalid: {error}") from error


def validate_seed_data():
    ids = set()
    for template in STROKE_TYPES:
        validate_template(template)
        if template["id"] in ids:
            raise ValueError(f"duplicate template id: {template['id']}")
        ids.add(template["id"])
    if len(set(REST_OPTIONS)) != len(REST_OPTIONS):
        raise ValueError("duplicate rest option")
    actions = [item["action"] for item in QUICK_TEMPLATES]
    if len(set(actions)) != len(actions):
        raise ValueError("duplicate quick template action")
    keywords = [item["keyword"] for item in SEARCH_KEYWORDS]
    if len(set(keywords)) != len(keywords):
        raise ValueError("duplicate search keyword")


def ensure_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS templates (
          id TEXT PRIMARY KEY,
          label TEXT NOT NULL,
          full TEXT NOT NULL,
          category TEXT NOT NULL,
          schema_json TEXT NOT NULL,
          is_active INTEGER NOT NULL DEFAULT 1,
          display_order INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS template_versions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          template_id TEXT NOT NULL,
          version_number INTEGER NOT NULL,
          schema_json TEXT NOT NULL,
          copy_format_json TEXT,
          change_summary TEXT,
          change_reason TEXT,
          created_by TEXT NOT NULL DEFAULT 'system',
          created_at TEXT NOT NULL,
          approved_by TEXT,
          approved_at TEXT,
          FOREIGN KEY (template_id) REFERENCES templates(id),
          UNIQUE (template_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS template_audit_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          template_id TEXT NOT NULL,
          version_id INTEGER,
          action TEXT NOT NULL,
          actor_id TEXT,
          actor_name TEXT NOT NULL DEFAULT 'system',
          acted_at TEXT NOT NULL,
          before_json TEXT,
          after_json TEXT,
          diff_json TEXT,
          reason TEXT,
          client_info TEXT,
          FOREIGN KEY (template_id) REFERENCES templates(id),
          FOREIGN KEY (version_id) REFERENCES template_versions(id)
        );

        CREATE TABLE IF NOT EXISTS rest_options (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          label TEXT NOT NULL,
          display_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS quick_templates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          label TEXT NOT NULL,
          sub TEXT NOT NULL,
          action TEXT NOT NULL,
          display_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS search_keywords (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          keyword TEXT NOT NULL,
          template_action TEXT NOT NULL,
          display_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_rest_options_label
          ON rest_options(label);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_quick_templates_action
          ON quick_templates(action);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_search_keywords_keyword
          ON search_keywords(keyword);

        CREATE INDEX IF NOT EXISTS idx_template_versions_template_id
          ON template_versions(template_id);

        CREATE INDEX IF NOT EXISTS idx_template_audit_logs_template_id
          ON template_audit_logs(template_id);
        """
    )
    ensure_column(conn, "templates", "current_version_id", "INTEGER")
    ensure_column(conn, "templates", "status", "TEXT NOT NULL DEFAULT 'published'")


def ensure_column(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def record_migration(conn, version, name, now):
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name, applied_at)
        VALUES (?, ?, ?)
        """,
        (version, name, now),
    )


def exists(conn, query, params):
    return conn.execute(query, params).fetchone() is not None


def seed_templates(conn, now):
    for order, template in enumerate(STROKE_TYPES, start=1):
        if exists(conn, "SELECT 1 FROM templates WHERE id = ?", (template["id"],)):
            continue
        schema = {
            "vitals": template["vitals"],
            "symptoms": template["symptoms"],
            "neuro": template["neuro"],
            "rest": template["rest"],
        }
        schema = normalize_schema(schema)
        conn.execute(
            """
            INSERT INTO templates
              (id, label, full, category, schema_json, is_active, display_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                template["id"],
                template["label"],
                template["full"],
                "stroke",
                json.dumps(schema, ensure_ascii=False),
                order,
                now,
                now,
            ),
        )


def migrate_template_versions(conn, now):
    rows = conn.execute(
        """
        SELECT id, schema_json, current_version_id
        FROM templates
        WHERE is_active = 1
        ORDER BY display_order, id
        """
    ).fetchall()
    for template_id, schema_json, current_version_id in rows:
        if current_version_id:
            continue

        existing = conn.execute(
            """
            SELECT id
            FROM template_versions
            WHERE template_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (template_id,),
        ).fetchone()
        if existing:
            version_id = existing[0]
        else:
            cursor = conn.execute(
                """
                INSERT INTO template_versions
                  (template_id, version_number, schema_json, copy_format_json,
                   change_summary, change_reason, created_by, created_at, approved_by, approved_at)
                VALUES (?, 1, ?, NULL, ?, ?, 'system', ?, 'system', ?)
                """,
                (
                    template_id,
                    schema_json,
                    "Initial version migrated from templates.schema_json",
                    "Prepare versioned template storage",
                    now,
                    now,
                ),
            )
            version_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO template_audit_logs
                  (template_id, version_id, action, actor_name, acted_at, after_json, reason)
                VALUES (?, ?, 'migrate', 'system', ?, ?, ?)
                """,
                (
                    template_id,
                    version_id,
                    now,
                    schema_json,
                    "Create initial template version",
                ),
            )

        conn.execute(
            "UPDATE templates SET current_version_id = ?, status = 'published', updated_at = ? WHERE id = ?",
            (version_id, now, template_id),
        )


def seed_rest_options(conn):
    for order, label in enumerate(REST_OPTIONS, start=1):
        if exists(conn, "SELECT 1 FROM rest_options WHERE label = ?", (label,)):
            continue
        conn.execute(
            "INSERT INTO rest_options (label, display_order) VALUES (?, ?)",
            (label, order),
        )


def seed_quick_templates(conn):
    for order, item in enumerate(QUICK_TEMPLATES, start=1):
        if exists(conn, "SELECT 1 FROM quick_templates WHERE action = ?", (item["action"],)):
            continue
        conn.execute(
            """
            INSERT INTO quick_templates (label, sub, action, display_order)
            VALUES (?, ?, ?, ?)
            """,
            (item["label"], item["sub"], item["action"], order),
        )


def seed_search_keywords(conn):
    for order, item in enumerate(SEARCH_KEYWORDS, start=1):
        if exists(conn, "SELECT 1 FROM search_keywords WHERE keyword = ?", (item["keyword"],)):
            continue
        conn.execute(
            """
            INSERT INTO search_keywords (keyword, template_action, display_order)
            VALUES (?, ?, ?)
            """,
            (item["keyword"], item["template_action"], order),
        )


def main():
    validate_seed_data()
    now = datetime.now(timezone.utc).isoformat()
    db_path = get_db_path()
    with connect(db_path) as conn:
        ensure_schema(conn)
        record_migration(conn, "001", "initial sqlite template api", now)
        record_migration(conn, "002", "versioned template schema", now)
        record_migration(conn, "003", "read-only operational APIs", now)
        seed_templates(conn, now)
        migrate_template_versions(conn, now)
        seed_rest_options(conn)
        seed_quick_templates(conn)
        seed_search_keywords(conn)
    print(f"Prepared {db_path}")


if __name__ == "__main__":
    main()
