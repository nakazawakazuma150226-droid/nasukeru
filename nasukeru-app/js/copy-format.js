// ── Copy output ──
var currentCopyCard = null;
var currentCopySafetyResult = { blocks: [], warnings: [] };
var currentCopyRenderResult = { text: "", unresolvedRefs: [], warnings: [] };
function openCov(card) {
  currentCopyCard = card;
  buildCopyText();
  document.getElementById("cov").classList.add("show");
}
function closeCov() { document.getElementById("cov").classList.remove("show"); currentCopyCard = null; }

function buildCopyText() {
  if (!currentCopyCard) return;
  currentCopySafetyResult = getSafetyValidationResult(currentCopyCard);
  if (currentCopyCard.dataset.schemaFormat === "generic-v1" || currentCopyCard.dataset.schemaFormat === "generic-v2") {
    buildGenericCopyText();
    renderSafetyValidation(currentCopySafetyResult);
    return;
  }
  currentCopySafetyResult = {
    blocks: [{ fieldRef: "", code: "unsupported_template_format", severity: "block", message: "このテンプレート形式は通常画面では表示できません" }],
    warnings: [],
  };
  renderSafetyValidation(currentCopySafetyResult);
  document.getElementById("prev").textContent = "";
}

function buildGenericCopyText() {
  var copyFormat = currentCopyCard.copyFormat;
  if (copyFormat && copyFormat.format === "text-v1" && Array.isArray(copyFormat.lines)) {
    buildGenericTemplateCopyText(copyFormat);
    return;
  }

  var lines = [];
  var titleEl = currentCopyCard.querySelector(".stroke-title");
  var title = titleEl ? titleEl.textContent : "";
  lines.push(title);
  lines.push("");

  var currentSection = "";
  currentCopyCard.querySelectorAll(".generic-input").forEach(function(input) {
    var row = input.closest(".nrow");
    if (row && row.hidden) return;
    var section = input.dataset.sectionLabel || "";
    if (section && section !== currentSection) {
      if (currentSection) lines.push("");
      lines.push(section);
      currentSection = section;
    }
    var label = input.dataset.fieldLabel || "入力項目";
    lines.push(label + "：" + (genericInputValueForCopy(input) || "__"));
  });

  document.getElementById("prev").textContent = lines.join("\n");
}

function collectGenericValues() {
  var values = {};
  currentCopyCard.querySelectorAll(".generic-input").forEach(function(input) {
    var row = input.closest(".nrow");
    if (row && row.hidden) return;
    values[input.dataset.sectionId + "." + input.dataset.fieldId] = genericInputValueForCopy(input);
  });
  return values;
}

function collectGenericConditionValues() {
  return NasukeruGenericValues.collectTypedValues(currentCopyCard);
}

function genericInputValueForCopy(input) {
  return NasukeruGenericValues.formatInputValueForCopy(
    input,
    NasukeruGenericValues.parseInputValue(input)
  );
}

function buildGenericTemplateCopyText(copyFormat) {
  var values = collectGenericValues();
  var conditionValues = collectGenericConditionValues();
  var result = NasukeruCopyRenderer.renderGenericTemplateCopyResult(copyFormat, values, conditionValues);
  currentCopyRenderResult = result;
  currentCopySafetyResult = mergeCopyRenderWarnings(currentCopySafetyResult, result);
  document.getElementById("prev").textContent = result.text;
}

function genericFieldMetaByRef(card) {
  var meta = {};
  card.querySelectorAll(".generic-input").forEach(function(input) {
    var ref = input.dataset.sectionId + "." + input.dataset.fieldId;
    meta[ref] = {
      label: input.dataset.fieldLabel || ref,
    };
  });
  return meta;
}

function mergeCopyRenderWarnings(safetyResult, renderResult) {
  var result = {
    blocks: ((safetyResult && safetyResult.blocks) || []).slice(),
    warnings: ((safetyResult && safetyResult.warnings) || []).slice(),
  };
  var seen = {};
  result.blocks.concat(result.warnings).forEach(function(issue) {
    if (issue && issue.fieldRef) seen[issue.fieldRef] = true;
  });
  var meta = genericFieldMetaByRef(currentCopyCard);
  (renderResult.unresolvedRefs || []).forEach(function(ref) {
    if (seen[ref]) return;
    seen[ref] = true;
    result.warnings.push({
      fieldRef: ref,
      code: "unresolved_copy_ref",
      severity: "warn",
      message: (meta[ref] && meta[ref].label ? meta[ref].label : ref) + "が未入力のままコピー文に含まれています",
    });
  });
  return result;
}

function doCopy() {
  var blocks = (currentCopySafetyResult && currentCopySafetyResult.blocks) || [];
  var warnings = (currentCopySafetyResult && currentCopySafetyResult.warnings) || [];
  if (blocks.length) {
    toast("修正が必要な項目があるためコピーできません", "#b91c1c");
    return;
  }
  if (warnings.length && !window.confirm("確認が必要な項目があります。このままコピーしますか？")) {
    return;
  }
  var text = document.getElementById("prev").textContent;
  var btn = document.getElementById("cpbtn"); var orig = btn.innerHTML;
  navigator.clipboard.writeText(text).then(function() {
    btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>コピー完了';
    btn.style.background="#0f7b5e";
    setTimeout(function(){ btn.innerHTML=orig; btn.style.background=""; }, 1800);
    toast("✓ クリップボードにコピーしました");
  }).catch(function(){ toast("テキストを手動でコピーしてください","#c05621"); });
}




