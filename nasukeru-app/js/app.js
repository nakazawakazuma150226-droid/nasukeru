var currentCard = null;
var templates = [];
var genericTemplates = [];
var quickTemplates = [];
var restOptions = [];
var routeOptions = [];
var allKw = [];

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
      openTarget(q.target);
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
  var ms = routeOptions.filter(function(item){ return item.label.toLowerCase().includes(q.toLowerCase()); }).slice(0,6);
  acd.innerHTML = "";
  ms.forEach(function(item) {
    var el = document.createElement("div"); el.className = "aci";
    var icon = document.createElement("span"); icon.textContent = "⌕";
    var label = document.createElement("span"); appendHighlightedText(label, item.label, q);
    var badge = document.createElement("span"); badge.className = "acb"; badge.textContent = item.target && item.target.type === "group" ? "グループ" : "専用テンプレ";
    badge.style.background = "var(--neul)"; badge.style.color = "var(--neu)";
    el.appendChild(icon); el.appendChild(label); el.appendChild(badge);
    el.addEventListener("mousedown", function(){ inp.value=item.label; acd.classList.remove("show"); openTarget(item.target); });
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
  var item = routeOptions.find(function(option){ return option.label.toLowerCase() === q.toLowerCase(); });
  if (item) openTarget(item.target);
  else showTemplateNotFound();
}

function schemaFormat(template) {
  return template.schema_format || (template.schema && template.schema.schemaFormat) || "unknown";
}

function showTemplateNotFound() {
  toast("登録済みテンプレートを選択してください", "#c05621");
}

function showTemplateById(id) {
  var generic = genericTemplates.find(function(template){ return template.id === id; });
  if (generic) {
    showGeneric(generic);
    return true;
  }
  showTemplateNotFound();
  return false;
}

function openTarget(target) {
  if (!target || !target.type || !target.id) {
    showTemplateNotFound();
    return;
  }
  if (target.type === "template") {
    showTemplateById(target.id);
    return;
  }
  if (target.type === "group") {
    showTemplateGroup(target.id);
    return;
  }
  showTemplateNotFound();
}

function showGeneric(template) {
  document.getElementById("empty").style.display = "none";
  document.getElementById("ta").innerHTML = "";
  var card = buildGenericCard(template);
  document.getElementById("ta").appendChild(card);
  currentCard = card;
  scrollTemplateIntoView(card);
}

function scrollTemplateIntoView(card) {
  if (!card || !window.matchMedia("(max-width: 820px)").matches) return;
  window.requestAnimationFrame(function() {
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function readGenericInputState(card) {
  return NasukeruGenericValues.collectTypedValues(card);
}

function restoreGenericInputState(card, values) {
  if (!card || !values) return;
  card.querySelectorAll(".generic-input").forEach(function(input) {
    var ref = input.dataset.sectionId + "." + input.dataset.fieldId;
    var value = Object.prototype.hasOwnProperty.call(values, ref) ? values[ref] : "";
    NasukeruGenericValues.applyInputValue(input, value);
  });
  updateGenericConditions(card);
}

async function showTemplateGroup(groupId) {
  try {
    var group = await getTemplateGroup(groupId);
    if (!group.templates || !group.templates.length) {
      showTemplateNotFound();
      return;
    }
    document.getElementById("empty").style.display = "none";
    document.getElementById("ta").innerHTML = "";
    var card = buildTemplateGroupCard(group);
    document.getElementById("ta").appendChild(card);
    currentCard = card.querySelector(".tc");
    scrollTemplateIntoView(card);
  } catch (error) {
    console.error(error);
    showTemplateNotFound();
  }
}

function buildTemplateGroupCard(group) {
  var wrap = document.createElement("div");
  wrap.className = "group-wrap";
  wrap.dataset.groupId = group.id;
  var groupState = {};

  var tabs = document.createElement("div");
  tabs.className = "subtabs";
  var body = document.createElement("div");
  body.className = "group-body";
  wrap.appendChild(tabs);
  wrap.appendChild(body);

  var selectedTemplateId = group.templates[0].id;

  function saveCurrentState() {
    var activeCard = body.querySelector(".tc");
    if (activeCard && activeCard.dataset.templateId) {
      groupState[activeCard.dataset.templateId] = readGenericInputState(activeCard);
    }
  }

  function renderSelected(templateId, shouldSaveState) {
    if (shouldSaveState !== false) saveCurrentState();
    selectedTemplateId = templateId;
    body.innerHTML = "";
    tabs.querySelectorAll(".stab").forEach(function(button) {
      button.classList.toggle("on", button.dataset.templateId === templateId);
    });
    var template = group.templates.find(function(item){ return item.id === templateId; });
    if (!template) return;
    var templateCard = buildGenericCard(template, {
      onClear: function() {
        groupState[templateId] = {};
        renderSelected(templateId, false);
      },
    });
    body.appendChild(templateCard);
    restoreGenericInputState(templateCard, groupState[templateId]);
    currentCard = templateCard;
  }

  group.templates.forEach(function(template) {
    var button = document.createElement("button");
    button.className = "stab";
    button.dataset.templateId = template.id;
    button.textContent = template.label;
    button.addEventListener("click", function(){ renderSelected(template.id); });
    tabs.appendChild(button);
  });

  renderSelected(selectedTemplateId);
  return wrap;
}

function buildGenericCard(template, options) {
  options = options || {};
  var div = document.createElement("div");
  div.className = "tc";
  div.dataset.schemaFormat = schemaFormat(template);
  div.dataset.templateId = template.id;
  div.copyFormat = template.copy_format || null;

  var hdr = document.createElement("div"); hdr.className = "tch";
  var bdg = document.createElement("span"); bdg.className = "bdg bsav"; bdg.textContent = "記録";
  var ttl = document.createElement("span"); ttl.className = "stroke-title"; ttl.textContent = template.full;
  var sub = document.createElement("span"); sub.className = "stroke-sub"; sub.textContent = template.label || "";
  hdr.appendChild(bdg); hdr.appendChild(ttl); hdr.appendChild(sub);

  var body = document.createElement("div"); body.className = "tcb";
  renderGenericBody(body, template.schema);

  var ftr = document.createElement("div"); ftr.className = "tcf";
  var cpBtn = document.createElement("button"); cpBtn.className = "btn bp"; cpBtn.textContent = "コピー出力";
  cpBtn.addEventListener("click", function(){ openCov(div); });
  var clBtn = document.createElement("button"); clBtn.className = "btn bg"; clBtn.textContent = "クリア";
  clBtn.addEventListener("click", function(){
    if (options.onClear) options.onClear();
    else showGeneric(template);
  });
  ftr.appendChild(cpBtn); ftr.appendChild(clBtn);

  div.appendChild(hdr); div.appendChild(body); div.appendChild(ftr);
  return div;
}

function renderGenericBody(body, schema) {
  NasukeruGenericRenderer.renderGenericBody(body, schema);
}

function updateGenericConditions(container) {
  NasukeruGenericRenderer.updateConditions(container);
}

function makeSec(section) {
  var isSection = section && typeof section === "object";
  var sec = document.createElement("div"); sec.className = "sec";
  if (isSection && section.id) sec.dataset.sectionId = section.id;
  sec.genericVisibleIf = (isSection && section.visibleIf) || null;
  var t = document.createElement("div"); t.className = "sec-title"; t.textContent = isSection ? section.label : section;
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

function uniqueRouteOptions(items) {
  var seen = {};
  return items.filter(function(item) {
    if (!item || !item.label || !item.target) return false;
    var key = item.label.toLowerCase();
    if (seen[key]) return false;
    seen[key] = true;
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
  routeOptions = uniqueRouteOptions(
    quickTemplates.map(function(q) {
      return { label: q.label, target: q.target };
    })
      .concat(apiKeywords.map(function(item) {
        if (typeof item === "string") {
          return { label: item, target: null };
        }
        return { label: item.keyword, target: item.target };
      }))
      .concat(genericTemplates.map(function(st){ return { label: st.label, target: { type: "template", id: st.id } }; }))
      .concat(genericTemplates.map(function(st){ return { label: st.full, target: { type: "template", id: st.id } }; }))
  );
  allKw = uniqueList(routeOptions.map(function(item){ return item.label; }));
}

// Init
async function initApp() {
  try {
    templates = await getTemplates();
    genericTemplates = templates.filter(function(template){
      var fmt = schemaFormat(template);
      return fmt === "generic-v1" || fmt === "generic-v2";
    });
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

