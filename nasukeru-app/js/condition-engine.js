(function(root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./blank.js"));
    return;
  }
  var api = factory(root.NasukeruBlank);
  root.NasukeruConditionEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function(blank) {
  function compareNumbers(left, right, op) {
    var a = Number(left);
    var b = Number(right);
    if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
    if (op === "gt") return a > b;
    if (op === "gte") return a >= b;
    if (op === "lt") return a < b;
    if (op === "lte") return a <= b;
    return false;
  }

  function evaluateCondition(condition, values) {
    if (!condition || typeof condition !== "object") return true;
    var op = condition.op;
    if (op === "and") {
      return Array.isArray(condition.conditions) && condition.conditions.every(function(child) {
        return evaluateCondition(child, values);
      });
    }
    if (op === "or") {
      return Array.isArray(condition.conditions) && condition.conditions.some(function(child) {
        return evaluateCondition(child, values);
      });
    }
    if (op === "not") {
      return !evaluateCondition(condition.condition, values);
    }

    var actual = values ? values[condition.field] : undefined;
    var expected = condition.value;
    if (op === "is_blank") return blank.isBlank(actual);
    if (op === "eq") return actual === expected;
    if (op === "neq") return actual !== expected;
    if (op === "in") return Array.isArray(expected) && expected.indexOf(actual) >= 0;
    if (op === "not_in") return Array.isArray(expected) && expected.indexOf(actual) < 0;
    if (op === "contains") {
      if (Array.isArray(actual)) return actual.indexOf(expected) >= 0;
      return String(actual || "").indexOf(String(expected)) >= 0;
    }
    if (op === "gt" || op === "gte" || op === "lt" || op === "lte") {
      return compareNumbers(actual, expected, op);
    }
    return false;
  }

  return {
    evaluateCondition: evaluateCondition,
    isBlank: blank.isBlank,
  };
});
