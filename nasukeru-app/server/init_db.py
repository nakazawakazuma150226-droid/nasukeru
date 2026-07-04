import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from template_schema import (
    SchemaValidationError,
    normalize_copy_format,
    normalize_schema,
    validate_template_id,
)


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
JCS_OPTIONS = ["\u2160-1", "\u2160-2", "\u2160-3", "\u2161-10", "\u2161-20", "\u2161-30", "\u2162-100", "\u2162-200", "\u2162-300"]
NEURO_COMMON_TEMPLATE = {
    "id": "neuro_common",
    "label": "脳卒中共通",
    "full": "脳神経共通テンプレート",
    "category": "neuro_common",
}
QUICK_TEMPLATES = [
    {"label": "脳梗塞", "sub": "5パターン専用テンプレ", "action": "stroke", "target_type": "group", "target_id": "cerebral_infarction"},
    {"label": "脳卒中共通", "sub": "脳神経共通テンプレ", "action": "neuro_common", "target_type": "template", "target_id": "neuro_common"},
]
SEARCH_KEYWORDS = [
    {"keyword": "脳梗塞", "template_action": "stroke", "target_type": "group", "target_id": "cerebral_infarction"},
    {"keyword": "脳卒中", "template_action": "stroke", "target_type": "group", "target_id": "cerebral_infarction"},
    {"keyword": "stroke", "template_action": "stroke", "target_type": "group", "target_id": "cerebral_infarction"},
    {"keyword": "MCA", "template_action": "mca", "target_type": "template", "target_id": "mca"},
    {"keyword": "ACA", "template_action": "aca", "target_type": "template", "target_id": "aca"},
    {"keyword": "PCA", "template_action": "pca", "target_type": "template", "target_id": "pca"},
    {"keyword": "ラクナ", "template_action": "lacunar", "target_type": "template", "target_id": "lacunar"},
    {"keyword": "脳幹", "template_action": "brainstem", "target_type": "template", "target_id": "brainstem"},
    {"keyword": "脳卒中共通", "template_action": "neuro_common", "target_type": "template", "target_id": "neuro_common"},
    {"keyword": "脳神経共通テンプレート", "template_action": "neuro_common", "target_type": "template", "target_id": "neuro_common"},
]

TEMPLATE_GROUPS = [
    {
        "id": "cerebral_infarction",
        "label": "脳梗塞",
        "sub": "5パターン専用テンプレ",
        "items": ["mca", "aca", "pca", "lacunar", "brainstem"],
    }
]

STROKE_EXTRA_FIELDS = {
    "mca": [
        {"id": "left_mouth_droop", "label": "左口角下垂", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "left_sensory_dullness", "label": "左半身感覚鈍麻", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
    "aca": [
        {"id": "spontaneity_decrease", "label": "自発性低下", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "speech_amount_decrease", "label": "発語量低下", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "excretion", "label": "排泄", "type": "text", "allowEmpty": True, "placeholder": "例: 尿失禁にて経過"},
    ],
    "pca": [
        {"id": "left_homonymous_hemianopia", "label": "左同名半盲", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "visual_impairment", "label": "視覚障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "left_sensory_dullness", "label": "左半身感覚鈍麻", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
    "lacunar": [
        {"id": "mild_dysarthria", "label": "軽度構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "mild_facial_palsy", "label": "顔面麻痺軽度", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "sensory_disturbance", "label": "感覚障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
    "brainstem": [
        {"id": "horizontal_nystagmus_right_gaze", "label": "右方視時の水平性眼振", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "diplopia", "label": "複視", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysphagia", "label": "嚥下障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "limb_ataxia", "label": "四肢失調", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
}


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


def generic_field(field_id, label, field_type="text", **extra):
    field = {"id": field_id, "label": label, "type": field_type, "allowEmpty": True}
    field.update(extra)
    return field


def build_generic_stroke_schema(template):
    sections = [
        {
            "id": "vitals",
            "label": "バイタル",
            "displayOrder": 1,
            "fields": [
                generic_field("jcs", "JCS", "select", options=JCS_OPTIONS, requiredWarning=True),
                generic_field("t", "T", unit="℃", requiredWarning=True),
                generic_field("bp", "BP", unit="mmHg", requiredWarning=True),
                generic_field("hr", "HR", requiredWarning=True),
                generic_field("spo2", "SpO₂", unit="%", requiredWarning=True),
            ],
        },
        {
            "id": "symptoms",
            "label": "症状",
            "displayOrder": 2,
            "fields": [
                generic_field("headache", "頭痛"),
                generic_field("dizzy", "めまい"),
                generic_field("nausea", "嘔気"),
            ],
        },
        {
            "id": "neuro",
            "label": "神経所見",
            "displayOrder": 3,
            "fields": [
                generic_field("pupil", "瞳孔（左右）", placeholder="例: 2.5/2.5mm", requiredWarning=True),
                generic_field("light", "対光反射", placeholder="例: あり", requiredWarning=True),
                generic_field("eye", "眼球位置", placeholder="例: 正中位"),
                generic_field("barre", "バレー徴候"),
                generic_field("mingazzini", "ミンガッチー徴候"),
                generic_field("nihss", "NIHSS（別紙記録参照）", requiredWarning=True),
                generic_field("other", "その他神経症状", "textarea"),
            ],
        },
        {
            "id": "mmt",
            "label": "MMT",
            "displayOrder": 4,
            "fields": [
                generic_field("ru", "右上肢", requiredWarning=True),
                generic_field("rl", "右下肢", requiredWarning=True),
                generic_field("lu", "左上肢", requiredWarning=True),
                generic_field("ll", "左下肢", requiredWarning=True),
            ],
        },
        {
            "id": "stroke_findings",
            "label": f"{template['label']} 個別観察項目",
            "displayOrder": 5,
            "fields": STROKE_EXTRA_FIELDS[template["id"]],
        },
        {
            "id": "rest",
            "label": "安静度",
            "displayOrder": 6,
            "fields": [
                generic_field("level", "安静度", "select", options=REST_OPTIONS, requiredWarning=True),
            ],
        },
    ]
    return normalize_schema({"schemaFormat": "generic-v1", "sections": sections})


def build_generic_stroke_copy_format(template):
    extra_lines = [
        {
            "text": f"{field['label']}：{{{{stroke_findings.{field['id']}}}}}",
            "omitIfAllBlank": [f"stroke_findings.{field['id']}"],
        }
        for field in STROKE_EXTRA_FIELDS[template["id"]]
    ]
    return normalize_copy_format(
        {
            "format": "text-v1",
            "lines": [
                template["full"],
                "",
                "JCS{{vitals.jcs}}　T{{vitals.t}}℃　BP{{vitals.bp}}mmHg　HR{{vitals.hr}}　SpO₂{{vitals.spo2}}%",
                "",
                "頭痛：{{symptoms.headache}}",
                "めまい：{{symptoms.dizzy}}",
                "嘔気：{{symptoms.nausea}}",
                "",
                "神経所見",
                "瞳孔：{{neuro.pupil}}",
                "対光反射：{{neuro.light}}",
                "眼球位置：{{neuro.eye}}",
                {"text": "バレー徴候：{{neuro.barre}}", "omitIfAllBlank": ["neuro.barre"]},
                {"text": "ミンガッチー徴候：{{neuro.mingazzini}}", "omitIfAllBlank": ["neuro.mingazzini"]},
                "MMT：右上肢{{mmt.ru}}、右下肢{{mmt.rl}}、左上肢{{mmt.lu}}、左下肢{{mmt.ll}}",
                "NIHSS：{{neuro.nihss}}",
                {"text": "{{neuro.other}}", "splitLinesFrom": "neuro.other", "omitIfAllBlank": ["neuro.other"]},
                *extra_lines,
                "",
                "安静度",
                "{{rest.level}}",
            ],
        }
    )


def build_neuro_common_schema():
    sections = [
        {
            "id": "consciousness",
            "label": "意識レベル",
            "displayOrder": 1,
            "fields": [
                generic_field("jcs", "JCS", "select", options=JCS_OPTIONS, requiredWarning=True),
            ],
        },
        {
            "id": "vitals",
            "label": "バイタルサイン",
            "displayOrder": 2,
            "fields": [
                generic_field("t", "体温", "number", unit="℃", step=0.1, requiredWarning=True),
                generic_field("bp", "血圧", requiredWarning=True, placeholder="例: 120/70"),
                generic_field("hr", "心拍数", "number", unit="回/分", min=0, step=1, requiredWarning=True),
                generic_field("ecg_rhythm", "心電図リズム", "select", options=["SR", "Af", "PAC", "PVC", "その他"]),
                generic_field("spo2", "SpO₂", "number", unit="%", min=0, max=100, step=1, requiredWarning=True),
                generic_field("oxygen_use", "酸素使用", "select", options=["RA", "O2使用"]),
                generic_field("oxygen_flow", "酸素流量", "number", unit="L", min=0, step=0.5),
            ],
        },
        {
            "id": "eye",
            "label": "瞳孔・眼球所見",
            "displayOrder": 3,
            "fields": [
                generic_field("pupil_right", "右瞳孔径", "number", unit="mm", min=0, step=0.5, requiredWarning=True),
                generic_field("pupil_left", "左瞳孔径", "number", unit="mm", min=0, step=0.5, requiredWarning=True),
                generic_field("light", "対光反射", "select", options=["あり", "鈍い", "なし"], requiredWarning=True),
                generic_field("anisocoria", "瞳孔不同", "select", options=["なし", "あり"]),
                generic_field("eye_position", "眼位", "select", options=["正中", "右共同偏視", "左共同偏視"]),
                generic_field("nystagmus", "眼振", "select", options=["なし", "あり"]),
                generic_field("diplopia", "複視", "select", options=["なし", "あり"]),
                generic_field("ptosis", "眼瞼下垂", "select", options=["なし", "あり"]),
            ],
        },
        {
            "id": "motor",
            "label": "運動機能",
            "displayOrder": 4,
            "fields": [
                generic_field("mmt_ru", "MMT 右上肢", requiredWarning=True, placeholder="例: 5/5"),
                generic_field("mmt_rl", "MMT 右下肢", requiredWarning=True, placeholder="例: 5/5"),
                generic_field("mmt_lu", "MMT 左上肢", requiredWarning=True, placeholder="例: 5/5"),
                generic_field("mmt_ll", "MMT 左下肢", requiredWarning=True, placeholder="例: 5/5"),
                generic_field("barre_status", "バレー徴候", "select", options=["陰性", "陽性"]),
                generic_field("barre_side", "バレー左右", "multi_select", options=["右", "左"]),
                generic_field("barre_angle", "バレー保持角度", "number", unit="度", min=0, max=90, step=1),
                generic_field("barre_detail", "バレー詳細", "multi_select", options=["軽度下垂", "下垂", "保持困難", "挙上不可"]),
                generic_field("mingazzini_status", "ミンガッチーニ徴候", "select", options=["陰性", "陽性"]),
                generic_field("mingazzini_side", "ミンガッチーニ左右", "multi_select", options=["右", "左"]),
                generic_field("mingazzini_detail", "ミンガッチーニ詳細", "multi_select", options=["軽度下垂", "下垂", "保持困難", "肢位不可"]),
                generic_field("mingazzini_note", "ミンガッチーニ備考"),
            ],
        },
        {
            "id": "nihss",
            "label": "NIHSS",
            "displayOrder": 5,
            "fields": [
                generic_field("total", "合計点数", "number", min=0, step=1, requiredWarning=True, helpText="詳細採点は別紙記録参照"),
            ],
        },
        {
            "id": "higher",
            "label": "高次脳機能",
            "displayOrder": 6,
            "fields": [
                generic_field("findings", "高次脳機能所見", "multi_select", options=["構音障害", "失語", "半側空間無視", "病態失認"]),
            ],
        },
        {
            "id": "icp",
            "label": "頭蓋内圧亢進症状",
            "displayOrder": 7,
            "fields": [
                generic_field("symptoms", "症状", "multi_select", options=["頭痛", "嘔気", "嘔吐", "痙攣"]),
            ],
        },
        {
            "id": "swallow",
            "label": "嚥下",
            "displayOrder": 8,
            "fields": [
                generic_field("meal", "食事・飲水", "multi_select", options=["禁食", "飲水可", "とろみ水", "嚥下食", "常食"]),
                generic_field("choking", "むせ", "select", options=["なし", "あり"]),
            ],
        },
        {
            "id": "activity",
            "label": "安静度・ADL",
            "displayOrder": 9,
            "fields": [
                generic_field("rest", "安静度", "select", options=REST_OPTIONS, requiredWarning=True),
                generic_field("adl", "ADL", "select", options=["自立", "見守り", "一部介助", "全介助"]),
            ],
        },
        {
            "id": "elimination",
            "label": "排泄",
            "displayOrder": 10,
            "fields": [
                generic_field("urination", "排尿", "select", options=["自立", "尿器", "失禁", "バルーン"]),
                generic_field("defecation", "排便", "select", options=["自立", "失禁", "オムツ"]),
            ],
        },
        {
            "id": "treatment",
            "label": "治療",
            "displayOrder": 11,
            "fields": [
                generic_field("antihypertensive", "降圧薬", "multi_select", options=["ニカルジピン", "アムロジピン", "その他"]),
                generic_field("nicardipine_rate", "ニカルジピン速度", "number", unit="ml/h", min=0, step=0.1),
                generic_field("other", "治療メモ", "textarea"),
            ],
        },
    ]
    return normalize_schema({"schemaFormat": "generic-v1", "sections": sections})


def build_neuro_common_copy_format():
    return normalize_copy_format(
        {
            "format": "text-v1",
            "lines": [
                NEURO_COMMON_TEMPLATE["full"],
                "",
                "JCS{{consciousness.jcs}}、T{{vitals.t}}℃、BP{{vitals.bp}}mmHg、HR{{vitals.hr}}回/分、SpO₂{{vitals.spo2}}%。",
                "心電図リズム：{{vitals.ecg_rhythm}}。酸素：{{vitals.oxygen_use}} {{vitals.oxygen_flow}}L。",
                "",
                "瞳孔：右{{eye.pupil_right}}mm／左{{eye.pupil_left}}mm、対光反射：{{eye.light}}、瞳孔不同：{{eye.anisocoria}}、眼位：{{eye.eye_position}}。",
                "眼振：{{eye.nystagmus}}、複視：{{eye.diplopia}}、眼瞼下垂：{{eye.ptosis}}。",
                "",
                "MMT：右上肢{{motor.mmt_ru}}、右下肢{{motor.mmt_rl}}、左上肢{{motor.mmt_lu}}、左下肢{{motor.mmt_ll}}。",
                "バレー徴候：{{motor.barre_status}}、左右：{{motor.barre_side}}、保持角度：{{motor.barre_angle}}度、詳細：{{motor.barre_detail}}。",
                "ミンガッチーニ徴候：{{motor.mingazzini_status}}、左右：{{motor.mingazzini_side}}、詳細：{{motor.mingazzini_detail}}。",
                {"text": "ミンガッチーニ備考：{{motor.mingazzini_note}}", "omitIfAllBlank": ["motor.mingazzini_note"]},
                "NIHSS：{{nihss.total}}点（別紙記録参照）。",
                "",
                "高次脳機能所見：{{higher.findings}}。",
                "頭蓋内圧亢進症状：{{icp.symptoms}}。",
                "嚥下：{{swallow.meal}}、むせ：{{swallow.choking}}。",
                "安静度：{{activity.rest}}、ADL：{{activity.adl}}。",
                "排尿：{{elimination.urination}}、排便：{{elimination.defecation}}。",
                "降圧薬：{{treatment.antihypertensive}}、ニカルジピン速度：{{treatment.nicardipine_rate}}ml/h。",
                {"text": "{{treatment.other}}", "splitLinesFrom": "treatment.other", "omitIfAllBlank": ["treatment.other"]},
            ],
        }
    )


def validate_seed_data():
    ids = set()
    for template in STROKE_TYPES:
        validate_template(template)
        build_generic_stroke_schema(template)
        build_generic_stroke_copy_format(template)
        if template["id"] in ids:
            raise ValueError(f"duplicate template id: {template['id']}")
        ids.add(template["id"])
    validate_template_id(NEURO_COMMON_TEMPLATE["id"])
    build_neuro_common_schema()
    build_neuro_common_copy_format()
    if NEURO_COMMON_TEMPLATE["id"] in ids:
        raise ValueError(f"duplicate template id: {NEURO_COMMON_TEMPLATE['id']}")
    ids.add(NEURO_COMMON_TEMPLATE["id"])
    if len(set(REST_OPTIONS)) != len(REST_OPTIONS):
        raise ValueError("duplicate rest option")
    actions = [item["action"] for item in QUICK_TEMPLATES]
    if len(set(actions)) != len(actions):
        raise ValueError("duplicate quick template action")
    keywords = [item["keyword"] for item in SEARCH_KEYWORDS]
    if len(set(keywords)) != len(keywords):
        raise ValueError("duplicate search keyword")
    group_ids = [item["id"] for item in TEMPLATE_GROUPS]
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("duplicate template group")
    all_template_ids = ids
    for group in TEMPLATE_GROUPS:
        validate_template_id(group["id"])
        for template_id in group["items"]:
            validate_template_id(template_id)
            if template_id not in all_template_ids:
                raise ValueError(f"group {group['id']} references unknown template: {template_id}")
    for item in QUICK_TEMPLATES:
        if item["target_type"] not in {"template", "group"}:
            raise ValueError(f"invalid quick template target type: {item['target_type']}")
        validate_template_id(item["target_id"])
    for item in SEARCH_KEYWORDS:
        if item["target_type"] not in {"template", "group"}:
            raise ValueError(f"invalid search keyword target type: {item['target_type']}")
        validate_template_id(item["target_id"])


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
          base_version_id INTEGER,
          status TEXT NOT NULL DEFAULT 'published',
          FOREIGN KEY (template_id) REFERENCES templates(id),
          FOREIGN KEY (base_version_id) REFERENCES template_versions(id),
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

        CREATE TABLE IF NOT EXISTS template_groups (
          id TEXT PRIMARY KEY,
          label TEXT NOT NULL,
          sub TEXT NOT NULL,
          display_order INTEGER NOT NULL DEFAULT 0,
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS template_group_items (
          group_id TEXT NOT NULL,
          template_id TEXT NOT NULL,
          display_order INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (group_id, template_id),
          FOREIGN KEY (group_id) REFERENCES template_groups(id),
          FOREIGN KEY (template_id) REFERENCES templates(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_rest_options_label
          ON rest_options(label);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_quick_templates_action
          ON quick_templates(action);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_search_keywords_keyword
          ON search_keywords(keyword);

        CREATE INDEX IF NOT EXISTS idx_template_group_items_group_id
          ON template_group_items(group_id, display_order);

        CREATE INDEX IF NOT EXISTS idx_template_versions_template_id
          ON template_versions(template_id);

        CREATE INDEX IF NOT EXISTS idx_template_audit_logs_template_id
          ON template_audit_logs(template_id);
        """
    )
    ensure_column(conn, "templates", "current_version_id", "INTEGER")
    ensure_column(conn, "templates", "status", "TEXT NOT NULL DEFAULT 'published'")
    ensure_column(conn, "template_versions", "status", "TEXT NOT NULL DEFAULT 'published'")
    ensure_column(conn, "template_versions", "base_version_id", "INTEGER")
    ensure_column(conn, "quick_templates", "target_type", "TEXT")
    ensure_column(conn, "quick_templates", "target_id", "TEXT")
    ensure_column(conn, "search_keywords", "target_type", "TEXT")
    ensure_column(conn, "search_keywords", "target_id", "TEXT")
    ensure_current_version_triggers(conn)


def ensure_current_version_triggers(conn):
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS trg_templates_current_version_insert
        BEFORE INSERT ON templates
        FOR EACH ROW
        WHEN NEW.current_version_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM template_versions
            WHERE id = NEW.current_version_id
              AND template_id = NEW.id
              AND status = 'published'
          )
        BEGIN
          SELECT RAISE(ABORT, 'current_version_id must reference a published version of the same template');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_templates_current_version_update
        BEFORE UPDATE OF current_version_id ON templates
        FOR EACH ROW
        WHEN NEW.current_version_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM template_versions
            WHERE id = NEW.current_version_id
              AND template_id = NEW.id
              AND status = 'published'
          )
        BEGIN
          SELECT RAISE(ABORT, 'current_version_id must reference a published version of the same template');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_template_versions_current_status_update
        BEFORE UPDATE OF status ON template_versions
        FOR EACH ROW
        WHEN NEW.status <> 'published'
          AND EXISTS (
            SELECT 1
            FROM templates
            WHERE current_version_id = OLD.id
          )
        BEGIN
          SELECT RAISE(ABORT, 'current version must remain published');
        END;
        """
    )


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


def migration_applied(conn, version):
    return exists(conn, "SELECT 1 FROM schema_migrations WHERE version = ?", (version,))


def migrate_stroke_templates_to_generic(conn, now):
    if migration_applied(conn, "004"):
        return

    for template in STROKE_TYPES:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.schema_json,
              t.current_version_id,
              COALESCE(v.schema_json, t.schema_json) AS current_schema_json,
              v.copy_format_json AS current_copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ?
            """,
            (template["id"],),
        ).fetchone()
        if row is None:
            continue

        current_schema = json.loads(row[3])
        if current_schema.get("schemaFormat") == "generic-v1":
            continue

        schema = build_generic_stroke_schema(template)
        copy_format = build_generic_stroke_copy_format(template)
        schema_json = json.dumps(schema, ensure_ascii=False)
        copy_format_json = json.dumps(copy_format, ensure_ascii=False)
        version_number = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM template_versions
            WHERE template_id = ?
            """,
            (template["id"],),
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, 'system', ?, 'system', ?)
            """,
            (
                template["id"],
                version_number,
                schema_json,
                copy_format_json,
                "Convert stroke template to generic-v1",
                "Add region-specific observation fields without default patient values",
                now,
                now,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (schema_json, version_id, now, template["id"]),
        )
        conn.execute(
            """
            INSERT INTO template_audit_logs
              (template_id, version_id, action, actor_name, acted_at, before_json, after_json, reason)
            VALUES (?, ?, 'migrate', 'system', ?, ?, ?, ?)
            """,
            (
                template["id"],
                version_id,
                now,
                json.dumps(
                    {
                        "schema": current_schema,
                        "copy_format": json.loads(row[4]) if row[4] else None,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "schema": schema,
                        "copy_format": copy_format,
                    },
                    ensure_ascii=False,
                ),
                "Convert stroke-v1 to generic-v1 with region-specific observation fields",
            ),
        )

    record_migration(conn, "004", "convert stroke templates to generic v1", now)


def migrate_stroke_copy_format_to_compat(conn, now):
    if migration_applied(conn, "005"):
        return

    for template in STROKE_TYPES:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.current_version_id,
              COALESCE(v.schema_json, t.schema_json) AS current_schema_json,
              v.copy_format_json AS current_copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ?
            """,
            (template["id"],),
        ).fetchone()
        if row is None:
            continue

        schema = build_generic_stroke_schema(template)
        copy_format = build_generic_stroke_copy_format(template)
        schema_json = json.dumps(schema, ensure_ascii=False)
        copy_format_json = json.dumps(copy_format, ensure_ascii=False)
        version_number = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM template_versions
            WHERE template_id = ?
            """,
            (template["id"],),
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, 'system', ?, 'system', ?)
            """,
            (
                template["id"],
                version_number,
                schema_json,
                copy_format_json,
                "Align generic copy output with stroke-v1",
                "Preserve existing nursing note text while keeping generic-v1 fields",
                now,
                now,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (schema_json, version_id, now, template["id"]),
        )
        conn.execute(
            """
            INSERT INTO template_audit_logs
              (template_id, version_id, action, actor_name, acted_at, before_json, after_json, reason)
            VALUES (?, ?, 'migrate', 'system', ?, ?, ?, ?)
            """,
            (
                template["id"],
                version_id,
                now,
                json.dumps(
                    {
                        "schema": json.loads(row[2]),
                        "copy_format": json.loads(row[3]) if row[3] else None,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "schema": schema,
                        "copy_format": copy_format,
                    },
                    ensure_ascii=False,
                ),
                "Align generic-v1 stroke copy output with stroke-v1 output",
            ),
        )

    record_migration(conn, "005", "align stroke generic copy output with stroke v1", now)


def migrate_add_neuro_common_template(conn, now):
    if migration_applied(conn, "006"):
        return

    template = NEURO_COMMON_TEMPLATE
    if exists(conn, "SELECT 1 FROM templates WHERE id = ?", (template["id"],)):
        record_migration(conn, "006", "add neuro common template", now)
        return

    schema = build_neuro_common_schema()
    copy_format = build_neuro_common_copy_format()
    schema_json = json.dumps(schema, ensure_ascii=False)
    copy_format_json = json.dumps(copy_format, ensure_ascii=False)
    display_order = conn.execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM templates").fetchone()[0]

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
            template["category"],
            schema_json,
            display_order,
            now,
            now,
        ),
    )
    cursor = conn.execute(
        """
        INSERT INTO template_versions
          (template_id, version_number, schema_json, copy_format_json,
           change_summary, change_reason, created_by, created_at, approved_by, approved_at)
        VALUES (?, 1, ?, ?, ?, ?, 'system', ?, 'system', ?)
        """,
        (
            template["id"],
            schema_json,
            copy_format_json,
            "Add neuro common generic template",
            "Add flat generic-v1 template for common stroke/neuro observations",
            now,
            now,
        ),
    )
    version_id = cursor.lastrowid
    conn.execute(
        """
        UPDATE templates
        SET current_version_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (version_id, now, template["id"]),
    )
    conn.execute(
        """
        INSERT INTO template_audit_logs
          (template_id, version_id, action, actor_name, acted_at, after_json, reason)
        VALUES (?, ?, 'migrate', 'system', ?, ?, ?)
        """,
        (
            template["id"],
            version_id,
            now,
            json.dumps({"schema": schema, "copy_format": copy_format}, ensure_ascii=False),
            "Add neuro common template as generic-v1",
        ),
    )

    record_migration(conn, "006", "add neuro common template", now)


def migrate_stroke_jcs_to_select(conn, now):
    if migration_applied(conn, "007"):
        return

    for template in STROKE_TYPES:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.current_version_id,
              COALESCE(v.schema_json, t.schema_json) AS current_schema_json,
              v.copy_format_json AS current_copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ?
            """,
            (template["id"],),
        ).fetchone()
        if row is None:
            continue

        current_schema = json.loads(row[2])
        if current_schema.get("schemaFormat") != "generic-v1":
            continue

        schema = build_generic_stroke_schema(template)
        copy_format = json.loads(row[3]) if row[3] else build_generic_stroke_copy_format(template)
        schema_json = json.dumps(schema, ensure_ascii=False)
        copy_format_json = json.dumps(copy_format, ensure_ascii=False) if copy_format is not None else None
        version_number = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM template_versions
            WHERE template_id = ?
            """,
            (template["id"],),
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO template_versions
              (template_id, version_number, schema_json, copy_format_json,
               change_summary, change_reason, created_by, created_at, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, 'system', ?, 'system', ?)
            """,
            (
                template["id"],
                version_number,
                schema_json,
                copy_format_json,
                "Change JCS to selectable options",
                "Use fixed JCS choices on stroke templates",
                now,
                now,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'published', approved_by = 'system', approved_at = ?
            WHERE id = ?
            """,
            (now, version_id),
        )
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (schema_json, version_id, now, template["id"]),
        )
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'retired'
            WHERE template_id = ? AND status = 'published' AND id <> ?
            """,
            (template["id"], version_id),
        )
        conn.execute(
            """
            INSERT INTO template_audit_logs
              (template_id, version_id, action, actor_name, acted_at, before_json, after_json, reason)
            VALUES (?, ?, 'migrate', 'system', ?, ?, ?, ?)
            """,
            (
                template["id"],
                version_id,
                now,
                json.dumps(
                    {
                        "schema": current_schema,
                        "copy_format": copy_format,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "schema": schema,
                        "copy_format": copy_format,
                    },
                    ensure_ascii=False,
                ),
                "Change stroke JCS field to fixed select choices",
            ),
        )

    record_migration(conn, "007", "change stroke jcs to select", now)


def replace_jcs_fields(schema):
    changed = False
    for section in schema.get("sections", []):
        for field in section.get("fields", []):
            if field.get("id") != "jcs":
                continue
            if field.get("type") == "select" and field.get("options") == JCS_OPTIONS:
                continue
            field["type"] = "select"
            field["options"] = JCS_OPTIONS
            changed = True
    return changed


def migrate_jcs_option_values(conn, now):
    if migration_applied(conn, "008"):
        return

    target_ids = [template["id"] for template in STROKE_TYPES] + [NEURO_COMMON_TEMPLATE["id"]]
    for template_id in target_ids:
        row = conn.execute(
            """
            SELECT
              t.id,
              t.current_version_id,
              COALESCE(v.schema_json, t.schema_json) AS current_schema_json,
              v.copy_format_json AS current_copy_format_json
            FROM templates t
            LEFT JOIN template_versions v ON v.id = t.current_version_id
            WHERE t.id = ?
            """,
            (template_id,),
        ).fetchone()
        if row is None:
            continue

        current_schema = json.loads(row[2])
        if current_schema.get("schemaFormat") not in ("generic-v1", "generic-v2"):
            continue
        schema = json.loads(json.dumps(current_schema, ensure_ascii=False))
        if not replace_jcs_fields(schema):
            continue

        copy_format = json.loads(row[3]) if row[3] else None
        schema_json = json.dumps(schema, ensure_ascii=False)
        copy_format_json = json.dumps(copy_format, ensure_ascii=False) if copy_format is not None else None
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
            VALUES (?, ?, ?, ?, ?, ?, 'system', ?, 'system', ?)
            """,
            (
                template_id,
                version_number,
                schema_json,
                copy_format_json,
                "Fix JCS option values",
                "Use fixed Japanese roman numeral JCS choices",
                now,
                now,
            ),
        )
        version_id = cursor.lastrowid
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'published', approved_by = 'system', approved_at = ?
            WHERE id = ?
            """,
            (now, version_id),
        )
        conn.execute(
            """
            UPDATE templates
            SET schema_json = ?, current_version_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (schema_json, version_id, now, template_id),
        )
        conn.execute(
            """
            UPDATE template_versions
            SET status = 'retired'
            WHERE template_id = ? AND status = 'published' AND id <> ?
            """,
            (template_id, version_id),
        )
        conn.execute(
            """
            INSERT INTO template_audit_logs
              (template_id, version_id, action, actor_name, acted_at, before_json, after_json, reason)
            VALUES (?, ?, 'migrate', 'system', ?, ?, ?, ?)
            """,
            (
                template_id,
                version_id,
                now,
                json.dumps({"schema": current_schema, "copy_format": copy_format}, ensure_ascii=False),
                json.dumps({"schema": schema, "copy_format": copy_format}, ensure_ascii=False),
                "Fix JCS option values",
            ),
        )

    record_migration(conn, "008", "fix jcs option values", now)


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
            conn.execute(
                """
                UPDATE quick_templates
                SET label = ?, sub = ?, target_type = ?, target_id = ?, display_order = ?
                WHERE action = ?
                """,
                (
                    item["label"],
                    item["sub"],
                    item["target_type"],
                    item["target_id"],
                    order,
                    item["action"],
                ),
            )
            continue
        conn.execute(
            """
            INSERT INTO quick_templates (label, sub, action, target_type, target_id, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item["label"], item["sub"], item["action"], item["target_type"], item["target_id"], order),
        )


def seed_search_keywords(conn):
    for order, item in enumerate(SEARCH_KEYWORDS, start=1):
        if exists(conn, "SELECT 1 FROM search_keywords WHERE keyword = ?", (item["keyword"],)):
            conn.execute(
                """
                UPDATE search_keywords
                SET template_action = ?, target_type = ?, target_id = ?, display_order = ?
                WHERE keyword = ?
                """,
                (
                    item["template_action"],
                    item["target_type"],
                    item["target_id"],
                    order,
                    item["keyword"],
                ),
            )
            continue
        conn.execute(
            """
            INSERT INTO search_keywords (keyword, template_action, target_type, target_id, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item["keyword"],
                item["template_action"],
                item["target_type"],
                item["target_id"],
                order,
            ),
        )


def seed_template_groups(conn, now):
    for group_order, group in enumerate(TEMPLATE_GROUPS, start=1):
        if exists(conn, "SELECT 1 FROM template_groups WHERE id = ?", (group["id"],)):
            conn.execute(
                """
                UPDATE template_groups
                SET label = ?, sub = ?, display_order = ?, is_active = 1, updated_at = ?
                WHERE id = ?
                """,
                (group["label"], group["sub"], group_order, now, group["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO template_groups
                  (id, label, sub, display_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (group["id"], group["label"], group["sub"], group_order, now, now),
            )

        for item_order, template_id in enumerate(group["items"], start=1):
            conn.execute(
                """
                INSERT INTO template_group_items (group_id, template_id, display_order)
                VALUES (?, ?, ?)
                ON CONFLICT(group_id, template_id)
                DO UPDATE SET display_order = excluded.display_order
                """,
                (group["id"], template_id, item_order),
            )


def normalize_template_version_statuses(conn):
    conn.execute(
        """
        UPDATE template_versions
        SET status = 'published'
        WHERE id IN (
          SELECT current_version_id
          FROM templates
          WHERE current_version_id IS NOT NULL
        )
        """
    )
    conn.execute(
        """
        UPDATE template_versions
        SET status = 'retired'
        WHERE id NOT IN (
          SELECT current_version_id
          FROM templates
          WHERE current_version_id IS NOT NULL
        )
        AND status = 'published'
        """
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
        migrate_stroke_templates_to_generic(conn, now)
        migrate_stroke_copy_format_to_compat(conn, now)
        migrate_add_neuro_common_template(conn, now)
        migrate_stroke_jcs_to_select(conn, now)
        migrate_jcs_option_values(conn, now)
        normalize_template_version_statuses(conn)
        seed_template_groups(conn, now)
        seed_rest_options(conn)
        seed_quick_templates(conn)
        seed_search_keywords(conn)
    print(f"Prepared {db_path}")


if __name__ == "__main__":
    main()
