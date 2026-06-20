function getMissingRequiredItems(card) {
  var missing = [];
  var vitals = card.querySelectorAll(".vinput");
  vitals.forEach(function(v) {
    var meta = FIELD_META.vitals[v.dataset.vkey] || {};
    if (!v.value.trim()) missing.push(meta.warningLabel || "バイタル");
  });

  var nihss = card.querySelector('[data-neuro="nihss"]');
  if (nihss && !nihss.value.trim()) missing.push("NIHSS");

  [
    {key:"pupil", label:"瞳孔"},
    {key:"light", label:"対光反射"}
  ].forEach(function(item) {
    var field = card.querySelector('[data-neuro="'+item.key+'"]');
    if (field && !field.value.trim()) missing.push(item.label);
  });

  card.querySelectorAll(".mmt-input").forEach(function(input) {
    var meta = FIELD_META.mmt[input.dataset.mmt] || {};
    if (!input.value.trim()) missing.push(meta.warningLabel || "MMT");
  });

  var restEl = card.querySelector(".rest-opt.on");
  if (!restEl) missing.push("安静度");

  return missing;
}

function renderMissingWarning(items) {
  var warn = document.getElementById("warn");
  if (!warn) return;
  if (!items.length) {
    warn.classList.remove("show");
    warn.innerHTML = "";
    return;
  }
  warn.innerHTML = "";
  var title = document.createElement("div");
  title.className = "warn-title";
  title.textContent = "未入力の重要項目があります";
  var list = document.createElement("ul");
  list.className = "warn-list";
  items.forEach(function(item) {
    var li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  warn.appendChild(title);
  warn.appendChild(list);
  warn.classList.add("show");
}


