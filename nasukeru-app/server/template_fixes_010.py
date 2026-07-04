import json
import os
from datetime import datetime, timezone
from pathlib import Path

from init_db import (
    DEFAULT_DB_PATH,
    JCS_OPTIONS,
    NEURO_COMMON_TEMPLATE,
    REST_OPTIONS,
    STROKE_TYPES,
    connect,
    generic_field,
)
from template_schema import normalize_copy_format, normalize_schema, validate_copy_format_references


MIGRATION_VERSION = "010"
MIGRATION_NAME = "fix built-in template clinical inputs"

SIDE_OPTIONS = ["なし", "右", "左", "両側"]
HORIZONTAL_NYSTAGMUS_OPTIONS = ["なし", "右方視時", "左方視時", "両方向"]
THICKENED_WATER_LEVELS = ["薄め", "中程度", "濃いめ"]
DYSPHAGIA_DIET_LEVELS = ["1", "2", "3", "4", "5"]

STROKE_EXTRA_FIELDS_010 = {
    "mca": [
        {"id": "mouth_droop", "label": "口角下垂", "type": "select", "options": SIDE_OPTIONS, "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "sensory_dullness", "label": "半身感覚鈍麻", "type": "select", "options": SIDE_OPTIONS, "allowEmpty": True},
    ],
    "aca": [
        {"id": "spontaneity_decrease", "label": "自発性低下", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "speech_amount_decrease", "label": "発語量低下", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "excretion", "label": "排泄", "type": "text", "allowEmpty": True, "placeholder": "例: 尿失禁にて経過"},
    ],
    "pca": [
        {"id": "homonymous_hemianopia", "label": "同名半盲", "type": "select", "options": SIDE_OPTIONS, "allowEmpty": True},
        {"id": "visual_impairment", "label": "視覚障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "sensory_dullness", "label": "半身感覚鈍麻", "type": "select", "options": SIDE_OPTIONS, "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
    "lacunar": [
        {"id": "mild_dysarthria", "label": "軽度構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "mild_facial_palsy", "label": "顔面麻痺軽度", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "sensory_disturbance", "label": "感覚障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
    "brainstem": [
        {"id": "horizontal_nystagmus", "label": "水平性眼振", "type": "select", "options": HORIZONTAL_NYSTAGMUS_OPTIONS, "allowEmpty": True},
        {"id": "diplopia", "label": "複視", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysphagia", "label": "嚥下障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "dysarthria", "label": "構音障害", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
        {"id": "limb_ataxia", "label": "四肢失調", "type": "select", "options": ["なし", "あり"], "allowEmpty": True},
    ],
}


def eq(field, value):
    return {"op": "eq", "field": field, "value": value}


def contains(field, value):
    return {"op": "contains", "field": field, "value": value}


def conditional_field(field_id, label, field_type, condition, **extra):
    return generic_field(
        field_id,
        label,
        field_type,
        visibleIf=condition,
        requiredIf=condition,
        **extra,
    )


def build_corrected_stroke_schema(template):
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
            "fields": STROKE_EXTRA_FIELDS_010[template["id"]],
        },
        {
            "id": "rest",
            "label": "安静度",
            "displayOrder": 6,
            "fields": [generic_field("level", "安静度", "select", options=REST_OPTIONS, requiredWarning=True)],
        },
    ]
    return normalize_schema({"schemaFormat": "generic-v1", "sections": sections})


def build_corrected_stroke_copy_format(template):
    extra_lines = [
        {
            "text": f"{field['label']}：{{{{stroke_findings.{field['id']}}}}}",
            "omitIfAllBlank": [f"stroke_findings.{field['id']}"],
        }
        for field in STROKE_EXTRA_FIELDS_010[template["id"]]
    ]
    vital_line = {
        "segments": [
            {"ref": "vitals.jcs", "label": "JCS"},
            {"ref": "vitals.t", "label": "T", "suffix": "℃"},
            {"ref": "vitals.bp", "label": "BP", "suffix": "mmHg"},
            {"ref": "vitals.hr", "label": "HR"},
            {"ref": "vitals.spo2", "label": "SpO₂", "suffix": "%"},
        ],
        "separator": "　",
    }
    mmt_line = {
        "prefix": "MMT：",
        "segments": [
            {"ref": "mmt.ru", "label": "右上肢"},
            {"ref": "mmt.rl", "label": "右下肢"},
            {"ref": "mmt.lu", "label": "左上肢"},
            {"ref": "mmt.ll", "label": "左下肢"},
        ],
        "separator": "、",
    }
    neuro_refs = [
        "neuro.pupil", "neuro.light", "neuro.eye", "neuro.barre", "neuro.mingazzini",
        "mmt.ru", "mmt.rl", "mmt.lu", "mmt.ll", "neuro.nihss", "neuro.other",
    ]
    return normalize_copy_format({
        "format": "text-v1",
        "lines": [
            template["full"], "", vital_line, "",
            {"text": "頭痛：{{symptoms.headache}}", "omitIfAllBlank": ["symptoms.headache"]},
            {"text": "めまい：{{symptoms.dizzy}}", "omitIfAllBlank": ["symptoms.dizzy"]},
            {"text": "嘔気：{{symptoms.nausea}}", "omitIfAllBlank": ["symptoms.nausea"]},
            "",
            {"text": "神経所見", "omitIfAllBlank": neuro_refs},
            {"text": "瞳孔：{{neuro.pupil}}", "omitIfAllBlank": ["neuro.pupil"]},
            {"text": "対光反射：{{neuro.light}}", "omitIfAllBlank": ["neuro.light"]},
            {"text": "眼球位置：{{neuro.eye}}", "omitIfAllBlank": ["neuro.eye"]},
            {"text": "バレー徴候：{{neuro.barre}}", "omitIfAllBlank": ["neuro.barre"]},
            {"text": "ミンガッチー徴候：{{neuro.mingazzini}}", "omitIfAllBlank": ["neuro.mingazzini"]},
            mmt_line,
            {"text": "NIHSS：{{neuro.nihss}}", "omitIfAllBlank": ["neuro.nihss"]},
            {"text": "{{neuro.other}}", "splitLinesFrom": "neuro.other", "omitIfAllBlank": ["neuro.other"]},
            *extra_lines,
            "",
            {"text": "安静度\n{{rest.level}}", "omitIfAllBlank": ["rest.level"]},
        ],
    })


def build_corrected_neuro_common_schema():
    oxygen_condition = eq("vitals.oxygen_use", "O2使用")
    ecg_other_condition = eq("vitals.ecg_rhythm", "その他")
    barre_positive = eq("motor.barre_status", "陽性")
    mingazzini_positive = eq("motor.mingazzini_status", "陽性")
    thickened_condition = contains("swallow.meal", "とろみ水")
    dysphagia_diet_condition = contains("swallow.meal", "嚥下食")
    nicardipine_condition = contains("treatment.antihypertensive", "ニカルジピン")
    antihypertensive_other_condition = contains("treatment.antihypertensive", "その他")

    sections = [
        {"id": "consciousness", "label": "意識レベル", "displayOrder": 1, "fields": [
            generic_field("jcs", "JCS", "select", options=JCS_OPTIONS, requiredWarning=True),
        ]},
        {"id": "vitals", "label": "バイタルサイン", "displayOrder": 2, "fields": [
            generic_field("t", "体温", "number", unit="℃", step=0.1, requiredWarning=True),
            generic_field("bp", "血圧", requiredWarning=True, placeholder="例: 120/70"),
            generic_field("hr", "心拍数", "number", unit="回/分", min=0, step=1, requiredWarning=True),
            generic_field("ecg_rhythm", "心電図リズム", "select", options=["SR", "Af", "PAC", "PVC", "その他"]),
            conditional_field("ecg_rhythm_other", "その他の心電図リズム", "text", ecg_other_condition, placeholder="例: VT"),
            generic_field("spo2", "SpO₂", "number", unit="%", min=0, max=100, step=1, requiredWarning=True),
            generic_field("oxygen_use", "酸素使用", "select", options=["RA", "O2使用"]),
            conditional_field("oxygen_flow", "酸素流量", "number", oxygen_condition, unit="L/分", min=0, step=0.5),
        ]},
        {"id": "eye", "label": "瞳孔・眼球所見", "displayOrder": 3, "fields": [
            generic_field("pupil_right", "右瞳孔径", "number", unit="mm", min=0, step=0.5, requiredWarning=True),
            generic_field("pupil_left", "左瞳孔径", "number", unit="mm", min=0, step=0.5, requiredWarning=True),
            generic_field("light", "対光反射", "select", options=["あり", "鈍い", "なし"], requiredWarning=True),
            generic_field("anisocoria", "瞳孔不同", "select", options=["なし", "あり"]),
            generic_field("eye_position", "眼位", "select", options=["正中", "右共同偏視", "左共同偏視"]),
            generic_field("nystagmus", "眼振", "select", options=["なし", "あり"]),
            generic_field("diplopia", "複視", "select", options=["なし", "あり"]),
            generic_field("ptosis", "眼瞼下垂", "select", options=["なし", "あり"]),
        ]},
        {"id": "motor", "label": "運動機能", "displayOrder": 4, "fields": [
            generic_field("mmt_ru", "MMT 右上肢", requiredWarning=True, placeholder="例: 5/5"),
            generic_field("mmt_rl", "MMT 右下肢", requiredWarning=True, placeholder="例: 5/5"),
            generic_field("mmt_lu", "MMT 左上肢", requiredWarning=True, placeholder="例: 5/5"),
            generic_field("mmt_ll", "MMT 左下肢", requiredWarning=True, placeholder="例: 5/5"),
            generic_field("barre_status", "バレー徴候", "select", options=["陰性", "陽性"]),
            conditional_field("barre_side", "バレー左右", "multi_select", barre_positive, options=["右", "左"]),
            generic_field("barre_angle", "バレー保持角度", "number", unit="度", min=0, max=90, step=1, visibleIf=barre_positive),
            generic_field("barre_detail", "バレー詳細", "multi_select", options=["軽度下垂", "下垂", "保持困難", "挙上不可"], visibleIf=barre_positive),
            generic_field("mingazzini_status", "ミンガッチーニ徴候", "select", options=["陰性", "陽性"]),
            conditional_field("mingazzini_side", "ミンガッチーニ左右", "multi_select", mingazzini_positive, options=["右", "左"]),
            generic_field("mingazzini_detail", "ミンガッチーニ詳細", "multi_select", options=["軽度下垂", "下垂", "保持困難", "肢位不可"], visibleIf=mingazzini_positive),
            generic_field("mingazzini_note", "ミンガッチーニ備考", visibleIf=mingazzini_positive),
        ]},
        {"id": "nihss", "label": "NIHSS", "displayOrder": 5, "fields": [
            generic_field("total", "合計点数", "number", min=0, step=1, requiredWarning=True, helpText="詳細採点は別紙記録参照"),
        ]},
        {"id": "higher", "label": "高次脳機能", "displayOrder": 6, "fields": [
            generic_field("findings", "高次脳機能所見", "multi_select", options=["構音障害", "失語", "半側空間無視", "病態失認"]),
        ]},
        {"id": "icp", "label": "頭蓋内圧亢進症状", "displayOrder": 7, "fields": [
            generic_field("symptoms", "症状", "multi_select", options=["頭痛", "嘔気", "嘔吐", "痙攣"]),
        ]},
        {"id": "swallow", "label": "嚥下", "displayOrder": 8, "fields": [
            generic_field("meal", "食事・飲水", "multi_select", options=["禁食", "飲水可", "とろみ水", "嚥下食", "常食"]),
            conditional_field("thickened_water_level", "とろみの程度", "select", thickened_condition, options=THICKENED_WATER_LEVELS),
            conditional_field("dysphagia_diet_level", "嚥下食レベル", "select", dysphagia_diet_condition, options=DYSPHAGIA_DIET_LEVELS),
            generic_field("choking", "むせ", "select", options=["なし", "あり"]),
        ]},
        {"id": "activity", "label": "安静度・ADL", "displayOrder": 9, "fields": [
            generic_field("rest", "安静度", "select", options=REST_OPTIONS, requiredWarning=True),
            generic_field("adl", "ADL", "select", options=["自立", "見守り", "一部介助", "全介助"]),
        ]},
        {"id": "elimination", "label": "排泄", "displayOrder": 10, "fields": [
            generic_field("urination", "排尿", "select", options=["自立", "尿器", "失禁", "バルーン"]),
            generic_field("defecation", "排便", "select", options=["自立", "失禁", "オムツ"]),
        ]},
        {"id": "treatment", "label": "治療", "displayOrder": 11, "fields": [
            generic_field("antihypertensive", "降圧薬", "multi_select", options=["ニカルジピン", "アムロジピン", "その他"]),
            conditional_field("nicardipine_rate", "ニカルジピン速度", "number", nicardipine_condition, unit="ml/h", min=0, step=0.1),
            conditional_field("antihypertensive_other", "その他の降圧薬", "text", antihypertensive_other_condition, placeholder="薬剤名を入力"),
            generic_field("other", "治療メモ", "textarea"),
        ]},
    ]
    return normalize_schema({"schemaFormat": "generic-v2", "sections": sections})


def build_corrected_neuro_common_copy_format():
    return normalize_copy_format({
        "format": "text-v1",
        "lines": [
            NEURO_COMMON_TEMPLATE["full"], "",
            {"segments": [
                {"ref": "consciousness.jcs", "label": "JCS"},
                {"ref": "vitals.t", "label": "T", "suffix": "℃"},
                {"ref": "vitals.bp", "label": "BP", "suffix": "mmHg"},
                {"ref": "vitals.hr", "label": "HR", "suffix": "回/分"},
                {"ref": "vitals.spo2", "label": "SpO₂", "suffix": "%"},
            ], "separator": "　"},
            {"text": "心電図リズム：{{vitals.ecg_rhythm}}", "omitIfAllBlank": ["vitals.ecg_rhythm"]},
            {"text": "心電図リズム詳細：{{vitals.ecg_rhythm_other}}", "showIf": eq("vitals.ecg_rhythm", "その他")},
            {"segments": [
                {"ref": "vitals.oxygen_use", "label": "酸素："},
                {"ref": "vitals.oxygen_flow", "suffix": "L/分"},
            ], "separator": " "},
            "",
            {"prefix": "瞳孔・眼球所見：", "segments": [
                {"ref": "eye.pupil_right", "label": "右瞳孔", "suffix": "mm"},
                {"ref": "eye.pupil_left", "label": "左瞳孔", "suffix": "mm"},
                {"ref": "eye.light", "label": "対光反射："},
                {"ref": "eye.anisocoria", "label": "瞳孔不同："},
                {"ref": "eye.eye_position", "label": "眼位："},
            ], "separator": "、"},
            {"segments": [
                {"ref": "eye.nystagmus", "label": "眼振："},
                {"ref": "eye.diplopia", "label": "複視："},
                {"ref": "eye.ptosis", "label": "眼瞼下垂："},
            ], "separator": "、"},
            "",
            {"prefix": "MMT：", "segments": [
                {"ref": "motor.mmt_ru", "label": "右上肢"},
                {"ref": "motor.mmt_rl", "label": "右下肢"},
                {"ref": "motor.mmt_lu", "label": "左上肢"},
                {"ref": "motor.mmt_ll", "label": "左下肢"},
            ], "separator": "、"},
            {"text": "バレー徴候：{{motor.barre_status}}", "omitIfAllBlank": ["motor.barre_status"]},
            {"prefix": "バレー詳細：", "segments": [
                {"ref": "motor.barre_side", "label": "側："},
                {"ref": "motor.barre_angle", "label": "保持角度：", "suffix": "度"},
                {"ref": "motor.barre_detail", "label": "所見："},
            ], "separator": "、", "showIf": eq("motor.barre_status", "陽性")},
            {"text": "ミンガッチーニ徴候：{{motor.mingazzini_status}}", "omitIfAllBlank": ["motor.mingazzini_status"]},
            {"prefix": "ミンガッチーニ詳細：", "segments": [
                {"ref": "motor.mingazzini_side", "label": "側："},
                {"ref": "motor.mingazzini_detail", "label": "所見："},
            ], "separator": "、", "showIf": eq("motor.mingazzini_status", "陽性")},
            {"text": "ミンガッチーニ備考：{{motor.mingazzini_note}}", "showIf": eq("motor.mingazzini_status", "陽性"), "omitIfAllBlank": ["motor.mingazzini_note"]},
            {"text": "NIHSS：{{nihss.total}}点（別紙記録参照）", "omitIfAllBlank": ["nihss.total"]},
            "",
            {"text": "高次脳機能所見：{{higher.findings}}", "omitIfAllBlank": ["higher.findings"]},
            {"text": "頭蓋内圧亢進症状：{{icp.symptoms}}", "omitIfAllBlank": ["icp.symptoms"]},
            {"text": "食事・飲水：{{swallow.meal}}", "omitIfAllBlank": ["swallow.meal"]},
            {"text": "とろみの程度：{{swallow.thickened_water_level}}", "showIf": contains("swallow.meal", "とろみ水")},
            {"text": "嚥下食レベル：{{swallow.dysphagia_diet_level}}", "showIf": contains("swallow.meal", "嚥下食")},
            {"text": "むせ：{{swallow.choking}}", "omitIfAllBlank": ["swallow.choking"]},
            {"segments": [
                {"ref": "activity.rest", "label": "安静度："},
                {"ref": "activity.adl", "label": "ADL："},
            ], "separator": "、"},
            {"segments": [
                {"ref": "elimination.urination", "label": "排尿："},
                {"ref": "elimination.defecation", "label": "排便："},
            ], "separator": "、"},
            {"text": "降圧薬：{{treatment.antihypertensive}}", "omitIfAllBlank": ["treatment.antihypertensive"]},
            {"text": "ニカルジピン速度：{{treatment.nicardipine_rate}}ml/h", "showIf": contains("treatment.antihypertensive", "ニカルジピン")},
            {"text": "その他の降圧薬：{{treatment.antihypertensive_other}}", "showIf": contains("treatment.antihypertensive", "その他")},
            {"text": "{{treatment.other}}", "splitLinesFrom": "treatment.other", "omitIfAllBlank": ["treatment.other"]},
        ],
    })


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


def apply_template_fixes(db_path=None):
    db_path = Path(db_path) if db_path is not None else get_db_path()
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        if migration_applied(conn):
            return False
        for template in STROKE_TYPES:
            publish_system_version(
                conn, template["id"], build_corrected_stroke_schema(template),
                build_corrected_stroke_copy_format(template),
                "Normalize side-specific stroke findings",
                "Replace left/right-fixed labels with selectable side or direction values", now,
            )
        publish_system_version(
            conn, NEURO_COMMON_TEMPLATE["id"], build_corrected_neuro_common_schema(),
            build_corrected_neuro_common_copy_format(),
            "Add conditional clinical detail inputs",
            "Add other text, swallowing levels, and conditional treatment detail fields", now,
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (MIGRATION_VERSION, MIGRATION_NAME, now),
        )
    return True


def main():
    applied = apply_template_fixes()
    print("Applied template fixes migration 010" if applied else "Template fixes migration 010 already applied")


if __name__ == "__main__":
    main()
