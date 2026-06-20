import re


TEMPLATE_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")

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


def validate_string_map(obj, keys, field):
    require_keys(obj, keys, field)
    for key in keys:
        require_string(obj[key], f"{field}.{key}")


def validate_template_schema(schema):
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


def ordered_with_known_keys(obj, known_keys):
    ordered = {key: obj[key] for key in known_keys if key in obj}
    for key, value in obj.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def normalize_schema(schema):
    validate_template_schema(schema)
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
