(function(root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./blank.js"));
    return;
  }
  var api = factory(root.NasukeruBlank);
  root.NasukeruGenericValues = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function(blank) {
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
      if (Array.isArray(input.genericMultiValues)) return input.genericMultiValues.slice();
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

  function optionLabel(input, value) {
    var labels = input.genericOptionLabels || {};
    return labels[value] || value;
  }

  function formatInputValueForCopy(input, value) {
    if (blank.isBlank(value)) return "";
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

  function formatInputValueForRenderer(input, value) {
    if (blank.isBlank(value)) return "";
    if (input.dataset.fieldType === "multi_select") {
      return splitMultiValue(value).map(function(item) {
        return optionLabel(input, item);
      });
    }
    return formatInputValueForCopy(input, value);
  }

  function applyInputValue(input, value) {
    if (input.dataset.fieldType === "multi_select") {
      var selected = splitMultiValue(value);
      input.genericMultiValues = selected.slice();
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
    formatInputValueForRenderer: formatInputValueForRenderer,
    isBlankValue: blank.isBlank,
    parseInputValue: parseInputValue,
    normalizeNumberField: normalizeNumberField,
    normalizeNumberInput: normalizeNumberInput,
    splitMultiValue: splitMultiValue,
  };
});
