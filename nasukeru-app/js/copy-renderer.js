(function(root, factory) {
  var renderer = factory(root.NasukeruConditionEngine);
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./condition-engine.js"));
  }
  root.NasukeruCopyRenderer = renderer;
})(typeof globalThis !== "undefined" ? globalThis : this, function(conditionEngine) {
  var PLACEHOLDER_RE = /\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}/g;

  function valueFor(values, ref) {
    return values[ref] || "__";
  }

  function renderCopyLine(text, values, overrideRef, overrideValue) {
    return String(text || "").replace(PLACEHOLDER_RE, function(match, sectionId, fieldId) {
      var ref = sectionId + "." + fieldId;
      if (ref === overrideRef) return overrideValue || "__";
      return valueFor(values, ref);
    });
  }

  function shouldOmitCopyLine(line, values) {
    if (!line || !Array.isArray(line.omitIfAllBlank)) return false;
    return line.omitIfAllBlank.every(function(ref) {
      return !String(values[ref] || "").trim();
    });
  }

  function appendSplitCopyLines(lines, line, values) {
    var ref = line.splitLinesFrom;
    if (!ref) return false;
    String(values[ref] || "").split(/\r?\n/).forEach(function(part) {
      var text = part.trim();
      if (text) {
        lines.push(renderCopyLine(line.text || "{{" + ref + "}}", values, ref, text));
      }
    });
    return true;
  }

  function renderGenericTemplateCopyText(copyFormat, values, conditionValues) {
    var lines = [];
    copyFormat.lines.forEach(function(line) {
      if (typeof line === "string") {
        lines.push(renderCopyLine(line, values));
        return;
      }
      if (line.showIf && conditionEngine && !conditionEngine.evaluateCondition(line.showIf, conditionValues || values)) return;
      if (shouldOmitCopyLine(line, values)) return;
      if (appendSplitCopyLines(lines, line, values)) return;
      lines.push(renderCopyLine(line.text || "", values));
    });
    return lines.join("\n");
  }

  return {
    renderCopyLine: renderCopyLine,
    renderGenericTemplateCopyText: renderGenericTemplateCopyText,
    shouldOmitCopyLine: shouldOmitCopyLine,
  };
});
