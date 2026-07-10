(function(root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./generic-values.js"), require("./condition-engine.js"));
    return;
  }
  var api = factory(root.NasukeruGenericValues, root.NasukeruConditionEngine);
  root.NasukeruGenericRenderer = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function(genericValues, conditionEngine) {
  function sortedByDisplayOrder(items) {
    return (items || []).slice().sort(function(a, b) {
      var ao = typeof a.displayOrder === "number" ? a.displayOrder : 9999;
      var bo = typeof b.displayOrder === "number" ? b.displayOrder : 9999;
      return ao - bo;
    });
  }

  function optionValue(option) {
    return option && typeof option === "object" ? option.value : option;
  }

  function optionLabel(option) {
    return option && typeof option === "object" ? option.label : option;
  }

  function optionLabelMap(options) {
    var labels = {};
    (options || []).forEach(function(option) {
      labels[optionValue(option)] = optionLabel(option);
    });
    return labels;
  }

  function makeSection(section) {
    var sec = document.createElement("div");
    sec.className = "sec";
    if (section && section.id) sec.dataset.sectionId = section.id;
    sec.genericVisibleIf = (section && section.visibleIf) || null;
    var title = document.createElement("div");
    title.className = "sec-title";
    title.textContent = section && section.label ? section.label : "";
    sec.appendChild(title);
    return sec;
  }

  function applyInputMeta(input, section, field) {
    input.dataset.sectionId = section.id;
    input.dataset.sectionLabel = section.label;
    input.dataset.fieldId = field.id;
    input.dataset.fieldLabel = field.label;
    input.dataset.fieldType = field.type;
    input.dataset.requiredWarning = field.requiredWarning ? "true" : "false";
    input.dataset.blankPolicy = field.blankPolicy || "";
    if (field.type === "number") {
      if (typeof field.min === "number") input.dataset.min = String(field.min);
      if (typeof field.max === "number") input.dataset.max = String(field.max);
      if (typeof field.step === "number") input.dataset.step = String(field.step);
    }
    input.genericOptionLabels = optionLabelMap(field.options);
    input.genericRequiredIf = field.requiredIf || null;
    input.genericHardRange = field.hardRange || null;
    input.genericWarningRange = field.warningRange || null;
  }

  function makeField(section, field) {
    var row = document.createElement("div");
    row.className = "nrow";
    row.genericVisibleIf = field.visibleIf || null;
    var label = document.createElement("div");
    label.className = "nlabel";
    label.textContent = field.label;
    var input;
    if (field.type === "textarea") {
      input = document.createElement("textarea");
      input.className = "nval generic-input";
      input.rows = 2;
    } else if (field.type === "select") {
      input = document.createElement("select");
      input.className = "nval generic-input";
      var emptyOpt = document.createElement("option");
      emptyOpt.value = "";
      emptyOpt.textContent = "";
      input.appendChild(emptyOpt);
      (field.options || []).forEach(function(opt) {
        var option = document.createElement("option");
        option.value = optionValue(opt);
        option.textContent = optionLabel(opt);
        input.appendChild(option);
      });
    } else if (field.type === "multi_select") {
      input = document.createElement("input");
      input.type = "hidden";
      input.className = "generic-input";
      input.value = "";
      applyInputMeta(input, section, field);
      var group = document.createElement("div");
      group.className = "generic-multi";
      (field.options || []).forEach(function(opt) {
        var item = document.createElement("label");
        item.className = "generic-multi-option";
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = optionValue(opt);
        var text = document.createElement("span");
        text.textContent = optionLabel(opt);
        checkbox.addEventListener("change", function() {
          var values = [];
          group.querySelectorAll("input[type='checkbox']:checked").forEach(function(checked) {
            values.push(checked.value);
          });
          input.genericMultiValues = values.slice();
          input.value = values.join("、");
          input.dispatchEvent(new Event("change", { bubbles: true }));
        });
        item.appendChild(checkbox);
        item.appendChild(text);
        group.appendChild(item);
      });
      row.appendChild(label);
      row.appendChild(group);
      row.appendChild(input);
      return row;
    } else {
      input = document.createElement("input");
      input.type = "text";
      input.className = "nval generic-input";
      if (field.type === "number") {
        input.inputMode = "decimal";
        input.addEventListener("compositionend", function() {
          genericValues.normalizeNumberField(input);
          input.dispatchEvent(new Event("change", { bubbles: true }));
        });
        input.addEventListener("blur", function() {
          genericValues.normalizeNumberField(input);
        });
      }
    }
    input.value = "";
    input.placeholder = field.placeholder || "";
    applyInputMeta(input, section, field);
    row.appendChild(label);
    row.appendChild(input);
    if (field.unit) {
      var unit = document.createElement("span");
      unit.className = "generic-unit";
      unit.textContent = field.unit;
      row.appendChild(unit);
    }
    return row;
  }

  function bindConditionUpdates(container) {
    container.querySelectorAll(".generic-input").forEach(function(input) {
      input.addEventListener("input", function(){ updateConditions(container); });
      input.addEventListener("change", function(){ updateConditions(container); });
    });
  }

  function updateConditions(container) {
    var sections = Array.prototype.slice.call(container.querySelectorAll(".sec"));
    var rows = Array.prototype.slice.call(container.querySelectorAll(".nrow")).filter(function(row) {
      return row.querySelector(".generic-input");
    });
    var stable = false;
    for (var pass = 0; pass <= rows.length + sections.length; pass += 1) {
      var values = genericValues.collectTypedValues(container);
      var changed = false;
      sections.forEach(function(sec) {
        var visible = sec.genericVisibleIf
          ? conditionEngine.evaluateCondition(sec.genericVisibleIf, values)
          : true;
        if (sec.hidden === visible) {
          sec.hidden = !visible;
          changed = true;
        }
      });
      rows.forEach(function(row) {
        var input = row.querySelector(".generic-input");
        var ownVisible = row.genericVisibleIf
          ? conditionEngine.evaluateCondition(row.genericVisibleIf, values)
          : true;
        var parentSec = row.closest(".sec");
        var sectionVisible = parentSec ? !parentSec.hidden : true;
        var visible = ownVisible && sectionVisible;
        if (row.hidden === visible) {
          row.hidden = !visible;
          changed = true;
        }
        input.dataset.conditionVisible = visible ? "true" : "false";
        if (!visible && !genericValues.isBlankValue(genericValues.parseInputValue(input))) {
          genericValues.applyInputValue(input, "");
          changed = true;
        }
      });
      if (!changed) {
        stable = true;
        break;
      }
    }
    container.dataset.conditionError = stable ? "false" : "true";
    var card = container.closest(".tc");
    if (card) card.dataset.conditionError = container.dataset.conditionError;
  }

  function renderGenericBody(body, schema) {
    sortedByDisplayOrder(schema.sections).forEach(function(section) {
      var sec = makeSection(section);
      sortedByDisplayOrder(section.fields).forEach(function(field) {
        sec.appendChild(makeField(section, field));
      });
      body.appendChild(sec);
    });
    bindConditionUpdates(body);
    updateConditions(body);
  }

  function collectCopyValues(container) {
    var values = {};
    container.querySelectorAll(".generic-input").forEach(function(input) {
      var row = input.closest(".nrow");
      if (row && row.hidden) return;
      values[genericValues.fieldRef(input)] = genericValues.formatInputValueForCopy(input, genericValues.parseInputValue(input));
    });
    return values;
  }

  return {
    bindConditionUpdates: bindConditionUpdates,
    collectConditionValues: genericValues.collectTypedValues,
    collectCopyValues: collectCopyValues,
    makeField: makeField,
    makeSection: makeSection,
    optionLabel: optionLabel,
    optionLabelMap: optionLabelMap,
    optionValue: optionValue,
    renderGenericBody: renderGenericBody,
    sortedByDisplayOrder: sortedByDisplayOrder,
    updateConditions: updateConditions,
  };
});
