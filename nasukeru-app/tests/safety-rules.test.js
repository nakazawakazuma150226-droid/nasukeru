const assert = require("node:assert/strict");
const test = require("node:test");

const safety = require("../js/safety-rules.js");

test("blankPolicy block creates a block issue", () => {
  const result = safety.validateFields(
    [{ ref: "vitals.spo2", label: "SpO2", type: "number", value: null, visible: true, blankPolicy: "block" }],
    {}
  );
  assert.equal(result.blocks.length, 1);
  assert.equal(result.blocks[0].code, "required_blank");
});

test("requiredWarning remains warn-compatible", () => {
  const result = safety.validateFields(
    [{ ref: "vitals.jcs", label: "JCS", type: "text", value: "", visible: true, requiredWarning: true }],
    {}
  );
  assert.equal(result.blocks.length, 0);
  assert.equal(result.warnings.length, 1);
});

test("hardRange blocks and warningRange warns", () => {
  const result = safety.validateFields(
    [
      {
        ref: "vitals.spo2",
        label: "SpO2",
        type: "number",
        value: 85,
        visible: true,
        hardRange: { min: 0, max: 100 },
        warningRange: { min: 90, max: 100 },
      },
      {
        ref: "vitals.hr",
        label: "HR",
        type: "number",
        value: 250,
        visible: true,
        hardRange: { min: 0, max: 220 },
      },
    ],
    {}
  );
  assert.equal(result.warnings.length, 1);
  assert.equal(result.warnings[0].code, "warning_range");
  assert.equal(result.blocks.length, 1);
  assert.equal(result.blocks[0].code, "hard_range");
});

test("invalid number creates a block issue", () => {
  const result = safety.validateFields(
    [{ ref: "vitals.spo2", label: "SpO2", type: "number", value: "abc", visible: true }],
    {}
  );
  assert.equal(result.blocks.length, 1);
  assert.equal(result.blocks[0].code, "invalid_number");
  assert.equal(result.warnings.length, 0);
});

test("hidden fields do not produce safety issues", () => {
  const result = safety.validateFields(
    [{ ref: "vitals.flow", label: "Flow", type: "number", value: null, visible: false, blankPolicy: "block" }],
    {}
  );
  assert.deepEqual(result, { blocks: [], warnings: [] });
});
