import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import init_db
import template_fixes_010 as m010
from template_fixes_011 import apply_neuro_common_alignment
from template_schema import validate_copy_format_references


def option_labels(field):
    return [option["label"] if isinstance(option, dict) else option for option in field.get("options", [])]


def field_map(schema):
    return {
        f"{section['id']}.{field['id']}": field
        for section in schema.get("sections", [])
        for field in section.get("fields", [])
    }


def current_definition(conn, template_id):
    row = conn.execute(
        """
        SELECT v.id, v.status, v.schema_json, v.copy_format_json
        FROM templates t
        JOIN template_versions v ON v.id = t.current_version_id
        WHERE t.id = ?
        """,
        (template_id,),
    ).fetchone()
    return row[0], row[1], json.loads(row[2]), json.loads(row[3])


def antihypertensive_copy_lines(copy_format):
    return [
        line.get("text")
        for line in copy_format["lines"]
        if isinstance(line, dict) and "antihypertensive" in json.dumps(line, ensure_ascii=False)
    ]


def seed_legacy_010_neuro_common(conn, now):
    # Reproduce the shape a real production DB would have if migration 010 ran
    # before this task introduced the genesis (init_db.py) fix: dysphagia as a
    # select, "濃いめ" wording, and antihypertensive-other on its own copy line.
    schema = m010.build_corrected_neuro_common_schema()
    copy_format = m010.build_corrected_neuro_common_copy_format()
    for section in schema["sections"]:
        if section["id"] == "swallow":
            for field in section["fields"]:
                if field["id"] == "thickened_water_level":
                    field["options"] = [{"value": v, "label": v} for v in ["薄め", "中程度", "濃いめ"]]
                if field["id"] == "dysphagia_diet_level":
                    field["type"] = "select"
                    field.pop("min", None)
                    field.pop("max", None)
                    field.pop("step", None)
                    field["options"] = [{"value": v, "label": v} for v in ["1", "2", "3", "4", "5"]]
        if section["id"] == "treatment":
            for field in section["fields"]:
                if field["id"] == "antihypertensive_other":
                    field["label"] = "その他の降圧薬"
    m010.publish_system_version(conn, "neuro_common", schema, copy_format, "seed legacy", "seed legacy", now)
    conn.execute(
        "INSERT INTO schema_migrations (version, name, applied_at) VALUES ('010', 'legacy seed', ?)",
        (now,),
    )


def assert_unified_spec(schema, copy_format):
    fields = field_map(schema)
    assert option_labels(fields["swallow.thickened_water_level"]) == ["薄め", "中程度", "濃い"]
    dysphagia = fields["swallow.dysphagia_diet_level"]
    assert dysphagia["type"] == "number"
    assert dysphagia["min"] == 1
    assert dysphagia["max"] == 5
    assert fields["treatment.antihypertensive_other"]["label"] == "降圧薬その他"
    lines = antihypertensive_copy_lines(copy_format)
    # antihypertensive_other must stay on its own showIf-gated line (never concatenated
    # onto another field's value), so a blank value can never render as an unlabeled "__"
    # glued to the antihypertensive/nicardipine line.
    assert "降圧薬その他：{{treatment.antihypertensive_other}}。" in lines
    assert not any(text and text.startswith("その他の降圧薬") for text in lines)
    assert not any(
        text and "{{treatment.antihypertensive}}{{treatment.antihypertensive_other}}" in text for text in lines
    )
    validate_copy_format_references(schema, copy_format)


def main():
    old_db_path = os.environ.get("NASUKERU_DB_PATH")
    failures = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        db_path = Path(temp_dir) / "nasukeru-test.db"
        os.environ["NASUKERU_DB_PATH"] = str(db_path)
        try:
            # Case 1: fresh DB (genesis already has the unified spec; migration 010's
            # own inserts for these three fields no-op via has_field()).
            init_db.main()
            assert m010.apply_template_fixes(db_path) is True
            with init_db.connect(db_path) as conn:
                before_count = conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0]
            assert apply_neuro_common_alignment(db_path) is True
            with init_db.connect(db_path) as conn:
                migration = conn.execute("SELECT name FROM schema_migrations WHERE version = '011'").fetchone()
                assert migration is not None
                _, status, schema, copy_format = current_definition(conn, "neuro_common")
                assert status == "published"
                assert_unified_spec(schema, copy_format)
                after_count = conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0]
                assert after_count == before_count + 1

            assert apply_neuro_common_alignment(db_path) is False
            with init_db.connect(db_path) as conn:
                assert conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0] == after_count

            print(" OK  migration 011 aligns freshly seeded database")
        except Exception as error:
            failures.append(str(error))
            print("FAIL migration 011 aligns freshly seeded database")
            print(error)
        finally:
            if old_db_path is None:
                os.environ.pop("NASUKERU_DB_PATH", None)
            else:
                os.environ["NASUKERU_DB_PATH"] = old_db_path

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        db_path = Path(temp_dir) / "nasukeru-legacy.db"
        os.environ["NASUKERU_DB_PATH"] = str(db_path)
        try:
            # Case 2: a database that already applied the old migration 010 shape
            # (simulating a real pre-existing production database).
            init_db.main()
            now = datetime.now(timezone.utc).isoformat()
            with init_db.connect(db_path) as conn:
                seed_legacy_010_neuro_common(conn, now)

            assert apply_neuro_common_alignment(db_path) is True
            with init_db.connect(db_path) as conn:
                _, status, schema, copy_format = current_definition(conn, "neuro_common")
                assert status == "published"
                assert_unified_spec(schema, copy_format)

            print(" OK  migration 011 upgrades a previously migrated database")
        except Exception as error:
            failures.append(str(error))
            print("FAIL migration 011 upgrades a previously migrated database")
            print(error)
        finally:
            if old_db_path is None:
                os.environ.pop("NASUKERU_DB_PATH", None)
            else:
                os.environ["NASUKERU_DB_PATH"] = old_db_path

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
