import re


TEMPLATE_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
SCHEMA_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
COPY_REF_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}\.[a-z0-9_-]{1,32}$")
COPY_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}")
SCHEMA_FORMAT_STROKE_V1 = "stroke-v1"
SCHEMA_FORMAT_GENERIC_V1 = "generic-v1"
SCHEMA_FORMAT_GENERIC_V2 = "generic-v2"
ALLOWED_SCHEMA_FORMATS = (SCHEMA_FORMAT_STROKE_V1, SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2)
ALLOWED_GENERIC_FIELD_TYPES = ("text", "textarea", "select", "multi_select", "number")
BLANK_POLICIES = ("allow", "warn", "block")
CONDITION_OPS = ("eq", "neq", "in", "not_in", "contains", "gt", "gte", "lt", "lte", "is_blank", "and", "or", "not")
CONDITION_MAX_DEPTH = 10
COPY_FORMAT_TEXT_V1 = "text-v1"
COPY_FORMAT_MULTI_V1 = "multi-v1"

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


def reject_unknown_keys(obj, allowed_keys, field):
    unknown = [key for key in obj if key not in allowed_keys]
    if unknown:
        raise SchemaValidationError(f"{field} has unknown keys: {', '.join(unknown)}")


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
    if key in obj and (isinstance(obj[key], bool) or not isinstance(obj[key], (int, float))):
        raise SchemaValidationError(f"{field}.{key} must be a number")


def validate_range(value, field):
    require_object(value, field)
    reject_unknown_keys(value, ("min", "max"), field)
    if "min" not in value and "max" not in value:
        raise SchemaValidationError(f"{field} requires min or max")
    require_optional_number(value, "min", field)
    require_optional_number(value, "max", field)
    if "min" in value and "max" in value and value["min"] > value["max"]:
        raise SchemaValidationError(f"{field}.min must be less than or equal to max")


def normalize_option(option, field):
    if isinstance(option, str):
        value = require_text(option, field)
        return {"value": value, "label": value}
    require_object(option, field)
    reject_unknown_keys(option, ("value", "label"), field)
    return {
        "value": require_text(option.get("value"), f"{field}.value"),
        "label": require_text(option.get("label"), f"{field}.label"),
    }


def validate_options(options, field):
    if not isinstance(options, list):
        raise SchemaValidationError(f"{field} must be an array")
    used_values = set()
    for index, option in enumerate(options):
        normalized = normalize_option(option, f"{field}[{index}]")
        value = normalized["value"]
        if value in used_values:
            raise SchemaValidationError(f"{field}[{index}].value is duplicated: {value}")
        used_values.add(value)


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
    if fmt in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        return validate_generic_v1_schema(schema)
    return validate_stroke_v1_schema(schema)


def validate_stroke_v1_schema(schema):
    require_object(schema, "schema")

    reject_unknown_keys(schema, ("schemaFormat", "vitals", "symptoms", "neuro", "rest"), "schema")
    require_keys(schema, ("vitals", "symptoms", "neuro", "rest"), "schema")
    vitals = require_object(schema["vitals"], "schema.vitals")
    symptoms = require_object(schema["symptoms"], "schema.symptoms")
    neuro = require_object(schema["neuro"], "schema.neuro")
    require_string(schema["rest"], "schema.rest")

    reject_unknown_keys(vitals, REQUIRED_VITAL_KEYS, "schema.vitals")
    reject_unknown_keys(symptoms, REQUIRED_SYMPTOM_KEYS, "schema.symptoms")
    reject_unknown_keys(neuro, REQUIRED_NEURO_KEYS, "schema.neuro")
    validate_string_map(vitals, REQUIRED_VITAL_KEYS, "schema.vitals")
    validate_string_map(symptoms, REQUIRED_SYMPTOM_KEYS, "schema.symptoms")
    require_keys(neuro, REQUIRED_NEURO_KEYS, "schema.neuro")

    for key in REQUIRED_NEURO_KEYS:
        if key == "mmt":
            continue
        require_string(neuro[key], f"schema.neuro.{key}")

    mmt = require_object(neuro["mmt"], "schema.neuro.mmt")
    reject_unknown_keys(mmt, REQUIRED_MMT_KEYS, "schema.neuro.mmt")
    validate_string_map(mmt, REQUIRED_MMT_KEYS, "schema.neuro.mmt")
    return schema


def validate_generic_field(field, section_field, used_ids):
    require_object(field, section_field)
    reject_unknown_keys(
        field,
        (
            "id",
            "label",
            "type",
            "options",
            "allowEmpty",
            "requiredWarning",
            "blankPolicy",
            "placeholder",
            "helpText",
            "displayOrder",
            "unit",
            "min",
            "max",
            "step",
            "hardRange",
            "warningRange",
            "visibleIf",
            "requiredIf",
        ),
        section_field,
    )
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
    if "blankPolicy" in field:
        blank_policy = require_text(field["blankPolicy"], f"{section_field}.blankPolicy")
        if blank_policy not in BLANK_POLICIES:
            raise SchemaValidationError(f"{section_field}.blankPolicy must be one of: {', '.join(BLANK_POLICIES)}")
    require_optional_number(field, "displayOrder", section_field)
    require_optional_number(field, "min", section_field)
    require_optional_number(field, "max", section_field)
    require_optional_number(field, "step", section_field)
    if "min" in field and "max" in field and field["min"] > field["max"]:
        raise SchemaValidationError(f"{section_field}.min must be less than or equal to max")
    if "step" in field and field["step"] <= 0:
        raise SchemaValidationError(f"{section_field}.step must be greater than 0")
    if "hardRange" in field:
        if field_type != "number":
            raise SchemaValidationError(f"{section_field}.hardRange requires number field")
        validate_range(field["hardRange"], f"{section_field}.hardRange")
    if "warningRange" in field:
        if field_type != "number":
            raise SchemaValidationError(f"{section_field}.warningRange requires number field")
        validate_range(field["warningRange"], f"{section_field}.warningRange")

    if field_type in ("select", "multi_select"):
        if "options" not in field:
            raise SchemaValidationError(f"{section_field}.options is required for {field_type}")
        options = field["options"]
        if not isinstance(options, list) or not options:
            raise SchemaValidationError(f"{section_field}.options must be a non-empty array")
        validate_options(options, f"{section_field}.options")
    elif "options" in field:
        raise SchemaValidationError(f"{section_field}.options requires select or multi_select field")


def option_value(option):
    return option if isinstance(option, str) else option.get("value")


def generic_field_refs(schema):
    refs = {}
    for section in schema["sections"]:
        section_id = section["id"]
        for field in section["fields"]:
            refs[f"{section_id}.{field['id']}"] = field
    return refs


def validate_condition(condition, field_refs, field, depth=0):
    if depth > CONDITION_MAX_DEPTH:
        raise SchemaValidationError(f"{field} exceeds maximum nesting depth")
    require_object(condition, field)
    op = require_text(condition.get("op"), f"{field}.op")
    if op not in CONDITION_OPS:
        raise SchemaValidationError(f"{field}.op must be one of: {', '.join(CONDITION_OPS)}")

    if op in ("and", "or"):
        reject_unknown_keys(condition, ("op", "conditions"), field)
        conditions = condition.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise SchemaValidationError(f"{field}.conditions must be a non-empty array")
        for index, child in enumerate(conditions):
            validate_condition(child, field_refs, f"{field}.conditions[{index}]", depth + 1)
        return

    if op == "not":
        reject_unknown_keys(condition, ("op", "condition"), field)
        validate_condition(condition.get("condition"), field_refs, f"{field}.condition", depth + 1)
        return

    allowed_keys = ("op", "field") if op == "is_blank" else ("op", "field", "value")
    reject_unknown_keys(condition, allowed_keys, field)
    ref = require_text(condition.get("field"), f"{field}.field")
    if not COPY_REF_PATTERN.fullmatch(ref):
        raise SchemaValidationError(f"{field}.field must match section.field")
    target = field_refs.get(ref)
    if target is None:
        raise SchemaValidationError(f"{field}.field references unknown schema field: {ref}")

    if op == "is_blank":
        return

    if "value" not in condition:
        raise SchemaValidationError(f"{field}.value is required")
    value = condition["value"]
    target_type = target.get("type")
    if target_type == "multi_select" and op != "contains":
        raise SchemaValidationError(f"{field}.field: multi_select only supports contains or is_blank conditions")
    if op in ("gt", "gte", "lt", "lte"):
        if target_type != "number":
            raise SchemaValidationError(f"{field}.field must reference a number field for {op}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaValidationError(f"{field}.value must be a number for {op}")
    elif op in ("in", "not_in"):
        if not isinstance(value, list) or not value:
            raise SchemaValidationError(f"{field}.value must be a non-empty array for {op}")
        if target_type == "number" and any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in value):
            raise SchemaValidationError(f"{field}.value must contain numbers for {op}")
        if target_type in ("select", "multi_select"):
            allowed_values = {option_value(option) for option in target.get("options", [])}
            unknown_values = [item for item in value if item not in allowed_values]
            if unknown_values:
                raise SchemaValidationError(f"{field}.value references unknown option value: {unknown_values[0]}")
    elif op == "contains":
        if target_type != "multi_select":
            raise SchemaValidationError(f"{field}.field must reference a multi_select field for contains")
        if isinstance(value, (dict, list)):
            raise SchemaValidationError(f"{field}.value must be a scalar for contains")
        allowed_values = {option_value(option) for option in target.get("options", [])}
        if value not in allowed_values:
            raise SchemaValidationError(f"{field}.value references unknown option value: {value}")
    elif target_type == "number" and op in ("eq", "neq"):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaValidationError(f"{field}.value must be a number for {op}")
    elif target_type == "select" and op in ("eq", "neq"):
        allowed_values = {option_value(option) for option in target.get("options", [])}
        if value not in allowed_values:
            raise SchemaValidationError(f"{field}.value references unknown option value: {value}")
    elif isinstance(value, (dict, list)):
        raise SchemaValidationError(f"{field}.value must be a scalar for {op}")


def detect_visible_condition_cycles(schema):
    refs = generic_field_refs(schema)
    graph = {ref: set() for ref in refs}
    for section in schema.get("sections", []):
        graph.setdefault(section["id"], set())

    for section in schema.get("sections", []):
        section_id = section["id"]
        for dependency in iter_condition_field_refs(section.get("visibleIf")):
            if dependency in graph:
                graph[section_id].add(dependency)
        for field in section.get("fields", []):
            ref = f"{section_id}.{field['id']}"
            # a field's effective visibility always depends on its parent section
            graph[ref].add(section_id)
            for dependency in iter_condition_field_refs(field.get("visibleIf")):
                if dependency in graph:
                    graph[ref].add(dependency)

    visiting = set()
    visited = set()

    def visit(ref, path):
        if ref in visiting:
            cycle = " -> ".join(path + [ref])
            raise SchemaValidationError(f"visibleIf condition cycle detected: {cycle}")
        if ref in visited:
            return
        visiting.add(ref)
        for dependency in graph.get(ref, set()):
            visit(dependency, path + [ref])
        visiting.remove(ref)
        visited.add(ref)

    for ref in graph:
        visit(ref, [])


def validate_generic_v1_schema(schema):
    require_object(schema, "schema")
    reject_unknown_keys(schema, ("schemaFormat", "sections"), "schema")
    require_keys(schema, ("schemaFormat", "sections"), "schema")
    fmt = schema["schemaFormat"]
    if fmt not in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        raise SchemaValidationError("schema.schemaFormat must be generic-v1 or generic-v2")

    sections = schema["sections"]
    if not isinstance(sections, list) or not sections:
        raise SchemaValidationError("schema.sections must be a non-empty array")

    used_section_ids = set()
    for section_index, section in enumerate(sections):
        section_field = f"schema.sections[{section_index}]"
        require_object(section, section_field)
        reject_unknown_keys(
            section,
            ("id", "label", "displayOrder", "helpText", "fields", "visibleIf"),
            section_field,
        )
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
    if fmt == SCHEMA_FORMAT_GENERIC_V1:
        for section_index, section in enumerate(sections):
            if "visibleIf" in section:
                raise SchemaValidationError(
                    f"schema.sections[{section_index}].visibleIf requires generic-v2"
                )
            for field_index, field in enumerate(section["fields"]):
                if "visibleIf" in field or "requiredIf" in field:
                    raise SchemaValidationError(
                        f"schema.sections[{section_index}].fields[{field_index}] condition keys require generic-v2"
                    )
        return schema
    refs = generic_field_refs(schema)
    for section_index, section in enumerate(sections):
        section_path = f"schema.sections[{section_index}]"
        if "visibleIf" in section:
            validate_condition(section["visibleIf"], refs, f"{section_path}.visibleIf")
        for field_index, field in enumerate(section["fields"]):
            field_path = f"{section_path}.fields[{field_index}]"
            if "visibleIf" in field:
                validate_condition(field["visibleIf"], refs, f"{field_path}.visibleIf")
            if "requiredIf" in field:
                validate_condition(field["requiredIf"], refs, f"{field_path}.requiredIf")
    detect_visible_condition_cycles(schema)
    return schema


def ordered_with_known_keys(obj, known_keys):
    ordered = {key: obj[key] for key in known_keys if key in obj}
    for key, value in obj.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def normalize_schema(schema):
    validate_template_schema(schema)
    if schema_format(schema) in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
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
            normalized_field = dict(field)
            if "options" in normalized_field:
                normalized_field["options"] = [
                    normalize_option(option, f"schema.sections[].fields[].options[{index}]")
                    for index, option in enumerate(normalized_field["options"])
                ]
            normalized_fields.append(
                ordered_with_known_keys(
                    normalized_field,
                    (
                        "id",
                        "label",
                        "type",
                        "options",
                        "allowEmpty",
                        "requiredWarning",
                        "blankPolicy",
                        "placeholder",
                        "helpText",
                        "displayOrder",
                        "unit",
                        "min",
                        "max",
                        "step",
                        "hardRange",
                        "warningRange",
                        "visibleIf",
                        "requiredIf",
                    ),
                )
            )
        normalized_sections.append(
            ordered_with_known_keys(
                {**section, "fields": normalized_fields},
                ("id", "label", "displayOrder", "helpText", "fields", "visibleIf"),
            )
        )
    return ordered_with_known_keys(
        {**schema, "sections": normalized_sections},
        ("schemaFormat", "sections"),
    )


def iter_stroke_v1_values(schema):
    for key in REQUIRED_VITAL_KEYS:
        yield f"schema.vitals.{key}", schema["vitals"][key]
    for key in REQUIRED_SYMPTOM_KEYS:
        yield f"schema.symptoms.{key}", schema["symptoms"][key]
    neuro = schema["neuro"]
    for key in REQUIRED_NEURO_KEYS:
        if key == "mmt":
            continue
        yield f"schema.neuro.{key}", neuro[key]
    for key in REQUIRED_MMT_KEYS:
        yield f"schema.neuro.mmt.{key}", neuro["mmt"][key]
    yield "schema.rest", schema["rest"]


def enforce_empty_initial_values(schema):
    if schema_format(schema) != SCHEMA_FORMAT_STROKE_V1:
        return
    non_empty_fields = [
        field
        for field, value in iter_stroke_v1_values(schema)
        if isinstance(value, str) and value.strip()
    ]
    if non_empty_fields:
        preview = ", ".join(non_empty_fields[:5])
        if len(non_empty_fields) > 5:
            preview += ", ..."
        raise SchemaValidationError(
            f"stroke-v1 initial values must be empty: {preview}"
        )


def validate_copy_format(copy_format):
    if copy_format is None:
        return None
    require_object(copy_format, "copy_format")
    require_keys(copy_format, ("format",), "copy_format")
    fmt = require_text(copy_format["format"], "copy_format.format")
    if fmt == COPY_FORMAT_TEXT_V1:
        reject_unknown_keys(copy_format, ("format", "lines"), "copy_format")
        require_keys(copy_format, ("format", "lines"), "copy_format")
        validate_copy_lines(copy_format["lines"], "copy_format.lines")
        return copy_format
    if fmt == COPY_FORMAT_MULTI_V1:
        reject_unknown_keys(copy_format, ("format", "variants"), "copy_format")
        require_keys(copy_format, ("format", "variants"), "copy_format")
        variants = copy_format["variants"]
        if not isinstance(variants, list) or not variants:
            raise SchemaValidationError("copy_format.variants must be a non-empty array")
        seen = set()
        for index, variant in enumerate(variants):
            field = f"copy_format.variants[{index}]"
            require_object(variant, field)
            reject_unknown_keys(variant, ("id", "label", "lines"), field)
            require_keys(variant, ("id", "label", "lines"), field)
            variant_id = require_text(variant["id"], f"{field}.id")
            if not SCHEMA_ID_PATTERN.fullmatch(variant_id):
                raise SchemaValidationError(f"{field}.id must match ^[a-z0-9_-]{{1,32}}$")
            if variant_id in seen:
                raise SchemaValidationError(f"{field}.id must be unique")
            seen.add(variant_id)
            require_text(variant["label"], f"{field}.label")
            validate_copy_lines(variant["lines"], f"{field}.lines")
        return copy_format
    raise SchemaValidationError("copy_format.format must be text-v1 or multi-v1")


def validate_copy_lines(lines, field):
    if not isinstance(lines, list):
        raise SchemaValidationError(f"{field} must be an array")
    for index, line in enumerate(lines):
        validate_copy_line(line, f"{field}[{index}]")


def validate_copy_line(line, field):
    if isinstance(line, str):
        return
    require_object(line, field)
    reject_unknown_keys(line, ("text", "segments", "prefix", "separator", "splitLinesFrom", "omitIfAllBlank", "showIf"), field)
    if "segments" in line:
        validate_copy_line_segments(line["segments"], f"{field}.segments")
        require_optional_string(line, "prefix", field)
        require_optional_string(line, "separator", field)
    else:
        require_keys(line, ("text",), field)
    if "text" in line:
        require_string(line["text"], f"{field}.text")
    if "showIf" in line:
        require_object(line["showIf"], f"{field}.showIf")
    if "splitLinesFrom" in line:
        ref = line["splitLinesFrom"]
        if not isinstance(ref, str) or not COPY_REF_PATTERN.fullmatch(ref):
            raise SchemaValidationError(f"{field}.splitLinesFrom must match section.field")
    if "omitIfAllBlank" in line:
        refs = line["omitIfAllBlank"]
        if not isinstance(refs, list) or not refs:
            raise SchemaValidationError(f"{field}.omitIfAllBlank must be a non-empty array")
        for index, ref in enumerate(refs):
            if not isinstance(ref, str) or not COPY_REF_PATTERN.fullmatch(ref):
                raise SchemaValidationError(
                    f"{field}.omitIfAllBlank[{index}] must match section.field"
                )


def validate_copy_line_segments(segments, field):
    if not isinstance(segments, list) or not segments:
        raise SchemaValidationError(f"{field} must be a non-empty array")
    for index, segment in enumerate(segments):
        segment_field = f"{field}[{index}]"
        require_object(segment, segment_field)
        reject_unknown_keys(segment, ("ref", "label", "suffix", "replaceItems"), segment_field)
        ref = require_text(segment.get("ref"), f"{segment_field}.ref")
        if not COPY_REF_PATTERN.fullmatch(ref):
            raise SchemaValidationError(f"{segment_field}.ref must match section.field")
        require_optional_string(segment, "label", segment_field)
        require_optional_string(segment, "suffix", segment_field)
        if "replaceItems" in segment:
            replacements = segment["replaceItems"]
            if not isinstance(replacements, list) or not replacements:
                raise SchemaValidationError(f"{segment_field}.replaceItems must be a non-empty array")
            seen_values = set()
            for replacement_index, replacement in enumerate(replacements):
                replacement_field = f"{segment_field}.replaceItems[{replacement_index}]"
                require_object(replacement, replacement_field)
                reject_unknown_keys(replacement, ("value", "ref"), replacement_field)
                replacement_value = require_text(replacement.get("value"), f"{replacement_field}.value")
                if replacement_value in seen_values:
                    raise SchemaValidationError(f"{replacement_field}.value is duplicated: {replacement_value}")
                seen_values.add(replacement_value)
                replacement_ref = require_text(replacement.get("ref"), f"{replacement_field}.ref")
                if not COPY_REF_PATTERN.fullmatch(replacement_ref):
                    raise SchemaValidationError(f"{replacement_field}.ref must match section.field")


def normalize_copy_format(copy_format):
    validate_copy_format(copy_format)
    if copy_format is None:
        return None
    if copy_format["format"] == COPY_FORMAT_MULTI_V1:
        variants = []
        for variant in copy_format["variants"]:
            variants.append(
                ordered_with_known_keys(
                    {
                        **variant,
                        "lines": normalize_copy_lines(variant["lines"]),
                    },
                    ("id", "label", "lines"),
                )
            )
        return ordered_with_known_keys({**copy_format, "variants": variants}, ("format", "variants"))
    normalized_lines = normalize_copy_lines(copy_format["lines"])
    return ordered_with_known_keys({**copy_format, "lines": normalized_lines}, ("format", "lines"))


def normalize_copy_lines(lines):
    normalized_lines = []
    for line in lines:
        if isinstance(line, str):
            normalized_lines.append(line)
        else:
            normalized_line = dict(line)
            if "segments" in normalized_line:
                normalized_line["segments"] = [
                    ordered_with_known_keys(
                        {
                            **segment,
                            **(
                                {
                                    "replaceItems": [
                                        ordered_with_known_keys(replacement, ("value", "ref"))
                                        for replacement in segment.get("replaceItems", [])
                                    ]
                                }
                                if "replaceItems" in segment
                                else {}
                            ),
                        },
                        ("ref", "label", "suffix", "replaceItems"),
                    )
                    for segment in normalized_line["segments"]
                ]
            normalized_lines.append(
                ordered_with_known_keys(
                    normalized_line,
                    ("text", "segments", "prefix", "separator", "splitLinesFrom", "omitIfAllBlank", "showIf"),
                )
            )
    return normalized_lines


def iter_copy_format_variants(copy_format):
    if not copy_format:
        return
    if copy_format.get("format") == COPY_FORMAT_MULTI_V1:
        for variant in copy_format.get("variants", []):
            yield variant.get("id"), variant.get("label"), variant.get("lines", [])
        return
    yield "default", "標準", copy_format.get("lines", [])


def collect_generic_field_refs(schema):
    if schema_format(schema) not in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        return set()
    refs = set()
    for section in schema["sections"]:
        section_id = section["id"]
        for field in section["fields"]:
            refs.add(f"{section_id}.{field['id']}")
    return refs


def iter_copy_line_refs(line):
    yield from iter_copy_line_output_refs(line)
    yield from iter_copy_line_control_refs(line)


def iter_copy_line_output_refs(line):
    text = line if isinstance(line, str) else line.get("text", "")
    for match in COPY_PLACEHOLDER_PATTERN.finditer(text):
        yield f"{match.group(1)}.{match.group(2)}"
    if isinstance(line, dict):
        for segment in line.get("segments", []):
            yield segment["ref"]
            for replacement in segment.get("replaceItems", []):
                yield replacement["ref"]
        split_ref = line.get("splitLinesFrom")
        if split_ref:
            yield split_ref


def iter_condition_field_refs(condition):
    if not isinstance(condition, dict):
        return
    op = condition.get("op")
    if op in ("and", "or"):
        for child in condition.get("conditions", []):
            yield from iter_condition_field_refs(child)
        return
    if op == "not":
        yield from iter_condition_field_refs(condition.get("condition"))
        return
    ref = condition.get("field")
    if isinstance(ref, str):
        yield ref


def iter_copy_line_control_refs(line):
    if isinstance(line, dict):
        for ref in line.get("omitIfAllBlank", []):
            yield ref
        yield from iter_condition_field_refs(line.get("showIf"))


def collect_unreferenced_fields(schema, copy_format):
    if copy_format is None or schema_format(schema) not in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        return []
    output_refs = set()
    variant_output_refs = {}
    for variant_id, variant_label, lines in iter_copy_format_variants(copy_format):
        refs = set()
        for line in lines:
            refs.update(iter_copy_line_output_refs(line))
        variant_output_refs[variant_id] = (variant_label, refs)
        output_refs.update(refs)
    warnings = []
    fields = []
    for section in schema["sections"]:
        section_label = section.get("label") or section.get("id")
        section_conditional = bool(section.get("visibleIf"))
        for field in section["fields"]:
            ref = f"{section['id']}.{field['id']}"
            field_label = field.get("label") or field.get("id")
            suffix = "（条件付き表示）" if field.get("visibleIf") or section_conditional else ""
            label = f"{section_label} > {field_label}{suffix}"
            fields.append((ref, label))
            if ref in output_refs:
                continue
            warnings.append(
                {
                    "code": "unreferenced_field",
                    "fieldRef": ref,
                    "label": label,
                    "message": f"入力項目『{label}』はコピー出力に含まれていません",
                }
            )
    if copy_format.get("format") == COPY_FORMAT_MULTI_V1:
        for variant_id, (variant_label, refs) in variant_output_refs.items():
            for ref, label in fields:
                if ref not in output_refs or ref in refs:
                    continue
                warnings.append(
                    {
                        "code": "variant_unreferenced_field",
                        "fieldRef": ref,
                        "label": label,
                        "variantId": variant_id,
                        "variantLabel": variant_label,
                        "message": f"入力項目『{label}』は出力形式『{variant_label}』に含まれていません",
                    }
                )
    return warnings


def iter_condition_eq_in_pairs(condition):
    if not isinstance(condition, dict):
        return
    op = condition.get("op")
    if op in ("and", "or"):
        for child in condition.get("conditions", []):
            yield from iter_condition_eq_in_pairs(child)
        return
    if op == "not":
        # A negated condition has the opposite meaning of its inner condition,
        # so its (field, value) pair must not be treated as equal/duplicate.
        return
    ref = condition.get("field")
    if not isinstance(ref, str):
        return
    if op == "eq":
        yield (ref, condition.get("value"))
    elif op == "in" and isinstance(condition.get("value"), list):
        for value in condition["value"]:
            yield (ref, value)


def collect_duplicate_section_conditions(schema):
    if schema_format(schema) != SCHEMA_FORMAT_GENERIC_V2:
        return []
    sections_by_pair = {}
    for section in schema.get("sections", []):
        condition = section.get("visibleIf")
        if not condition:
            continue
        section_label = section.get("label") or section.get("id")
        for pair in set(iter_condition_eq_in_pairs(condition)):
            sections_by_pair.setdefault(pair, []).append(section_label)
    warnings = []
    for (field_ref, value), labels in sections_by_pair.items():
        if len(labels) < 2:
            continue
        warnings.append(
            {
                "code": "duplicate_section_condition",
                "fieldRef": field_ref,
                "value": value,
                "sections": labels,
                "message": (
                    f"セクション「{'」「'.join(labels)}」が同じ条件（{field_ref} = {value}）"
                    "で表示されます。コピー&ペースト間違いの可能性があります"
                ),
            }
        )
    return warnings


def validate_copy_format_references(schema, copy_format):
    if copy_format is None or schema_format(schema) not in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        return
    allowed_refs = collect_generic_field_refs(schema)
    field_refs = generic_field_refs(schema)
    unknown_refs = []
    for variant_id, _variant_label, lines in iter_copy_format_variants(copy_format):
        location = "copy_format.lines[]" if copy_format.get("format") == COPY_FORMAT_TEXT_V1 else f"copy_format.variants[{variant_id}].lines[]"
        for line in lines:
            if isinstance(line, dict) and "showIf" in line:
                if schema_format(schema) != SCHEMA_FORMAT_GENERIC_V2:
                    raise SchemaValidationError(f"{location}.showIf requires generic-v2")
                validate_condition(line["showIf"], field_refs, f"{location}.showIf")
            if isinstance(line, dict):
                for segment_index, segment in enumerate(line.get("segments", [])):
                    if "replaceItems" not in segment:
                        continue
                    source = field_refs.get(segment["ref"])
                    if source is None:
                        continue
                    if source.get("type") != "multi_select":
                        raise SchemaValidationError(
                            f"{location}.segments[{segment_index}].replaceItems requires a multi_select source field"
                        )
                    allowed_values = {option_value(option) for option in source.get("options", [])}
                    for replacement_index, replacement in enumerate(segment["replaceItems"]):
                        if replacement["value"] not in allowed_values:
                            raise SchemaValidationError(
                                f"{location}.segments[{segment_index}].replaceItems[{replacement_index}].value "
                                f"references unknown option value: {replacement['value']}"
                            )
            for ref in iter_copy_line_refs(line):
                if ref not in allowed_refs:
                    unknown_refs.append(ref)
    if unknown_refs:
        unique_refs = []
        for ref in unknown_refs:
            if ref not in unique_refs:
                unique_refs.append(ref)
        raise SchemaValidationError(
            f"copy_format references unknown schema fields: {', '.join(unique_refs)}"
        )


def blank_policy(field):
    if field.get("blankPolicy"):
        return field["blankPolicy"]
    if field.get("requiredWarning"):
        return "warn"
    return "allow"


def policy_rank(policy):
    return {"allow": 0, "warn": 1, "block": 2}.get(policy or "allow", 0)


def range_relaxed(before_range, after_range):
    if before_range and not after_range:
        return True
    if not before_range:
        return False
    before_min = before_range.get("min")
    before_max = before_range.get("max")
    after_min = after_range.get("min") if after_range else None
    after_max = after_range.get("max") if after_range else None
    if before_min is not None and (after_min is None or after_min < before_min):
        return True
    if before_max is not None and (after_max is None or after_max > before_max):
        return True
    return False


def collect_generic_fields(schema):
    if not schema or schema_format(schema) not in (SCHEMA_FORMAT_GENERIC_V1, SCHEMA_FORMAT_GENERIC_V2):
        return {}
    fields = {}
    for section in schema.get("sections", []):
        for field in section.get("fields", []):
            fields[f"{section.get('id')}.{field.get('id')}"] = field
    return fields


def normalized_copy_lines(copy_format):
    if not copy_format:
        return []
    return [repr(line) for line in copy_format.get("lines", [])]


def normalized_copy_line_groups(copy_format):
    if not copy_format:
        return {}
    return {
        variant_id: [repr(line) for line in lines]
        for variant_id, _variant_label, lines in iter_copy_format_variants(copy_format)
    }


def detect_high_risk_changes(before_schema, after_schema, before_copy_format=None, after_copy_format=None):
    changes = []
    before_fields = collect_generic_fields(before_schema)
    after_fields = collect_generic_fields(after_schema)
    for ref, before_field in before_fields.items():
        after_field = after_fields.get(ref)
        label = before_field.get("label") or ref
        if after_field is None:
            changes.append({"code": "field_deleted", "fieldRef": ref, "message": f"{label}が削除されました"})
            continue
        before_policy = blank_policy(before_field)
        after_policy = blank_policy(after_field)
        if policy_rank(before_policy) > policy_rank(after_policy):
            changes.append(
                {
                    "code": "blank_policy_relaxed",
                    "fieldRef": ref,
                    "message": f"{label}のblankPolicyが {before_policy} → {after_policy} に緩和されました",
                }
            )
        if before_field.get("requiredIf") and not after_field.get("requiredIf"):
            changes.append({"code": "required_if_deleted", "fieldRef": ref, "message": f"{label}のrequiredIfが削除されました"})
        if before_field.get("visibleIf") != after_field.get("visibleIf"):
            changes.append({"code": "condition_changed", "fieldRef": ref, "message": f"{label}のvisibleIfが変更されました"})
        if before_field.get("requiredIf") != after_field.get("requiredIf") and after_field.get("requiredIf"):
            changes.append({"code": "condition_changed", "fieldRef": ref, "message": f"{label}のrequiredIfが変更されました"})
        if range_relaxed(before_field.get("hardRange"), after_field.get("hardRange")):
            changes.append({"code": "hard_range_relaxed", "fieldRef": ref, "message": f"{label}のhardRangeが緩和されました"})

    before_groups = normalized_copy_line_groups(before_copy_format)
    after_groups = normalized_copy_line_groups(after_copy_format)
    after_default_lines = next(iter(after_groups.values()), [])
    for variant_id, before_lines in before_groups.items():
        after_lines = after_groups.get(variant_id)
        if after_lines is None and variant_id == "default":
            after_lines = after_default_lines
        if after_lines is None:
            changes.append({"code": "copy_variant_deleted", "fieldRef": "", "message": f"copy_formatの出力形式 {variant_id} が削除されました"})
            continue
        if len(after_lines) < len(before_lines) or any(line not in after_lines for line in before_lines):
            changes.append({"code": "copy_line_deleted", "fieldRef": "", "message": f"copy_formatの行が削除または変更されました（{variant_id}）"})
    return changes


def validate_template_payload(
    payload,
    require_identity=True,
    require_change_summary=False,
    enforce_empty_defaults=True,
):
    require_object(payload, "payload")
    result = {}
    if require_identity:
        result["id"] = validate_template_id(payload.get("id"))
        result["label"] = require_text(payload.get("label"), "label")
        result["full"] = require_text(payload.get("full"), "full")
        result["category"] = require_text(payload.get("category"), "category")

    result["schema"] = normalize_schema(payload.get("schema"))
    if enforce_empty_defaults:
        enforce_empty_initial_values(result["schema"])
    result["copy_format"] = normalize_copy_format(payload.get("copy_format"))
    validate_copy_format_references(result["schema"], result["copy_format"])

    if require_change_summary:
        result["change_summary"] = require_text(payload.get("change_summary"), "change_summary")
    else:
        summary = payload.get("change_summary")
        if summary is not None and not isinstance(summary, str):
            raise SchemaValidationError("change_summary must be a string")
        result["change_summary"] = summary.strip() if isinstance(summary, str) else ""

    result["change_reason"] = require_text(payload.get("change_reason"), "change_reason")
    return result
