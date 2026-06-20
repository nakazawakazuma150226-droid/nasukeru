var adminTemplates = [];
var adminFilter = "active";
var restOptionCache = null;

var VITAL_KEYS = ["jcs", "t", "bp", "hr", "spo2"];
var SYMPTOM_KEYS = ["headache", "dizzy", "nausea"];
var MMT_KEYS = ["ru", "rl", "lu", "ll"];
var NEURO_KEYS = ["pupil", "light", "eye", "barre", "mingazzini", "nihss", "other"];
var NEURO_LABELS = {
  pupil: "瞳孔",
  light: "対光反射",
  eye: "眼球位置",
  barre: "バレー徴候",
  mingazzini: "ミンガッツィーニ",
  nihss: "NIHSS",
  other: "その他神経症状"
};

function $(id) {
  return document.getElementById(id);
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function toast(msg, color) {
  var t = $("toast");
  t.textContent = msg;
  t.style.background = color || "var(--t1)";
  t.classList.add("show");
  setTimeout(function(){ t.classList.remove("show"); }, 2500);
}

function formatDate(value) {
  if (!value) return "-";
  var date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function labelFor(section, key) {
  if (section === "vitals") return (FIELD_META.vitals[key] || {}).warningLabel || key;
  if (section === "symptoms") return (FIELD_META.symptoms[key] || {}).outputLabel || key;
  if (section === "mmt") return (FIELD_META.mmt[key] || {}).warningLabel || key;
  if (section === "neuro") return NEURO_LABELS[key] || key;
  return key;
}

function defaultSchema() {
  return {
    vitals: { jcs: "", t: "", bp: "", hr: "", spo2: "" },
    symptoms: { headache: "", dizzy: "", nausea: "" },
    neuro: {
      pupil: "",
      light: "",
      eye: "",
      barre: "",
      mingazzini: "",
      mmt: { ru: "", rl: "", lu: "", ll: "" },
      nihss: "",
      other: ""
    },
    rest: ""
  };
}

function normalizeDetailToSchema(detail) {
  return {
    vitals: detail.vitals || {},
    symptoms: detail.symptoms || {},
    neuro: detail.neuro || {},
    rest: typeof detail.rest === "string" ? detail.rest : ""
  };
}

function setModalError(message) {
  var el = $("admin-modal-error");
  el.textContent = message || "";
  el.classList.toggle("show", Boolean(message));
}

function openModal(title, subtitle) {
  $("admin-modal-title").textContent = title || "";
  $("admin-modal-subtitle").textContent = subtitle || "";
  setModalError("");
  clearNode($("admin-modal-body"));
  clearNode($("admin-modal-actions"));
  $("admin-modal").classList.add("show");
}

function closeModal() {
  $("admin-modal").classList.remove("show");
}

function button(label, className, onClick) {
  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = className || "btn bg";
  btn.textContent = label;
  btn.addEventListener("click", onClick);
  return btn;
}

function formField(label, name, value, options) {
  options = options || {};
  var wrap = document.createElement("label");
  wrap.className = "admin-field";
  var caption = document.createElement("span");
  caption.textContent = label;
  var input;
  if (options.textarea) {
    input = document.createElement("textarea");
    input.rows = options.rows || 3;
  } else {
    input = document.createElement("input");
    input.type = options.type || "text";
  }
  input.name = name;
  input.value = value || "";
  input.className = "admin-input";
  if (options.readonly) input.readOnly = true;
  if (options.placeholder) input.placeholder = options.placeholder;
  wrap.appendChild(caption);
  wrap.appendChild(input);
  return wrap;
}

function formSection(title) {
  var section = document.createElement("section");
  section.className = "admin-form-section";
  var h = document.createElement("h3");
  h.textContent = title;
  section.appendChild(h);
  return section;
}

function collectText(form, name) {
  var el = form.elements[name];
  return el ? el.value.trim() : "";
}

function showErrorForApi(error) {
  if (error.status === 403) return "ローカル防御ヘッダを確認してください。";
  if (error.status === 409) return error.message || "状態が競合しています。";
  if (error.status === 400) return error.message || "入力内容を確認してください。";
  if (error.status === 404) return "対象が見つかりません。";
  return error.message || "処理に失敗しました。";
}

function renderAdminRows() {
  var tbody = $("admin-template-rows");
  clearNode(tbody);
  var rows = adminTemplates.filter(function(item) {
    return adminFilter === "all" || item.is_active;
  });
  var activeCount = adminTemplates.filter(function(item){ return item.is_active; }).length;
  var inactiveCount = adminTemplates.length - activeCount;
  $("admin-summary").textContent = "有効 " + activeCount + " 件 / 削除済み " + inactiveCount + " 件";

  if (!rows.length) {
    var empty = document.createElement("tr");
    var td = document.createElement("td");
    td.colSpan = 6;
    td.className = "admin-empty-cell";
    td.textContent = "表示するテンプレートがありません";
    empty.appendChild(td);
    tbody.appendChild(empty);
    return;
  }

  rows.forEach(function(item) {
    var tr = document.createElement("tr");
    if (!item.is_active) tr.className = "admin-row-muted";

    var status = document.createElement("td");
    var badge = document.createElement("span");
    badge.className = "admin-status " + (item.is_active ? "active" : "inactive");
    badge.textContent = item.is_active ? "有効" : "削除済み";
    status.appendChild(badge);

    var name = document.createElement("td");
    var label = document.createElement("div");
    label.className = "admin-template-label";
    label.textContent = item.label;
    var full = document.createElement("div");
    full.className = "admin-template-full";
    full.textContent = item.full;
    name.appendChild(label);
    name.appendChild(full);

    var category = document.createElement("td");
    category.textContent = item.category;

    var version = document.createElement("td");
    version.textContent = item.current_version_number ? "v" + item.current_version_number : "-";

    var updated = document.createElement("td");
    updated.textContent = formatDate(item.updated_at);

    var actions = document.createElement("td");
    actions.className = "admin-actions";
    if (item.is_active) {
      actions.appendChild(button("編集", "btn bg admin-row-btn", function(){ openEditModal(item); }));
      actions.appendChild(button("削除", "btn bg admin-row-btn danger", function(){ openReasonModal("delete", item); }));
    } else {
      actions.appendChild(button("復元", "btn bg admin-row-btn", function(){ openReasonModal("restore", item); }));
    }
    actions.appendChild(button("履歴", "btn bg admin-row-btn", function(){ openHistoryModal(item); }));

    [status, name, category, version, updated, actions].forEach(function(td){ tr.appendChild(td); });
    tbody.appendChild(tr);
  });
}

async function loadAdminTemplates() {
  var tbody = $("admin-template-rows");
  clearNode(tbody);
  var loading = document.createElement("tr");
  var td = document.createElement("td");
  td.colSpan = 6;
  td.className = "admin-empty-cell";
  td.textContent = "読み込み中";
  loading.appendChild(td);
  tbody.appendChild(loading);
  try {
    adminTemplates = await getAdminTemplates();
    renderAdminRows();
  } catch (error) {
    td.textContent = "読み込みに失敗しました";
    toast("テンプレート一覧を読み込めませんでした", "#b91c1c");
  }
}

function openCreateModal() {
  openModal("新規追加", "");
  var form = document.createElement("form");
  form.className = "admin-form";
  form.appendChild(formField("ID", "id", "", { placeholder: "例: brainstem_custom" }));
  form.appendChild(formField("表示名", "label", "", { placeholder: "例: 脳幹" }));
  form.appendChild(formField("正式名称", "full", "", { placeholder: "例: 脳幹梗塞" }));
  form.appendChild(formField("分類", "category", "stroke"));
  form.appendChild(formField("追加理由", "change_reason", "", { textarea: true, rows: 3 }));
  $("admin-modal-body").appendChild(form);

  $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
  $("admin-modal-actions").appendChild(button("追加", "btn bp", async function() {
    var id = collectText(form, "id");
    if (!/^[a-z0-9_-]{1,32}$/.test(id)) {
      setModalError("IDは小文字英数字・アンダースコア・ハイフンの1〜32文字で入力してください。");
      return;
    }
    var label = collectText(form, "label");
    var full = collectText(form, "full");
    var category = collectText(form, "category");
    var reason = collectText(form, "change_reason");
    if (!label || !full || !category || !reason) {
      setModalError("必須項目を入力してください。");
      return;
    }
    try {
      await createTemplate({
        id: id,
        label: label,
        full: full,
        category: category,
        schema: defaultSchema(),
        change_reason: reason
      });
      closeModal();
      await loadAdminTemplates();
      toast("テンプレートを追加しました", "#2d7a3a");
    } catch (error) {
      setModalError(showErrorForApi(error));
    }
  }));
}

async function getRestOptionsCached() {
  if (!restOptionCache) restOptionCache = await getRestOptions();
  return restOptionCache;
}

function appendSchemaFields(form, schema, restOptions) {
  var vitalSection = formSection("バイタル");
  var vitalGrid = document.createElement("div");
  vitalGrid.className = "admin-field-grid";
  VITAL_KEYS.forEach(function(key) {
    vitalGrid.appendChild(formField(labelFor("vitals", key), "vitals." + key, schema.vitals[key]));
  });
  vitalSection.appendChild(vitalGrid);
  form.appendChild(vitalSection);

  var symptomSection = formSection("症状");
  var symptomGrid = document.createElement("div");
  symptomGrid.className = "admin-field-grid";
  SYMPTOM_KEYS.forEach(function(key) {
    symptomGrid.appendChild(formField(labelFor("symptoms", key), "symptoms." + key, schema.symptoms[key]));
  });
  symptomSection.appendChild(symptomGrid);
  form.appendChild(symptomSection);

  var neuroSection = formSection("神経所見");
  var neuroGrid = document.createElement("div");
  neuroGrid.className = "admin-field-grid";
  NEURO_KEYS.forEach(function(key) {
    neuroGrid.appendChild(formField(labelFor("neuro", key), "neuro." + key, schema.neuro[key], { textarea: key === "other", rows: 3 }));
  });
  neuroSection.appendChild(neuroGrid);
  form.appendChild(neuroSection);

  var mmtSection = formSection("MMT");
  var mmtGrid = document.createElement("div");
  mmtGrid.className = "admin-field-grid";
  MMT_KEYS.forEach(function(key) {
    mmtGrid.appendChild(formField(labelFor("mmt", key), "mmt." + key, schema.neuro.mmt[key]));
  });
  mmtSection.appendChild(mmtGrid);
  form.appendChild(mmtSection);

  var restSection = formSection("安静度");
  var restLabel = document.createElement("label");
  restLabel.className = "admin-field";
  var restCaption = document.createElement("span");
  restCaption.textContent = "安静度";
  var select = document.createElement("select");
  select.name = "rest";
  select.className = "admin-input";
  var emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "空欄";
  select.appendChild(emptyOpt);
  restOptions.forEach(function(opt) {
    var option = document.createElement("option");
    option.value = opt;
    option.textContent = opt;
    select.appendChild(option);
  });
  select.value = schema.rest || "";
  restLabel.appendChild(restCaption);
  restLabel.appendChild(select);
  restSection.appendChild(restLabel);
  form.appendChild(restSection);
}

function collectSchema(form) {
  var schema = defaultSchema();
  VITAL_KEYS.forEach(function(key){ schema.vitals[key] = form.elements["vitals." + key].value; });
  SYMPTOM_KEYS.forEach(function(key){ schema.symptoms[key] = form.elements["symptoms." + key].value; });
  NEURO_KEYS.forEach(function(key){ schema.neuro[key] = form.elements["neuro." + key].value; });
  MMT_KEYS.forEach(function(key){ schema.neuro.mmt[key] = form.elements["mmt." + key].value; });
  schema.rest = form.elements.rest.value;
  return schema;
}

async function openEditModal(item) {
  openModal("schema編集", item.label + " / " + item.full);
  var body = $("admin-modal-body");
  var loading = document.createElement("div");
  loading.className = "admin-empty-cell";
  loading.textContent = "読み込み中";
  body.appendChild(loading);
  try {
    var detail = await getTemplateDetail(item.id);
    var restOptions = await getRestOptionsCached();
    clearNode(body);
    var form = document.createElement("form");
    form.className = "admin-form";
    form.appendChild(formField("表示名", "label", item.label, { readonly: true }));
    form.appendChild(formField("正式名称", "full", item.full, { readonly: true }));
    form.appendChild(formField("分類", "category", item.category, { readonly: true }));
    appendSchemaFields(form, normalizeDetailToSchema(detail), restOptions);
    form.appendChild(formField("変更概要", "change_summary", "", { textarea: true, rows: 2 }));
    form.appendChild(formField("変更理由", "change_reason", "", { textarea: true, rows: 3 }));
    body.appendChild(form);

    clearNode($("admin-modal-actions"));
    $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
    $("admin-modal-actions").appendChild(button("保存", "btn bp", async function() {
      var summary = collectText(form, "change_summary");
      var reason = collectText(form, "change_reason");
      if (!summary || !reason) {
        setModalError("変更概要と変更理由を入力してください。");
        return;
      }
      try {
        await createTemplateVersion(item.id, {
          schema: collectSchema(form),
          change_summary: summary,
          change_reason: reason
        });
        closeModal();
        await loadAdminTemplates();
        toast("新しいバージョンを作成しました", "#2d7a3a");
      } catch (error) {
        setModalError(showErrorForApi(error));
      }
    }));
  } catch (error) {
    clearNode(body);
    setModalError(showErrorForApi(error));
  }
}

function openReasonModal(mode, item) {
  var isDelete = mode === "delete";
  openModal(isDelete ? "削除" : "復元", item.label + " / " + item.full);
  var form = document.createElement("form");
  form.className = "admin-form";
  form.appendChild(formField(isDelete ? "削除理由" : "復元理由", "reason", "", { textarea: true, rows: 4 }));
  $("admin-modal-body").appendChild(form);
  $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
  $("admin-modal-actions").appendChild(button(isDelete ? "削除" : "復元", isDelete ? "btn bp admin-danger-btn" : "btn bp", async function() {
    var reason = collectText(form, "reason");
    if (!reason) {
      setModalError("理由を入力してください。");
      return;
    }
    try {
      if (isDelete) await deleteTemplate(item.id, reason);
      else await restoreTemplate(item.id, reason);
      closeModal();
      await loadAdminTemplates();
      toast(isDelete ? "テンプレートを削除済みにしました" : "テンプレートを復元しました", "#2d7a3a");
    } catch (error) {
      setModalError(showErrorForApi(error));
    }
  }));
}

function renderJsonBlock(value) {
  var pre = document.createElement("pre");
  pre.className = "admin-json";
  pre.textContent = JSON.stringify(value, null, 2);
  return pre;
}

function buildSmallTable(headers, rows) {
  var table = document.createElement("table");
  table.className = "admin-mini-table";
  var thead = document.createElement("thead");
  var htr = document.createElement("tr");
  headers.forEach(function(header) {
    var th = document.createElement("th");
    th.textContent = header;
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  table.appendChild(thead);
  var tbody = document.createElement("tbody");
  rows.forEach(function(cells) {
    var tr = document.createElement("tr");
    cells.forEach(function(cell) {
      var td = document.createElement("td");
      if (cell instanceof Node) td.appendChild(cell);
      else td.textContent = cell == null ? "" : String(cell);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

async function openHistoryModal(item) {
  openModal("履歴", item.label + " / " + item.full);
  var body = $("admin-modal-body");
  body.appendChild(document.createTextNode("読み込み中"));
  $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
  try {
    var results = await Promise.all([getTemplateVersions(item.id), getTemplateLogs(item.id)]);
    var versions = results[0];
    var logs = results[1];
    clearNode(body);

    var detailBox = document.createElement("div");
    detailBox.className = "admin-version-detail";

    var versionRows = versions.map(function(version) {
      var detailBtn = button("詳細", "btn bg admin-row-btn", async function() {
        detailBox.textContent = "読み込み中";
        try {
          var detail = await getTemplateVersion(item.id, version.id);
          clearNode(detailBox);
          detailBox.appendChild(renderJsonBlock(detail.schema));
        } catch (error) {
          detailBox.textContent = showErrorForApi(error);
        }
      });
      return [
        "v" + version.version_number,
        version.change_summary || "",
        version.change_reason || "",
        formatDate(version.created_at),
        detailBtn
      ];
    });
    var versionSection = formSection("バージョン履歴");
    versionSection.appendChild(buildSmallTable(["版", "概要", "理由", "作成日時", "詳細"], versionRows));
    versionSection.appendChild(detailBox);
    body.appendChild(versionSection);

    var logRows = logs.map(function(log) {
      return [
        log.action,
        formatDate(log.acted_at),
        log.reason || "",
        log.actor_name || ""
      ];
    });
    var logSection = formSection("監査ログ");
    logSection.appendChild(buildSmallTable(["操作", "日時", "理由", "担当"], logRows));
    body.appendChild(logSection);
  } catch (error) {
    clearNode(body);
    setModalError(showErrorForApi(error));
  }
}

function initAdminEvents() {
  $("new-template-btn").addEventListener("click", openCreateModal);
  $("refresh-admin-btn").addEventListener("click", loadAdminTemplates);
  $("admin-modal-close").addEventListener("click", closeModal);
  $("admin-modal").addEventListener("click", function(event) {
    if (event.target === event.currentTarget) closeModal();
  });
  document.querySelectorAll(".admin-tab").forEach(function(tab) {
    tab.addEventListener("click", function() {
      adminFilter = tab.dataset.filter;
      document.querySelectorAll(".admin-tab").forEach(function(btn) {
        btn.classList.toggle("on", btn === tab);
      });
      renderAdminRows();
    });
  });
}

document.addEventListener("DOMContentLoaded", function() {
  initAdminEvents();
  loadAdminTemplates();
});
