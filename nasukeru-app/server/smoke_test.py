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
    ("/api/health", 200),
    ("/api/admin/templates", 200),
    ("/api/admin/templates/mca", 200),
    ("/api/templates", 200),
    ("/api/templates/mca", 200),
    ("/api/templates/mca/versions", 200),
    ("/api/templates/mca/versions/1", 200),
    ("/api/templates/mca/logs", 200),
    ("/api/templates/unknown", 404),
    ("/api/templates/unknown/versions", 404),
    ("/api/templates/unknown/logs", 404),
    ("/api/quick-templates", 200),
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
                    "options": ["none", "present"],
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
            assert_status(client.post("/api/templates", json=create_payload, headers=LOCAL_HEADERS), 201, "POST /api/templates", failures)
            assert_status(client.post("/api/templates", json=create_payload, headers=LOCAL_HEADERS), 409, "POST /api/templates duplicate", failures)
            assert_status(client.get("/api/templates/test_template"), 200, "GET /api/templates/test_template", failures)

            update_payload = {
                "schema": BASE_SCHEMA,
                "change_summary": "smoke update",
                "change_reason": "smoke edit",
            }
            missing_reason = {"schema": BASE_SCHEMA, "change_summary": "smoke update"}
            assert_status(
                client.post("/api/templates/test_template/versions", json=missing_reason, headers=LOCAL_HEADERS),
                400,
                "POST /api/templates/test_template/versions missing reason",
                failures,
            )
            assert_status(
                client.post("/api/templates/test_template/versions", json=update_payload, headers=LOCAL_HEADERS),
                201,
                "POST /api/templates/test_template/versions",
                failures,
            )
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
                client.post("/api/templates/test_template/versions", json=update_payload, headers=LOCAL_HEADERS),
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
                and item["copy_format"]["format"] == "text-v1",
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
