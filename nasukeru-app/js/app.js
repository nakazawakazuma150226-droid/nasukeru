var currentCard = null;
var currentStrokeIdx = 0;
var strokeTemplates = [];
var quickTemplates = [];
var restOptions = [];
var defaultKeywords = ["脳梗塞","脳卒中","stroke"];
var allKw = defaultKeywords.slice();

// ── Quick list ──
function buildQuickList() {
  var list = document.getElementById("qlist");
  list.innerHTML = "";
  quickTemplates.forEach(function(q) {
    var el = document.createElement("div"); el.className = "qitem";
    var dot = document.createElement("span"); dot.className = "qi-dot";
    var name = document.createElement("span"); name.className = "qi-name"; name.textContent = q.label;
    var tag = document.createElement("span"); tag.className = "qi-tag"; tag.textContent = q.sub;
    el.appendChild(dot); el.appendChild(name); el.appendChild(tag);
    el.addEventListener("click", function() {
      document.getElementById("si").value = q.label;
      showStroke();
    });
    list.appendChild(el);
  });
}

// ── Autocomplete ──
var inp = document.getElementById("si");
var acd = document.getElementById("acd");

function appendHighlightedText(parent, txt, q) {
  var i = txt.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) {
    parent.textContent = txt;
    return;
  }
  parent.appendChild(document.createTextNode(txt.slice(0, i)));
  var mark = document.createElement("span"); mark.className = "ahi"; mark.textContent = txt.slice(i, i + q.length);
  parent.appendChild(mark);
  parent.appendChild(document.createTextNode(txt.slice(i + q.length)));
}

function showAC(q) {
  if (!q) { acd.classList.remove("show"); return; }
  var ms = allKw.filter(function(k){ return k.toLowerCase().includes(q.toLowerCase()); }).slice(0,6);
  acd.innerHTML = "";
  ms.forEach(function(k) {
    var el = document.createElement("div"); el.className = "aci";
    var icon = document.createElement("span"); icon.textContent = "⌕";
    var label = document.createElement("span"); appendHighlightedText(label, k, q);
    var badge = document.createElement("span"); badge.className = "acb"; badge.textContent = "専用テンプレ";
    badge.style.background = "var(--neul)"; badge.style.color = "var(--neu)";
    el.appendChild(icon); el.appendChild(label); el.appendChild(badge);
    el.addEventListener("mousedown", function(){ inp.value=k; acd.classList.remove("show"); showStroke(); });
    acd.appendChild(el);
  });
  if (!ms.length) {
    var emptyEl = document.createElement("div"); emptyEl.className = "aci";
    emptyEl.textContent = "登録済みテンプレートがありません";
    acd.appendChild(emptyEl);
  }
  acd.classList.add("show");
}
inp.addEventListener("input",  function(e){ showAC(e.target.value); });
inp.addEventListener("focus",  function(e){ if(e.target.value) showAC(e.target.value); });
inp.addEventListener("blur",   function(){ setTimeout(function(){ acd.classList.remove("show"); }, 150); });
inp.addEventListener("keydown",function(e){
  var items = acd.querySelectorAll(".aci");
  if (!items.length) { if(e.key==="Enter") handleEnter(); return; }
  if (e.key==="Escape") acd.classList.remove("show");
  if (e.key==="Enter") { e.preventDefault(); handleEnter(); }
});
function handleEnter() {
  acd.classList.remove("show");
  var q = inp.value.trim(); if (!q) return;
  if (allKw.some(function(k){ return k.toLowerCase() === q.toLowerCase(); })) showStroke();
  else toast("登録済みテンプレートを選択してください","#c05621");
}

// ── Stroke template ──
function showStroke() {
  document.getElementById("empty").style.display = "none";
  document.getElementById("ta").innerHTML = "";
  var card = buildStrokeCard();
  document.getElementById("ta").appendChild(card);
  currentCard = card;
  switchStrokeTab(0);
}

function buildStrokeCard() {
  var div = document.createElement("div"); div.className = "tc";

  // Subtabs
  var tabs = document.createElement("div"); tabs.className = "subtabs"; tabs.id = "stroke-tabs";
  strokeTemplates.forEach(function(st, i) {
    var b = document.createElement("button"); b.className = "stab"; b.textContent = st.label;
    b.addEventListener("click", function(){ switchStrokeTab(i); });
    tabs.appendChild(b);
  });

  // Header
  var hdr = document.createElement("div"); hdr.className = "tch";
  var bdg = document.createElement("span"); bdg.className = "bdg bneu"; bdg.textContent = "脳神経";
  var ttl = document.createElement("span"); ttl.className = "stroke-title"; ttl.id = "stroke-title";
  var sub = document.createElement("span"); sub.className = "stroke-sub"; sub.textContent = "脳梗塞テンプレート Ver1";
  hdr.appendChild(bdg); hdr.appendChild(ttl); hdr.appendChild(sub);

  // Body
  var body = document.createElement("div"); body.className = "tcb"; body.id = "stroke-body";

  // Footer
  var ftr = document.createElement("div"); ftr.className = "tcf";
  var cpBtn = document.createElement("button"); cpBtn.className = "btn bp";
  cpBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>コピー出力';
  cpBtn.addEventListener("click", function(){ openCov(div); });
  var clBtn = document.createElement("button"); clBtn.className = "btn bg"; clBtn.textContent = "クリア";
  clBtn.addEventListener("click", function(){ switchStrokeTab(currentStrokeIdx); });
  ftr.appendChild(cpBtn); ftr.appendChild(clBtn);

  div.appendChild(tabs); div.appendChild(hdr); div.appendChild(body); div.appendChild(ftr);
  return div;
}

function switchStrokeTab(idx) {
  currentStrokeIdx = idx;
  var st = strokeTemplates[idx];
  document.querySelectorAll(".stab").forEach(function(b,i){ b.classList.toggle("on", i===idx); });
  document.getElementById("stroke-title").textContent = st.full;
  renderStrokeBody(st);
}

function renderStrokeBody(st) {
  var body = document.getElementById("stroke-body");
  body.innerHTML = "";

  // ── バイタル ──
  var sec = makeSec("バイタル");
  var vrow = document.createElement("div"); vrow.className = "vrow";
  [
    {key:"jcs", label:"JCS",      val:st.vitals.jcs,  ph:"Ⅰ-0"},
    {key:"t",   label:"T (℃)",   val:st.vitals.t,    ph:"36.5"},
    {key:"bp",  label:"BP (mmHg)",val:st.vitals.bp,   ph:"120"},
    {key:"hr",  label:"HR",       val:st.vitals.hr,   ph:"70台"},
    {key:"spo2",label:"SpO₂ (%)", val:st.vitals.spo2, ph:"98"}
  ].forEach(function(f) {
    var vitem = document.createElement("div"); vitem.className = "vitem";
    var lbl = document.createElement("div"); lbl.className = "vlabel"; lbl.textContent = f.label;
    var inp2 = document.createElement("input"); inp2.className = "vinput";
    inp2.type="text"; inp2.value=f.val; inp2.placeholder=f.ph;
    inp2.dataset.vkey = f.key;
    vitem.appendChild(lbl); vitem.appendChild(inp2);
    vrow.appendChild(vitem);
  });
  sec.appendChild(vrow); body.appendChild(sec);

  // ── 症状 ──
  var ssec = makeSec("症状");
  var srow = document.createElement("div"); srow.className = "srow";
  [
    {key:"headache", label:"頭痛", val:st.symptoms.headache},
    {key:"dizzy",    label:"めまい", val:st.symptoms.dizzy},
    {key:"nausea",   label:"嘔気",  val:st.symptoms.nausea}
  ].forEach(function(f) {
    var si2 = document.createElement("div"); si2.className = "sym-item";
    var sl = document.createElement("span"); sl.className = "sym-label"; sl.textContent = f.label+"：";
    var sv = document.createElement("input"); sv.className = "sym-input";
    sv.type="text"; sv.value=f.val; sv.placeholder="記載";
    sv.dataset.skey = f.key;
    si2.appendChild(sl); si2.appendChild(sv);
    srow.appendChild(si2);
  });
  ssec.appendChild(srow); body.appendChild(ssec);

  // ── 神経所見 ──
  var nsec = makeSec("神経所見");

  // 瞳孔・対光反射・眼球位置
  [
    {key:"pupil",     label:"瞳孔",     val:st.neuro.pupil,      ph:"2.5/2.5mm", ta:false},
    {key:"light",     label:"対光反射", val:st.neuro.light,      ph:"あり/なし",  ta:false},
    {key:"eye",       label:"眼球位置", val:st.neuro.eye,        ph:"正中位",     ta:false},
    {key:"barre",     label:"バレー徴候",val:st.neuro.barre,     ph:"左__°回内", ta:false},
    {key:"mingazzini",label:"ミンガッチー",val:st.neuro.mingazzini,ph:"左軽度下垂",ta:false}
  ].forEach(function(f) {
    nsec.appendChild(makeNRow(f.label, f.val, f.ph, f.ta, f.key));
  });

  // MMT
  var mmtRow = document.createElement("div"); mmtRow.className = "nrow";
  var mmtLbl = document.createElement("div"); mmtLbl.className = "nlabel"; mmtLbl.textContent = "MMT";
  var mmtGrid = document.createElement("div"); mmtGrid.className = "mmt-grid";
  [
    {key:"ru", label:"右上肢", val:st.neuro.mmt.ru},
    {key:"rl", label:"右下肢", val:st.neuro.mmt.rl},
    {key:"lu", label:"左上肢", val:st.neuro.mmt.lu},
    {key:"ll", label:"左下肢", val:st.neuro.mmt.ll}
  ].forEach(function(m) {
    var mi2 = document.createElement("div"); mi2.className = "mmt-item";
    var ml = document.createElement("span"); ml.className = "mmt-label"; ml.textContent = m.label;
    var mv = document.createElement("input"); mv.className = "mmt-input";
    mv.type="text"; mv.value=m.val; mv.placeholder="5/5"; mv.dataset.mmt=m.key;
    mi2.appendChild(ml); mi2.appendChild(mv);
    mmtGrid.appendChild(mi2);
  });
  mmtRow.appendChild(mmtLbl); mmtRow.appendChild(mmtGrid);
  nsec.appendChild(mmtRow);

  // NIHSS
  nsec.appendChild(makeNRow("NIHSS", st.neuro.nihss, "0点（別紙記録参照）", false, "nihss"));

  // その他神経症状
  var otherRow = document.createElement("div"); otherRow.className = "nrow";
  var otherLbl = document.createElement("div"); otherLbl.className = "nlabel"; otherLbl.textContent = "その他神経症状";
  var otherTa = document.createElement("textarea"); otherTa.className = "other-neuro";
  otherTa.value = st.neuro.other; otherTa.placeholder = "神経症状を記載";
  otherTa.dataset.neuro = "other";
  otherRow.appendChild(otherLbl); otherRow.appendChild(otherTa);
  nsec.appendChild(otherRow);
  body.appendChild(nsec);

  // ── 安静度 ──
  var rsec = makeSec("安静度");
  var ropts = document.createElement("div"); ropts.className = "rest-opts";
  restOptions.forEach(function(opt) {
    var lbl = document.createElement("label"); lbl.className = "rest-opt" + (opt === st.rest ? " on" : "");
    var rb = document.createElement("input"); rb.type = "radio"; rb.name = "rest"; rb.value = opt;
    if (opt === st.rest) rb.checked = true;
    lbl.appendChild(rb);
    lbl.appendChild(document.createTextNode(opt));
    lbl.addEventListener("click", function(){
      document.querySelectorAll(".rest-opt").forEach(function(l){ l.classList.remove("on"); });
      lbl.classList.add("on"); rb.checked = true;
    });
    ropts.appendChild(lbl);
  });
  rsec.appendChild(ropts); body.appendChild(rsec);
}

function makeSec(title) {
  var sec = document.createElement("div"); sec.className = "sec";
  var t = document.createElement("div"); t.className = "sec-title"; t.textContent = title;
  sec.appendChild(t);
  return sec;
}
function makeNRow(label, val, ph, isTA, key) {
  var row = document.createElement("div"); row.className = "nrow";
  var lbl = document.createElement("div"); lbl.className = "nlabel"; lbl.textContent = label;
  var inp2;
  if (isTA) {
    inp2 = document.createElement("textarea"); inp2.className = "nval"; inp2.rows = 2;
  } else {
    inp2 = document.createElement("input"); inp2.className = "nval"; inp2.type = "text";
  }
  inp2.value = val; inp2.placeholder = ph;
  if (key) inp2.dataset.neuro = key;
  row.appendChild(lbl); row.appendChild(inp2);
  return row;
}

function toast(msg, color) {
  var t = document.getElementById("toast");
  t.textContent=msg; t.style.background=color||"var(--t1)";
  t.classList.add("show"); setTimeout(function(){ t.classList.remove("show"); }, 2500);
}

document.getElementById("cov").addEventListener("click", function(e){ if(e.target===e.currentTarget) closeCov(); });

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function showInitError() {
  var empty = document.getElementById("empty");
  var target = document.getElementById("ta");
  empty.style.display = "block";
  target.innerHTML = "";
  clearNode(empty);

  var icon = document.createElement("div"); icon.className = "ei"; icon.textContent = "!";
  var title = document.createElement("div"); title.className = "et"; title.textContent = "テンプレートを読み込めませんでした";
  var body = document.createElement("div"); body.className = "es"; body.textContent = "サーバー起動とDB初期化の状態を確認してください";
  empty.appendChild(icon); empty.appendChild(title); empty.appendChild(body);
  toast("テンプレートを読み込めませんでした", "#c05621");
}

function uniqueList(items) {
  var seen = {};
  return items.filter(function(item) {
    if (!item || seen[item]) return false;
    seen[item] = true;
    return true;
  });
}

async function loadSearchKeywords() {
  var apiKeywords = [];
  try {
    apiKeywords = await getSearchKeywords();
  } catch (err) {
    console.warn("search keywords fallback", err);
  }
  allKw = uniqueList(
    apiKeywords
      .concat(defaultKeywords)
      .concat(quickTemplates.map(function(q){ return q.label; }))
      .concat(strokeTemplates.map(function(st){ return st.label; }))
      .concat(strokeTemplates.map(function(st){ return st.full; }))
  );
}

// Init
async function initApp() {
  try {
    strokeTemplates = await getTemplates();
    quickTemplates = await getQuickTemplates();
    restOptions = await getRestOptions();
    await loadSearchKeywords();
    buildQuickList();
  } catch (err) {
    console.error(err);
    showInitError();
  }
}

initApp();

