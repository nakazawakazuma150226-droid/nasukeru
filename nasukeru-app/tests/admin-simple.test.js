const assert = require("node:assert/strict");
const test = require("node:test");

const model = require("../js/simple-template-model.js");

test("effectiveBlankPolicy maps legacy requiredWarning to warn", () => {
  assert.equal(model.effectiveBlankPolicy({ requiredWarning: true }), "warn");
  assert.equal(model.effectiveBlankPolicy({ blankPolicy: "block", requiredWarning: true }), "block");
  assert.equal(model.effectiveBlankPolicy({}), "allow");
});

test("blank editor model compiles to generic-v2 without exposing IDs", () => {
  const editor = model.blankEditorModel();
  editor.label = "慢性硬膜下血腫";
  editor.full = "慢性硬膜下血腫 看護観察テンプレート";
  const schema = model.editorModelToSchema(editor);
  assert.equal(schema.schemaFormat, "generic-v2");
  assert.match(schema.sections[0].id, /^sec_/);
  assert.match(schema.sections[0].fields[0].id, /^fld_/);
});

test("option value is preserved when label changes", () => {
  const editor = model.schemaToEditorModel({
    schema: {
      schemaFormat: "generic-v2",
      sections: [
        {
          id: "vitals",
          label: "バイタル",
          fields: [
            {
              id: "oxygen_use",
              label: "酸素使用",
              type: "select",
              options: [{ value: "oxygen", label: "O2使用" }],
            },
          ],
        },
      ],
    },
  });
  editor.sections[0].fields[0].options[0].label = "酸素投与あり";
  const schema = model.editorModelToSchema(editor);
  assert.deepEqual(schema.sections[0].fields[0].options[0], {
    value: "oxygen",
    label: "酸素投与あり",
  });
});

test("automatic copy compiler omits blank fields", () => {
  const editor = model.schemaToEditorModel({
    full: "テスト",
    schema: {
      schemaFormat: "generic-v2",
      sections: [
        {
          id: "vitals",
          label: "バイタル",
          fields: [
            { id: "t", label: "体温", type: "number", unit: "℃" },
            { id: "bp", label: "血圧", type: "text" },
          ],
        },
      ],
    },
  });
  editor.sections[0].copyStyle = "inline";
  const copyFormat = model.editorModelToCopyFormat(editor);
  assert.deepEqual(copyFormat.lines[2], {
    segments: [
      { ref: "vitals.t", label: "体温：", suffix: "℃" },
      { ref: "vitals.bp", label: "血圧：", suffix: "" },
    ],
    separator: "、",
  });
});

test("condition metadata round-trips through simple editor model", () => {
  const visibleIf = { op: "eq", field: "status.phase", value: "postop" };
  const requiredIf = { op: "contains", field: "status.symptoms", value: "headache" };
  const editor = model.schemaToEditorModel({
    schema: {
      schemaFormat: "generic-v2",
      sections: [
        {
          id: "status",
          label: "状態",
          visibleIf,
          fields: [
            {
              id: "phase",
              label: "フェーズ",
              type: "select",
              options: [{ value: "postop", label: "術後" }],
            },
            {
              id: "symptoms",
              label: "症状",
              type: "multi_select",
              options: [{ value: "headache", label: "頭痛" }],
            },
            {
              id: "memo",
              label: "メモ",
              type: "text",
              visibleIf,
              requiredIf,
            },
          ],
        },
      ],
    },
  });
  const schema = model.editorModelToSchema(editor);
  assert.deepEqual(schema.sections[0].visibleIf, visibleIf);
  assert.deepEqual(schema.sections[0].fields[2].visibleIf, visibleIf);
  assert.deepEqual(schema.sections[0].fields[2].requiredIf, requiredIf);
});
