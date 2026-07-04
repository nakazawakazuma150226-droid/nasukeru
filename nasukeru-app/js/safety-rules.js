(function(root, factory) {
  var api = factory(root.NasukeruConditionEngine);
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./condition-engine.js"));
  }
  root.NasukeruSafetyRules = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function(conditionEngine) {
  function isBlank(value) {
    if (Array.isArray(value)) return value.length === 0;
    if (value === null || value === undefined) return true;
    if (typeof value === "number") return false;
    return !String(value).trim();
  }

  function blankPolicyFor(field, values) {
    if (field.blankPolicy) return field.blankPolicy;
    if (field.requiredWarning) return "warn";
    if (field.requiredIf && conditionEngine.evaluateCondition(field.requiredIf, values)) return "warn";
    return "allow";
  }

  function isOutsideRange(value, range) {
    if (!range || isBlank(value)) return false;
    var numeric = Number(value);
    if (!Number.isFinite(numeric)) return false;
    if (typeof range.min === "number" && numeric < range.min) return true;
    if (typeof range.max === "number" && numeric > range.max) return true;
    return false;
  }

  function issue(field, code, severity, message) {
    return {
      fieldRef: field.ref,
      code: code,
      severity: severity,
      message: message,
    };
  }

  function validateField(field, values) {
    var result = { blocks: [], warnings: [] };
    if (field.visible === false) return result;
    var value = field.value;
    var label = field.label || field.ref || "入力項目";
    var policy = blankPolicyFor(field, values);
    if (isBlank(value)) {
      if (policy === "block") {
        result.blocks.push(issue(field, "required_blank", "block", label + "が未入力です"));
      } else if (policy === "warn") {
        result.warnings.push(issue(field, "required_blank", "warn", label + "が未入力です"));
      }
      return result;
    }

    if (field.type === "number" && isOutsideRange(value, field.hardRange)) {
      result.blocks.push(issue(field, "hard_range", "block", label + "が入力可能範囲外です"));
    }
    if (field.type === "number" && isOutsideRange(value, field.warningRange)) {
      result.warnings.push(issue(field, "warning_range", "warn", label + "が確認範囲外です"));
    }
    return result;
  }

  function validateFields(fields, values) {
    return (fields || []).reduce(function(result, field) {
      var next = validateField(field, values || {});
      result.blocks = result.blocks.concat(next.blocks);
      result.warnings = result.warnings.concat(next.warnings);
      return result;
    }, { blocks: [], warnings: [] });
  }

  function hasIssues(result) {
    return Boolean(result && ((result.blocks && result.blocks.length) || (result.warnings && result.warnings.length)));
  }

  return {
    hasIssues: hasIssues,
    isBlank: isBlank,
    validateField: validateField,
    validateFields: validateFields,
  };
});
