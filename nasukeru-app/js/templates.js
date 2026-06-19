// Template repository boundary. Keep callers using these functions so the
// backing store can change without touching app.js.
async function getJson(path) {
  var res = await fetch(path);
  if (!res.ok) throw new Error("API request failed: " + path);
  return res.json();
}

async function getTemplates() {
  return getJson("/api/templates");
}

async function getQuickTemplates() {
  return getJson("/api/quick-templates");
}

async function getRestOptions() {
  return getJson("/api/rest-options");
}
