import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).with_name("nasukeru.db")


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


def main():
    now = datetime.now(timezone.utc).isoformat()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS templates;
            DROP TABLE IF EXISTS rest_options;
            DROP TABLE IF EXISTS quick_templates;

            CREATE TABLE templates (
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

            CREATE TABLE rest_options (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              label TEXT NOT NULL,
              display_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE quick_templates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              label TEXT NOT NULL,
              sub TEXT NOT NULL,
              action TEXT NOT NULL,
              display_order INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        for order, template in enumerate(STROKE_TYPES, start=1):
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

        for order, label in enumerate(REST_OPTIONS, start=1):
            conn.execute(
                "INSERT INTO rest_options (label, display_order) VALUES (?, ?)",
                (label, order),
            )

        for order, item in enumerate(QUICK_TEMPLATES, start=1):
            conn.execute(
                """
                INSERT INTO quick_templates (label, sub, action, display_order)
                VALUES (?, ?, ?, ?)
                """,
                (item["label"], item["sub"], item["action"], order),
            )

    print(f"Initialized {DB_PATH}")


if __name__ == "__main__":
    main()
