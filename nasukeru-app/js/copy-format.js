// ── Copy output ──
var currentCopyCard = null;
function openCov(card) {
  currentCopyCard = card;
  buildCopyText();
  document.getElementById("cov").classList.add("show");
}
function closeCov() { document.getElementById("cov").classList.remove("show"); currentCopyCard = null; }

function buildCopyText() {
  if (!currentCopyCard) return;
  renderMissingWarning(getMissingRequiredItems(currentCopyCard));
  var lines = [];
  var titleEl = currentCopyCard.querySelector(".stroke-title");
  var title = titleEl ? titleEl.textContent : "";

  lines.push(title);
  lines.push("");

  // Vitals
  var vitals = currentCopyCard.querySelectorAll(".vinput");
  if (vitals.length) {
    var keys = ["JCS","T","BP","HR","SpO₂"];
    var units = ["","℃","mmHg","","%" ];
    var vline = "";
    vitals.forEach(function(v, i){ vline += keys[i]+(v.value||"__")+units[i]+"　"; });
    lines.push(vline.trim());
    lines.push("");
  }

  // Symptoms
  var syms = currentCopyCard.querySelectorAll(".sym-input");
  if (syms.length) {
    var slabels = ["頭痛","めまい","嘔気"];
    syms.forEach(function(s,i){ lines.push(slabels[i]+"："+(s.value||"__")); });
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
      var mmtLabels = ["右上肢","右下肢","左上肢","左下肢"];
      var mmtLine = "MMT：";
      mmtItems.forEach(function(m,i){ mmtLine += mmtLabels[i]+(m.value||"__")+"、"; });
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

function doCopy() {
  var text = document.getElementById("prev").textContent;
  var btn = document.getElementById("cpbtn"); var orig = btn.innerHTML;
  navigator.clipboard.writeText(text).then(function() {
    btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>コピー完了';
    btn.style.background="#0f7b5e";
    setTimeout(function(){ btn.innerHTML=orig; btn.style.background=""; }, 1800);
    toast("✓ クリップボードにコピーしました");
  }).catch(function(){ toast("テキストを手動でコピーしてください","#c05621"); });
}




