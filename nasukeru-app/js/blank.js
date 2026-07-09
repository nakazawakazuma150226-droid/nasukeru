(function(root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.NasukeruBlank = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  function isBlank(value) {
    if (Array.isArray(value)) return value.length === 0;
    if (value === null || value === undefined) return true;
    if (typeof value === "number") return false;
    return !String(value).trim();
  }

  return {
    isBlank: isBlank,
  };
});
