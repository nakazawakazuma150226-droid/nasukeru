const test = require("node:test");
const assert = require("node:assert/strict");
const model = require("../js/simple-template-model.js");

test("effective blank policy preserves legacy warning semantics", () => {
  assert.equal(model.effectiveBlankPolicy({ requiredWarning: true }), "warn");
  assert.equal(model.effectiveBlankPolicy({ blankPolicy: "block", requiredWarning: true }), "block");
  assert.equal(model.effectiveBlankPolicy({}), "allow");
});

test("blank schema uses generic-v2 and unique internal ids", () => {
  let values = [0.1, 0.2];
  const schema = model.createBlankSchema(() => values.shift());
  assert.equal(schema.schemaFormat, "generic-v2");
  assert.match(schema.sections[0].id, /^sec_[a-f0-9]{8}$/);
  assert.match(schema.sections[0].fields[0].id, /^fld_[a-f0-9]{8}$/);
  assert.notEqual(schema.sections[0].id, schema.sections[0].fields[0].id);
});

test("automatic copy format omits blank fields and supports inline sections", () => {
  const schema = {
    schemaFormat: "generic-v2",
    sections: [{ id: "vitals", label: "バイタル", fields: [
      { id: "t", label: "体温", type: "number", unit: "℃" },
      { id: "spo2", label: "SpO₂", type: "number", unit: "%" },
    ] }],
  };
  const copy = model.automaticCopyFormat(schema, { title: "テスト", sectionStyles: { vitals: "inline" } });
  assert.equal(copy.lines[0], "テスト");
  assert.deepEqual(copy.lines[3].segments.map((item) => item.ref), ["vitals.t", "vitals.spo2"]);
  assert.equal(copy.lines[3].separator, "、");
});

test("collect output refs finds placeholders, segments, and split refs", () => {
  const refs = model.collectOutputRefs({ format: "text-v1", lines: [
    "{{a.one}}", { segments: [{ ref: "b.two" }] }, { text: "{{c.three}}", splitLinesFrom: "d.four" },
  ] });
  assert.deepEqual(Object.keys(refs).sort(), ["a.one", "b.two", "c.three", "d.four"]);
});

test("template ids are generated without colliding with existing ids", () => {
  const seq = [0.1, 0.2];
  const id = model.templateId(["tpl_19999999"], () => seq.shift());
  assert.notEqual(id, "tpl_19999999");
  assert.match(id, /^tpl_[a-f0-9]{8}$/);
});
