// Template repository boundary. Keep callers using these functions so the
// backing store can change without touching app.js.
async function getJson(path) {
  var res = await fetch(path);
  if (!res.ok) throw new Error("API request failed: " + path);
  return res.json();
}

async function sendJson(path, options) {
  var res = await fetch(path, options || {});
  var data = null;
  try {
    data = await res.json();
  } catch (error) {
    data = null;
  }
  if (!res.ok) {
    var message = data && (data.detail || data.error) ? (data.detail || data.error) : "API request failed: " + path;
    var apiError = new Error(message);
    apiError.status = res.status;
    apiError.data = data;
    throw apiError;
  }
  return data;
}

async function postJson(path, payload) {
  return sendJson(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Nasukeru-Local": "1"
    },
    body: JSON.stringify(payload)
  });
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

async function getSearchKeywords() {
  return getJson("/api/search-keywords");
}

async function getTemplateGroup(id) {
  return getJson("/api/template-groups/" + encodeURIComponent(id));
}

async function getAdminTemplates() {
  return getJson("/api/admin/templates");
}

async function getTemplateDetail(id) {
  return getJson("/api/admin/templates/" + encodeURIComponent(id));
}

async function getTemplateVersions(id) {
  return getJson("/api/templates/" + encodeURIComponent(id) + "/versions");
}

async function getTemplateVersion(id, versionId) {
  return getJson("/api/templates/" + encodeURIComponent(id) + "/versions/" + encodeURIComponent(versionId));
}

async function getTemplateLogs(id) {
  return getJson("/api/templates/" + encodeURIComponent(id) + "/logs");
}

async function createTemplate(payload) {
  return postJson("/api/templates", payload);
}

async function createTemplateVersion(id, payload) {
  return postJson("/api/templates/" + encodeURIComponent(id) + "/versions", payload);
}

async function deleteTemplate(id, reason) {
  return postJson("/api/templates/" + encodeURIComponent(id) + "/delete", { reason: reason });
}

async function restoreTemplate(id, reason) {
  return postJson("/api/templates/" + encodeURIComponent(id) + "/restore", { reason: reason });
}
