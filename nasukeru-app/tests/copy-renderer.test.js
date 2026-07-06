const assert = require("node:assert/strict");
const test = require("node:test");

const renderer = require("../js/copy-renderer.js");

test("renders placeholders with blank fallback", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      "JCS{{vitals.jcs}}",
      "T{{vitals.t}}",
    ],
  };
  const output = renderer.renderGenericTemplateCopyText(copyFormat, {
    "vitals.jcs": "0",
  });
  assert.equal(output, "JCS0\nT__");
});

test("omits object line when all refs are blank", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      "Title",
      { text: "Barre: {{neuro.barre}}", omitIfAllBlank: ["neuro.barre"] },
      { text: "NIHSS: {{neuro.nihss}}", omitIfAllBlank: ["neuro.nihss"] },
    ],
  };
  const output = renderer.renderGenericTemplateCopyText(copyFormat, {
    "neuro.barre": "",
    "neuro.nihss": "2",
  });
  assert.equal(output, "Title\nNIHSS: 2");
});

test("renders only filled dynamic segments", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      {
        segments: [
          { ref: "vitals.jcs", label: "JCS" },
          { ref: "vitals.t", label: "T", suffix: "℃" },
          { ref: "vitals.hr", label: "HR" },
          { ref: "vitals.spo2", label: "SpO₂", suffix: "%" },
        ],
        separator: "　",
      },
      {
        prefix: "MMT：",
        segments: [
          { ref: "mmt.ru", label: "右上肢" },
          { ref: "mmt.rl", label: "右下肢" },
        ],
        separator: "、",
      },
    ],
  };
  const output = renderer.renderGenericTemplateCopyText(copyFormat, {
    "vitals.jcs": "Ⅲ-300",
    "vitals.t": "30",
    "vitals.hr": "",
    "vitals.spo2": "",
    "mmt.ru": "",
    "mmt.rl": "",
  });
  assert.equal(output, "JCSⅢ-300　T30℃");
});

test("splits textarea value into non-empty lines", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      "Neuro",
      {
        text: "{{neuro.other}}",
        splitLinesFrom: "neuro.other",
        omitIfAllBlank: ["neuro.other"],
      },
      "Rest: {{rest.level}}",
    ],
  };
  const output = renderer.renderGenericTemplateCopyText(copyFormat, {
    "neuro.other": "line 1\n\nline 2\r\n line 3 ",
    "rest.level": "bed rest",
  });
  assert.equal(output, "Neuro\nline 1\nline 2\nline 3\nRest: bed rest");
});

test("uses showIf with condition values", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      "Status: {{vitals.status}}",
      {
        text: "Oxygen flow: {{vitals.oxygen_flow}}L",
        showIf: { op: "eq", field: "vitals.oxygen_use", value: "oxygen" },
      },
    ],
  };
  const displayValues = {
    "vitals.status": "stable",
    "vitals.oxygen_use": "O2使用",
    "vitals.oxygen_flow": "2",
  };
  assert.equal(
    renderer.renderGenericTemplateCopyText(copyFormat, displayValues, { "vitals.oxygen_use": "oxygen" }),
    "Status: stable\nOxygen flow: 2L"
  );
  assert.equal(
    renderer.renderGenericTemplateCopyText(copyFormat, displayValues, { "vitals.oxygen_use": "room_air" }),
    "Status: stable"
  );
});

test("optional conditional field stays on its own line instead of concatenating onto another value", () => {
  // Regression test: a blank optional field must never be concatenated directly
  // after another field's placeholder in the same text-line, since a blank value
  // renders as a bare "__" with no label, which reads as a garbled attachment to
  // whatever value precedes it (e.g. "ニカルジピン__" instead of a clearly labeled
  // separate line).
  const copyFormat = {
    format: "text-v1",
    lines: [
      "降圧薬：{{treatment.antihypertensive}}、ニカルジピン速度：{{treatment.nicardipine_rate}}ml/h。",
      {
        text: "降圧薬その他：{{treatment.antihypertensive_other}}。",
        showIf: { op: "contains", field: "treatment.antihypertensive", value: "その他" },
      },
    ],
  };
  const noOtherValues = {
    "treatment.antihypertensive": "ニカルジピン",
    "treatment.nicardipine_rate": "5",
  };
  const noOtherResult = renderer.renderGenericTemplateCopyResult(copyFormat, noOtherValues, noOtherValues);
  assert.equal(noOtherResult.text, "降圧薬：ニカルジピン、ニカルジピン速度：5ml/h。");
  assert.ok(!noOtherResult.text.includes("__"));

  const withOtherValues = {
    "treatment.antihypertensive": "その他",
    "treatment.antihypertensive_other": "ワーファリン",
    "treatment.nicardipine_rate": "",
  };
  const withOtherResult = renderer.renderGenericTemplateCopyResult(copyFormat, withOtherValues, withOtherValues);
  assert.equal(withOtherResult.text, "降圧薬：その他、ニカルジピン速度：__ml/h。\n降圧薬その他：ワーファリン。");
});

test("returns structured render result with unresolved refs", () => {
  const copyFormat = {
    format: "text-v1",
    lines: [
      "JCS{{vitals.jcs}}",
      { text: "Hidden {{vitals.hidden}}", omitIfAllBlank: ["vitals.hidden"] },
      "SpO2{{vitals.spo2}}",
    ],
  };
  const result = renderer.renderGenericTemplateCopyResult(copyFormat, {
    "vitals.jcs": "0",
    "vitals.spo2": "",
  });
  assert.equal(result.text, "JCS0\nSpO2__");
  assert.deepEqual(result.unresolvedRefs, ["vitals.spo2"]);
  assert.deepEqual(result.warnings, []);
});
