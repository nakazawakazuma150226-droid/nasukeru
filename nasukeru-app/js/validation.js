function getMissingRequiredItems(card) {
  var missing = [];
  var vitals = card.querySelectorAll(".vinput");
  var vitalLabels = ["JCS","体温","血圧","脈拍","SpO₂"];
  vitals.forEach(function(v, i) {
    if (!v.value.trim()) missing.push(vitalLabels[i] || "バイタル");
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

  var mmtLabels = {
    ru: "MMT 右上肢",
    rl: "MMT 右下肢",
    lu: "MMT 左上肢",
    ll: "MMT 左下肢"
  };
  card.querySelectorAll(".mmt-input").forEach(function(input) {
    if (!input.value.trim()) missing.push(mmtLabels[input.dataset.mmt] || "MMT");
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


