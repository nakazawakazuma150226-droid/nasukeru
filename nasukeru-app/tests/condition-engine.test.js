const assert = require("node:assert/strict");
const test = require("node:test");

const engine = require("../js/condition-engine.js");

test("evaluates scalar and number operators", () => {
  const values = {
    "vitals.oxygen_use": "oxygen",
    "vitals.spo2": 96,
  };
  assert.equal(engine.evaluateCondition({ op: "eq", field: "vitals.oxygen_use", value: "oxygen" }, values), true);
  assert.equal(engine.evaluateCondition({ op: "neq", field: "vitals.oxygen_use", value: "room_air" }, values), true);
  assert.equal(engine.evaluateCondition({ op: "gte", field: "vitals.spo2", value: 95 }, values), true);
  assert.equal(engine.evaluateCondition({ op: "lt", field: "vitals.spo2", value: 95 }, values), false);
});

test("evaluates array and nested operators", () => {
  const values = {
    "observe.symptoms": ["headache", "nausea"],
    "vitals.oxygen_use": "oxygen",
  };
  assert.equal(engine.evaluateCondition({ op: "contains", field: "observe.symptoms", value: "nausea" }, values), true);
  assert.equal(engine.evaluateCondition({ op: "in", field: "vitals.oxygen_use", value: ["oxygen", "room_air"] }, values), true);
  assert.equal(
    engine.evaluateCondition(
      {
        op: "and",
        conditions: [
          { op: "contains", field: "observe.symptoms", value: "headache" },
          { op: "not", condition: { op: "is_blank", field: "vitals.oxygen_use" } },
        ],
      },
      values
    ),
    true
  );
});

test("detects blank values", () => {
  assert.equal(engine.evaluateCondition({ op: "is_blank", field: "a.b" }, { "a.b": "" }), true);
  assert.equal(engine.evaluateCondition({ op: "is_blank", field: "a.b" }, { "a.b": [] }), true);
  assert.equal(engine.evaluateCondition({ op: "is_blank", field: "a.b" }, { "a.b": 0 }), false);
});
