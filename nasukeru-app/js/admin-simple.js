(function(root, factory) {
  root.NasukeruAdminSimple = factory(
    root.NasukeruSimpleTemplateModel,
    root.NasukeruGenericRenderer,
    root.NasukeruCopyRenderer,
    root.NasukeruSafetyRules
  );
})(typeof globalThis !== "undefined" ? globalThis : this, function(modelApi, genericRenderer, copyRenderer, safetyRules) {
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

  function create(container, initialModel, options) {
    options = options || {};
    var model = initialModel || modelApi.blankEditorModel();
    var root = el("div", "simple-editor");
    container.appendChild(root);

    function currentGeneratedSchema() {
      return modelApi.editorModelToSchema(model);
    }

    function currentGeneratedCopyFormat() {
      return modelApi.editorModelToCopyFormat(model);
    }

    function prettyJson(value) {
      return JSON.stringify(value, null, 2);
    }

    function syncDeveloperJsonFromForm() {
      model.developerSchemaJson = prettyJson(currentGeneratedSchema());
      model.developerCopyFormatJson = prettyJson(currentGeneratedCopyFormat());
    }

    function ensureDeveloperJson() {
      if (!model.developerSchemaJson) model.developerSchemaJson = prettyJson(currentGeneratedSchema());
      if (!model.developerCopyFormatJson) model.developerCopyFormatJson = prettyJson(currentGeneratedCopyFormat());
    }

    function parseDeveloperJsonText(text, label) {
      try {
        return JSON.parse(text);
      } catch (error) {
        throw new Error(label + " JSONの形式を確認してください");
      }
    }

    function collectEditorSchema() {
      if (model.useDeveloperJson) {
        return parseDeveloperJsonText(model.developerSchemaJson, "schema");
      }
      return currentGeneratedSchema();
    }

    function collectEditorCopyFormat() {
      if (model.useDeveloperJson) {
        return parseDeveloperJsonText(model.developerCopyFormatJson, "copy_format");
      }
      return currentGeneratedCopyFormat();
    }

    function refresh() {
      root.innerHTML = "";
      renderBasics();
      renderSections();
      renderCopySettings();
      renderPreview();
      renderDeveloperMode();
    }

    function fieldRef(sectionModel, field) {
      return sectionModel.id + "." + field.id;
    }

    function fieldChoices() {
      var choices = [];
      model.sections.forEach(function(sectionModel) {
        (sectionModel.fields || []).forEach(function(field) {
          choices.push({
            value: fieldRef(sectionModel, field),
            label: (sectionModel.label || sectionModel.id) + " / " + (field.label || field.id),
            type: field.type || "text",
            options: field.options || [],
          });
        });
      });
      return choices;
    }

    function fieldMeta(ref) {
      return fieldChoices().find(function(choice) { return choice.value === ref; }) || null;
    }

    function opsForType(type) {
      if (type === "number") {
        return [
          { value: "eq", label: "等しい" },
          { value: "neq", label: "等しくない" },
          { value: "gt", label: "より大きい" },
          { value: "gte", label: "以上" },
          { value: "lt", label: "より小さい" },
          { value: "lte", label: "以下" },
          { value: "is_blank", label: "空欄" },
        ];
      }
      if (type === "select") {
        return [
          { value: "eq", label: "等しい" },
          { value: "neq", label: "等しくない" },
          { value: "in", label: "いずれか" },
          { value: "not_in", label: "いずれでもない" },
          { value: "is_blank", label: "空欄" },
        ];
      }
      if (type === "multi_select") {
        return [
          { value: "contains", label: "含む" },
          { value: "is_blank", label: "空欄" },
        ];
      }
      return [
        { value: "eq", label: "等しい" },
        { value: "neq", label: "等しくない" },
        { value: "is_blank", label: "空欄" },
      ];
    }

    function defaultFieldCondition() {
      var choices = fieldChoices();
      var first = choices[0];
      if (!first) return null;
      var op = opsForType(first.type)[0].value;
      return op === "is_blank" ? { op: op, field: first.value } : { op: op, field: first.value, value: "" };
    }

    function conditionKind(condition) {
      if (!condition) return "none";
      if (condition.op === "and" || condition.op === "or" || condition.op === "not") return condition.op;
      return "field";
    }

    function normalizeConditionValue(condition, meta) {
      if (!condition || condition.op === "is_blank") {
        if (condition) delete condition.value;
        return;
      }
      if (condition.op === "in" || condition.op === "not_in") {
        if (!Array.isArray(condition.value)) condition.value = condition.value ? [condition.value] : [];
        return;
      }
      if (meta && meta.type === "number") {
        var numeric = Number(condition.value);
        condition.value = Number.isFinite(numeric) ? numeric : "";
      } else if (Array.isArray(condition.value)) {
        condition.value = condition.value[0] || "";
      }
    }

    function replaceCondition(target, key, next) {
      if (next) target[key] = next;
      else delete target[key];
      refresh();
    }

    function conditionValueControl(condition, meta, onChange) {
      if (!condition || condition.op === "is_blank") {
        var disabled = input("", "", "text");
        disabled.disabled = true;
        return disabled;
      }
      if (meta && (meta.type === "select" || meta.type === "multi_select")) {
        if (condition.op === "in" || condition.op === "not_in") {
          var multi = document.createElement("select");
          multi.className = "admin-input";
          multi.multiple = true;
          (meta.options || []).forEach(function(optionModel) {
            var opt = document.createElement("option");
            opt.value = optionModel.value;
            opt.textContent = optionModel.label || optionModel.value;
            opt.selected = Array.isArray(condition.value) && condition.value.indexOf(optionModel.value) >= 0;
            multi.appendChild(opt);
          });
          multi.addEventListener("change", function() {
            condition.value = Array.prototype.slice.call(multi.selectedOptions).map(function(opt) { return opt.value; });
            onChange();
          });
          return multi;
        }
        var optionSelect = select(condition.value, [{ value: "", label: "値を選択" }].concat(meta.options || []));
        optionSelect.addEventListener("change", function() {
          condition.value = optionSelect.value;
          onChange();
        });
        return optionSelect;
      }
      var valueInput = input(condition.value, "", meta && meta.type === "number" ? "number" : "text");
      valueInput.addEventListener("change", function() {
        condition.value = valueInput.value;
        normalizeConditionValue(condition, meta);
        onChange();
      });
      return valueInput;
    }

    function renderConditionNode(condition, onChange, depth) {
      depth = depth || 0;
      var wrap = el("div", "simple-condition-node");
      var kind = conditionKind(condition);
      var kindSelect = select(kind, [
        { value: "none", label: "条件なし" },
        { value: "field", label: "項目条件" },
        { value: "and", label: "すべて満たす" },
        { value: "or", label: "いずれかを満たす" },
        { value: "not", label: "満たさない" },
      ]);
      kindSelect.addEventListener("change", function() {
        if (kindSelect.value === "none") onChange(null);
        else if (kindSelect.value === "field") onChange(defaultFieldCondition());
        else if (kindSelect.value === "not") onChange({ op: "not", condition: defaultFieldCondition() });
        else onChange({ op: kindSelect.value, conditions: [defaultFieldCondition()].filter(Boolean) });
      });
      wrap.appendChild(kindSelect);
      if (!condition || kind === "none") return wrap;

      if (kind === "field") {
        var choices = fieldChoices();
        var fieldSelect = select(condition.field, choices.length ? choices : [{ value: "", label: "項目なし" }]);
        fieldSelect.addEventListener("change", function() {
          condition.field = fieldSelect.value;
          var meta = fieldMeta(condition.field);
          var ops = opsForType(meta && meta.type);
          if (!ops.some(function(item) { return item.value === condition.op; })) condition.op = ops[0].value;
          normalizeConditionValue(condition, meta);
          onChange(condition);
        });
        wrap.appendChild(fieldSelect);
        var meta = fieldMeta(condition.field);
        var opSelect = select(condition.op, opsForType(meta && meta.type));
        opSelect.addEventListener("change", function() {
          condition.op = opSelect.value;
          normalizeConditionValue(condition, meta);
          onChange(condition);
        });
        wrap.appendChild(opSelect);
        wrap.appendChild(conditionValueControl(condition, meta, function() { onChange(condition); }));
        return wrap;
      }

      if (kind === "not") {
        wrap.appendChild(renderConditionNode(condition.condition || null, function(next) {
          condition.condition = next || defaultFieldCondition();
          onChange(condition);
        }, depth + 1));
        return wrap;
      }

      var children = Array.isArray(condition.conditions) ? condition.conditions : [];
      var childBox = el("div", "simple-condition-children");
      children.forEach(function(child, index) {
        var line = el("div", "simple-condition-child");
        line.appendChild(renderConditionNode(child, function(next) {
          if (next) children[index] = next;
          else children.splice(index, 1);
          condition.conditions = children;
          onChange(condition);
        }, depth + 1));
        var remove = el("button", "btn bg admin-row-btn danger", "削除");
        remove.type = "button";
        remove.addEventListener("click", function() {
          children.splice(index, 1);
          condition.conditions = children;
          onChange(condition);
        });
        line.appendChild(remove);
        childBox.appendChild(line);
      });
      wrap.appendChild(childBox);
      if (depth < 9) {
        var add = el("button", "btn bg admin-row-btn", "条件を追加");
        add.type = "button";
        add.addEventListener("click", function() {
          children.push(defaultFieldCondition());
          condition.conditions = children.filter(Boolean);
          onChange(condition);
        });
        wrap.appendChild(add);
      }
      return wrap;
    }

    function conditionEditor(label, condition, onChange) {
      var details = document.createElement("details");
      details.className = "simple-condition-editor";
      var summary = document.createElement("summary");
      summary.textContent = label;
      details.appendChild(summary);
      details.appendChild(renderConditionNode(condition || null, onChange, 0));
      return details;
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
      card.appendChild(conditionEditor("セクションの表示条件", sectionModel.visibleIf, function(next) {
        replaceCondition(sectionModel, "visibleIf", next);
      }));

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
      var shell = el("div", "simple-field-shell");
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
      details.appendChild(conditionEditor("表示条件", field.visibleIf, function(next) {
        replaceCondition(field, "visibleIf", next);
      }));
      details.appendChild(conditionEditor("必須条件", field.requiredIf, function(next) {
        replaceCondition(field, "requiredIf", next);
      }));
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
      details.appendChild(actions);

      var quickRemove = el("button", "btn bg admin-row-btn danger simple-field-quick-delete", "削除");
      quickRemove.type = "button";
      quickRemove.setAttribute("aria-label", (field.label || "項目") + "を削除");
      quickRemove.addEventListener("click", function() {
        sectionModel.fields.splice(fieldIndex, 1);
        refresh();
      });
      shell.appendChild(details);
      shell.appendChild(quickRemove);
      return shell;
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
      var section = el("section", "simple-panel");
      section.appendChild(el("h3", "", "プレビュー"));
      var grid = el("div", "simple-preview-grid");
      var formSide = el("div", "simple-preview-box");
      formSide.appendChild(el("h4", "", "実際の入力画面"));
      var copySide = el("div", "simple-preview-box");
      copySide.appendChild(el("h4", "", "コピー文"));
      var pre = el("pre", "admin-json simple-copy-preview");
      copySide.appendChild(pre);
      var schema;
      var copyFormat;
      try {
        schema = collectEditorSchema();
        copyFormat = collectEditorCopyFormat();
        genericRenderer.renderGenericBody(formSide, schema);
      } catch (error) {
        formSide.appendChild(el("div", "admin-alert show", error.message));
        pre.textContent = "";
        grid.appendChild(formSide);
        grid.appendChild(copySide);
        section.appendChild(grid);
        root.appendChild(section);
        return;
      }
      function updatePreview() {
        genericRenderer.updateConditions(formSide);
        var values = genericRenderer.collectCopyValues(formSide);
        var conditionValues = genericRenderer.collectConditionValues(formSide);
        if (!copyFormat || (copyFormat.format !== "text-v1" && copyFormat.format !== "multi-v1")) {
          pre.textContent = "";
          return;
        }
        try {
          var result = copyRenderer.renderGenericTemplateCopyResult(copyFormat, values, conditionValues);
          pre.textContent = result.text;
        } catch (error) {
          pre.textContent = error.message;
        }
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
      if (!model.useDeveloperJson) syncDeveloperJsonFromForm();
      ensureDeveloperJson();
      var details = document.createElement("details");
      details.className = "admin-dev-mode";
      var summary = document.createElement("summary");
      summary.textContent = "開発者向け編集";
      details.appendChild(summary);
      details.appendChild(el("p", "simple-note", "JSONを直接編集する場合は下の切り替えを有効にします。保存時はサーバ側の検証を必ず通ります。"));
      var toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = Boolean(model.useDeveloperJson);
      toggle.addEventListener("change", function() {
        if (toggle.checked) syncDeveloperJsonFromForm();
        model.useDeveloperJson = toggle.checked;
        refresh();
      });
      details.appendChild(row("JSON直接編集を使う", toggle));
      var schemaText = textarea(model.developerSchemaJson);
      schemaText.rows = 12;
      schemaText.disabled = !model.useDeveloperJson;
      schemaText.addEventListener("input", function() {
        model.developerSchemaJson = schemaText.value;
      });
      details.appendChild(row("schema JSON", schemaText));
      var copyText = textarea(model.developerCopyFormatJson);
      copyText.rows = 8;
      copyText.disabled = !model.useDeveloperJson;
      copyText.addEventListener("input", function() {
        model.developerCopyFormatJson = copyText.value;
      });
      details.appendChild(row("copy_format JSON", copyText));
      if (model.useDeveloperJson) {
        var apply = el("button", "btn bg admin-row-btn", "プレビューに反映");
        apply.type = "button";
        apply.addEventListener("click", refresh);
        details.appendChild(apply);
      }
      root.appendChild(details);
    }

    refresh();
    return {
      element: root,
      model: model,
      collectSchema: collectEditorSchema,
      collectCopyFormat: collectEditorCopyFormat,
    };
  }

  return {
    create: create,
  };
});
