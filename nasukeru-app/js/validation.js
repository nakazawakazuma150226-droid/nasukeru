function getMissingRequiredItems(card) {
  if (card.dataset.schemaFormat === "generic-v1" || card.dataset.schemaFormat === "generic-v2") {
    return getMissingGenericRequiredItems(card);
  }
  return [];
}

function getSafetyValidationResult(card) {
  if (card.dataset.schemaFormat === "generic-v1" || card.dataset.schemaFormat === "generic-v2") {
    return getGenericSafetyValidationResult(card);
  }
  return {
    blocks: [{ fieldRef: "", code: "unsupported_template_format", severity: "block", message: "このテンプレート形式は通常画面では表示できません" }],
    warnings: [],
  };
}

function getGenericSafetyValidationResult(card) {
  if (card.dataset.conditionError === "true") {
    return {
      blocks: [{ fieldRef: "", code: "condition_error", severity: "block", message: "条件表示の設定を確認してください" }],
      warnings: [],
    };
  }
  var values = NasukeruGenericValues.collectTypedValues(card);
  var fields = [];
  card.querySelectorAll(".generic-input").forEach(function(input) {
    var row = input.closest(".nrow");
    fields.push({
      ref: NasukeruGenericValues.fieldRef(input),
      label: input.dataset.fieldLabel || "入力項目",
      type: input.dataset.fieldType || "text",
      value: NasukeruGenericValues.parseInputValue(input),
      visible: !(row && row.hidden),
      blankPolicy: input.dataset.blankPolicy || "",
      requiredWarning: input.dataset.requiredWarning === "true",
      requiredIf: input.genericRequiredIf || null,
      hardRange: input.genericHardRange || null,
      warningRange: input.genericWarningRange || null,
    });
  });
  return NasukeruSafetyRules.validateFields(fields, values);
}

function getMissingGenericRequiredItems(card) {
  var missing = [];
  var values = NasukeruGenericValues.collectTypedValues(card);
  card.querySelectorAll(".generic-input").forEach(function(input) {
    var row = input.closest(".nrow");
    if (row && row.hidden) return;
    var value = NasukeruGenericValues.parseInputValue(input);
    var required = input.dataset.requiredWarning === "true"
      || (input.genericRequiredIf && NasukeruConditionEngine.evaluateCondition(input.genericRequiredIf, values));
    if (required && NasukeruGenericValues.isBlankValue(value)) {
      missing.push(input.dataset.fieldLabel || "入力項目");
    }
  });
  return missing;
}

function renderMissingWarning(items) {
  renderSafetyValidation({
    blocks: [],
    warnings: (items || []).map(function(label) {
      return { message: label };
    }),
  });
}

function renderSafetyValidation(result) {
  var warn = document.getElementById("warn");
  if (!warn) return;
  var blocks = (result && result.blocks) || [];
  var warnings = (result && result.warnings) || [];
  if (!blocks.length && !warnings.length) {
    warn.classList.remove("show");
    warn.classList.remove("block");
    warn.innerHTML = "";
    return;
  }
  warn.innerHTML = "";
  warn.classList.toggle("block", blocks.length > 0);
  var title = document.createElement("div");
  title.className = "warn-title";
  title.textContent = blocks.length ? "コピー前に修正が必要な項目があります" : "確認が必要な項目があります";
  var list = document.createElement("ul");
  list.className = "warn-list";
  blocks.concat(warnings).forEach(function(item) {
    var li = document.createElement("li");
    li.textContent = item.message || item;
    list.appendChild(li);
  });
  warn.appendChild(title);
  warn.appendChild(list);
  warn.classList.add("show");
}


