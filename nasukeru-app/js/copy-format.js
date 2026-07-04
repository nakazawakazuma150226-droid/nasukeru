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
  renderSafetyValidation(currentCopySafetyResult);
  var lines = [];
  var titleEl = currentCopyCard.querySelector(".stroke-title");
  var title = titleEl ? titleEl.textContent : "";

  lines.push(title);
  lines.push("");

  // Vitals
  var vitals = currentCopyCard.querySelectorAll(".vinput");
  if (vitals.length) {
    var vline = "";
    vitals.forEach(function(v) {
      var meta = FIELD_META.vitals[v.dataset.vkey] || {};
      vline += (meta.outputLabel || "バイタル") + (v.value || "__") + (meta.unit || "") + "　";
    });
    lines.push(vline.trim());
    lines.push("");
  }

  // Symptoms
  var syms = currentCopyCard.querySelectorAll(".sym-input");
  if (syms.length) {
    syms.forEach(function(s) {
      var meta = FIELD_META.symptoms[s.dataset.skey] || {};
      lines.push((meta.outputLabel || "症状") + "：" + (s.value || "__"));
    });
    lines.push("");
  }

  // Neuro
  lines.push("神経所見");
  var neuroRows = currentCopyCard.querySelectorAll(".nrow");
  neuroRows.forEach(function(row) {
    var lbl = row.querySelector(".nlabel");
    var val = row.querySelector(".nval, .other-neuro");
    var mmtGrid = row.querySelector(".mmt-grid");
    if (mmtGrid) {
      var mmtItems = mmtGrid.querySelectorAll(".mmt-input");
      var mmtLine = "MMT：";
      mmtItems.forEach(function(m) {
        var meta = FIELD_META.mmt[m.dataset.mmt] || {};
        mmtLine += (meta.outputLabel || "MMT") + (m.value || "__") + "、";
      });
      lines.push(mmtLine.replace(/、$/,""));
    } else if (lbl && val) {
      var lblText = lbl.textContent.trim();
      var valText = (val.value || val.textContent || "").trim();
      if (lblText === "NIHSS") {
        lines.push("NIHSS："+(valText||"__"));
      } else if (lblText === "その他神経症状") {
        valText.split("\n").forEach(function(l){ if(l.trim()) lines.push(l.trim()); });
      } else {
        var line = "";
        if (lblText === "瞳孔") line = "瞳孔："+(valText||"__");
        else if (lblText === "対光反射") line = "対光反射："+(valText||"__");
        else if (lblText === "眼球位置") line = "眼球位置："+(valText||"__");
        else if (lblText === "バレー徴候") { if(valText) line = "バレー徴候："+valText; }
        else if (lblText === "ミンガッチー") { if(valText) line = "ミンガッチー徴候："+valText; }
        else line = lblText+"："+valText;
        if (line) lines.push(line);
      }
    }
  });
  lines.push("");

  // Rest
  var restEl = currentCopyCard.querySelector(".rest-opt.on");
  lines.push("安静度");
  lines.push(restEl ? restEl.textContent.trim() : "__");

  document.getElementById("prev").textContent = lines.join("\n");
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




