(function(root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.NasukeruGenericValues = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  function splitMultiValue(raw) {
    if (Array.isArray(raw)) return raw;
    return String(raw || "").split("、").filter(function(value) {
      return value;
    });
  }

  function joinMultiValue(value) {
    return splitMultiValue(value).join("、");
  }

  function parseInputValue(input) {
    var fieldType = input.dataset.fieldType || "text";
    var raw = input.value || "";
    if (fieldType === "multi_select") {
      return splitMultiValue(raw);
    }
    if (fieldType === "number") {
      raw = normalizeNumberInput(raw);
      if (!raw.trim()) return null;
      var parsed = Number(raw);
      return Number.isFinite(parsed) ? parsed : raw;
    }
    return raw;
  }

  function normalizeNumberInput(value) {
    return String(value || "")
      .replace(/[０-９]/g, function(ch) {
        return String.fromCharCode(ch.charCodeAt(0) - 0xfee0);
      })
      .replace(/[．]/g, ".")
      .replace(/[－ー−]/g, "-")
      .replace(/　/g, " ")
      .trim();
  }

  function normalizeNumberField(input) {
    if (!input || input.dataset.fieldType !== "number") return;
    var normalized = normalizeNumberInput(input.value);
    if (input.value !== normalized) input.value = normalized;
  }

  function isBlankValue(value) {
    if (Array.isArray(value)) return value.length === 0;
    if (value === null || value === undefined) return true;
    if (typeof value === "number") return false;
    return !String(value).trim();
  }

  function optionLabel(input, value) {
    var labels = input.genericOptionLabels || {};
    return labels[value] || value;
  }

  function formatInputValueForCopy(input, value) {
    if (isBlankValue(value)) return "";
    if (input.dataset.fieldType === "multi_select") {
      return splitMultiValue(value).map(function(item) {
        return optionLabel(input, item);
      }).join("、");
    }
    if (input.dataset.fieldType === "select") {
      return optionLabel(input, value);
    }
    return String(value);
  }

  function applyInputValue(input, value) {
    if (input.dataset.fieldType === "multi_select") {
      var selected = splitMultiValue(value);
      input.value = selected.join("、");
      var row = input.closest ? input.closest(".nrow") : null;
      if (row) {
        row.querySelectorAll(".generic-multi-option input[type='checkbox']").forEach(function(checkbox) {
          checkbox.checked = selected.indexOf(checkbox.value) >= 0;
        });
      }
      return;
    }
    if (input.dataset.fieldType === "number") {
      input.value = value === null || value === undefined ? "" : String(value);
      return;
    }
    input.value = value === null || value === undefined ? "" : String(value);
  }

  function fieldRef(input) {
    return input.dataset.sectionId + "." + input.dataset.fieldId;
  }

  function collectTypedValues(container) {
    var values = {};
    if (!container) return values;
    container.querySelectorAll(".generic-input").forEach(function(input) {
      values[fieldRef(input)] = parseInputValue(input);
    });
    return values;
  }

  return {
    applyInputValue: applyInputValue,
    collectTypedValues: collectTypedValues,
    fieldRef: fieldRef,
    formatInputValueForCopy: formatInputValueForCopy,
    isBlankValue: isBlankValue,
    parseInputValue: parseInputValue,
    normalizeNumberField: normalizeNumberField,
    normalizeNumberInput: normalizeNumberInput,
    splitMultiValue: splitMultiValue,
  };
});
