(function(root, factory) {
  root.NasukeruAdminSimple = factory(
    root.NasukeruSimpleTemplateModel,
    root.NasukeruGenericValues,
    root.NasukeruCopyRenderer,
    root.NasukeruSafetyRules
  );
})(typeof globalThis !== "undefined" ? globalThis : this, function(modelApi, genericValues, copyRenderer, safetyRules) {
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function input(value, className, type) {
    var node = document.createElement("input");
    node.type = type || "text";
    node.className = "admin-input " + (className || "");
    node.value = value == null ? "" : String(value);
    return node;
  }

  function textarea(value) {
    var node = document.createElement("textarea");
    node.className = "admin-input";
    node.rows = 3;
    node.value = value || "";
    return node;
  }

  function select(value, choices) {
    var node = document.createElement("select");
    node.className = "admin-input";
    choices.forEach(function(choice) {
      var option = document.createElement("option");
      option.value = choice.value;
      option.textContent = choice.label;
      node.appendChild(option);
    });
    node.value = value || choices[0].value;
    return node;
  }

  function row(label, control) {
    var wrap = el("label", "simple-field");
    wrap.appendChild(el("span", "", label));
    wrap.appendChild(control);
    return wrap;
  }

  function moveItem(items, index, delta) {
    var next = index + delta;
    if (next < 0 || next >= items.length) return;
    var item = items[index];
    items.splice(index, 1);
    items.splice(next, 0, item);
  }

  function makePreviewInput(section, field) {
    var wrap = el("label", "simple-preview-field");
    wrap.appendChild(el("span", "", field.label));
    var control;
    if (field.type === "textarea") {
      control = document.createElement("textarea");
      control.rows = 2;
    } else if (field.type === "select") {
      control = document.createElement("select");
      control.appendChild(new Option("", ""));
      (field.options || []).forEach(function(option) {
        control.appendChild(new Option(option.label || option.value, option.value));
      });
    } else if (field.type === "multi_select") {
      control = input("", "", "text");
      control.placeholder = "複数選択は「、」区切り";
    } else {
      control = input("", "", "text");
      if (field.type === "number") control.inputMode = "decimal";
    }
    control.className = "admin-input generic-input";
    control.dataset.sectionId = section.id;
    control.dataset.sectionLabel = section.label;
    control.dataset.fieldId = field.id;
    control.dataset.fieldLabel = field.label;
    control.dataset.fieldType = field.type || "text";
    control.dataset.blankPolicy = field.blankPolicy || "";
    control.genericOptionLabels = {};
    (field.options || []).forEach(function(option) {
      control.genericOptionLabels[option.value] = option.label || option.value;
    });
    wrap.appendChild(control);
    if (field.unit) wrap.appendChild(el("small", "", field.unit));
    return wrap;
  }

  function formatValuesForCopy(container) {
    var displayValues = {};
    container.querySelectorAll(".generic-input").forEach(function(inputNode) {
      var ref = genericValues.fieldRef(inputNode);
      var typed = genericValues.parseInputValue(inputNode);
      displayValues[ref] = genericValues.formatInputValueForCopy(inputNode, typed);
    });
    return displayValues;
  }

  function create(container, initialModel, options) {
    options = options || {};
    var model = initialModel || modelApi.blankEditorModel();
    var root = el("div", "simple-editor");
    container.appendChild(root);

    function refresh() {
      root.innerHTML = "";
      renderBasics();
      renderSections();
      renderCopySettings();
      renderPreview();
      renderDeveloperMode();
    }

    function renderBasics() {
      var section = el("section", "simple-panel");
      section.appendChild(el("h3", "", "基本情報"));
      var labelInput = input(model.label);
      labelInput.addEventListener("input", function() { model.label = labelInput.value; });
      section.appendChild(row("テンプレート名", labelInput));
      var fullInput = input(model.full);
      fullInput.addEventListener("input", function() { model.full = fullInput.value; });
      section.appendChild(row("正式名称", fullInput));
      var categoryInput = input(model.category);
      categoryInput.addEventListener("input", function() { model.category = categoryInput.value; });
      section.appendChild(row("分類", categoryInput));
      root.appendChild(section);
    }

    function renderSections() {
      var section = el("section", "simple-panel");
      var head = el("div", "simple-panel-head");
      head.appendChild(el("h3", "", "入力項目"));
      var add = el("button", "btn bg admin-row-btn", "セクションを追加");
      add.type = "button";
      add.addEventListener("click", function() {
        modelApi.addSection(model);
        refresh();
      });
      head.appendChild(add);
      section.appendChild(head);
      model.sections.forEach(function(item, sectionIndex) {
        section.appendChild(renderSection(item, sectionIndex));
      });
      root.appendChild(section);
    }

    function renderSection(sectionModel, sectionIndex) {
      var card = el("div", "simple-section-card");
      var sectionName = input(sectionModel.label);
      sectionName.addEventListener("input", function() { sectionModel.label = sectionName.value; });
      var top = el("div", "simple-row-head");
      top.appendChild(sectionName);
      [["上へ", -1], ["下へ", 1]].forEach(function(pair) {
        var btn = el("button", "btn bg admin-row-btn", pair[0]);
        btn.type = "button";
        btn.addEventListener("click", function() {
          moveItem(model.sections, sectionIndex, pair[1]);
          refresh();
        });
        top.appendChild(btn);
      });
      var remove = el("button", "btn bg admin-row-btn danger", "削除");
      remove.type = "button";
      remove.addEventListener("click", function() {
        model.sections.splice(sectionIndex, 1);
        refresh();
      });
      top.appendChild(remove);
      card.appendChild(top);

      var style = select(sectionModel.copyStyle || "stacked", [
        { value: "stacked", label: "項目ごとに1行で出力" },
        { value: "inline", label: "1行にまとめて出力" },
      ]);
      style.addEventListener("change", function() {
        sectionModel.copyStyle = style.value;
        refresh();
      });
      card.appendChild(row("コピー文での出し方", style));

      sectionModel.fields.forEach(function(field, fieldIndex) {
        card.appendChild(renderField(sectionModel, field, fieldIndex));
      });
      var addField = el("button", "btn bg", "項目を追加");
      addField.type = "button";
      addField.addEventListener("click", function() {
        modelApi.addField(sectionModel);
        refresh();
      });
      card.appendChild(addField);
      return card;
    }

    function renderField(sectionModel, field, fieldIndex) {
      var details = document.createElement("details");
      details.className = "simple-field-card";
      var summary = document.createElement("summary");
      summary.textContent = field.label + "　" + (modelApi.FIELD_TYPES[field.type] || field.type) + "　" + (modelApi.BLANK_POLICIES[field.blankPolicy] || "未入力でも問題なし");
      details.appendChild(summary);
      var grid = el("div", "simple-grid");
      var labelInput = input(field.label);
      labelInput.addEventListener("input", function() { field.label = labelInput.value; });
      labelInput.addEventListener("change", refresh);
      grid.appendChild(row("項目名", labelInput));
      var typeSelect = select(field.type || "text", Object.keys(modelApi.FIELD_TYPES).map(function(key) {
        return { value: key, label: modelApi.FIELD_TYPES[key] };
      }));
      typeSelect.addEventListener("change", function() {
        field.type = typeSelect.value;
        if (field.type !== "select" && field.type !== "multi_select") field.options = [];
        refresh();
      });
      grid.appendChild(row("入力方法", typeSelect));
      var unitInput = input(field.unit || "");
      unitInput.addEventListener("input", function() { field.unit = unitInput.value; });
      grid.appendChild(row("単位", unitInput));
      var policySelect = select(field.blankPolicy || "allow", Object.keys(modelApi.BLANK_POLICIES).map(function(key) {
        return { value: key, label: modelApi.BLANK_POLICIES[key] };
      }));
      policySelect.addEventListener("change", function() { field.blankPolicy = policySelect.value; });
      grid.appendChild(row("未入力の場合", policySelect));
      var copyCheck = document.createElement("input");
      copyCheck.type = "checkbox";
      copyCheck.checked = field.includeInCopy !== false;
      copyCheck.addEventListener("change", function() { field.includeInCopy = copyCheck.checked; refresh(); });
      var copyWrap = row("コピー文に含める", copyCheck);
      grid.appendChild(copyWrap);
      var placeholderInput = input(field.placeholder || "");
      placeholderInput.addEventListener("input", function() { field.placeholder = placeholderInput.value; });
      grid.appendChild(row("入力例", placeholderInput));
      var helpInput = textarea(field.helpText || "");
      helpInput.addEventListener("input", function() { field.helpText = helpInput.value; });
      grid.appendChild(row("補足説明", helpInput));
      if (field.type === "select" || field.type === "multi_select") {
        grid.appendChild(renderOptions(field));
      }
      if (field.type === "number") {
        grid.appendChild(renderRange(field, "hardRange", "範囲外ではコピーできない"));
        grid.appendChild(renderRange(field, "warningRange", "注意が必要な範囲"));
      }
      details.appendChild(grid);
      var actions = el("div", "simple-inline-actions");
      [["上へ", -1], ["下へ", 1]].forEach(function(pair) {
        var btn = el("button", "btn bg admin-row-btn", pair[0]);
        btn.type = "button";
        btn.addEventListener("click", function() {
          moveItem(sectionModel.fields, fieldIndex, pair[1]);
          refresh();
        });
        actions.appendChild(btn);
      });
      var remove = el("button", "btn bg admin-row-btn danger", "削除");
      remove.type = "button";
      remove.addEventListener("click", function() {
        sectionModel.fields.splice(fieldIndex, 1);
        refresh();
      });
      actions.appendChild(remove);
      details.appendChild(actions);
      return details;
    }

    function renderOptions(field) {
      var wrap = el("div", "simple-options");
      wrap.appendChild(el("span", "", "選択肢"));
      (field.options || []).forEach(function(option, index) {
        var line = el("div", "simple-option-row");
        var optionInput = input(option.label || option.value || "");
        optionInput.addEventListener("input", function() {
          option.label = optionInput.value;
          if (!option.value) option.value = modelApi.randomId("opt");
        });
        line.appendChild(optionInput);
        [["↑", -1], ["↓", 1]].forEach(function(pair) {
          var btn = el("button", "btn bg admin-row-btn", pair[0]);
          btn.type = "button";
          btn.addEventListener("click", function() { moveItem(field.options, index, pair[1]); refresh(); });
          line.appendChild(btn);
        });
        var del = el("button", "btn bg admin-row-btn danger", "削除");
        del.type = "button";
        del.addEventListener("click", function() { field.options.splice(index, 1); refresh(); });
        line.appendChild(del);
        wrap.appendChild(line);
      });
      var add = el("button", "btn bg admin-row-btn", "選択肢を追加");
      add.type = "button";
      add.addEventListener("click", function() {
        field.options = field.options || [];
        field.options.push({ value: modelApi.randomId("opt"), label: "新しい選択肢" });
        refresh();
      });
      wrap.appendChild(add);
      return wrap;
    }

    function renderRange(field, key, label) {
      var wrap = el("div", "simple-range");
      var check = document.createElement("input");
      check.type = "checkbox";
      check.checked = Boolean(field[key]);
      wrap.appendChild(row(label, check));
      var min = input(field[key] && field[key].min, "", "number");
      var max = input(field[key] && field[key].max, "", "number");
      function update() {
        if (!check.checked) {
          delete field[key];
          return;
        }
        field[key] = {};
        if (min.value !== "") field[key].min = Number(min.value);
        if (max.value !== "") field[key].max = Number(max.value);
      }
      check.addEventListener("change", update);
      min.addEventListener("input", update);
      max.addEventListener("input", update);
      wrap.appendChild(row("下限", min));
      wrap.appendChild(row("上限", max));
      return wrap;
    }

    function renderCopySettings() {
      var section = el("section", "simple-panel");
      section.appendChild(el("h3", "", "コピー文"));
      var mode = select(model.copyMode || "auto", [
        { value: "auto", label: "入力項目から自動で作る" },
        { value: "custom", label: "詳細に編集する" },
      ]);
      mode.addEventListener("change", function() {
        model.copyMode = mode.value;
        refresh();
      });
      section.appendChild(row("作り方", mode));
      if (model.copyMode === "custom") {
        section.appendChild(el("p", "simple-note", "詳細編集は下の開発者向け編集で確認できます。通常編集では内容を保持します。"));
      }
      root.appendChild(section);
    }

    function renderPreview() {
      var schema = modelApi.editorModelToSchema(model);
      var copyFormat = modelApi.editorModelToCopyFormat(model);
      var section = el("section", "simple-panel");
      section.appendChild(el("h3", "", "プレビュー"));
      var grid = el("div", "simple-preview-grid");
      var formSide = el("div", "simple-preview-box");
      formSide.appendChild(el("h4", "", "実際の入力画面"));
      schema.sections.forEach(function(sectionModel) {
        formSide.appendChild(el("div", "simple-preview-section", sectionModel.label));
        sectionModel.fields.forEach(function(field) {
          formSide.appendChild(makePreviewInput(sectionModel, field));
        });
      });
      var copySide = el("div", "simple-preview-box");
      copySide.appendChild(el("h4", "", "コピー文"));
      var pre = el("pre", "admin-json simple-copy-preview");
      copySide.appendChild(pre);
      function updatePreview() {
        var values = formatValuesForCopy(formSide);
        var result = copyRenderer.renderGenericTemplateCopyResult(copyFormat, values, values);
        pre.textContent = result.text;
      }
      formSide.addEventListener("input", updatePreview);
      formSide.addEventListener("change", updatePreview);
      updatePreview();
      grid.appendChild(formSide);
      grid.appendChild(copySide);
      section.appendChild(grid);
      root.appendChild(section);
    }

    function renderDeveloperMode() {
      var schema = modelApi.editorModelToSchema(model);
      var copyFormat = modelApi.editorModelToCopyFormat(model);
      var details = document.createElement("details");
      details.className = "admin-dev-mode";
      var summary = document.createElement("summary");
      summary.textContent = "開発者向け編集";
      details.appendChild(summary);
      details.appendChild(el("p", "simple-note", "JSONや詳細なcopy formatは調査用です。通常は編集しません。"));
      var pre = el("pre", "admin-json");
      pre.textContent = JSON.stringify({ schema: schema, copy_format: copyFormat }, null, 2);
      details.appendChild(pre);
      root.appendChild(details);
    }

    refresh();
    return {
      element: root,
      model: model,
      collectSchema: function() { return modelApi.editorModelToSchema(model); },
      collectCopyFormat: function() { return modelApi.editorModelToCopyFormat(model); },
    };
  }

  return {
    create: create,
  };
});
