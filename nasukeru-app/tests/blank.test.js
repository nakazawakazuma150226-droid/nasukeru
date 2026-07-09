const assert = require("node:assert/strict");
const test = require("node:test");

const blank = require("../js/blank.js");

test("detects canonical blank values", () => {
  assert.equal(blank.isBlank(null), true);
  assert.equal(blank.isBlank(undefined), true);
  assert.equal(blank.isBlank(""), true);
  assert.equal(blank.isBlank("   "), true);
  assert.equal(blank.isBlank([]), true);
});

test("detects canonical non-blank values", () => {
  assert.equal(blank.isBlank(0), false);
  assert.equal(blank.isBlank(42), false);
  assert.equal(blank.isBlank("0"), false);
  assert.equal(blank.isBlank([""]), false);
  assert.equal(blank.isBlank({}), false);
});
