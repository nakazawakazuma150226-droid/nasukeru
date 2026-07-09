(function(root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./condition-engine.js"), require("./blank.js"));
    return;
  }
  var renderer = factory(root.NasukeruConditionEngine, root.NasukeruBlank);
  root.NasukeruCopyRenderer = renderer;
})(typeof globalThis !== "undefined" ? globalThis : this, function(conditionEngine, blank) {
  var PLACEHOLDER_RE = /\{\{\s*([a-z0-9_-]+)\.([a-z0-9_-]+)\s*\}\}/g;

  function selectedCopyVariant(copyFormat, variantId) {
    if (!copyFormat) return null;
    if (copyFormat.format === "multi-v1" && Array.isArray(copyFormat.variants)) {
      return copyFormat.variants.find(function(variant) {
        return variant.id === variantId;
      }) || copyFormat.variants[0] || null;
    }
    if (copyFormat.format === "text-v1") {
      return { id: "default", label: "標準", lines: copyFormat.lines || [] };
    }
    return null;
  }

  function collectCopyLineOutputRefs(line, refs) {
    refs = refs || [];
    var text = typeof line === "string" ? line : (line && line.text) || "";
    var match;
    PLACEHOLDER_RE.lastIndex = 0;
    while ((match = PLACEHOLDER_RE.exec(text))) {
      var ref = match[1] + "." + match[2];
      if (refs.indexOf(ref) < 0) refs.push(ref);
    }
    if (line && typeof line === "object") {
      (line.segments || []).forEach(function(segment) {
        if (segment.ref && refs.indexOf(segment.ref) < 0) refs.push(segment.ref);
      });
      if (line.splitLinesFrom && refs.indexOf(line.splitLinesFrom) < 0) refs.push(line.splitLinesFrom);
    }
    return refs;
  }

  function collectVariantOutputRefs(copyFormat, variantId) {
    var variant = selectedCopyVariant(copyFormat, variantId);
    var refs = [];
    if (!variant) return refs;
    (variant.lines || []).forEach(function(line) {
      collectCopyLineOutputRefs(line, refs);
    });
    return refs;
  }

  function valueFor(values, ref, unresolvedRefs) {
    var value = values[ref];
    if (blank.isBlank(value)) {
      if (unresolvedRefs && unresolvedRefs.indexOf(ref) < 0) unresolvedRefs.push(ref);
      return "__";
    }
    return value;
  }

  function renderCopyLine(text, values, overrideRef, overrideValue, unresolvedRefs) {
    return String(text || "").replace(PLACEHOLDER_RE, function(match, sectionId, fieldId) {
      var ref = sectionId + "." + fieldId;
      if (ref === overrideRef) return blank.isBlank(overrideValue) ? "__" : overrideValue;
      return valueFor(values, ref, unresolvedRefs);
    });
  }

  function renderSegments(line, values) {
    if (!line || !Array.isArray(line.segments)) return null;
    var parts = [];
    line.segments.forEach(function(segment) {
      var value = values[segment.ref];
      if (blank.isBlank(value)) return;
      parts.push(String(segment.label || "") + String(value) + String(segment.suffix || ""));
    });
    if (!parts.length) return null;
    return String(line.prefix || "") + parts.join(line.separator || "");
  }

  function shouldOmitCopyLine(line, values) {
    if (!line || !Array.isArray(line.omitIfAllBlank)) return false;
    return line.omitIfAllBlank.every(function(ref) {
      return blank.isBlank(values[ref]);
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

  function renderGenericTemplateCopyResult(copyFormat, values, conditionValues, variantId) {
    var variant = selectedCopyVariant(copyFormat, variantId);
    var lines = [];
    var unresolvedRefs = [];
    if (!variant) {
      return { text: "", unresolvedRefs: [], warnings: [], variant: null, outputRefs: [] };
    }
    variant.lines.forEach(function(line) {
      if (typeof line === "string") {
        lines.push(renderCopyLine(line, values, null, null, unresolvedRefs));
        return;
      }
      if (line.showIf && conditionEngine && !conditionEngine.evaluateCondition(line.showIf, conditionValues || values)) return;
      if (shouldOmitCopyLine(line, values)) return;
      if (appendSplitCopyLines(lines, line, values, unresolvedRefs)) return;
      if (Array.isArray(line.segments)) {
        var segmentLine = renderSegments(line, values);
        if (segmentLine) lines.push(segmentLine);
        return;
      }
      lines.push(renderCopyLine(line.text || "", values, null, null, unresolvedRefs));
    });
    return {
      text: lines.join("\n"),
      unresolvedRefs: unresolvedRefs,
      warnings: [],
      variant: { id: variant.id, label: variant.label },
      outputRefs: collectVariantOutputRefs(copyFormat, variant.id),
    };
  }

  function renderGenericTemplateCopyText(copyFormat, values, conditionValues, variantId) {
    return renderGenericTemplateCopyResult(copyFormat, values, conditionValues, variantId).text;
  }

  return {
    collectVariantOutputRefs: collectVariantOutputRefs,
    renderCopyLine: renderCopyLine,
    renderGenericTemplateCopyResult: renderGenericTemplateCopyResult,
    renderGenericTemplateCopyText: renderGenericTemplateCopyText,
    selectedCopyVariant: selectedCopyVariant,
    shouldOmitCopyLine: shouldOmitCopyLine,
  };
});
