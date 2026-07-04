const assert = require("node:assert/strict");
const test = require("node:test");

const values = require("../js/generic-values.js");

function input(fieldType, value, labels = {}) {
  return {
    dataset: { fieldType },
    genericOptionLabels: labels,
    value,
  };
}

test("parses number zero as a real value", () => {
  const parsed = values.parseInputValue(input("number", "0"));
  assert.equal(parsed, 0);
  assert.equal(values.isBlankValue(parsed), false);
});

test("parses blank number as null", () => {
  const parsed = values.parseInputValue(input("number", ""));
  assert.equal(parsed, null);
  assert.equal(values.isBlankValue(parsed), true);
});

test("normalizes full-width number input", () => {
  assert.equal(values.normalizeNumberInput("　３８．５　"), "38.5");
  assert.equal(values.normalizeNumberInput("－５"), "-5");
  assert.equal(values.normalizeNumberInput("ー５"), "-5");
});

test("parses normalized full-width number", () => {
  const parsed = values.parseInputValue(input("number", "３８．５"));
  assert.equal(parsed, 38.5);
});

test("parses multi_select as an array", () => {
  const parsed = values.parseInputValue(input("multi_select", "headache、nausea"));
  assert.deepEqual(parsed, ["headache", "nausea"]);
});

test("formats select and multi_select values with labels for copy", () => {
  assert.equal(
    values.formatInputValueForCopy(input("select", "oxygen", { oxygen: "O2使用" }), "oxygen"),
    "O2使用"
  );
  assert.equal(
    values.formatInputValueForCopy(
      input("multi_select", "headache、nausea", { headache: "頭痛", nausea: "嘔気" }),
      ["headache", "nausea"]
    ),
    "頭痛、嘔気"
  );
});
