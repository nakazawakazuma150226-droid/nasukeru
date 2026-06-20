import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


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
    required = ("id", "label", "full", "vitals", "symptoms", "neuro", "rest")
    missing = [key for key in required if key not in template]
    if missing:
        raise ValueError(f"template {template.get('id', '<unknown>')} missing: {', '.join(missing)}")
    if "mmt" not in template["neuro"]:
        raise ValueError(f"template {template['id']} missing: neuro.mmt")


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
        """
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
        seed_templates(conn, now)
        seed_rest_options(conn)
        seed_quick_templates(conn)
        seed_search_keywords(conn)
    print(f"Prepared {db_path}")


if __name__ == "__main__":
    main()
