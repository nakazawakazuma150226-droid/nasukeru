(function(root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.NasukeruSimpleTemplateModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  var FIELD_TYPES = {
    text: "文字を入力",
    textarea: "長い文章を入力",
    select: "1つ選ぶ",
    multi_select: "複数選ぶ",
    number: "数字を入力",
  };

  var BLANK_POLICIES = {
    allow: "未入力でも問題なし",
    warn: "コピー前に確認する",
    block: "未入力ではコピーできない",
  };

  function randomId(prefix) {
    var random = Math.random().toString(16).slice(2, 10);
    return (prefix + "_" + random).slice(0, 32);
  }

  function clone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function normalizeOptions(options) {
    return (options || []).map(function(option) {
      if (typeof option === "string") return { value: option, label: option };
      return {
        value: option.value,
        label: option.label || option.value,
      };
    });
  }

  function effectiveBlankPolicy(field) {
    if (field.blankPolicy) return field.blankPolicy;
    if (field.requiredWarning) return "warn";
    return "allow";
  }

  function fieldToModel(field) {
    var model = clone(field);
    model.options = normalizeOptions(field.options);
    model.blankPolicy = effectiveBlankPolicy(field);
    return model;
  }

  function schemaToEditorModel(template) {
    var schema = clone(template.schema || { schemaFormat: "generic-v2", sections: [] });
    schema.schemaFormat = "generic-v2";
    return {
      id: template.id || randomId("tpl"),
      label: template.label || "",
      full: template.full || "",
      category: template.category || "neuro",
      schemaFormat: "generic-v2",
      copyMode: inferCopyMode(template.copy_format),
      sections: (schema.sections || []).map(function(section, sectionIndex) {
        return {
          id: section.id || randomId("sec"),
          label: section.label || "セクション",
          displayOrder: typeof section.displayOrder === "number" ? section.displayOrder : sectionIndex + 1,
          helpText: section.helpText || "",
          visibleIf: clone(section.visibleIf) || null,
          fields: (section.fields || []).map(fieldToModel),
          copyStyle: inferSectionCopyStyle(section, template.copy_format),
        };
      }),
      copyFormat: clone(template.copy_format) || null,
    };
  }

  function blankEditorModel() {
    return schemaToEditorModel({
      id: randomId("tpl"),
      label: "",
      full: "",
      category: "neuro",
      schema: {
        schemaFormat: "generic-v2",
        sections: [
          {
            id: randomId("sec"),
            label: "基本情報",
            displayOrder: 1,
            fields: [
              {
                id: randomId("fld"),
                label: "記載項目",
                type: "text",
                blankPolicy: "allow",
                displayOrder: 1,
              },
            ],
          },
        ],
      },
      copy_format: null,
    });
  }

  function inferCopyMode(copyFormat) {
    if (!copyFormat || !Array.isArray(copyFormat.lines)) return "auto";
    return "custom";
  }

  function inferSectionCopyStyle(section, copyFormat) {
    if (!copyFormat || !Array.isArray(copyFormat.lines)) return "stacked";
    var fieldRefs = (section.fields || []).map(function(field) { return section.id + "." + field.id; });
    var hasSegment = copyFormat.lines.some(function(line) {
      return line && Array.isArray(line.segments) && line.segments.some(function(segment) {
        return fieldRefs.indexOf(segment.ref) >= 0;
      });
    });
    return hasSegment ? "inline" : "stacked";
  }

  function editorModelToSchema(model) {
    return {
      schemaFormat: "generic-v2",
      sections: (model.sections || []).map(function(section, sectionIndex) {
        var nextSection = {
          id: section.id || randomId("sec"),
          label: section.label || "セクション",
          displayOrder: sectionIndex + 1,
          fields: (section.fields || []).map(function(field, fieldIndex) {
            var next = clone(field);
            next.id = next.id || randomId("fld");
            next.label = next.label || "項目";
            next.type = next.type || "text";
            next.displayOrder = fieldIndex + 1;
            delete next.includeInCopy;
            delete next.requiredWarning;
            if (next.blankPolicy === "allow") {
              next.blankPolicy = "allow";
            } else if (next.blankPolicy !== "warn" && next.blankPolicy !== "block") {
              delete next.blankPolicy;
            }
            if (next.type === "select" || next.type === "multi_select") {
              next.options = normalizeOptions(next.options).map(function(option) {
                return {
                  value: option.value || randomId("opt"),
                  label: option.label || option.value || "選択肢",
                };
              });
            } else {
              delete next.options;
            }
            if (next.type !== "number") {
              delete next.min;
              delete next.max;
              delete next.step;
              delete next.hardRange;
              delete next.warningRange;
            }
            return next;
          }),
        };
        if (section.helpText) nextSection.helpText = section.helpText;
        if (section.visibleIf) nextSection.visibleIf = clone(section.visibleIf);
        return nextSection;
      }),
    };
  }

  function unitSuffix(field) {
    return field.unit || "";
  }

  function editorModelToCopyFormat(model) {
    if (model.copyMode === "custom" && model.copyFormat) return clone(model.copyFormat);
    var lines = [model.full || model.label || "テンプレート", ""];
    (model.sections || []).forEach(function(section) {
      var included = (section.fields || []).filter(function(field) {
        return field.includeInCopy !== false;
      });
      if (!included.length) return;
      if (section.copyStyle === "inline") {
        lines.push({
          segments: included.map(function(field) {
            return {
              ref: section.id + "." + field.id,
              label: field.label + "：",
              suffix: unitSuffix(field),
            };
          }),
          separator: "、",
        });
      } else {
        lines.push({
          text: section.label,
          omitIfAllBlank: included.map(function(field) { return section.id + "." + field.id; }),
        });
        included.forEach(function(field) {
          lines.push({
            text: field.label + "：{{" + section.id + "." + field.id + "}}" + unitSuffix(field),
            omitIfAllBlank: [section.id + "." + field.id],
          });
        });
      }
      lines.push("");
    });
    while (lines.length && lines[lines.length - 1] === "") lines.pop();
    return {
      format: "text-v1",
      lines: lines,
    };
  }

  function addSection(model) {
    model.sections.push({
      id: randomId("sec"),
      label: "新しいセクション",
      displayOrder: model.sections.length + 1,
      visibleIf: null,
      copyStyle: "stacked",
      fields: [],
    });
  }

  function addField(section) {
    section.fields.push({
      id: randomId("fld"),
      label: "新しい項目",
      type: "text",
      blankPolicy: "allow",
      includeInCopy: true,
      displayOrder: section.fields.length + 1,
    });
  }

  return {
    BLANK_POLICIES: BLANK_POLICIES,
    FIELD_TYPES: FIELD_TYPES,
    addField: addField,
    addSection: addSection,
    blankEditorModel: blankEditorModel,
    clone: clone,
    editorModelToCopyFormat: editorModelToCopyFormat,
    editorModelToSchema: editorModelToSchema,
    effectiveBlankPolicy: effectiveBlankPolicy,
    randomId: randomId,
    schemaToEditorModel: schemaToEditorModel,
  };
});
