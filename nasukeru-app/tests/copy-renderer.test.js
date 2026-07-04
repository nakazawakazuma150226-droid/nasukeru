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
