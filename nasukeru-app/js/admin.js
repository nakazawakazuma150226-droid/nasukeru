var adminTemplates = [];
var adminFilter = "active";
var restOptionCache = null;
var DEFAULT_NEW_SCHEMA_FORMAT = "generic-v2";

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
  if (detail.schema) return detail.schema;
  return {
    vitals: detail.vitals || {},
    symptoms: detail.symptoms || {},
    neuro: detail.neuro || {},
    rest: typeof detail.rest === "string" ? detail.rest : ""
  };
}

function defaultGenericSchema() {
  return {
    schemaFormat: "generic-v2",
    sections: [
      {
        id: "basic",
        label: "基本情報",
        displayOrder: 1,
        fields: [
          {
            id: "note",
            label: "記載項目",
            type: "text",
            allowEmpty: true
          }
        ]
      }
    ]
  };
}

function isGenericSchemaFormat(format) {
  return format === "generic-v1" || format === "generic-v2";
}

function schemaFormatLabel(format) {
  if (format === "generic-v1") return "通常テンプレート（条件なし）";
  if (format === "generic-v2") return "条件付きテンプレート";
  if (format === "stroke-v1") return "旧形式（履歴用）";
  return format || "-";
}

function defaultGenericCopyFormat() {
  return {
    format: "text-v1",
    lines: [
      "{{basic.note}}"
    ]
  };
}

function templateById(id) {
  return adminTemplates.find(function(item) { return item.id === id; });
}

function generateTemplateId() {
  return NasukeruSimpleTemplateModel.randomId("tpl");
}

function appendGenericEditor(form, schema, copyFormat, schemaFormatGetter) {
  var builderSection = formSection("Template Builder");
  var mount = document.createElement("div");
  builderSection.appendChild(mount);
  form.appendChild(builderSection);
  var builder = NasukeruAdminBuilder.create(mount, schema, copyFormat || defaultGenericCopyFormat(), {
    schemaFormat: schemaFormatGetter
  });
  form.genericBuilder = builder;

  var details = document.createElement("details");
  details.className = "admin-dev-mode";
  var summary = document.createElement("summary");
  summary.textContent = "Developer Mode / JSON";
  details.appendChild(summary);
  var useJson = document.createElement("label");
  useJson.className = "admin-dev-toggle";
  var checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.name = "use_json_mode";
  var span = document.createElement("span");
  span.textContent = "JSONを保存に使用する";
  useJson.appendChild(checkbox);
  useJson.appendChild(span);
  details.appendChild(useJson);
  details.appendChild(formField("generic schema JSON", "generic_schema_json", JSON.stringify(schema, null, 2), { textarea: true, rows: 10 }));
  details.appendChild(formField("copy_format JSON", "copy_format_json", JSON.stringify(copyFormat || defaultGenericCopyFormat(), null, 2), { textarea: true, rows: 6 }));
  form.appendChild(details);
  return builder;
}

function syncGenericJsonFromBuilder(form, schemaFormat) {
  if (!form.genericBuilder) return;
  form.elements.generic_schema_json.value = JSON.stringify(form.genericBuilder.collectSchema(schemaFormat), null, 2);
  form.elements.copy_format_json.value = JSON.stringify(form.genericBuilder.collectCopyFormat(), null, 2);
}

function setModalError(message) {
  var el = $("admin-modal-error");
  el.textContent = message || "";
  el.classList.toggle("show", Boolean(message));
}

function warningMessages(warnings) {
  return (warnings || []).map(function(warning) {
    return warning.message || warning;
  });
}

function appendWarnings(parent, warnings) {
  var messages = warningMessages(warnings);
  if (!messages.length) return;
  var box = document.createElement("div");
  box.className = "admin-alert show";
  var title = document.createElement("div");
  title.className = "warn-title";
  title.textContent = "コピー出力に含まれない入力項目があります";
  var list = document.createElement("ul");
  list.className = "warn-list";
  messages.forEach(function(message) {
    var item = document.createElement("li");
    item.textContent = message;
    list.appendChild(item);
  });
  box.appendChild(title);
  box.appendChild(list);
  parent.appendChild(box);
}

function showWarningsToast(warnings) {
  var count = warningMessages(warnings).length;
  if (count) toast("保存しました。未参照フィールド警告 " + count + " 件があります", "#c05621");
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

function formSelect(label, name, value, choices) {
  var wrap = document.createElement("label");
  wrap.className = "admin-field";
  var caption = document.createElement("span");
  caption.textContent = label;
  var select = document.createElement("select");
  select.name = name;
  select.className = "admin-input";
  choices.forEach(function(choice) {
    var option = document.createElement("option");
    option.value = choice.value;
    option.textContent = choice.label;
    select.appendChild(option);
  });
  select.value = value || "";
  wrap.appendChild(caption);
  wrap.appendChild(select);
  return wrap;
}

function collectText(form, name) {
  var el = form.elements[name];
  return el ? el.value.trim() : "";
}

function collectNamedText(root, name) {
  var el = root.querySelector('[name="' + name + '"]');
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
    status.dataset.label = "状態";
    var badge = document.createElement("span");
    badge.className = "admin-status " + (item.is_active ? "active" : "inactive");
    badge.textContent = item.is_active ? "有効" : "削除済み";
    status.appendChild(badge);

    var name = document.createElement("td");
    name.dataset.label = "テンプレート";
    var label = document.createElement("div");
    label.className = "admin-template-label";
    label.textContent = item.label;
    var full = document.createElement("div");
    full.className = "admin-template-full";
    full.textContent = item.full;
    name.appendChild(label);
    name.appendChild(full);

    var category = document.createElement("td");
    category.dataset.label = "分類";
    category.textContent = item.category;
    if (item.schema_format) category.textContent += " / " + schemaFormatLabel(item.schema_format);

    var version = document.createElement("td");
    version.dataset.label = "版";
    version.textContent = item.current_version_number ? "v" + item.current_version_number : "-";

    var updated = document.createElement("td");
    updated.dataset.label = "更新日時";
    updated.textContent = formatDate(item.updated_at);

    var actions = document.createElement("td");
    actions.dataset.label = "操作";
    actions.className = "admin-actions";
    if (item.is_active) {
      actions.appendChild(button("編集", "btn bg admin-row-btn", function(){ openEditModal(item); }));
      actions.appendChild(button("下書きを確認", "btn bg admin-row-btn", function(){ openDraftReviewModal(item); }));
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
  openModal("新しいテンプレート", "似ているテンプレートから作るのがおすすめです");
  renderCreateMethodStep();
}

function renderCreateMethodStep() {
  var body = $("admin-modal-body");
  var actions = $("admin-modal-actions");
  clearNode(body);
  clearNode(actions);
  var wrap = document.createElement("div");
  wrap.className = "simple-choice-grid";
  var cloneCard = document.createElement("button");
  cloneCard.type = "button";
  cloneCard.className = "simple-choice-card recommended";
  cloneCard.innerHTML = "<strong>似ているテンプレートから作る</strong><span>おすすめ</span><small>項目やコピー文を引き継ぎます</small>";
  cloneCard.addEventListener("click", renderCloneStep);
  var blankCard = document.createElement("button");
  blankCard.type = "button";
  blankCard.className = "simple-choice-card";
  blankCard.innerHTML = "<strong>白紙から作る</strong><small>すべて最初から設定します</small>";
  blankCard.addEventListener("click", function() {
    var model = NasukeruSimpleTemplateModel.blankEditorModel();
    model.id = generateTemplateId();
    renderSimpleCreateEditor(model);
  });
  wrap.appendChild(cloneCard);
  wrap.appendChild(blankCard);
  body.appendChild(wrap);
  actions.appendChild(button("閉じる", "btn bg", closeModal));
}

function renderCloneStep() {
  var body = $("admin-modal-body");
  var actions = $("admin-modal-actions");
  clearNode(body);
  clearNode(actions);
  var form = document.createElement("form");
  form.className = "admin-form";
  var choices = adminTemplates.filter(function(item) {
    return item.is_active && item.current_version_id;
  }).map(function(item) {
    return { value: item.id, label: item.label + " / " + item.full };
  });
  if (!choices.length) {
    form.appendChild(elText("div", "admin-empty-cell", "元にできる公開テンプレートがありません。白紙から作成してください。"));
    body.appendChild(form);
    actions.appendChild(button("戻る", "btn bg", renderCreateMethodStep));
    return;
  }
  form.appendChild(formSelect("元にするテンプレート", "source_id", choices[0] && choices[0].value, choices));
  form.appendChild(formField("新しいテンプレート名", "label", ""));
  form.appendChild(formField("正式名称", "full", ""));
  form.appendChild(formField("分類", "category", "neuro"));
  body.appendChild(form);
  actions.appendChild(button("戻る", "btn bg", renderCreateMethodStep));
  actions.appendChild(button("この内容から作成", "btn bp", async function() {
    try {
      var source = await getTemplateDetail(collectText(form, "source_id"));
      var model = NasukeruSimpleTemplateModel.schemaToEditorModel({
        id: generateTemplateId(),
        label: collectText(form, "label") || source.label + " コピー",
        full: collectText(form, "full") || source.full + " コピー",
        category: collectText(form, "category") || source.category,
        schema: source.schema,
        copy_format: source.copy_format,
      });
      renderSimpleCreateEditor(model);
    } catch (error) {
      setModalError(showErrorForApi(error));
    }
  }));
}

function renderSimpleCreateEditor(model) {
  var body = $("admin-modal-body");
  var actions = $("admin-modal-actions");
  clearNode(body);
  clearNode(actions);
  var mount = document.createElement("div");
  body.appendChild(mount);
  var editor = NasukeruAdminSimple.create(mount, model);
  var reason = formField("作成理由", "change_reason", "", { textarea: true, rows: 3 });
  body.appendChild(reason);
  var confirmUnreferencedWrap = document.createElement("label");
  confirmUnreferencedWrap.className = "admin-dev-toggle";
  var confirmUnreferenced = document.createElement("input");
  confirmUnreferenced.type = "checkbox";
  confirmUnreferenced.name = "confirm_unreferenced";
  confirmUnreferencedWrap.appendChild(confirmUnreferenced);
  confirmUnreferencedWrap.appendChild(document.createTextNode("出力に含まれない項目を確認しました"));
  body.appendChild(confirmUnreferencedWrap);
  actions.appendChild(button("閉じる", "btn bg", closeModal));
  actions.appendChild(button("保存", "btn bp", async function() {
    if (!model.label || !model.full || !model.category || !collectNamedText(body, "change_reason")) {
      setModalError("テンプレート名、正式名称、分類、作成理由を入力してください。");
      return;
    }
    try {
      var result = await createTemplate({
        id: model.id || generateTemplateId(),
        label: model.label,
        full: model.full,
        category: model.category,
        schema: editor.collectSchema(),
        copy_format: editor.collectCopyFormat(),
        change_reason: collectNamedText(body, "change_reason"),
        confirm_unreferenced: confirmUnreferenced.checked,
      });
      closeModal();
      await loadAdminTemplates();
      if (result && result.warnings && result.warnings.length) showWarningsToast(result.warnings);
      else toast("テンプレートを追加しました", "#2d7a3a");
    } catch (error) {
      var unreferenced = error.data && error.data.unreferenced_fields;
      if (error.status === 409 && unreferenced && unreferenced.length) {
        setModalError("出力に含まれない項目があります。内容を確認してチェックを入れてください。\n" + unreferencedSummary(unreferenced));
        return;
      }
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

function appendGenericSchemaEditor(form, schema) {
  appendGenericEditor(form, schema, null, function(){ return collectText(form, "schema_format"); });
}

function appendGenericCopyFormatEditor(form, copyFormat) {
  if (form.genericBuilder) {
    form.elements.copy_format_json.value = JSON.stringify(copyFormat || defaultGenericCopyFormat(), null, 2);
  }
}

function collectGenericSchema(form) {
  try {
    if (form.elements.use_json_mode && form.elements.use_json_mode.checked) {
      return JSON.parse(form.elements.generic_schema_json.value);
    }
    var schemaFormat = collectText(form, "schema_format") || "generic-v1";
    syncGenericJsonFromBuilder(form, schemaFormat);
    return form.genericBuilder.collectSchema(schemaFormat);
  } catch (error) {
    throw new Error("generic schema JSONの形式を確認してください。");
  }
}

function collectGenericCopyFormat(form) {
  try {
    if (form.elements.use_json_mode && form.elements.use_json_mode.checked) {
      return JSON.parse(form.elements.copy_format_json.value);
    }
    syncGenericJsonFromBuilder(form, collectText(form, "schema_format") || "generic-v1");
    return form.genericBuilder.collectCopyFormat();
  } catch (error) {
    throw new Error("copy_format JSONの形式を確認してください。");
  }
}

async function openEditModal(item) {
  openModal("テンプレート編集", item.label + " / " + item.full);
  var body = $("admin-modal-body");
  var loading = document.createElement("div");
  loading.className = "admin-empty-cell";
  loading.textContent = "読み込み中";
  body.appendChild(loading);
  try {
    var detail = await getTemplateDetail(item.id);
    var schema = normalizeDetailToSchema(detail);
    var isGeneric = isGenericSchemaFormat(detail.schema_format || schema.schemaFormat || "stroke-v1");
    clearNode(body);
    if (!isGeneric) {
      setModalError("旧形式のテンプレートは履歴確認用です。新しい編集画面では編集できません。");
      return;
    }
    appendWarnings(body, detail.warnings);
    var mount = document.createElement("div");
    body.appendChild(mount);
    var model = NasukeruSimpleTemplateModel.schemaToEditorModel({
      id: item.id,
      label: item.label,
      full: item.full,
      category: item.category,
      schema: schema,
      copy_format: detail.copy_format,
    });
    if (detail.copy_format) model.copyMode = "custom";
    var editor = NasukeruAdminSimple.create(mount, model);
    var metaForm = document.createElement("form");
    metaForm.className = "admin-form";
    metaForm.appendChild(formField("変更概要", "change_summary", "", { textarea: true, rows: 2 }));
    metaForm.appendChild(formField("変更理由", "change_reason", "", { textarea: true, rows: 3 }));
    body.appendChild(metaForm);

    clearNode($("admin-modal-actions"));
    $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
    $("admin-modal-actions").appendChild(button("下書き保存", "btn bp", async function() {
      var summary = collectText(metaForm, "change_summary");
      var reason = collectText(metaForm, "change_reason");
      if (!summary || !reason) {
        setModalError("変更概要と変更理由を入力してください。");
        return;
      }
      try {
        var result = await createTemplateVersion(item.id, {
          base_version_id: detail.current_version_id,
          schema: editor.collectSchema(),
          copy_format: editor.collectCopyFormat(),
          change_summary: summary,
          change_reason: reason
        });
        closeModal();
        await loadAdminTemplates();
        if (result && result.warnings && result.warnings.length) showWarningsToast(result.warnings);
        else toast("下書きバージョンを作成しました", "#2d7a3a");
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

function versionStatusLabel(status, item, version) {
  if (item.current_version_id === version.id) return "公開中";
  if (status === "draft") return "下書き";
  if (status === "published") return "公開";
  if (status === "retired") return "退役";
  return status || "-";
}

function highRiskSummary(changes) {
  return (changes || []).map(function(change) {
    return change.message || change.code;
  }).join("\n");
}

function unreferencedSummary(fields) {
  return (fields || []).map(function(field) {
    return field.message || field.label || field.fieldRef;
  }).join("\n");
}

async function runVersionPublicationAction(item, version, mode) {
  var isPublish = mode === "publish";
  var reason = window.prompt(isPublish ? "公開理由を入力してください" : "復元公開理由を入力してください", "");
  if (!reason || !reason.trim()) return;
  async function submit(confirmHighRisk, confirmUnreferenced) {
    if (isPublish) return publishTemplateVersion(item.id, version.id, reason.trim(), confirmHighRisk, confirmUnreferenced);
    return rollbackTemplateVersion(item.id, version.id, reason.trim(), confirmHighRisk, confirmUnreferenced);
  }
  try {
    await submit(false, false);
  } catch (error) {
    var changes = error.data && error.data.high_risk_changes;
    if (error.status === 409 && changes && changes.length) {
      var ok = window.confirm("高リスク変更があります。確認して続行しますか？\n\n" + highRiskSummary(changes));
      if (!ok) return;
      try {
        await submit(true, false);
      } catch (nextError) {
        var nextUnreferenced = nextError.data && nextError.data.unreferenced_fields;
        if (nextError.status === 409 && nextUnreferenced && nextUnreferenced.length) {
          var okNext = window.confirm("出力に含まれない項目があります。確認して続行しますか？\n\n" + unreferencedSummary(nextUnreferenced));
          if (!okNext) return;
          await submit(true, true);
        } else {
          throw nextError;
        }
      }
    } else if (error.status === 409 && error.data && error.data.unreferenced_fields && error.data.unreferenced_fields.length) {
      var okUnreferenced = window.confirm("出力に含まれない項目があります。確認して続行しますか？\n\n" + unreferencedSummary(error.data.unreferenced_fields));
      if (!okUnreferenced) return;
      await submit(false, true);
    } else {
      throw error;
    }
  }
  closeModal();
  await loadAdminTemplates();
  toast(isPublish ? "バージョンを公開しました" : "復元公開版を作成しました", "#2d7a3a");
}

function versionActionCell(item, version) {
  var wrap = document.createElement("div");
  wrap.className = "admin-actions";
  if (!item.is_active) return wrap;
  if (item.current_version_id !== version.id && version.status !== "draft") {
    wrap.appendChild(button("復元公開", "btn bg admin-row-btn", async function() {
      try {
        await runVersionPublicationAction(item, version, "rollback");
      } catch (error) {
        setModalError(showErrorForApi(error));
      }
    }));
  }
  return wrap;
}

async function openDraftReviewModal(item) {
  openModal("下書きを確認", item.label + " / " + item.full);
  var body = $("admin-modal-body");
  body.appendChild(document.createTextNode("読み込み中"));
  $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
  try {
    var versions = await getTemplateVersions(item.id);
    var draft = versions.find(function(version) { return version.status === "draft"; });
    clearNode(body);
    clearNode($("admin-modal-actions"));
    if (!draft) {
      body.appendChild(elText("div", "admin-empty-cell", "下書きはありません。編集から下書きを保存してください。"));
      $("admin-modal-actions").appendChild(button("閉じる", "btn bg", closeModal));
      return;
    }
    var detail = await getTemplateVersion(item.id, draft.id);
    var section = formSection("下書き v" + draft.version_number);
    section.appendChild(buildSmallTable(["項目", "内容"], [
      ["変更概要", draft.change_summary || ""],
      ["変更理由", draft.change_reason || ""],
      ["作成日時", formatDate(draft.created_at)],
    ]));
    body.appendChild(section);
    appendWarnings(body, detail.warnings);
    var previewSection = formSection("内容確認");
    previewSection.appendChild(renderJsonBlock({
      schema: detail.schema,
      copy_format: detail.copy_format,
    }));
    body.appendChild(previewSection);
    var form = document.createElement("form");
    form.className = "admin-form";
    form.appendChild(formField("公開理由", "reason", draft.change_reason || "", { textarea: true, rows: 3 }));
    var confirmWrap = document.createElement("label");
    confirmWrap.className = "admin-dev-toggle";
    var confirm = document.createElement("input");
    confirm.type = "checkbox";
    confirm.name = "confirm_high_risk";
    confirmWrap.appendChild(confirm);
    confirmWrap.appendChild(document.createTextNode("注意が必要な変更を確認しました"));
    form.appendChild(confirmWrap);
    var confirmUnreferencedWrap = document.createElement("label");
    confirmUnreferencedWrap.className = "admin-dev-toggle";
    var confirmUnreferenced = document.createElement("input");
    confirmUnreferenced.type = "checkbox";
    confirmUnreferenced.name = "confirm_unreferenced";
    confirmUnreferencedWrap.appendChild(confirmUnreferenced);
    confirmUnreferencedWrap.appendChild(document.createTextNode("出力に含まれない項目を確認しました"));
    form.appendChild(confirmUnreferencedWrap);
    body.appendChild(form);
    $("admin-modal-actions").appendChild(button("編集に戻る", "btn bg", function(){ openEditModal(item); }));
    $("admin-modal-actions").appendChild(button("公開する", "btn bp", async function() {
      var reason = collectText(form, "reason");
      if (!reason) {
        setModalError("公開理由を入力してください。");
        return;
      }
      try {
        await publishTemplateVersion(item.id, draft.id, reason, confirm.checked, confirmUnreferenced.checked);
        closeModal();
        await loadAdminTemplates();
        toast("下書きを公開しました", "#2d7a3a");
      } catch (error) {
        var changes = error.data && error.data.high_risk_changes;
        if (error.status === 409 && changes && changes.length) {
          setModalError("注意が必要な変更があります。内容を確認してチェックを入れてください。\n" + highRiskSummary(changes));
          return;
        }
        var unreferenced = error.data && error.data.unreferenced_fields;
        if (error.status === 409 && unreferenced && unreferenced.length) {
          setModalError("出力に含まれない項目があります。内容を確認してチェックを入れてください。\n" + unreferencedSummary(unreferenced));
          return;
        }
        setModalError(showErrorForApi(error));
      }
    }));
  } catch (error) {
    clearNode(body);
    setModalError(showErrorForApi(error));
  }
}

function elText(tag, className, text) {
  var node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = text;
  return node;
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
          appendWarnings(detailBox, detail.warnings);
          detailBox.appendChild(renderJsonBlock({
            schema: detail.schema,
            copy_format: detail.copy_format
          }));
        } catch (error) {
          detailBox.textContent = showErrorForApi(error);
        }
      });
      return [
        "v" + version.version_number,
        versionStatusLabel(version.status, item, version),
        version.change_summary || "",
        version.change_reason || "",
        formatDate(version.created_at),
        detailBtn,
        versionActionCell(item, version)
      ];
    });
    var versionSection = formSection("バージョン履歴");
    versionSection.appendChild(buildSmallTable(["版", "状態", "概要", "理由", "作成日時", "詳細", "操作"], versionRows));
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

function cloneDiscovery(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function publishedTemplateOptions(discovery) {
  return (discovery.templates || []).filter(function(template) {
    return template.is_active && template.current_version_id;
  }).map(function(template) {
    return { value: template.id, label: template.label + " / " + template.full };
  });
}

function activeGroupOptions(discovery) {
  return (discovery.template_groups || []).filter(function(group) {
    return group.is_active !== false;
  }).map(function(group) {
    return { value: group.id, label: group.label + " / " + group.id };
  });
}

function targetOptions(discovery, type) {
  return type === "group" ? activeGroupOptions(discovery) : publishedTemplateOptions(discovery);
}

function normalizeTarget(item) {
  item.target = item.target && typeof item.target === "object" ? item.target : { type: "template", id: "" };
  item.target.type = item.target.type === "group" ? "group" : "template";
  item.target.id = item.target.id || "";
  return item.target;
}

function renderTargetControls(discovery, item, refresh) {
  var target = normalizeTarget(item);
  var wrap = document.createElement("div");
  wrap.className = "admin-discovery-target";
  var type = formSelect("対象種別", "target_type", target.type, [
    { value: "template", label: "テンプレート" },
    { value: "group", label: "グループ" },
  ]);
  type.querySelector("select").addEventListener("change", function(event) {
    target.type = event.target.value;
    var choices = targetOptions(discovery, target.type);
    target.id = choices[0] ? choices[0].value : "";
    refresh();
  });
  var choices = targetOptions(discovery, target.type);
  if (!choices.some(function(choice) { return choice.value === target.id; }) && choices[0]) {
    target.id = choices[0].value;
  }
  var id = formSelect("対象", "target_id", target.id, choices.length ? choices : [{ value: "", label: "対象なし" }]);
  id.querySelector("select").addEventListener("change", function(event) {
    target.id = event.target.value;
  });
  wrap.appendChild(type);
  wrap.appendChild(id);
  return wrap;
}

function discoveryTextField(label, value, onInput) {
  var field = formField(label, "", value || "");
  var inputNode = field.querySelector(".admin-input");
  inputNode.addEventListener("input", function() { onInput(inputNode.value); });
  return field;
}

function renderDiscoveryQuickRow(discovery, item, index, refresh) {
  var card = document.createElement("div");
  card.className = "simple-section-card";
  card.appendChild(discoveryTextField("表示名", item.label, function(value) { item.label = value; }));
  card.appendChild(discoveryTextField("補足", item.sub, function(value) { item.sub = value; }));
  card.appendChild(discoveryTextField("互換キー", item.action, function(value) { item.action = value; }));
  card.appendChild(renderTargetControls(discovery, item, refresh));
  card.appendChild(button("削除", "btn bg admin-row-btn danger", function() {
    discovery.quick_templates.splice(index, 1);
    refresh();
  }));
  return card;
}

function renderDiscoveryKeywordRow(discovery, item, index, refresh) {
  var card = document.createElement("div");
  card.className = "simple-section-card";
  card.appendChild(discoveryTextField("検索語", item.keyword, function(value) { item.keyword = value; }));
  card.appendChild(discoveryTextField("互換キー", item.template_action, function(value) { item.template_action = value; }));
  card.appendChild(renderTargetControls(discovery, item, refresh));
  card.appendChild(button("削除", "btn bg admin-row-btn danger", function() {
    discovery.search_keywords.splice(index, 1);
    refresh();
  }));
  return card;
}

function renderGroupItems(discovery, group) {
  var choices = publishedTemplateOptions(discovery);
  var selectNode = document.createElement("select");
  selectNode.className = "admin-input";
  selectNode.multiple = true;
  choices.forEach(function(choice) {
    var option = document.createElement("option");
    option.value = choice.value;
    option.textContent = choice.label;
    option.selected = (group.items || []).indexOf(choice.value) >= 0;
    selectNode.appendChild(option);
  });
  selectNode.addEventListener("change", function() {
    group.items = Array.prototype.slice.call(selectNode.selectedOptions).map(function(option) {
      return option.value;
    });
  });
  return rowLike("テンプレート", selectNode);
}

function rowLike(label, control) {
  var wrap = document.createElement("label");
  wrap.className = "admin-field";
  var caption = document.createElement("span");
  caption.textContent = label;
  wrap.appendChild(caption);
  wrap.appendChild(control);
  return wrap;
}

function renderDiscoveryGroupRow(discovery, group, index, refresh) {
  var card = document.createElement("div");
  card.className = "simple-section-card";
  card.appendChild(discoveryTextField("ID", group.id, function(value) { group.id = value; }));
  card.appendChild(discoveryTextField("表示名", group.label, function(value) { group.label = value; }));
  card.appendChild(discoveryTextField("補足", group.sub, function(value) { group.sub = value; }));
  var active = document.createElement("input");
  active.type = "checkbox";
  active.checked = group.is_active !== false;
  active.addEventListener("change", function() {
    group.is_active = active.checked;
    refresh();
  });
  card.appendChild(rowLike("有効", active));
  card.appendChild(renderGroupItems(discovery, group));
  card.appendChild(button("削除", "btn bg admin-row-btn danger", function() {
    discovery.template_groups.splice(index, 1);
    refresh();
  }));
  return card;
}

function renderDiscoverySection(title, items, addLabel, onAdd, renderRow, discovery, refresh) {
  var section = formSection(title);
  items.forEach(function(item, index) {
    section.appendChild(renderRow(discovery, item, index, refresh));
  });
  section.appendChild(button(addLabel, "btn bg", function() {
    onAdd();
    refresh();
  }));
  return section;
}

async function openDiscoveryModal() {
  openModal("検索・導線設定", "検索語、クイックテンプレート、グループを管理します");
  var body = $("admin-modal-body");
  var actions = $("admin-modal-actions");
  body.appendChild(document.createTextNode("読み込み中"));
  actions.appendChild(button("閉じる", "btn bg", closeModal));
  try {
    var discovery = cloneDiscovery(await getAdminDiscovery());
    function refresh() {
      clearNode(body);
      clearNode(actions);
      body.appendChild(renderDiscoverySection(
        "クイックテンプレート",
        discovery.quick_templates,
        "クイックテンプレートを追加",
        function() {
          var choices = publishedTemplateOptions(discovery);
          discovery.quick_templates.push({
            label: "",
            sub: "",
            action: "",
            target: { type: "template", id: choices[0] ? choices[0].value : "" },
          });
        },
        renderDiscoveryQuickRow,
        discovery,
        refresh
      ));
      body.appendChild(renderDiscoverySection(
        "検索キーワード",
        discovery.search_keywords,
        "検索語を追加",
        function() {
          var choices = publishedTemplateOptions(discovery);
          discovery.search_keywords.push({
            keyword: "",
            template_action: "",
            target: { type: "template", id: choices[0] ? choices[0].value : "" },
          });
        },
        renderDiscoveryKeywordRow,
        discovery,
        refresh
      ));
      body.appendChild(renderDiscoverySection(
        "テンプレートグループ",
        discovery.template_groups,
        "グループを追加",
        function() {
          discovery.template_groups.push({
            id: "",
            label: "",
            sub: "",
            is_active: true,
            items: [],
          });
        },
        renderDiscoveryGroupRow,
        discovery,
        refresh
      ));
      actions.appendChild(button("閉じる", "btn bg", closeModal));
      actions.appendChild(button("保存", "btn bp", async function() {
        try {
          await saveAdminTemplateGroups(discovery.template_groups);
          await saveAdminQuickTemplates(discovery.quick_templates);
          await saveAdminSearchKeywords(discovery.search_keywords);
          closeModal();
          toast("検索・導線設定を保存しました", "#2d7a3a");
        } catch (error) {
          setModalError(showErrorForApi(error));
        }
      }));
    }
    refresh();
  } catch (error) {
    clearNode(body);
    setModalError(showErrorForApi(error));
  }
}

function initAdminEvents() {
  $("new-template-btn").addEventListener("click", openCreateModal);
  $("open-discovery-btn").addEventListener("click", openDiscoveryModal);
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
