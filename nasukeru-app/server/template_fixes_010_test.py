import json
import os
import tempfile
from pathlib import Path

import init_db
from template_fixes_010 import (
    HORIZONTAL_NYSTAGMUS_OPTIONS,
    SIDE_OPTIONS,
    apply_template_fixes,
)
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


def assert_condition(field, expected):
    assert field.get("visibleIf") == expected
    assert field.get("requiredIf") == expected


def main():
    old_db_path = os.environ.get("NASUKERU_DB_PATH")
    failures = []
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "nasukeru-test.db"
        os.environ["NASUKERU_DB_PATH"] = str(db_path)
        try:
            init_db.main()
            with init_db.connect(db_path) as conn:
                before_count = conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0]

            assert apply_template_fixes(db_path) is True

            with init_db.connect(db_path) as conn:
                migration = conn.execute("SELECT name FROM schema_migrations WHERE version = '010'").fetchone()
                assert migration is not None

                _, status, mca_schema, mca_copy = current_definition(conn, "mca")
                assert status == "published"
                mca_fields = field_map(mca_schema)
                assert "stroke_findings.left_mouth_droop" not in mca_fields
                assert "stroke_findings.left_sensory_dullness" not in mca_fields
                assert option_labels(mca_fields["stroke_findings.mouth_droop"]) == SIDE_OPTIONS
                assert option_labels(mca_fields["stroke_findings.sensory_dullness"]) == SIDE_OPTIONS
                validate_copy_format_references(mca_schema, mca_copy)

                _, _, pca_schema, pca_copy = current_definition(conn, "pca")
                pca_fields = field_map(pca_schema)
                assert "stroke_findings.left_homonymous_hemianopia" not in pca_fields
                assert "stroke_findings.left_sensory_dullness" not in pca_fields
                assert option_labels(pca_fields["stroke_findings.homonymous_hemianopia"]) == SIDE_OPTIONS
                assert option_labels(pca_fields["stroke_findings.sensory_dullness"]) == SIDE_OPTIONS
                validate_copy_format_references(pca_schema, pca_copy)

                _, _, brainstem_schema, brainstem_copy = current_definition(conn, "brainstem")
                brainstem_fields = field_map(brainstem_schema)
                assert "stroke_findings.horizontal_nystagmus_right_gaze" not in brainstem_fields
                assert option_labels(brainstem_fields["stroke_findings.horizontal_nystagmus"]) == HORIZONTAL_NYSTAGMUS_OPTIONS
                validate_copy_format_references(brainstem_schema, brainstem_copy)

                _, neuro_status, neuro_schema, neuro_copy = current_definition(conn, "neuro_common")
                assert neuro_status == "published"
                assert neuro_schema["schemaFormat"] == "generic-v2"
                fields = field_map(neuro_schema)

                assert_condition(fields["vitals.ecg_rhythm_other"], {"op": "eq", "field": "vitals.ecg_rhythm", "value": "その他"})
                assert_condition(fields["vitals.oxygen_flow"], {"op": "eq", "field": "vitals.oxygen_use", "value": "O2使用"})
                # thickened_water_level / dysphagia_diet_level / antihypertensive_other now
                # come from the genesis (init_db.py) definition; migration 010's own insert
                # is a no-op guard since these fields already exist (see has_field in
                # template_fixes_010.py). Genesis only sets visibleIf (optional fields),
                # not requiredIf, so these three are checked directly rather than via
                # assert_condition (which requires both to match).
                assert option_labels(fields["swallow.thickened_water_level"]) == ["薄め", "中程度", "濃い"]
                assert fields["swallow.thickened_water_level"]["visibleIf"] == {"op": "contains", "field": "swallow.meal", "value": "とろみ水"}
                assert fields["swallow.dysphagia_diet_level"]["type"] == "number"
                assert fields["swallow.dysphagia_diet_level"]["min"] == 1
                assert fields["swallow.dysphagia_diet_level"]["max"] == 5
                assert fields["swallow.dysphagia_diet_level"]["visibleIf"] == {"op": "contains", "field": "swallow.meal", "value": "嚥下食"}
                assert_condition(fields["treatment.nicardipine_rate"], {"op": "contains", "field": "treatment.antihypertensive", "value": "ニカルジピン"})
                assert fields["treatment.antihypertensive_other"]["visibleIf"] == {"op": "contains", "field": "treatment.antihypertensive", "value": "その他"}
                validate_copy_format_references(neuro_schema, neuro_copy)

                current_ids = conn.execute("SELECT current_version_id FROM templates WHERE id IN ('mca','aca','pca','lacunar','brainstem','neuro_common')").fetchall()
                for (version_id,) in current_ids:
                    assert conn.execute("SELECT status FROM template_versions WHERE id = ?", (version_id,)).fetchone()[0] == "published"

                after_count = conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0]
                assert after_count == before_count + 6

            assert apply_template_fixes(db_path) is False
            with init_db.connect(db_path) as conn:
                assert conn.execute("SELECT COUNT(*) FROM template_versions").fetchone()[0] == after_count

            print(" OK  template fixes migration 010")
        except Exception as error:
            failures.append(str(error))
            print("FAIL template fixes migration 010")
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
