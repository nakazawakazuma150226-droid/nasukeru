import re


TEMPLATE_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
SCHEMA_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
SCHEMA_FORMAT_STROKE_V1 = "stroke-v1"
SCHEMA_FORMAT_GENERIC_V1 = "generic-v1"
ALLOWED_SCHEMA_FORMATS = (SCHEMA_FORMAT_STROKE_V1, SCHEMA_FORMAT_GENERIC_V1)
ALLOWED_GENERIC_FIELD_TYPES = ("text", "textarea", "select")

REQUIRED_VITAL_KEYS = ("jcs", "t", "bp", "hr", "spo2")
REQUIRED_SYMPTOM_KEYS = ("headache", "dizzy", "nausea")
REQUIRED_NEURO_KEYS = (
    "pupil",
    "light",
    "eye",
    "barre",
    "mingazzini",
    "mmt",
    "nihss",
    "other",
)
REQUIRED_MMT_KEYS = ("ru", "rl", "lu", "ll")


class SchemaValidationError(ValueError):
    pass


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field} is required")
    return value.strip()


def validate_template_id(template_id):
    if not isinstance(template_id, str) or not TEMPLATE_ID_PATTERN.fullmatch(template_id):
        raise SchemaValidationError("id must match ^[a-z0-9_-]{1,32}$")
    return template_id


def require_object(value, field):
    if not isinstance(value, dict):
        raise SchemaValidationError(f"{field} must be an object")
    return value


def require_string(value, field):
    if not isinstance(value, str):
        raise SchemaValidationError(f"{field} must be a string")
    return value


def require_keys(obj, keys, field):
    missing = [key for key in keys if key not in obj]
    if missing:
        raise SchemaValidationError(f"{field} missing: {', '.join(missing)}")


def require_schema_id(value, field):
    if not isinstance(value, str) or not SCHEMA_ID_PATTERN.fullmatch(value):
        raise SchemaValidationError(f"{field} must match ^[a-z0-9_-]{{1,32}}$")
    return value


def require_optional_string(obj, key, field):
    if key in obj:
        require_string(obj[key], f"{field}.{key}")


def require_optional_bool(obj, key, field):
    if key in obj and not isinstance(obj[key], bool):
        raise SchemaValidationError(f"{field}.{key} must be a boolean")


def require_optional_number(obj, key, field):
    if key in obj and not isinstance(obj[key], (int, float)):
        raise SchemaValidationError(f"{field}.{key} must be a number")


def validate_string_map(obj, keys, field):
    require_keys(obj, keys, field)
    for key in keys:
        require_string(obj[key], f"{field}.{key}")


def schema_format(schema):
    require_object(schema, "schema")
    fmt = schema.get("schemaFormat", SCHEMA_FORMAT_STROKE_V1)
    if not isinstance(fmt, str):
        raise SchemaValidationError("schema.schemaFormat must be a string")
    if fmt not in ALLOWED_SCHEMA_FORMATS:
        raise SchemaValidationError(
            f"schema.schemaFormat must be one of: {', '.join(ALLOWED_SCHEMA_FORMATS)}"
        )
    return fmt


def validate_template_schema(schema):
    fmt = schema_format(schema)
    if fmt == SCHEMA_FORMAT_GENERIC_V1:
        return validate_generic_v1_schema(schema)
    return validate_stroke_v1_schema(schema)


def validate_stroke_v1_schema(schema):
    require_object(schema, "schema")

    require_keys(schema, ("vitals", "symptoms", "neuro", "rest"), "schema")
    vitals = require_object(schema["vitals"], "schema.vitals")
    symptoms = require_object(schema["symptoms"], "schema.symptoms")
    neuro = require_object(schema["neuro"], "schema.neuro")
    require_string(schema["rest"], "schema.rest")

    validate_string_map(vitals, REQUIRED_VITAL_KEYS, "schema.vitals")
    validate_string_map(symptoms, REQUIRED_SYMPTOM_KEYS, "schema.symptoms")
    require_keys(neuro, REQUIRED_NEURO_KEYS, "schema.neuro")

    for key in REQUIRED_NEURO_KEYS:
        if key == "mmt":
            continue
        require_string(neuro[key], f"schema.neuro.{key}")

    mmt = require_object(neuro["mmt"], "schema.neuro.mmt")
    validate_string_map(mmt, REQUIRED_MMT_KEYS, "schema.neuro.mmt")
    return schema


def validate_generic_field(field, section_field, used_ids):
    require_object(field, section_field)
    require_keys(field, ("id", "label", "type"), section_field)

    field_id = require_schema_id(field["id"], f"{section_field}.id")
    if field_id in used_ids:
        raise SchemaValidationError(f"{section_field}.id is duplicated: {field_id}")
    used_ids.add(field_id)

    require_text(field["label"], f"{section_field}.label")
    field_type = require_text(field["type"], f"{section_field}.type")
    if field_type not in ALLOWED_GENERIC_FIELD_TYPES:
        raise SchemaValidationError(
            f"{section_field}.type must be one of: {', '.join(ALLOWED_GENERIC_FIELD_TYPES)}"
        )

    require_optional_string(field, "placeholder", section_field)
    require_optional_string(field, "helpText", section_field)
    require_optional_string(field, "unit", section_field)
    require_optional_bool(field, "allowEmpty", section_field)
    require_optional_bool(field, "requiredWarning", section_field)
    require_optional_number(field, "displayOrder", section_field)

    if field_type == "select":
        if "options" not in field:
            raise SchemaValidationError(f"{section_field}.options is required for select")
        options = field["options"]
        if not isinstance(options, list) or not options:
            raise SchemaValidationError(f"{section_field}.options must be a non-empty array")
        for index, option in enumerate(options):
            require_string(option, f"{section_field}.options[{index}]")
    elif "options" in field:
        options = field["options"]
        if not isinstance(options, list):
            raise SchemaValidationError(f"{section_field}.options must be an array")
        for index, option in enumerate(options):
            require_string(option, f"{section_field}.options[{index}]")


def validate_generic_v1_schema(schema):
    require_object(schema, "schema")
    require_keys(schema, ("schemaFormat", "sections"), "schema")
    if schema["schemaFormat"] != SCHEMA_FORMAT_GENERIC_V1:
        raise SchemaValidationError("schema.schemaFormat must be generic-v1")

    sections = schema["sections"]
    if not isinstance(sections, list) or not sections:
        raise SchemaValidationError("schema.sections must be a non-empty array")

    used_section_ids = set()
    for section_index, section in enumerate(sections):
        section_field = f"schema.sections[{section_index}]"
        require_object(section, section_field)
        require_keys(section, ("id", "label", "fields"), section_field)

        section_id = require_schema_id(section["id"], f"{section_field}.id")
        if section_id in used_section_ids:
            raise SchemaValidationError(f"{section_field}.id is duplicated: {section_id}")
        used_section_ids.add(section_id)

        require_text(section["label"], f"{section_field}.label")
        require_optional_string(section, "helpText", section_field)
        require_optional_number(section, "displayOrder", section_field)

        fields = section["fields"]
        if not isinstance(fields, list) or not fields:
            raise SchemaValidationError(f"{section_field}.fields must be a non-empty array")
        used_field_ids = set()
        for field_index, field in enumerate(fields):
            validate_generic_field(field, f"{section_field}.fields[{field_index}]", used_field_ids)
    return schema


def ordered_with_known_keys(obj, known_keys):
    ordered = {key: obj[key] for key in known_keys if key in obj}
    for key, value in obj.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def normalize_schema(schema):
    validate_template_schema(schema)
    if schema_format(schema) == SCHEMA_FORMAT_GENERIC_V1:
        return normalize_generic_v1_schema(schema)
    return normalize_stroke_v1_schema(schema)


def normalize_stroke_v1_schema(schema):
    normalized = ordered_with_known_keys(
        {
            **schema,
            "vitals": ordered_with_known_keys(schema["vitals"], REQUIRED_VITAL_KEYS),
            "symptoms": ordered_with_known_keys(schema["symptoms"], REQUIRED_SYMPTOM_KEYS),
            "neuro": ordered_with_known_keys(
                {
                    **schema["neuro"],
                    "mmt": ordered_with_known_keys(schema["neuro"]["mmt"], REQUIRED_MMT_KEYS),
                },
                REQUIRED_NEURO_KEYS,
            ),
        },
        ("vitals", "symptoms", "neuro", "rest"),
    )
    return normalized


def normalize_generic_v1_schema(schema):
    normalized_sections = []
    for section in schema["sections"]:
        normalized_fields = []
        for field in section["fields"]:
            normalized_fields.append(
                ordered_with_known_keys(
                    field,
                    (
                        "id",
                        "label",
                        "type",
                        "options",
                        "allowEmpty",
                        "requiredWarning",
                        "placeholder",
                        "helpText",
                        "displayOrder",
                        "unit",
                    ),
                )
            )
        normalized_sections.append(
            ordered_with_known_keys(
                {**section, "fields": normalized_fields},
                ("id", "label", "displayOrder", "helpText", "fields"),
            )
        )
    return ordered_with_known_keys(
        {**schema, "schemaFormat": SCHEMA_FORMAT_GENERIC_V1, "sections": normalized_sections},
        ("schemaFormat", "sections"),
    )


def validate_template_payload(payload, require_identity=True, require_change_summary=False):
    require_object(payload, "payload")
    result = {}
    if require_identity:
        result["id"] = validate_template_id(payload.get("id"))
        result["label"] = require_text(payload.get("label"), "label")
        result["full"] = require_text(payload.get("full"), "full")
        result["category"] = require_text(payload.get("category"), "category")

    result["schema"] = normalize_schema(payload.get("schema"))

    if require_change_summary:
        result["change_summary"] = require_text(payload.get("change_summary"), "change_summary")
    else:
        summary = payload.get("change_summary")
        if summary is not None and not isinstance(summary, str):
            raise SchemaValidationError("change_summary must be a string")
        result["change_summary"] = summary.strip() if isinstance(summary, str) else ""

    result["change_reason"] = require_text(payload.get("change_reason"), "change_reason")
    return result
