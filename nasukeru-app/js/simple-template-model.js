(function(root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.NasukeruSimpleTemplateModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  var PLACEHOLDER_RE = /\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}/g;

  function clone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function sortedByDisplayOrder(items) {
    return (items || []).slice().sort(function(a, b) {
      var ao = typeof a.displayOrder === "number" ? a.displayOrder : 9999;
      var bo = typeof b.displayOrder === "number" ? b.displayOrder : 9999;
      return ao - bo;
    });
  }

  function effectiveBlankPolicy(field) {
    field = field || {};
    if (field.blankPolicy) return field.blankPolicy;
    if (field.requiredWarning) return "warn";
    return "allow";
  }

  function generateId(prefix, usedIds, randomFn) {
    usedIds = usedIds || {};
    randomFn = randomFn || Math.random;
    for (var attempt = 0; attempt < 1000; attempt += 1) {
      var token = Math.floor(randomFn() * 0xffffffff).toString(16).padStart(8, "0");
      var id = String(prefix || "id") + "_" + token;
      if (!usedIds[id]) {
        usedIds[id] = true;
        return id;
      }
    }
    throw new Error("内部IDを生成できませんでした");
  }

  function createBlankSchema(randomFn) {
    var used = {};
    var sectionId = generateId("sec", used, randomFn);
    var fieldId = generateId("fld", used, randomFn);
    return {
      schemaFormat: "generic-v2",
      sections: [{
        id: sectionId,
        label: "基本情報",
        displayOrder: 1,
        fields: [{
          id: fieldId,
          label: "記載項目",
          type: "text",
          blankPolicy: "allow",
          displayOrder: 1,
        }],
      }],
    };
  }

  function upgradeSchema(schema) {
    var next = clone(schema || createBlankSchema());
    next.schemaFormat = "generic-v2";
    next.sections = sortedByDisplayOrder(next.sections).map(function(section, sectionIndex) {
      section.displayOrder = sectionIndex + 1;
      section.fields = sortedByDisplayOrder(section.fields).map(function(field, fieldIndex) {
        field.displayOrder = fieldIndex + 1;
        return field;
      });
      return section;
    });
    return next;
  }

  function fieldRef(section, field) {
    return section.id + "." + field.id;
  }

  function collectOutputRefs(copyFormat) {
    var refs = {};
    ((copyFormat && copyFormat.lines) || []).forEach(function(line) {
      var lineObj = typeof line === "string" ? { text: line } : (line || {});
      String(lineObj.text || "").replace(PLACEHOLDER_RE, function(match, sectionId, fieldId) {
        refs[sectionId + "." + fieldId] = true;
        return match;
      });
      (lineObj.segments || []).forEach(function(segment) {
        if (segment && segment.ref) refs[segment.ref] = true;
      });
      if (lineObj.splitLinesFrom) refs[lineObj.splitLinesFrom] = true;
    });
    return refs;
  }

  function automaticCopyFormat(schema, options) {
    options = options || {};
    var title = String(options.title || "").trim();
    var includedRefs = options.includedRefs || null;
    var sectionStyles = options.sectionStyles || {};
    var lines = [];
    if (title) {
      lines.push(title);
      lines.push("");
    }
    sortedByDisplayOrder((schema || {}).sections).forEach(function(section) {
      var fields = sortedByDisplayOrder(section.fields).filter(function(field) {
        var ref = fieldRef(section, field);
        return !includedRefs || includedRefs[ref] !== false;
      });
      if (!fields.length) return;
      var refs = fields.map(function(field) { return fieldRef(section, field); });
      lines.push({ text: section.label, omitIfAllBlank: refs });
      if (sectionStyles[section.id] === "inline") {
        lines.push({
          segments: fields.map(function(field) {
            var segment = { ref: fieldRef(section, field), label: field.label + "：" };
            if (field.unit) segment.suffix = field.unit;
            return segment;
          }),
          separator: "、",
        });
      } else {
        fields.forEach(function(field) {
          var ref = fieldRef(section, field);
          lines.push({
            text: field.label + "：{{" + ref + "}}" + (field.unit || ""),
            omitIfAllBlank: [ref],
          });
        });
      }
      lines.push("");
    });
    while (lines.length && lines[lines.length - 1] === "") lines.pop();
    return { format: "text-v1", lines: lines };
  }

  function isSimpleCondition(condition) {
    if (!condition) return true;
    return ["eq", "neq", "contains", "gt", "gte", "lt", "lte", "is_blank"].indexOf(condition.op) >= 0
      && typeof condition.field === "string";
  }

  function conditionLabel(condition, fieldLabels, optionLabels) {
    if (!condition) return "条件なし";
    if (!isSimpleCondition(condition)) return "複雑な条件（詳細編集で確認）";
    var field = fieldLabels && fieldLabels[condition.field] ? fieldLabels[condition.field] : condition.field;
    var opLabels = {
      eq: "が", neq: "が次と異なる", contains: "に含まれる", gt: "が次より大きい",
      gte: "が次以上", lt: "が次より小さい", lte: "が次以下", is_blank: "が空欄",
    };
    if (condition.op === "is_blank") return field + opLabels.is_blank;
    var key = condition.field + "::" + String(condition.value);
    var value = optionLabels && optionLabels[key] ? optionLabels[key] : String(condition.value);
    return field + " " + (opLabels[condition.op] || condition.op) + "「" + value + "」";
  }

  function templateId(existingIds, randomFn) {
    var used = {};
    (existingIds || []).forEach(function(id) { used[id] = true; });
    return generateId("tpl", used, randomFn);
  }

  return {
    automaticCopyFormat: automaticCopyFormat,
    clone: clone,
    collectOutputRefs: collectOutputRefs,
    conditionLabel: conditionLabel,
    createBlankSchema: createBlankSchema,
    effectiveBlankPolicy: effectiveBlankPolicy,
    fieldRef: fieldRef,
    generateId: generateId,
    isSimpleCondition: isSimpleCondition,
    sortedByDisplayOrder: sortedByDisplayOrder,
    templateId: templateId,
    upgradeSchema: upgradeSchema,
  };
});
