(function(root, factory) {
  var renderer = factory(root.NasukeruConditionEngine);
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./condition-engine.js"));
  }
  root.NasukeruCopyRenderer = renderer;
})(typeof globalThis !== "undefined" ? globalThis : this, function(conditionEngine) {
  var PLACEHOLDER_RE = /\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}/g;

  function isBlank(value) {
    if (Array.isArray(value)) return value.length === 0;
    if (value === null || value === undefined) return true;
    if (typeof value === "number") return false;
    return !String(value).trim();
  }

  function valueFor(values, ref, unresolvedRefs) {
    var value = values[ref];
    if (isBlank(value)) {
      if (unresolvedRefs && unresolvedRefs.indexOf(ref) < 0) unresolvedRefs.push(ref);
      return "__";
    }
    return value;
  }

  function renderCopyLine(text, values, overrideRef, overrideValue, unresolvedRefs) {
    return String(text || "").replace(PLACEHOLDER_RE, function(match, sectionId, fieldId) {
      var ref = sectionId + "." + fieldId;
      if (ref === overrideRef) return isBlank(overrideValue) ? "__" : overrideValue;
      return valueFor(values, ref, unresolvedRefs);
    });
  }

  function shouldOmitCopyLine(line, values) {
    if (!line || !Array.isArray(line.omitIfAllBlank)) return false;
    return line.omitIfAllBlank.every(function(ref) {
      return isBlank(values[ref]);
    });
  }

  function appendSplitCopyLines(lines, line, values, unresolvedRefs) {
    var ref = line.splitLinesFrom;
    if (!ref) return false;
    String(values[ref] || "").split(/\r?\n/).forEach(function(part) {
      var text = part.trim();
      if (text) {
        lines.push(renderCopyLine(line.text || "{{" + ref + "}}", values, ref, text, unresolvedRefs));
      }
    });
    return true;
  }

  function renderGenericTemplateCopyResult(copyFormat, values, conditionValues) {
    var lines = [];
    var unresolvedRefs = [];
    copyFormat.lines.forEach(function(line) {
      if (typeof line === "string") {
        lines.push(renderCopyLine(line, values, null, null, unresolvedRefs));
        return;
      }
      if (line.showIf && conditionEngine && !conditionEngine.evaluateCondition(line.showIf, conditionValues || values)) return;
      if (shouldOmitCopyLine(line, values)) return;
      if (appendSplitCopyLines(lines, line, values, unresolvedRefs)) return;
      lines.push(renderCopyLine(line.text || "", values, null, null, unresolvedRefs));
    });
    return {
      text: lines.join("\n"),
      unresolvedRefs: unresolvedRefs,
      warnings: [],
    };
  }

  function renderGenericTemplateCopyText(copyFormat, values, conditionValues) {
    return renderGenericTemplateCopyResult(copyFormat, values, conditionValues).text;
  }

  return {
    renderCopyLine: renderCopyLine,
    renderGenericTemplateCopyResult: renderGenericTemplateCopyResult,
    renderGenericTemplateCopyText: renderGenericTemplateCopyText,
    shouldOmitCopyLine: shouldOmitCopyLine,
  };
});
