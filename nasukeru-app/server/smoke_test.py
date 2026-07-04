import copy
import os
import tempfile
from pathlib import Path

from app import app
from init_db import main as init_db_main


EXPECTED_GETS = [
    ("/", 200),
    ("/admin", 200),
    ("/admin/", 200),
    ("/js/admin.js", 200),
    ("/js/field-meta.js", 200),
    ("/js/generic-values.js", 200),
    ("/js/condition-engine.js", 200),
    ("/js/safety-rules.js", 200),
    ("/api/health", 200),
    ("/api/admin/templates", 200),
    ("/api/admin/templates/mca", 200),
    ("/api/templates", 200),
    ("/api/templates/mca", 200),
    ("/api/templates/neuro_common", 200),
    ("/api/templates/mca/versions", 200),
    ("/api/templates/neuro_common/versions", 200),
    ("/api/templates/mca/versions/1", 200),
    ("/api/templates/mca/logs", 200),
    ("/api/templates/neuro_common/logs", 200),
    ("/api/templates/unknown", 404),
    ("/api/templates/unknown/versions", 404),
    ("/api/templates/unknown/logs", 404),
    ("/api/quick-templates", 200),
    ("/api/template-groups/cerebral_infarction", 200),
    ("/api/template-groups/unknown", 404),
    ("/api/rest-options", 200),
    ("/api/search-keywords", 200),
    ("/api/migrations", 200),
    ("/server/app.py", 404),
    ("/server/nasukeru.db", 404),
    ("/.gitignore", 404),
]


LOCAL_HEADERS = {
    "Origin": "http://127.0.0.1:8000",
    "X-Nasukeru-Local": "1",
}


BASE_SCHEMA = {
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
}


NON_EMPTY_BASE_SCHEMA = copy.deepcopy(BASE_SCHEMA)
NON_EMPTY_BASE_SCHEMA["vitals"]["jcs"] = "0"
NON_EMPTY_BASE_SCHEMA["rest"] = "bed rest"


GENERIC_SCHEMA = {
    "schemaFormat": "generic-v1",
    "sections": [
        {
            "id": "basic",
            "label": "Basic",
            "displayOrder": 1,
            "fields": [
                {"id": "procedure", "label": "Procedure", "type": "text", "allowEmpty": True},
                {
                    "id": "status",
                    "label": "Status",
                    "type": "select",
                    "options": [
                        {"value": "none", "label": "なし"},
                        {"value": "present", "label": "あり"},
                    ],
                    "allowEmpty": True,
                },
            ],
        }
    ],
}


GENERIC_COPY_FORMAT = {
    "format": "text-v1",
    "lines": [
        "Procedure: {{basic.procedure}}",
        "Status: {{basic.status}}",
        {"text": "Status note: {{basic.status}}", "omitIfAllBlank": ["basic.status"]},
        {"text": "{{basic.status}}", "splitLinesFrom": "basic.status", "omitIfAllBlank": ["basic.status"]},
    ],
}


EXTENDED_GENERIC_SCHEMA = {
    "schemaFormat": "generic-v1",
    "sections": [
        {
            "id": "observe",
            "label": "Observe",
            "fields": [
                {
                    "id": "symptoms",
                    "label": "Symptoms",
                    "type": "multi_select",
                    "options": ["headache", "nausea"],
                    "allowEmpty": True,
                },
                {
                    "id": "drainage",
                    "label": "Drainage",
                    "type": "number",
                    "min": 0,
                    "max": 999,
                    "step": 1,
                    "unit": "ml",
                    "allowEmpty": True,
                },
            ],
        }
    ],
}


EXTENDED_GENERIC_COPY_FORMAT = {
    "format": "text-v1",
    "lines": [
        "Symptoms: {{observe.symptoms}}",
        "Drainage: {{observe.drainage}}ml",
    ],
}


GENERIC_V2_SCHEMA = {
    "schemaFormat": "generic-v2",
    "sections": [
        {
            "id": "vitals",
            "label": "Vitals",
            "fields": [
                {
                    "id": "oxygen_use",
                    "label": "Oxygen",
                    "type": "select",
                    "options": [
                        {"value": "room_air", "label": "RA"},
                        {"value": "oxygen", "label": "O2使用"},
                    ],
                    "allowEmpty": True,
                },
                {
                    "id": "oxygen_flow",
                    "label": "Oxygen flow",
                    "type": "number",
                    "unit": "L",
                    "blankPolicy": "block",
                    "hardRange": {"min": 0, "max": 15},
                    "warningRange": {"min": 1, "max": 5},
                    "allowEmpty": True,
                    "visibleIf": {"op": "eq", "field": "vitals.oxygen_use", "value": "oxygen"},
                    "requiredIf": {"op": "eq", "field": "vitals.oxygen_use", "value": "oxygen"},
                },
            ],
        }
    ],
}


GENERIC_V2_COPY_FORMAT = {
    "format": "text-v1",
    "lines": [
        "Oxygen: {{vitals.oxygen_use}}",
        {
            "text": "Flow: {{vitals.oxygen_flow}}L",
            "showIf": {"op": "eq", "field": "vitals.oxygen_use", "value": "oxygen"},
            "omitIfAllBlank": ["vitals.oxygen_flow"],
        },
    ],
}


def assert_status(response, expected_status, label, failures):
    status = response.status_code
    print(f"{status:3} {label}")
    if status != expected_status:
        failures.append((label, expected_status, status))


def assert_json_contains(response, predicate, label, failures):
    data = response.get_json()
    matched = predicate(data)
    print((" OK " if matched else "FAIL") + " " + label)
    if not matched:
        failures.append((label, "matching JSON", data))


def render_template_line(text, values, override_ref=None, override_value=None):
    import re

    def replace(match):
        ref = f"{match.group(1)}.{match.group(2)}"
        if ref == override_ref:
            return override_value or "__"
        return values.get(ref) or "__"

    return re.sub(r"\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}", replace, text)


def should_omit_line(line, values):
    refs = line.get("omitIfAllBlank")
    return isinstance(refs, list) and all(not str(values.get(ref, "")).strip() for ref in refs)


def render_generic_copy(copy_format, values):
    lines = []
    for line in copy_format["lines"]:
        if isinstance(line, str):
            lines.append(render_template_line(line, values))
            continue
        if should_omit_line(line, values):
            continue
        split_ref = line.get("splitLinesFrom")
        if split_ref:
            for part in str(values.get(split_ref, "")).splitlines():
                text = part.strip()
                if text:
                    lines.append(render_template_line(line.get("text", f"{{{{{split_ref}}}}}"), values, split_ref, text))
            continue
        lines.append(render_template_line(line.get("text", ""), values))
    return "\n".join(lines)


def value_or_blank(values, ref):
    return values.get(ref) or "__"


def render_legacy_stroke_copy(full, values):
    # Mirrors the old stroke-v1 branch in js/copy-format.js:
    # title, vitals as one full-width-space separated line, symptoms, neuro rows,
    # optional Barre/Mingazzini rows, newline-split "other", then rest.
    lines = [
        full,
        "",
        "JCS{jcs}　T{t}℃　BP{bp}mmHg　HR{hr}　SpO₂{spo2}%".format(
            jcs=value_or_blank(values, "vitals.jcs"),
            t=value_or_blank(values, "vitals.t"),
            bp=value_or_blank(values, "vitals.bp"),
            hr=value_or_blank(values, "vitals.hr"),
            spo2=value_or_blank(values, "vitals.spo2"),
        ),
        "",
        f"頭痛：{value_or_blank(values, 'symptoms.headache')}",
        f"めまい：{value_or_blank(values, 'symptoms.dizzy')}",
        f"嘔気：{value_or_blank(values, 'symptoms.nausea')}",
        "",
        "神経所見",
        f"瞳孔：{value_or_blank(values, 'neuro.pupil')}",
        f"対光反射：{value_or_blank(values, 'neuro.light')}",
        f"眼球位置：{value_or_blank(values, 'neuro.eye')}",
    ]
    if values.get("neuro.barre", "").strip():
        lines.append(f"バレー徴候：{values['neuro.barre']}")
    if values.get("neuro.mingazzini", "").strip():
        lines.append(f"ミンガッチー徴候：{values['neuro.mingazzini']}")
    lines.extend(
        [
            "MMT：右上肢{ru}、右下肢{rl}、左上肢{lu}、左下肢{ll}".format(
                ru=value_or_blank(values, "mmt.ru"),
                rl=value_or_blank(values, "mmt.rl"),
                lu=value_or_blank(values, "mmt.lu"),
                ll=value_or_blank(values, "mmt.ll"),
            ),
            f"NIHSS：{value_or_blank(values, 'neuro.nihss')}",
        ]
    )
    for line in str(values.get("neuro.other", "")).splitlines():
        if line.strip():
            lines.append(line.strip())
    lines.extend(["", "安静度", value_or_blank(values, "rest.level")])
    return "\n".join(lines)


def assert_stroke_copy_compat(client, failures):
    response = client.get("/api/templates/mca")
    data = response.get_json()
    copy_format = data["copy_format"]
    full = data["full"]
    cases = [
        ("empty", {}),
        (
            "representative",
            {
                "vitals.jcs": "0",
                "vitals.t": "36.5",
                "vitals.bp": "120/70",
                "vitals.hr": "72",
                "vitals.spo2": "98",
                "symptoms.headache": "なし",
                "symptoms.dizzy": "なし",
                "symptoms.nausea": "なし",
                "neuro.pupil": "2.5/2.5mm",
                "neuro.light": "あり",
                "neuro.eye": "正中位",
                "neuro.barre": "陰性",
                "neuro.mingazzini": "左軽度下垂",
                "mmt.ru": "5/5",
                "mmt.rl": "5/5",
                "mmt.lu": "4/5",
                "mmt.ll": "4/5",
                "neuro.nihss": "2",
                "neuro.other": "構音障害あり",
                "rest.level": "ベッド上安静",
            },
        ),
        (
            "branching",
            {
                "vitals.jcs": "I-1",
                "vitals.t": "36.4",
                "vitals.bp": "130/80",
                "vitals.hr": "80台",
                "vitals.spo2": "96",
                "symptoms.headache": "",
                "symptoms.dizzy": "あり",
                "symptoms.nausea": "",
                "neuro.pupil": "3.0/3.0mm",
                "neuro.light": "あり",
                "neuro.eye": "正中位",
                "neuro.barre": "",
                "neuro.mingazzini": "",
                "mmt.ru": "5/5",
                "mmt.rl": "5/5",
                "mmt.lu": "4/5",
                "mmt.ll": "4/5",
                "neuro.nihss": "4",
                "neuro.other": "左口角下垂あり\n構音障害あり\n\n左半身感覚鈍麻あり",
                "rest.level": "ベッド上安静",
            },
        ),
    ]
    for name, values in cases:
        expected = render_legacy_stroke_copy(full, values)
        actual = render_generic_copy(copy_format, values)
        matched = expected == actual
        print((" OK " if matched else "FAIL") + f" stroke copy compat {name}")
        if not matched:
            failures.append((f"stroke copy compat {name}", expected, actual))

    extra_values = {**cases[1][1], "stroke_findings.left_mouth_droop": "あり"}
    extra_output = render_generic_copy(copy_format, extra_values)
    matched = "左口角下垂：あり" in extra_output and "左口角下垂：__" not in render_generic_copy(copy_format, cases[1][1])
    print((" OK " if matched else "FAIL") + " stroke copy extra fields are optional")
    if not matched:
        failures.append(("stroke copy extra fields are optional", "optional extra output", extra_output))


def run_get_tests(client, failures):
    for path, expected_status in EXPECTED_GETS:
        response = client.get(path)
        assert_status(response, expected_status, path, failures)


def run_write_tests(failures):
    original_db_path = os.environ.get("NASUKERU_DB_PATH")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["NASUKERU_DB_PATH"] = str(Path(tmp) / "nasukeru-test.db")
            init_db_main()

            client = app.test_client()
            mca_response = client.get("/api/templates/mca")
            assert_status(mca_response, 200, "GET /api/templates/mca after migration", failures)
            assert_json_contains(
                mca_response,
                lambda item: item["schema_format"] == "generic-v1"
                and any(
                    section["id"] == "stroke_findings"
                    and any(field["id"] == "left_mouth_droop" for field in section["fields"])
                    for section in item["schema"]["sections"]
                )
                and any(
                    section["id"] == "neuro"
                    and any(field["id"] == "other" for field in section["fields"])
                    for section in item["schema"]["sections"]
                ),
                "GET /api/templates/mca includes MCA-specific generic fields",
                failures,
            )
            mca_admin_response = client.get("/api/admin/templates/mca")
            assert_status(mca_admin_response, 200, "GET /api/admin/templates/mca after migration", failures)
            assert_json_contains(
                mca_admin_response,
                lambda item: item["current_version_number"] >= 3,
                "GET /api/admin/templates/mca includes current version number",
                failures,
            )
            neuro_common_response = client.get("/api/templates/neuro_common")
            assert_status(neuro_common_response, 200, "GET /api/templates/neuro_common after migration", failures)
            assert_json_contains(
                neuro_common_response,
                lambda item: item["schema_format"] == "generic-v1"
                and item["label"] == "脳卒中共通"
                and any(
                    section["id"] == "motor"
                    and any(field["id"] == "barre_side" and field["type"] == "multi_select" for field in section["fields"])
                    and any(field["id"] == "barre_angle" and field["type"] == "number" for field in section["fields"])
                    for section in item["schema"]["sections"]
                )
                and item["copy_format"]["format"] == "text-v1",
                "GET /api/templates/neuro_common returns common generic schema",
                failures,
            )
            assert_json_contains(
                client.get("/api/quick-templates"),
                lambda items: any(
                    item["label"] == "脳梗塞"
                    and item["target"] == {"type": "group", "id": "cerebral_infarction"}
                    for item in items
                )
                and any(
                    item["label"] == "脳卒中共通"
                    and item["target"] == {"type": "template", "id": "neuro_common"}
                    for item in items
                ),
                "GET /api/quick-templates includes neuro common",
                failures,
            )
            assert_json_contains(
                client.get("/api/search-keywords"),
                lambda items: any(
                    item["keyword"] == "脳梗塞"
                    and item["target"] == {"type": "group", "id": "cerebral_infarction"}
                    for item in items
                )
                and any(
                    item["keyword"] == "脳卒中共通"
                    and item["target"] == {"type": "template", "id": "neuro_common"}
                    for item in items
                ),
                "GET /api/search-keywords includes neuro common keywords",
                failures,
            )
            assert_json_contains(
                client.get("/api/template-groups/cerebral_infarction"),
                lambda group: group["id"] == "cerebral_infarction"
                and [item["id"] for item in group["templates"]] == ["mca", "aca", "pca", "lacunar", "brainstem"],
                "GET /api/template-groups/cerebral_infarction returns stroke group",
                failures,
            )

            create_payload = {
                "id": "test_template",
                "label": "TEST",
                "full": "Test template",
                "category": "stroke",
                "schema": BASE_SCHEMA,
                "change_reason": "smoke create",
            }

            assert_status(client.post("/api/templates", json=create_payload), 403, "POST /api/templates without local guard", failures)
            bad_id_payload = {**create_payload, "id": "../bad"}
            assert_status(client.post("/api/templates", json=bad_id_payload, headers=LOCAL_HEADERS), 400, "POST /api/templates invalid id", failures)
            unknown_stroke_schema = copy.deepcopy(BASE_SCHEMA)
            unknown_stroke_schema["vitals"]["rr"] = ""
            unknown_stroke_payload = {
                **create_payload,
                "id": "bad_stroke_unknown",
                "schema": unknown_stroke_schema,
            }
            assert_status(
                client.post("/api/templates", json=unknown_stroke_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates stroke-v1 unknown schema key",
                failures,
            )
            non_empty_create_payload = {
                **create_payload,
                "id": "bad_initial",
                "schema": NON_EMPTY_BASE_SCHEMA,
            }
            assert_status(
                client.post("/api/templates", json=non_empty_create_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates stroke-v1 non-empty initial values",
                failures,
            )
            create_response = client.post("/api/templates", json=create_payload, headers=LOCAL_HEADERS)
            assert_status(create_response, 201, "POST /api/templates", failures)
            assert_status(client.post("/api/templates", json=create_payload, headers=LOCAL_HEADERS), 409, "POST /api/templates duplicate", failures)
            assert_status(client.get("/api/templates/test_template"), 200, "GET /api/templates/test_template", failures)
            created_detail = client.get("/api/admin/templates/test_template")
            assert_status(created_detail, 200, "GET /api/admin/templates/test_template before update", failures)
            base_version_id = (created_detail.get_json() or {}).get("current_version_id")

            update_payload = {
                "base_version_id": base_version_id,
                "schema": BASE_SCHEMA,
                "change_summary": "smoke update",
                "change_reason": "smoke edit",
            }
            non_empty_update_payload = {
                **update_payload,
                "schema": NON_EMPTY_BASE_SCHEMA,
            }
            missing_base_version = {
                "schema": BASE_SCHEMA,
                "change_summary": "smoke update",
                "change_reason": "smoke edit",
            }
            assert_status(
                client.post("/api/templates/test_template/versions", json=missing_base_version, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates/test_template/versions missing base_version_id",
                failures,
            )
            missing_reason = {"base_version_id": base_version_id, "schema": BASE_SCHEMA, "change_summary": "smoke update"}
            assert_status(
                client.post("/api/templates/test_template/versions", json=missing_reason, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates/test_template/versions missing reason",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/versions", json=non_empty_update_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates/test_template/versions stroke-v1 non-empty initial values",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/versions", json=update_payload, headers=LOCAL_HEADERS),
                201,
                "POST /api/templates/test_template/versions",
                failures,
            )
            updated_detail = client.get("/api/admin/templates/test_template")
            assert_status(updated_detail, 200, "GET /api/admin/templates/test_template after update", failures)
            current_version_id = (updated_detail.get_json() or {}).get("current_version_id")
            stale_update_payload = {
                **update_payload,
                "change_reason": "smoke stale edit",
            }
            assert_status(
                client.post("/api/templates/test_template/versions", json=stale_update_payload, headers=LOCAL_HEADERS),
                409,
                "POST /api/templates/test_template/versions stale base_version_id",
                failures,
            )
            latest_update_payload = {
                **update_payload,
                "base_version_id": current_version_id,
            }
            assert_status(
                client.post("/api/templates/test_template/delete", json={"reason": "smoke delete"}, headers=LOCAL_HEADERS),
                200,
                "POST /api/templates/test_template/delete",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/delete", json={"reason": "smoke delete again"}, headers=LOCAL_HEADERS),
                409,
                "POST /api/templates/test_template/delete again",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/versions", json=latest_update_payload, headers=LOCAL_HEADERS),
                409,
                "POST /api/templates/test_template/versions while deleted",
                failures,
            )
            assert_status(client.get("/api/templates/test_template"), 404, "GET /api/templates/test_template while deleted", failures)
            assert_status(client.get("/api/templates/test_template/versions"), 200, "GET /api/templates/test_template/versions while deleted", failures)
            assert_status(client.get("/api/templates/test_template/logs"), 200, "GET /api/templates/test_template/logs while deleted", failures)
            assert_status(client.get("/api/templates?include_inactive=1"), 200, "GET /api/templates?include_inactive=1", failures)
            admin_response = client.get("/api/admin/templates")
            assert_status(admin_response, 200, "GET /api/admin/templates after delete", failures)
            assert_json_contains(
                admin_response,
                lambda items: any(item["id"] == "test_template" and item["is_active"] is False for item in items),
                "GET /api/admin/templates includes deleted template",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/restore", json={"reason": "smoke restore"}, headers=LOCAL_HEADERS),
                200,
                "POST /api/templates/test_template/restore",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/restore", json={"reason": "smoke restore again"}, headers=LOCAL_HEADERS),
                409,
                "POST /api/templates/test_template/restore again",
                failures,
            )

            generic_payload = {
                "id": "generic_test",
                "label": "GEN",
                "full": "Generic test",
                "category": "procedure",
                "schema": GENERIC_SCHEMA,
                "copy_format": GENERIC_COPY_FORMAT,
                "change_reason": "smoke create generic",
            }
            assert_status(
                client.post("/api/templates", json=generic_payload, headers=LOCAL_HEADERS),
                201,
                "POST /api/templates generic-v1",
                failures,
            )
            generic_detail = client.get("/api/admin/templates/generic_test")
            assert_status(generic_detail, 200, "GET /api/admin/templates/generic_test", failures)
            assert_json_contains(
                generic_detail,
                lambda item: item["schema_format"] == "generic-v1"
                and item["schema"]["schemaFormat"] == "generic-v1"
                and item["schema"]["sections"][0]["fields"][1]["options"][0] == {"value": "none", "label": "なし"}
                and item["copy_format"]["format"] == "text-v1"
                and item["copy_format"]["lines"][2]["omitIfAllBlank"] == ["basic.status"]
                and item["copy_format"]["lines"][3]["splitLinesFrom"] == "basic.status",
                "GET /api/admin/templates/generic_test returns generic schema",
                failures,
            )
            generic_normal_detail = client.get("/api/templates/generic_test")
            assert_status(generic_normal_detail, 200, "GET /api/templates/generic_test", failures)
            assert_json_contains(
                generic_normal_detail,
                lambda item: item["schema_format"] == "generic-v1"
                and item["schema"]["schemaFormat"] == "generic-v1"
                and item["copy_format"]["lines"][0] == "Procedure: {{basic.procedure}}",
                "GET /api/templates/generic_test returns generic schema",
                failures,
            )
            templates_response = client.get("/api/templates")
            assert_status(templates_response, 200, "GET /api/templates after generic create", failures)
            assert_json_contains(
                templates_response,
                lambda items: any(item["id"] == "generic_test" and item["schema_format"] == "generic-v1" for item in items),
                "GET /api/templates includes generic-v1",
                failures,
            )

            extended_generic_payload = {
                "id": "generic_extended",
                "label": "EXT",
                "full": "Generic extended",
                "category": "procedure",
                "schema": EXTENDED_GENERIC_SCHEMA,
                "copy_format": EXTENDED_GENERIC_COPY_FORMAT,
                "change_reason": "smoke create extended generic",
            }
            assert_status(
                client.post("/api/templates", json=extended_generic_payload, headers=LOCAL_HEADERS),
                201,
                "POST /api/templates generic-v1 multi_select number",
                failures,
            )
            extended_detail = client.get("/api/admin/templates/generic_extended")
            assert_status(extended_detail, 200, "GET /api/admin/templates/generic_extended", failures)
            assert_json_contains(
                extended_detail,
                lambda item: item["schema"]["sections"][0]["fields"][0]["type"] == "multi_select"
                and item["schema"]["sections"][0]["fields"][0]["options"][0] == {"value": "headache", "label": "headache"}
                and item["schema"]["sections"][0]["fields"][1]["type"] == "number"
                and item["schema"]["sections"][0]["fields"][1]["unit"] == "ml",
                "GET /api/admin/templates/generic_extended returns extended field types",
                failures,
            )

            generic_v2_payload = {
                "id": "generic_v2_test",
                "label": "GV2",
                "full": "Generic v2 test",
                "category": "procedure",
                "schema": GENERIC_V2_SCHEMA,
                "copy_format": GENERIC_V2_COPY_FORMAT,
                "change_reason": "smoke create generic v2",
            }
            assert_status(
                client.post("/api/templates", json=generic_v2_payload, headers=LOCAL_HEADERS),
                201,
                "POST /api/templates generic-v2 condition",
                failures,
            )
            generic_v2_detail = client.get("/api/templates/generic_v2_test")
            assert_status(generic_v2_detail, 200, "GET /api/templates/generic_v2_test", failures)
            assert_json_contains(
                generic_v2_detail,
                lambda item: item["schema_format"] == "generic-v2"
                and item["schema"]["sections"][0]["fields"][1]["visibleIf"]["field"] == "vitals.oxygen_use"
                and item["schema"]["sections"][0]["fields"][1]["requiredIf"]["value"] == "oxygen"
                and item["schema"]["sections"][0]["fields"][1]["blankPolicy"] == "block"
                and item["schema"]["sections"][0]["fields"][1]["hardRange"] == {"min": 0, "max": 15}
                and item["copy_format"]["lines"][1]["showIf"]["op"] == "eq",
                "GET /api/templates/generic_v2_test returns condition schema",
                failures,
            )
            generic_v2_admin_detail = client.get("/api/admin/templates/generic_v2_test")
            assert_status(generic_v2_admin_detail, 200, "GET /api/admin/templates/generic_v2_test", failures)
            generic_v2_base_version_id = (generic_v2_admin_detail.get_json() or {}).get("current_version_id")
            risky_schema = copy.deepcopy(GENERIC_V2_SCHEMA)
            risky_schema["sections"][0]["fields"] = [risky_schema["sections"][0]["fields"][0]]
            risky_copy_format = {"format": "text-v1", "lines": ["Oxygen: {{vitals.oxygen_use}}"]}
            risky_update_payload = {
                "base_version_id": generic_v2_base_version_id,
                "schema": risky_schema,
                "copy_format": risky_copy_format,
                "change_summary": "smoke risky update",
                "change_reason": "smoke risk diff",
            }
            risky_update = client.post(
                "/api/templates/generic_v2_test/versions",
                json=risky_update_payload,
                headers=LOCAL_HEADERS,
            )
            assert_status(risky_update, 201, "POST /api/templates/generic_v2_test/versions high risk diff", failures)
            assert_json_contains(
                risky_update,
                lambda item: any(change["code"] == "field_deleted" for change in item["high_risk_changes"])
                and any(change["code"] == "copy_line_deleted" for change in item["high_risk_changes"]),
                "POST /api/templates/generic_v2_test/versions returns high risk changes",
                failures,
            )

            invalid_generic_payload = {
                **generic_payload,
                "id": "bad_generic",
                "schema": {
                    "schemaFormat": "generic-v1",
                    "sections": [
                        {
                            "id": "basic",
                            "label": "Basic",
                            "fields": [
                                {"id": "status", "label": "Status", "type": "select"}
                            ],
                        }
                    ],
                },
            }
            assert_status(
                client.post("/api/templates", json=invalid_generic_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid select options",
                failures,
            )

            invalid_multi_select_payload = copy.deepcopy(generic_payload)
            invalid_multi_select_payload["id"] = "bad_multi_select"
            invalid_multi_select_payload["schema"] = {
                "schemaFormat": "generic-v1",
                "sections": [
                    {
                        "id": "observe",
                        "label": "Observe",
                        "fields": [
                            {"id": "symptoms", "label": "Symptoms", "type": "multi_select"}
                        ],
                    }
                ],
            }
            assert_status(
                client.post("/api/templates", json=invalid_multi_select_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid multi_select options",
                failures,
            )

            duplicate_option_payload = copy.deepcopy(generic_payload)
            duplicate_option_payload["id"] = "bad_duplicate_option"
            duplicate_option_payload["schema"]["sections"][0]["fields"][1]["options"] = [
                {"value": "same", "label": "One"},
                {"value": "same", "label": "Two"},
            ]
            assert_status(
                client.post("/api/templates", json=duplicate_option_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 duplicate option value",
                failures,
            )

            unknown_option_key_payload = copy.deepcopy(generic_payload)
            unknown_option_key_payload["id"] = "bad_option_key"
            unknown_option_key_payload["schema"]["sections"][0]["fields"][1]["options"] = [
                {"value": "none", "label": "None", "code": "x"}
            ]
            assert_status(
                client.post("/api/templates", json=unknown_option_key_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 unknown option key",
                failures,
            )

            generic_v1_condition_payload = copy.deepcopy(generic_payload)
            generic_v1_condition_payload["id"] = "bad_v1_condition"
            generic_v1_condition_payload["schema"]["sections"][0]["fields"][1]["visibleIf"] = {
                "op": "eq",
                "field": "basic.procedure",
                "value": "x",
            }
            assert_status(
                client.post("/api/templates", json=generic_v1_condition_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 rejects condition keys",
                failures,
            )

            unknown_condition_ref_payload = copy.deepcopy(generic_v2_payload)
            unknown_condition_ref_payload["id"] = "bad_condition_ref"
            unknown_condition_ref_payload["schema"]["sections"][0]["fields"][1]["visibleIf"]["field"] = "vitals.unknown"
            assert_status(
                client.post("/api/templates", json=unknown_condition_ref_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v2 unknown condition field",
                failures,
            )

            invalid_show_if_payload = copy.deepcopy(generic_v2_payload)
            invalid_show_if_payload["id"] = "bad_show_if"
            invalid_show_if_payload["copy_format"]["lines"][1]["showIf"]["field"] = "vitals.unknown"
            assert_status(
                client.post("/api/templates", json=invalid_show_if_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v2 invalid showIf field",
                failures,
            )

            invalid_range_payload = copy.deepcopy(generic_v2_payload)
            invalid_range_payload["id"] = "bad_hard_range"
            invalid_range_payload["schema"]["sections"][0]["fields"][1]["hardRange"] = {"min": 20, "max": 10}
            assert_status(
                client.post("/api/templates", json=invalid_range_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v2 invalid hardRange",
                failures,
            )

            invalid_number_payload = copy.deepcopy(generic_payload)
            invalid_number_payload["id"] = "bad_number"
            invalid_number_payload["schema"] = copy.deepcopy(EXTENDED_GENERIC_SCHEMA)
            invalid_number_payload["schema"]["sections"][0]["fields"][1]["step"] = 0
            assert_status(
                client.post("/api/templates", json=invalid_number_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid number step",
                failures,
            )

            unknown_generic_payload = copy.deepcopy(generic_payload)
            unknown_generic_payload["id"] = "bad_generic_unknown"
            unknown_generic_payload["schema"]["sections"][0]["fields"][0]["unexpected"] = ""
            assert_status(
                client.post("/api/templates", json=unknown_generic_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 unknown schema key",
                failures,
            )

            invalid_copy_format_payload = {
                **generic_payload,
                "id": "bad_copy_format",
                "copy_format": {"format": "text-v1", "lines": [123]},
            }
            assert_status(
                client.post("/api/templates", json=invalid_copy_format_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid copy_format",
                failures,
            )

            unknown_copy_format_payload = {
                **generic_payload,
                "id": "bad_copy_unknown",
                "copy_format": {
                    "format": "text-v1",
                    "lines": [
                        {"text": "Status: {{basic.status}}", "unexpected": ""}
                    ],
                },
            }
            assert_status(
                client.post("/api/templates", json=unknown_copy_format_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 unknown copy_format key",
                failures,
            )

            missing_copy_ref_payload = {
                **generic_payload,
                "id": "bad_copy_missing_ref",
                "copy_format": {
                    "format": "text-v1",
                    "lines": [
                        "Missing: {{basic.missing}}"
                    ],
                },
            }
            assert_status(
                client.post("/api/templates", json=missing_copy_ref_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 missing copy_format ref",
                failures,
            )

            invalid_copy_ref_payload = {
                **generic_payload,
                "id": "bad_copy_ref",
                "copy_format": {
                    "format": "text-v1",
                    "lines": [
                        {"text": "Bad: {{basic.status}}", "omitIfAllBlank": ["bad ref"]}
                    ],
                },
            }
            assert_status(
                client.post("/api/templates", json=invalid_copy_ref_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid copy_format ref",
                failures,
            )

            invalid_copy_split_payload = {
                **generic_payload,
                "id": "bad_copy_split",
                "copy_format": {
                    "format": "text-v1",
                    "lines": [
                        {"text": "{{basic.status}}", "splitLinesFrom": "bad ref"}
                    ],
                },
            }
            assert_status(
                client.post("/api/templates", json=invalid_copy_split_payload, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates generic-v1 invalid copy_format split ref",
                failures,
            )
            assert_stroke_copy_compat(client, failures)
    finally:
        if original_db_path is None:
            os.environ.pop("NASUKERU_DB_PATH", None)
        else:
            os.environ["NASUKERU_DB_PATH"] = original_db_path


def main():
    client = app.test_client()
    failures = []
    run_get_tests(client, failures)
    run_write_tests(failures)
    if failures:
        details = ", ".join(
            f"{path}: expected {expected}, got {actual}"
            for path, expected, actual in failures
        )
        raise SystemExit(f"Smoke test failed: {details}")


if __name__ == "__main__":
    main()
