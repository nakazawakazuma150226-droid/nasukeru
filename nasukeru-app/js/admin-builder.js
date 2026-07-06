(function(root, factory) {
  root.NasukeruAdminBuilder = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  var FIELD_TYPE_CHOICES = [
    { value: "text", label: "短文入力" },
    { value: "textarea", label: "長文入力" },
    { value: "select", label: "単一選択" },
    { value: "multi_select", label: "複数選択" },
    { value: "number", label: "数値入力" },
  ];
  var BLANK_POLICY_CHOICES = [
    { value: "", label: "指定なし" },
    { value: "allow", label: "空欄を許可" },
    { value: "warn", label: "空欄なら警告" },
    { value: "block", label: "空欄ならコピー不可" },
  ];
  var CONDITION_OP_CHOICES = [
    { value: "", label: "条件なし" },
    { value: "eq", label: "等しい" },
    { value: "neq", label: "等しくない" },
    { value: "contains", label: "含む" },
    { value: "gt", label: "より大きい" },
    { value: "gte", label: "以上" },
    { value: "lt", label: "より小さい" },
    { value: "lte", label: "以下" },
    { value: "is_blank", label: "空欄" },
  ];

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function input(className, value, placeholder, type) {
    var node = document.createElement("input");
    node.type = type || "text";
    node.className = "admin-input " + className;
    node.value = value == null ? "" : String(value);
    if (placeholder) node.placeholder = placeholder;
    return node;
  }

  function textarea(className, value, rows) {
    var node = document.createElement("textarea");
    node.className = "admin-input " + className;
    node.rows = rows || 3;
    node.value = value || "";
    return node;
  }

  function select(className, value, choices) {
    var node = document.createElement("select");
    node.className = "admin-input " + className;
    choices.forEach(function(choice) {
      var opt = document.createElement("option");
      opt.value = typeof choice === "string" ? choice : choice.value;
      opt.textContent = typeof choice === "string" ? choice : choice.label;
      node.appendChild(opt);
    });
    node.value = value || "";
    return node;
  }

  function row(label, control, extraClass) {
    var wrap = el("label", "admin-builder-field");
    if (extraClass) wrap.className += " " + extraClass;
    wrap.appendChild(el("span", "", label));
    wrap.appendChild(control);
    return wrap;
  }

  function optionToLine(option) {
    if (typeof option === "string") return option;
    if (!option) return "";
    return option.value === option.label ? option.value : option.value + "=" + option.label;
  }

  function optionsToText(options) {
    return (options || []).map(optionToLine).join("\n");
  }

  function parseOptions(text) {
    return String(text || "").split(/\r?\n/).map(function(line) {
      return line.trim();
    }).filter(Boolean).map(function(line) {
      var pos = line.indexOf("=");
      if (pos < 0) return { value: line, label: line };
      return { value: line.slice(0, pos).trim(), label: line.slice(pos + 1).trim() };
    });
  }

  function refsFromBuilder(root) {
    return fieldsFromBuilder(root).map(function(field) { return field.ref; });
  }

  function fieldsFromBuilder(root) {
    var fields = [];
    root.querySelectorAll("[data-builder-section]").forEach(function(section) {
      var sectionId = section.querySelector(".builder-section-id").value.trim();
      section.querySelectorAll("[data-builder-field]").forEach(function(field) {
        var fieldId = field.querySelector(".builder-field-id").value.trim();
        if (sectionId && fieldId) {
          fields.push({
            ref: sectionId + "." + fieldId,
            type: field.querySelector(".builder-field-type").value,
            options: collectOptions(field),
          });
        }
      });
    });
    return fields;
  }

  function fieldMapFromBuilder(root) {
    var map = {};
    fieldsFromBuilder(root).forEach(function(field) {
      map[field.ref] = field;
    });
    return map;
  }

  function placeholderRefs(text) {
    var refs = [];
    String(text || "").replace(/\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}/g, function(match, sectionId, fieldId) {
      refs.push(sectionId + "." + fieldId);
      return match;
    });
    return refs;
  }

  function copyOutputRefs(copyFormat) {
    var refs = {};
    (copyFormat.lines || []).forEach(function(line) {
      var lineObj = typeof line === "string" ? { text: line } : line;
      placeholderRefs(lineObj.text || "").forEach(function(ref) { refs[ref] = true; });
      (lineObj.segments || []).forEach(function(segment) {
        if (segment.ref) refs[segment.ref] = true;
      });
      if (lineObj.splitLinesFrom) refs[lineObj.splitLinesFrom] = true;
    });
    return refs;
  }

  function unreferencedWarnings(schema, copyFormat) {
    if (!schema || !copyFormat || ["generic-v1", "generic-v2"].indexOf(schema.schemaFormat) < 0) return [];
    var outputRefs = copyOutputRefs(copyFormat);
    var warnings = [];
    (schema.sections || []).forEach(function(section) {
      (section.fields || []).forEach(function(field) {
        var ref = section.id + "." + field.id;
        if (outputRefs[ref]) return;
        var label = (section.label || section.id) + " > " + (field.label || field.id) + (field.visibleIf ? "（条件付き表示）" : "");
        warnings.push("入力項目『" + label + "』はコピー出力に含まれていません");
      });
    });
    return warnings;
  }

  function renderWarnings(root, warnings) {
    var box = root.querySelector(".admin-builder-warnings");
    if (!box) return;
    box.innerHTML = "";
    if (!warnings.length) {
      box.classList.remove("show");
      return;
    }
    var title = el("div", "warn-title", "コピー出力に含まれない入力項目があります");
    var list = document.createElement("ul");
    list.className = "warn-list";
    warnings.forEach(function(warning) {
      var item = document.createElement("li");
      item.textContent = warning;
      list.appendChild(item);
    });
    box.appendChild(title);
    box.appendChild(list);
    box.classList.add("show");
  }

  function updateRefSelects(root) {
    var fieldMap = fieldMapFromBuilder(root);
    var refs = Object.keys(fieldMap);
    root.querySelectorAll(".builder-ref-select").forEach(function(sel) {
      var current = sel.value || sel.dataset.pendingValue || "";
      sel.innerHTML = "";
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "なし";
      sel.appendChild(empty);
      refs.forEach(function(ref) {
        var opt = document.createElement("option");
        opt.value = ref;
        opt.textContent = ref;
        sel.appendChild(opt);
      });
      sel.value = refs.indexOf(current) >= 0 ? current : "";
      sel.dataset.pendingValue = sel.value;
    });
    root.querySelectorAll(".admin-condition-row").forEach(function(wrap) {
      updateConditionValueEditor(wrap, fieldMap);
    });
  }

  function replaceConditionValueControl(wrap, next) {
    var current = wrap.querySelector(".builder-condition-value");
    if (!current) {
      wrap.appendChild(next);
      return next;
    }
    if (current.tagName === "INPUT" && next.tagName === "INPUT" && current.type === next.type) {
      current.disabled = next.disabled;
      current.placeholder = next.placeholder;
      return current;
    }
    current.replaceWith(next);
    return next;
  }

  function updateConditionValueEditor(wrap, fieldMap) {
    var fieldRef = wrap.querySelector(".builder-condition-field").value;
    var op = wrap.querySelector(".builder-condition-op").value;
    var current = wrap.querySelector(".builder-condition-value");
    var currentValue = current ? current.value : "";
    var meta = fieldMap[fieldRef];
    if (op === "is_blank") {
      var blankInput = input("builder-condition-value", "", "");
      blankInput.disabled = true;
      replaceConditionValueControl(wrap, blankInput);
      return;
    }
    if (meta && (meta.type === "select" || (meta.type === "multi_select" && op === "contains"))) {
      var choices = [{ value: "", label: "select value" }].concat(meta.options || []);
      var optionSelect = select("builder-condition-value", currentValue, choices);
      replaceConditionValueControl(wrap, optionSelect);
      return;
    }
    if (meta && meta.type === "number") {
      var numberInput = input("builder-condition-value", currentValue, "value", "number");
      replaceConditionValueControl(wrap, numberInput);
      return;
    }
    var textInput = input("builder-condition-value", currentValue, "value");
    replaceConditionValueControl(wrap, textInput);
  }

  function conditionControls(condition) {
    condition = condition || {};
    var wrap = el("div", "admin-condition-row");
    var fieldSelect = select("builder-ref-select builder-condition-field", "", []);
    fieldSelect.dataset.pendingValue = condition.field || "";
    wrap.appendChild(fieldSelect);
    wrap.appendChild(select("builder-condition-op", condition.op || "", CONDITION_OP_CHOICES));
    wrap.appendChild(input("builder-condition-value", condition.value == null ? "" : condition.value, "値"));
    return wrap;
  }

  function updateFieldTypeUi(card) {
    var type = card.querySelector(".builder-field-type").value;
    var optionsRow = card.querySelector(".builder-options-row");
    if (optionsRow) optionsRow.hidden = type !== "select" && type !== "multi_select";
  }

  function addOptionRow(list, option) {
    option = option || {};
    if (typeof option === "string") option = { value: option, label: option };
    var optionRow = el("div", "admin-option-row");
    optionRow.dataset.builderOption = "1";
    optionRow.appendChild(input("builder-option-value", option.value || "", "値"));
    optionRow.appendChild(input("builder-option-label", option.label || option.value || "", "表示名"));
    var remove = el("button", "btn bg admin-row-btn", "削除");
    remove.type = "button";
    remove.addEventListener("click", function() { optionRow.remove(); });
    optionRow.appendChild(remove);
    list.appendChild(optionRow);
  }

  function optionBuilder(options) {
    var wrap = el("div", "admin-option-builder");
    var list = el("div", "admin-option-list");
    wrap.appendChild(list);
    (options || []).forEach(function(option) { addOptionRow(list, option); });
    var add = el("button", "btn bg admin-row-btn", "選択肢を追加");
    add.type = "button";
    add.addEventListener("click", function() { addOptionRow(list); });
    wrap.appendChild(add);
    return wrap;
  }

  function collectOptions(fieldNode) {
    var options = [];
    fieldNode.querySelectorAll("[data-builder-option]").forEach(function(optionNode) {
      var value = optionNode.querySelector(".builder-option-value").value.trim();
      var label = optionNode.querySelector(".builder-option-label").value.trim();
      if (value || label) options.push({ value: value || label, label: label || value });
    });
    return options;
  }

  function collectCondition(wrap) {
    if (!wrap) return null;
    var field = wrap.querySelector(".builder-condition-field").value;
    var op = wrap.querySelector(".builder-condition-op").value;
    var raw = wrap.querySelector(".builder-condition-value").value.trim();
    if (!field || !op) return null;
    if (op === "is_blank") return { op: op, field: field };
    var value = raw;
    var root = wrap.closest("[data-admin-builder]");
    var fieldMeta = root ? fieldMapFromBuilder(root)[field] : null;
    if (fieldMeta && fieldMeta.type === "number" && raw !== "") value = Number(raw);
    return { op: op, field: field, value: value };
  }

  function insertAtCursor(textareaNode, text) {
    var start = textareaNode.selectionStart == null ? textareaNode.value.length : textareaNode.selectionStart;
    var end = textareaNode.selectionEnd == null ? textareaNode.value.length : textareaNode.selectionEnd;
    textareaNode.value = textareaNode.value.slice(0, start) + text + textareaNode.value.slice(end);
    textareaNode.focus();
    textareaNode.selectionStart = start + text.length;
    textareaNode.selectionEnd = start + text.length;
    textareaNode.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function cloneValue(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function addField(sectionNode, field) {
    field = field || { id: "field", label: "項目", type: "text", allowEmpty: true };
    var card = el("div", "admin-builder-card", null);
    card.dataset.builderField = "1";
    card.originalField = cloneValue(field);
    var header = el("div", "admin-builder-card-head");
    header.appendChild(el("strong", "", "Field"));
    var remove = el("button", "btn bg admin-row-btn", "削除");
    remove.type = "button";
    remove.addEventListener("click", function() {
      card.remove();
      updateRefSelects(sectionNode.closest("[data-admin-builder]"));
    });
    header.appendChild(remove);
    card.appendChild(header);

    var grid = el("div", "admin-builder-grid");
    grid.appendChild(row("ID", input("builder-field-id", field.id, "例: oxygen_use")));
    grid.appendChild(row("ラベル", input("builder-field-label", field.label, "例: 酸素使用")));
    grid.appendChild(row("種別", select("builder-field-type", field.type, FIELD_TYPE_CHOICES)));
    grid.appendChild(row("表示順", input("builder-field-order", field.displayOrder == null ? "" : field.displayOrder, "", "number")));
    grid.appendChild(row("単位", input("builder-field-unit", field.unit || "", "例: L")));
    grid.appendChild(row("placeholder", input("builder-field-placeholder", field.placeholder || "", "")));
    grid.appendChild(row("空欄時", select("builder-field-blank-policy", field.blankPolicy || "", BLANK_POLICY_CHOICES)));
    grid.appendChild(row("最小値", input("builder-field-min", field.min, "", "number")));
    grid.appendChild(row("最大値", input("builder-field-max", field.max, "", "number")));
    grid.appendChild(row("刻み", input("builder-field-step", field.step, "", "number")));
    grid.appendChild(row("入力不可の下限", input("builder-hard-min", field.hardRange && field.hardRange.min, "", "number")));
    grid.appendChild(row("入力不可の上限", input("builder-hard-max", field.hardRange && field.hardRange.max, "", "number")));
    grid.appendChild(row("警告の下限", input("builder-warning-min", field.warningRange && field.warningRange.min, "", "number")));
    grid.appendChild(row("警告の上限", input("builder-warning-max", field.warningRange && field.warningRange.max, "", "number")));
    card.appendChild(grid);

    card.appendChild(row("補足説明", input("builder-field-help", field.helpText || "", "")));
    card.appendChild(row("選択肢", optionBuilder(field.options), "builder-options-row"));
    card.appendChild(row("表示条件", conditionControls(field.visibleIf), "builder-visible-if-row"));
    card.appendChild(row("必須条件", conditionControls(field.requiredIf), "builder-required-if-row"));

    ["builder-field-id", "builder-field-type"].forEach(function(cls) {
      var control = card.querySelector("." + cls);
      var sync = function() {
        updateFieldTypeUi(card);
        updateRefSelects(sectionNode.closest("[data-admin-builder]"));
      };
      control.addEventListener("input", sync);
      control.addEventListener("change", sync);
    });
    sectionNode.querySelector(".admin-builder-fields").appendChild(card);
    updateFieldTypeUi(card);
    updateRefSelects(sectionNode.closest("[data-admin-builder]"));
  }

  function addSection(root, section) {
    section = section || { id: "section", label: "セクション", displayOrder: 1, fields: [] };
    var card = el("section", "admin-builder-section", null);
    card.dataset.builderSection = "1";
    card.originalSection = cloneValue(section);
    var header = el("div", "admin-builder-card-head");
    header.appendChild(el("strong", "", "Section"));
    var remove = el("button", "btn bg admin-row-btn", "削除");
    remove.type = "button";
    remove.addEventListener("click", function() {
      card.remove();
      updateRefSelects(root);
    });
    header.appendChild(remove);
    card.appendChild(header);

    var grid = el("div", "admin-builder-grid");
    grid.appendChild(row("ID", input("builder-section-id", section.id, "例: vitals")));
    grid.appendChild(row("ラベル", input("builder-section-label", section.label, "例: バイタル")));
    grid.appendChild(row("表示順", input("builder-section-order", section.displayOrder || "", "", "number")));
    card.appendChild(grid);
    var fields = el("div", "admin-builder-fields");
    card.appendChild(fields);
    var add = el("button", "btn bg", "項目を追加");
    add.type = "button";
    add.addEventListener("click", function() { addField(card); });
    card.appendChild(add);
    root.querySelector(".admin-builder-sections").appendChild(card);
    card.querySelector(".builder-section-id").addEventListener("input", function() { updateRefSelects(root); });
    (section.fields || []).forEach(function(field) { addField(card, field); });
    updateRefSelects(root);
  }

  function copyLineControls(line) {
    var wrap = el("div", "admin-builder-card", null);
    wrap.dataset.builderCopyLine = "1";
    var lineObj = typeof line === "string" ? { text: line } : (line || { text: "" });
    wrap.originalCopyLine = cloneValue(lineObj);
    var header = el("div", "admin-builder-card-head");
    header.appendChild(el("strong", "", "Copy Line"));
    var remove = el("button", "btn bg admin-row-btn", "削除");
    remove.type = "button";
    remove.addEventListener("click", function() { wrap.remove(); });
    header.appendChild(remove);
    wrap.appendChild(header);
    var copyText = textarea("builder-copy-text", lineObj.text || "", 2);
    wrap.appendChild(row("出力文", copyText));
    var insertRow = el("div", "admin-copy-insert-row");
    var insertSelect = select("builder-ref-select builder-copy-insert", "", []);
    var insertButton = el("button", "btn bg admin-row-btn", "項目を挿入");
    insertButton.type = "button";
    insertButton.addEventListener("click", function() {
      if (insertSelect.value) insertAtCursor(copyText, "{{" + insertSelect.value + "}}");
    });
    insertRow.appendChild(insertSelect);
    insertRow.appendChild(insertButton);
    wrap.appendChild(row("入力項目", insertRow));
    wrap.appendChild(row("showIf", conditionControls(lineObj.showIf)));
    wrap.appendChild(row("omitIfAllBlank", textarea("builder-copy-omit", (lineObj.omitIfAllBlank || []).join("\n"), 2)));
    var splitSelect = select("builder-ref-select builder-copy-split", "", []);
    splitSelect.dataset.pendingValue = lineObj.splitLinesFrom || "";
    wrap.appendChild(row("splitLinesFrom", splitSelect));
    return wrap;
  }

  function collectSchema(root, schemaFormat) {
    var sections = [];
    root.querySelectorAll("[data-builder-section]").forEach(function(sectionNode) {
      var section = Object.assign({}, cloneValue(sectionNode.originalSection) || {}, {
        id: sectionNode.querySelector(".builder-section-id").value.trim(),
        label: sectionNode.querySelector(".builder-section-label").value.trim(),
        fields: [],
      });
      var order = sectionNode.querySelector(".builder-section-order").value;
      if (order !== "") section.displayOrder = Number(order);
      else delete section.displayOrder;
      sectionNode.querySelectorAll("[data-builder-field]").forEach(function(fieldNode) {
        var field = Object.assign({}, cloneValue(fieldNode.originalField) || {});
        field.id = fieldNode.querySelector(".builder-field-id").value.trim();
        field.label = fieldNode.querySelector(".builder-field-label").value.trim();
        field.type = fieldNode.querySelector(".builder-field-type").value;
        var displayOrder = fieldNode.querySelector(".builder-field-order").value;
        if (displayOrder !== "") field.displayOrder = Number(displayOrder);
        else delete field.displayOrder;
        ["unit", "placeholder", "helpText"].forEach(function(key) {
          var cls = key === "helpText" ? ".builder-field-help" : ".builder-field-" + key;
          var value = fieldNode.querySelector(cls).value.trim();
          if (value) field[key] = value;
          else delete field[key];
        });
        var blankPolicy = fieldNode.querySelector(".builder-field-blank-policy").value;
        if (blankPolicy) field.blankPolicy = blankPolicy;
        else delete field.blankPolicy;
        [["min", ".builder-field-min"], ["max", ".builder-field-max"], ["step", ".builder-field-step"]].forEach(function(item) {
          var value = fieldNode.querySelector(item[1]).value;
          if (value !== "") field[item[0]] = Number(value);
          else delete field[item[0]];
        });
        var options = collectOptions(fieldNode);
        if (field.type === "select" || field.type === "multi_select") {
          if (options.length) field.options = options;
        } else {
          delete field.options;
        }
        [["hardRange", ".builder-hard-min", ".builder-hard-max"], ["warningRange", ".builder-warning-min", ".builder-warning-max"]].forEach(function(item) {
          var min = fieldNode.querySelector(item[1]).value;
          var max = fieldNode.querySelector(item[2]).value;
          delete field[item[0]];
          if (field.type === "number" && (min !== "" || max !== "")) {
            field[item[0]] = {};
            if (min !== "") field[item[0]].min = Number(min);
            if (max !== "") field[item[0]].max = Number(max);
          }
        });
        if (field.type !== "number") {
          delete field.min;
          delete field.max;
          delete field.step;
        }
        var visibleIf = collectCondition(fieldNode.querySelector(".builder-visible-if-row .admin-condition-row"));
        var requiredIf = collectCondition(fieldNode.querySelector(".builder-required-if-row .admin-condition-row"));
        if (visibleIf) field.visibleIf = visibleIf;
        else delete field.visibleIf;
        if (requiredIf) field.requiredIf = requiredIf;
        else delete field.requiredIf;
        section.fields.push(field);
      });
      sections.push(section);
    });
    return { schemaFormat: schemaFormat || "generic-v1", sections: sections };
  }

  function collectCopyFormat(root) {
    var lines = [];
    root.querySelectorAll("[data-builder-copy-line]").forEach(function(lineNode) {
      var text = lineNode.querySelector(".builder-copy-text").value;
      var showIf = collectCondition(lineNode.querySelector(".admin-condition-row"));
      var omit = lineNode.querySelector(".builder-copy-omit").value.split(/\r?\n/).map(function(item) {
        return item.trim();
      }).filter(Boolean);
      var split = lineNode.querySelector(".builder-copy-split").value;
      if (
        lineNode.originalCopyLine
        && Array.isArray(lineNode.originalCopyLine.segments)
        && !text
        && !showIf
        && !omit.length
        && !split
      ) {
        lines.push(cloneValue(lineNode.originalCopyLine));
        return;
      }
      if (!showIf && !omit.length && !split) {
        lines.push(text);
        return;
      }
      var line = { text: text };
      if (showIf) line.showIf = showIf;
      if (omit.length) line.omitIfAllBlank = omit;
      if (split) line.splitLinesFrom = split;
      lines.push(line);
    });
    return { format: "text-v1", lines: lines };
  }

  function create(container, schema, copyFormat, options) {
    options = options || {};
    var root = el("div", "admin-builder");
    root.dataset.adminBuilder = "1";
    root.innerHTML = "";
    var toolbar = el("div", "admin-builder-toolbar");
    var addSectionButton = el("button", "btn bg", "セクション追加");
    addSectionButton.type = "button";
    toolbar.appendChild(addSectionButton);
    var addCopyButton = el("button", "btn bg", "コピー行追加");
    addCopyButton.type = "button";
    toolbar.appendChild(addCopyButton);
    root.appendChild(toolbar);
    root.appendChild(el("div", "admin-builder-sections"));
    var copySection = el("section", "admin-builder-section");
    copySection.appendChild(el("h3", "", "コピー出力"));
    copySection.appendChild(el("div", "admin-builder-copy-lines"));
    root.appendChild(copySection);
    var preview = el("pre", "admin-json admin-builder-preview");
    var warningsBox = el("div", "admin-alert admin-builder-warnings");
    root.appendChild(preview);
    root.appendChild(warningsBox);
    container.appendChild(root);

    (schema.sections || []).forEach(function(section) { addSection(root, section); });
    (copyFormat && copyFormat.lines || []).forEach(function(line) {
      root.querySelector(".admin-builder-copy-lines").appendChild(copyLineControls(line));
    });
    if (!root.querySelector("[data-builder-copy-line]")) {
      root.querySelector(".admin-builder-copy-lines").appendChild(copyLineControls("{{basic.note}}"));
    }

    addSectionButton.addEventListener("click", function() { addSection(root); refresh(); });
    addCopyButton.addEventListener("click", function() {
      root.querySelector(".admin-builder-copy-lines").appendChild(copyLineControls(""));
      updateRefSelects(root);
      refresh();
    });
    root.addEventListener("input", refresh);
    root.addEventListener("change", refresh);

    function refresh() {
      updateRefSelects(root);
      try {
        var schema = collectSchema(root, options.schemaFormat && options.schemaFormat());
        var copyFormat = collectCopyFormat(root);
        preview.textContent = JSON.stringify({
          schema: schema,
          copy_format: copyFormat,
        }, null, 2);
        renderWarnings(root, unreferencedWarnings(schema, copyFormat));
      } catch (error) {
        preview.textContent = error.message;
        renderWarnings(root, []);
      }
    }
    refresh();
    return {
      element: root,
      collectSchema: function(schemaFormat) { return collectSchema(root, schemaFormat || (options.schemaFormat && options.schemaFormat())); },
      collectCopyFormat: function() { return collectCopyFormat(root); },
      refresh: refresh,
    };
  }

  return {
    create: create,
  };
});
