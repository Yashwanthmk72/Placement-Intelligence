const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = {
  settings: { display_name: "Student", theme: "dark", max_upload_mb: 50, store_original_files: true },
  bootstrap: null,
  history: [],
  files: [],
  currentUpload: null,
  currentFileName: null,
  lastResult: null,
  activeView: "overview",
  modalAction: null,
  historySearchTimer: null,
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}
function formatINR(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value)) || Number(value) <= 0) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
}
function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function toast(message, kind = "") {
  const node = document.createElement("div");
  node.className = `toast ${kind}`;
  node.textContent = message;
  $("#toastRoot").append(node);
  setTimeout(() => node.remove(), 3800);
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  let body;
  if (contentType.includes("application/json")) body = await response.json();
  else body = await response.text();
  if (!response.ok) {
    const detail = body && typeof body === "object" ? body.detail : body;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body;
}
function applyTheme(theme, persist = false) {
  const value = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = value;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", value === "dark" ? "#0b1020" : "#f3f5fa");
  state.settings.theme = value;
  $$("[data-theme-choice]").forEach(btn => btn.classList.toggle("active", btn.dataset.themeChoice === value));
  const glyph = value === "dark" ? "☼" : "☾";
  $("#topTheme").textContent = glyph;
  $("#sidebarTheme").textContent = glyph;
  if (persist) api("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ theme: value }) }).catch(err => toast(err.message, "error"));
}
function setDisplayName(name) {
  const display = (name || "Student").trim() || "Student";
  state.settings.display_name = display;
  $("#topDisplayName").textContent = display;
  $("#greetingName").textContent = display.split(/\s+/)[0];
  $("#avatarInitials").textContent = display.split(/\s+/).slice(0, 2).map(x => x[0]).join("").toUpperCase();
}
function showWelcome() {
  const welcome = $("#welcome");
  const shell = $("#appShell");
  if (localStorage.getItem("pi_workspace_entered") === "yes") {
    welcome.classList.add("hidden");
    shell.classList.remove("hidden");
    return;
  }
  welcome.classList.remove("hidden");
  shell.classList.add("hidden");
  $("#welcomeName").value = state.settings.display_name === "Student" ? "" : state.settings.display_name;
}
async function enterWorkspace() {
  const name = $("#welcomeName").value.trim() || "Student";
  try {
    await api("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ display_name: name }) });
  } catch (error) { toast(error.message, "error"); }
  setDisplayName(name);
  localStorage.setItem("pi_workspace_entered", "yes");
  $("#welcome").classList.add("leaving");
  setTimeout(() => {
    $("#welcome").classList.add("hidden");
    $("#appShell").classList.remove("hidden");
  }, 610);
}
function goTo(viewName) {
  if (!$("#view-" + viewName)) return;
  const current = $("#view-" + state.activeView);
  const next = $("#view-" + viewName);
  if (state.activeView === viewName) return;
  current?.classList.remove("active-view");
  if (current) current.classList.add("leaving-view");
  $$(".nav-link").forEach(btn => btn.classList.toggle("active", btn.dataset.view === viewName));
  $("#pageCrumb").textContent = ({ overview: "Overview", working: "Work with a profile", world: "Globe · Base price", history: "History", settings: "Settings" })[viewName] || viewName;
  state.activeView = viewName;
  setTimeout(() => {
    if (current) { current.classList.remove("leaving-view"); current.style.display = "none"; }
    next.style.display = "block";
    requestAnimationFrame(() => next.classList.add("active-view"));
  }, 155);
  window.worldSetActive?.(viewName === "world");
  if (viewName === "world") window.worldOpen?.();
  if (viewName === "history") loadHistory();
  if (viewName === "settings") { loadFiles(); renderSettingsModel(); }
  if (viewName === "overview") loadOverview();
}
function animateNumber(el, target, suffix = "") {
  if (!el) return;
  const end = Number(target) || 0;
  const duration = 650;
  const startTime = performance.now();
  function step(now) {
    const p = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = `${Math.round(end * eased)}${suffix}`;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function renderModel(model) {
  if (!model) {
    $("#modelStatusText").textContent = "Dataset needed";
    $("#modelHealthPill").textContent = "Not ready";
    $("#modelAccuracy").textContent = "—";
    ["#modelPrecision", "#modelRecall", "#modelF1"].forEach(sel => $(sel).textContent = "—");
    return;
  }
  const p = model.placement;
  $("#modelStatusText").textContent = "Model ready";
  $("#modelHealthPill").textContent = "Trained locally";
  $("#modelAccuracy").textContent = `${p.accuracy.toFixed(1)}%`;
  $("#modelPrecision").textContent = `${p.precision.toFixed(1)}%`;
  $("#modelRecall").textContent = `${p.recall.toFixed(1)}%`;
  $("#modelF1").textContent = `${p.f1.toFixed(1)}%`;
  $("#precisionBar").style.width = `${p.precision}%`;
  $("#recallBar").style.width = `${p.recall}%`;
  $("#f1Bar").style.width = `${p.f1}%`;
  $("#modelRows").textContent = `${p.rows.toLocaleString("en-IN")} placement records · ${p.test_rows.toLocaleString("en-IN")} held out for evaluation · salary MAE ${formatINR(model.salary.mae)}`;
  $("#quickModelRows").textContent = p.rows.toLocaleString("en-IN");
  $("#quickModelAcc").textContent = `${p.accuracy.toFixed(1)}%`;
}
function renderChart(records) {
  const host = $("#overviewChart");
  const points = [...records].slice(0, 10).reverse();
  if (!points.length) {
    host.innerHTML = `<div class="empty-chart"><div class="empty-chart-icon">⌁</div><strong>Your trend will appear here</strong><span>Complete your first profile analysis to start tracking your progress.</span></div>`;
    $("#chartPeriod").textContent = "No saved runs yet";
    return;
  }
  const w = 660, h = 206, left = 34, right = 18, top = 16, bottom = 28;
  const innerW = w - left - right, innerH = h - top - bottom;
  const xy = points.map((item, i) => ({
    x: left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW),
    y: top + innerH - (Math.max(0, Math.min(100, Number(item.probability))) / 100) * innerH,
    item,
  }));
  const polyline = xy.map(p => `${p.x},${p.y}`).join(" ");
  const area = `${left},${top + innerH} ${polyline} ${left + innerW},${top + innerH}`;
  const grid = [0, 25, 50, 75, 100].map(n => {
    const y = top + innerH - (n / 100) * innerH;
    return `<line x1="${left}" y1="${y}" x2="${w - right}" y2="${y}" stroke="var(--line)" stroke-dasharray="3 5"/><text x="2" y="${y + 3}" fill="var(--muted-2)" font-size="9">${n}</text>`;
  }).join("");
  const dots = xy.map((p, i) => `<circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--purple)" stroke="var(--panel-solid)" stroke-width="2"><title>${escapeHtml(p.item.candidate_name)}: ${Number(p.item.probability).toFixed(1)}%</title></circle>`).join("");
  const labels = xy.map((p, i) => i === 0 || i === xy.length - 1 || i === Math.floor(xy.length / 2) ? `<text x="${p.x}" y="${h - 7}" fill="var(--muted-2)" font-size="8" text-anchor="middle">${new Date(p.item.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</text>` : "").join("");
  host.innerHTML = `<svg class="history-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Placement probability history chart">${grid}<polygon points="${area}" fill="url(#chartFill)" opacity=".34"/><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--purple)"/><stop offset="1" stop-color="var(--purple)" stop-opacity="0"/></linearGradient></defs><polyline points="${polyline}" fill="none" stroke="var(--purple)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${dots}${labels}</svg>`;
  $("#chartPeriod").textContent = `${points.length} most recent run${points.length === 1 ? "" : "s"}`;
}
function renderRecent(records) {
  const host = $("#recentList");
  if (!records.length) {
    host.innerHTML = `<div class="empty-list">Your saved analyses will show up here.</div>`;
    return;
  }
  host.innerHTML = records.slice(0, 5).map(item => `
    <div class="recent-item" data-open-record="${item.id}">
      <div class="recent-person"><span class="recent-avatar">${escapeHtml((item.candidate_name || "C").slice(0,1).toUpperCase())}</span><div><div class="recent-name">${escapeHtml(item.candidate_name)}</div><div class="recent-date">${escapeHtml(formatDate(item.created_at))}</div></div></div>
      <span class="muted">${Number(item.probability).toFixed(1)}%</span>
      <span class="result-badge ${item.prediction.toLowerCase() === "placed" ? "placed" : "notplaced"}">${escapeHtml(item.prediction)}</span>
    </div>`).join("");
}
async function loadOverview() {
  try {
    const data = await api("/api/bootstrap");
    state.bootstrap = data;
    state.settings = { ...state.settings, ...data.settings };
    const s = data.summary;
    animateNumber($("#statAnalyses"), s.analyses);
    animateNumber($("#statPlaced"), s.placed);
    $("#statProbability").textContent = s.analyses ? Number(s.average_probability).toFixed(1) : "—";
    $("#statSalary").textContent = s.average_salary ? formatINR(s.average_salary) : "—";
    renderModel(data.models);
    renderChart(data.recent);
    renderRecent(data.recent);
    renderCohort(data.cohort);
    setDisplayName(state.settings.display_name);
  } catch (error) {
    toast(error.message, "error");
    $("#modelStatusText").textContent = "Model unavailable";
  }
}
function setInputValue(id, value) {
  const el = $("#" + id);
  if (!el) return;
  el.value = value === null || value === undefined ? "" : value;
}
function fillProfile(profile) {
  setInputValue("candidateName", profile.name);
  setInputValue("cgpa", profile.cgpa);
  setInputValue("twelfth", profile.twelfth);
  setInputValue("tenth", profile.tenth);
  setInputValue("backlogs", profile.backlogs);
  setInputValue("majorProjects", profile.major_projects);
  setInputValue("miniProjects", profile.mini_projects);
  setInputValue("workshops", profile.workshops);
  setInputValue("skillsCount", profile.skills_count);
  setInputValue("communication", profile.communication);
  setInputValue("internship", profile.internship || "Unknown");
  setInputValue("hackathon", profile.hackathon || "Unknown");
  setInputValue("skillsText", (profile.skills || []).join(", "));
}
function numericValue(id) {
  const value = $("#" + id).value.trim();
  return value === "" ? null : Number(value);
}
function collectProfile() {
  const skills = $("#skillsText").value.split(",").map(x => x.trim()).filter(Boolean);
  return {
    name: $("#candidateName").value.trim() || "Candidate",
    cgpa: numericValue("cgpa"),
    twelfth: numericValue("twelfth"),
    tenth: numericValue("tenth"),
    backlogs: numericValue("backlogs"),
    major_projects: numericValue("majorProjects"),
    mini_projects: numericValue("miniProjects"),
    workshops: numericValue("workshops"),
    skills_count: numericValue("skillsCount") ?? Math.min(20, skills.length),
    communication: numericValue("communication"),
    internship: $("#internship").value,
    hackathon: $("#hackathon").value,
    skills,
  };
}
function showParseStatus(message, kind = "") {
  const el = $("#parseStatus");
  el.className = `parse-status ${kind}`;
  el.textContent = message;
}
async function parseResume(file) {
  state.currentUpload = null;
  state.currentFileName = file.name;
  $("#dropTitle").textContent = file.name;
  $("#dropCaption").textContent = `${formatBytes(file.size)} · extracting profile details...`;
  showParseStatus("Reading your document and looking for profile details…");
  const body = new FormData();
  body.append("file", file);
  try {
    const parsed = await api("/api/parse-resume", { method: "POST", body });
    fillProfile(parsed.profile);
    state.resumeText = parsed.text || "";
    state.currentUpload = parsed.upload;
    showParseStatus(`${parsed.message} ${parsed.extracted_characters.toLocaleString("en-IN")} readable characters found.`, "success");
    $("#dropCaption").textContent = `${formatBytes(file.size)} · ready for review`;
    toast("Resume details extracted. Review the form before predicting.", "success");
  } catch (error) {
    showParseStatus(error.message, "error");
    $("#dropCaption").textContent = `${formatBytes(file.size)} · manual entry is available below`;
    toast(error.message, "error");
  }
}
function renderResult(data) {
  const result = data.result;
  const placed = String(result.prediction).toLowerCase() === "placed";
  $("#resultPrediction").textContent = result.prediction;
  $("#resultPrediction").classList.toggle("notplaced", !placed);
  $("#resultSummary").textContent = placed ? "The model classified this profile in the Placed category." : "The model classified this profile in the NotPlaced category.";
  $("#resultProbability").textContent = `${Number(result.probability).toFixed(1)}%`;
  $("#probabilityRing").style.setProperty("--probability", `${Number(result.probability)}%`);
  $("#resultSalary").textContent = formatINR(result.salary);
  $("#resultScore").textContent = `${result.resume_score}/100`;
  $("#resultId").textContent = `#${data.id}`;
  $("#reportDownload").href = data.report_url;
  $("#resultNotice").textContent = data.notice;
  $("#missingSkills").innerHTML = data.recommendations.missing_skills.length
    ? data.recommendations.missing_skills.map(skill => `<span class="skill-chip">${escapeHtml(skill)}</span>`).join("")
    : `<span class="skill-chip">No priority skill gaps from the current checklist</span>`;
  $("#projectIdeas").innerHTML = data.recommendations.projects.map(project => `<div class="suggestion-card"><strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.difficulty)} · ${escapeHtml(project.technology)}</small></div>`).join("");
  $("#roadmapList").innerHTML = data.recommendations.roadmap.map(item => `<div class="roadmap-item"><span>${escapeHtml(item.week)}</span><strong>${escapeHtml(item.skill)}</strong><p>${escapeHtml(item.task)}</p></div>`).join("");
  $("#analysisResult").classList.remove("hidden");
  state.lastResult = data;
  setTimeout(() => $("#analysisResult").scrollIntoView({ behavior: "smooth", block: "start" }), 80);
}
async function submitAnalysis(event) {
  event.preventDefault();
  const button = $("#analyzeButton");
  button.disabled = true;
  button.textContent = "Analysing profile…";
  try {
    const data = await api("/api/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: collectProfile(), upload_id: state.currentUpload?.id || null, file_name: state.currentFileName || state.currentUpload?.name || null }),
    });
    renderResult(data);
    if (Number(data.result.probability) >= 60) window.confetti?.();
    toast("Analysis saved to your history.", "success");
    await loadOverview();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = `Generate placement analysis <span>↗</span>`;
  }
}
function renderHistory(records) {
  state.history = records;
  const placed = records.filter(x => String(x.prediction).toLowerCase() === "placed").length;
  const avgProb = records.length ? records.reduce((a,x) => a + Number(x.probability), 0) / records.length : 0;
  const avgSalary = records.filter(x => Number(x.salary) > 0);
  $("#historySummary").innerHTML = `
    <div class="history-summary-card"><span>Saved analyses</span><strong>${records.length}</strong></div>
    <div class="history-summary-card"><span>Placed classifications</span><strong>${placed}</strong></div>
    <div class="history-summary-card"><span>Average placed probability</span><strong>${records.length ? avgProb.toFixed(1) + "%" : "—"}</strong></div>`;
  $("#historyCount").textContent = `${records.length} record${records.length === 1 ? "" : "s"}`;
  const tbody = $("#historyTableBody");
  if (!records.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-table">No saved analyses found. Run a prediction from Work with a profile.</td></tr>`;
    return;
  }
  tbody.innerHTML = records.map(item => `
    <tr data-record="${item.id}">
      <td>${escapeHtml(item.candidate_name)}</td><td>${escapeHtml(formatDate(item.created_at))}</td>
      <td><span class="result-badge ${String(item.prediction).toLowerCase() === "placed" ? "placed" : "notplaced"}">${escapeHtml(item.prediction)}</span></td>
      <td>${Number(item.probability).toFixed(1)}%</td><td>${escapeHtml(formatINR(item.salary))}</td><td>${item.resume_score}/100</td><td class="table-action">View ↗</td>
    </tr>`).join("");
}
async function loadHistory(query = "") {
  try {
    const [records, cohort] = await Promise.all([
      api(`/api/history?limit=500&q=${encodeURIComponent(query)}`),
      api("/api/cohort"),
    ]);
    renderHistory(records);
    renderCohort(cohort);
  } catch (error) { toast(error.message, "error"); }
}
function renderCohort(cohort) {
  const host = $("#cohortSnapshot");
  if (!cohort || !cohort.ready) {
    host.innerHTML = `<div class="empty-list">Training cohort data is unavailable. Check the datasets in Settings.</div>`;
    return;
  }
  const rate = Number(cohort.placement_rate || 0);
  const total = Math.max(1, Number(cohort.total_students || 0));
  host.innerHTML = `
    <div class="cohort-stat"><span>Total students in dataset</span><strong>${Number(cohort.total_students).toLocaleString("en-IN")}</strong><small>Historical training rows</small></div>
    <div class="cohort-stat"><span>Previously placed</span><strong class="cohort-green">${Number(cohort.placed_count).toLocaleString("en-IN")}</strong><small>${(Number(cohort.placed_count) / total * 100).toFixed(1)}% of labelled records</small></div>
    <div class="cohort-stat"><span>Not placed</span><strong>${Number(cohort.not_placed_count).toLocaleString("en-IN")}</strong><small>${(Number(cohort.not_placed_count) / total * 100).toFixed(1)}% of labelled records</small></div>
    <div class="cohort-stat"><span>Historical placement rate</span><strong>${rate.toFixed(1)}%</strong><div class="cohort-track"><i style="width:${Math.max(0, Math.min(100, rate))}%"></i></div></div>
    <div class="cohort-stat"><span>Median salary · placed students</span><strong>${escapeHtml(formatINR(cohort.median_salary))}</strong><small>${Number(cohort.salary_records).toLocaleString("en-IN")} positive salary records</small></div>
    <div class="cohort-stat"><span>Average salary · placed students</span><strong>${escapeHtml(formatINR(cohort.average_salary))}</strong><small>Historical dataset average</small></div>`;
}
async function showHistoryDetail(id) {
  try {
    const item = await api(`/api/history/${id}`);
    const profile = item.profile || {};
    const metrics = item.model_metrics?.placement || {};
    $("#historyDetail").innerHTML = `
      <div class="panel-heading"><div><p class="eyebrow">SAVED ANALYSIS #${item.id}</p><h2>${escapeHtml(item.candidate_name)}</h2><p class="panel-subtitle">${escapeHtml(formatDate(item.created_at))} · ${escapeHtml(item.file_name || "Manual profile entry")}</p></div><button class="button button-quiet button-small" id="closeHistoryDetail">Close ×</button></div>
      <div class="detail-grid"><div class="detail-cell"><span>Prediction</span><strong>${escapeHtml(item.prediction)}</strong></div><div class="detail-cell"><span>Placed probability estimate</span><strong>${Number(item.probability).toFixed(1)}%</strong></div><div class="detail-cell"><span>Salary estimate</span><strong>${escapeHtml(formatINR(item.salary))}</strong></div><div class="detail-cell"><span>Resume score</span><strong>${item.resume_score}/100</strong></div></div>
      <h3>Profile inputs</h3><div class="detail-grid">${[
        ["CGPA", profile.cgpa], ["12th %", profile.twelfth], ["10th %", profile.tenth], ["Backlogs", profile.backlogs],
        ["Major projects", profile.major_projects], ["Mini projects", profile.mini_projects], ["Workshops", profile.workshops], ["Skill groups", profile.skills_count],
        ["Internship", profile.internship], ["Hackathon", profile.hackathon], ["Communication", profile.communication], ["Detected skills", (profile.skills || []).join(", ") || "—"]
      ].map(([label,value]) => `<div class="detail-cell"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value ?? "Not provided")}</strong></div>`).join("")}</div>
      <p class="panel-subtitle">Placement validation accuracy on this dataset: ${Number(metrics.accuracy || 0).toFixed(1)}%. Historical records preserve the model metrics used at the time of prediction.</p>
      ${item.has_report ? `<a class="button button-primary" href="/api/reports/${item.id}" target="_blank">Download saved report ↓</a>` : ""}`;
    $("#historyDetail").classList.remove("hidden");
    $("#closeHistoryDetail").addEventListener("click", () => $("#historyDetail").classList.add("hidden"));
    $("#historyDetail").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) { toast(error.message, "error"); }
}
function showConfirm(title, message, action, confirmText = "Confirm") {
  state.modalAction = action;
  $("#modalTitle").textContent = title;
  $("#modalText").textContent = message;
  $("#modalConfirm").textContent = confirmText;
  $("#modalLayer").classList.remove("hidden");
}
function hideConfirm() { $("#modalLayer").classList.add("hidden"); state.modalAction = null; }
async function clearHistory() {
  try {
    const result = await api("/api/history", { method: "DELETE" });
    $("#historyDetail").classList.add("hidden");
    toast(`${result.deleted} history report(s) removed.`, "success");
    await loadHistory(); await loadOverview();
  } catch (error) { toast(error.message, "error"); }
}
async function loadSettings() {
  try {
    state.settings = await api("/api/settings");
    setDisplayName(state.settings.display_name);
    $("#settingName").value = state.settings.display_name;
    $("#settingMaxUpload").value = String(state.settings.max_upload_mb);
    $("#settingStoreFiles").checked = Boolean(state.settings.store_original_files);
    applyTheme(state.settings.theme);
    renderSettingsModel();
  } catch (error) { toast(error.message, "error"); }
}
async function saveSettings() {
  const payload = {
    display_name: $("#settingName").value.trim() || "Student",
    theme: document.documentElement.dataset.theme,
    max_upload_mb: Number($("#settingMaxUpload").value),
    store_original_files: $("#settingStoreFiles").checked,
  };
  try {
    state.settings = await api("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setDisplayName(state.settings.display_name);
    $("#settingsSaved").textContent = "Saved successfully";
    setTimeout(() => $("#settingsSaved").textContent = "", 2500);
    toast("Workspace preferences saved.", "success");
  } catch (error) { toast(error.message, "error"); }
}
function renderSettingsModel() {
  const model = state.bootstrap?.models;
  if (!model) { $("#settingsModelMetrics").textContent = "Model not ready. Upload valid placement and salary datasets."; return; }
  $("#settingsModelMetrics").textContent = `Current placement data: ${model.placement.rows.toLocaleString("en-IN")} rows · accuracy ${model.placement.accuracy.toFixed(2)}% · salary training rows ${model.salary.rows.toLocaleString("en-IN")} · salary MAE ${formatINR(model.salary.mae)}.`;
}
async function uploadDataset(kind) {
  const input = kind === "placement" ? $("#placementDataset") : $("#salaryDataset");
  const status = $("#datasetStatus");
  const file = input.files[0];
  if (!file) { toast(`Choose the ${kind} dataset first.`, "error"); return; }
  status.className = "dataset-status";
  status.textContent = "Validating dataset and retraining both models…";
  const body = new FormData(); body.append("file", file);
  try {
    const result = await api(`/api/datasets/${kind}`, { method: "POST", body });
    status.className = "dataset-status success";
    status.textContent = `${result.message} Placement accuracy: ${result.placement_metrics.accuracy.toFixed(2)}%. Salary MAE: ${formatINR(result.salary_metrics.mae)}.`;
    input.value = "";
    await loadOverview();
    renderSettingsModel();
    toast("Training data updated successfully.", "success");
  } catch (error) {
    status.className = "dataset-status error";
    status.textContent = error.message;
    toast(error.message, "error");
  }
}
async function loadFiles() {
  try {
    state.files = await api("/api/files");
    const host = $("#libraryList");
    if (!state.files.length) { host.innerHTML = `<div class="empty-list">No files stored yet.</div>`; return; }
    host.innerHTML = state.files.map(file => {
      const ext = (file.name.split(".").pop() || "FILE").slice(0, 5).toUpperCase();
      return `<div class="library-item"><span class="file-type-icon">${escapeHtml(ext)}</span><div class="library-item-main"><strong title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</strong><small>${escapeHtml(file.category)} · ${formatBytes(file.size_bytes)} · ${escapeHtml(formatDate(file.uploaded_at))}</small></div><a class="library-action" href="/api/files/${file.id}/download">↓</a><button class="library-action" data-delete-file="${file.id}" title="Delete file">×</button></div>`;
    }).join("");
  } catch (error) { toast(error.message, "error"); }
}
async function uploadLibraryFile(file) {
  const body = new FormData(); body.append("file", file);
  try {
    await api("/api/upload", { method: "POST", body });
    toast("File added to your local library.", "success");
    await loadFiles();
    await loadOverview();
  } catch (error) { toast(error.message, "error"); }
}
async function deleteLibraryFile(id) {
  try {
    await api(`/api/files/${id}`, { method: "DELETE" });
    toast("File removed from local library.", "success");
    await loadFiles(); await loadOverview();
  } catch (error) { toast(error.message, "error"); }
}
function resetProfile() {
  $("#profileForm").reset();
  state.currentUpload = null;
  state.currentFileName = null;
  $("#dropTitle").textContent = "Drop your resume here";
  $("#dropCaption").innerHTML = `or <u>browse files</u> from your computer`;
  $("#parseStatus").classList.add("hidden");
}

// Navigation and global controls.
$$(".nav-link").forEach(btn => btn.addEventListener("click", () => goTo(btn.dataset.view)));
document.addEventListener("click", event => {
  const go = event.target.closest("[data-go]");
  if (go) goTo(go.dataset.go);
  const openRecord = event.target.closest("[data-open-record], tr[data-record]");
  if (openRecord) { goTo("history"); setTimeout(() => showHistoryDetail(openRecord.dataset.openRecord || openRecord.dataset.record), 190); }
  const deleteFile = event.target.closest("[data-delete-file]");
  if (deleteFile) { event.stopPropagation(); showConfirm("Remove this file?", "The selected file will be permanently removed from your local file library.", () => deleteLibraryFile(deleteFile.dataset.deleteFile), "Remove file"); }
});
$("#enterWorkspace").addEventListener("click", enterWorkspace);
$("#welcomeName").addEventListener("keydown", e => { if (e.key === "Enter") enterWorkspace(); });
["#topTheme", "#sidebarTheme"].forEach(selector => $(selector).addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true)));
$$("[data-theme-choice]").forEach(btn => btn.addEventListener("click", () => applyTheme(btn.dataset.themeChoice, true)));
$("#resumeFile").addEventListener("change", event => { const file = event.target.files[0]; if (file) parseResume(file); });
const drop = $("#resumeDrop");
["dragenter", "dragover"].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add("dragover"); }));
["dragleave", "drop"].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove("dragover"); }));
drop.addEventListener("drop", event => { const file = event.dataTransfer.files[0]; if (file) parseResume(file); });
$("#profileForm").addEventListener("submit", submitAnalysis);
$("#resetProfile").addEventListener("click", resetProfile);
$("#historySearch").addEventListener("input", () => {
  clearTimeout(state.historySearchTimer);
  state.historySearchTimer = setTimeout(() => loadHistory($("#historySearch").value), 260);
});
$("#refreshHistory").addEventListener("click", () => loadHistory($("#historySearch").value));
$("#clearHistory").addEventListener("click", () => showConfirm("Clear all analysis history?", "This permanently deletes all saved prediction records and generated report PDFs. Files in your file library will remain.", clearHistory, "Delete history"));
$("#settingsClearHistory").addEventListener("click", () => showConfirm("Delete all saved history?", "This permanently deletes all saved prediction records and generated report PDFs. Files in your file library will remain.", async () => { await clearHistory(); goTo("history"); }, "Delete history"));
$("#saveSettings").addEventListener("click", saveSettings);
$("#uploadPlacementDataset").addEventListener("click", () => uploadDataset("placement"));
$("#uploadSalaryDataset").addEventListener("click", () => uploadDataset("salary"));
$("#libraryFile").addEventListener("change", event => { const file = event.target.files[0]; if (file) uploadLibraryFile(file); event.target.value = ""; });
$("#modalCancel").addEventListener("click", hideConfirm);
$("#modalConfirm").addEventListener("click", async () => { const action = state.modalAction; hideConfirm(); if (action) await action(); });
$("#modalLayer").addEventListener("click", event => { if (event.target === $("#modalLayer")) hideConfirm(); });

async function init() {
  try {
    const data = await api("/api/bootstrap");
    state.bootstrap = data;
    state.settings = { ...state.settings, ...data.settings };
    applyTheme(state.settings.theme);
    setDisplayName(state.settings.display_name);
    showWelcome();
    renderModel(data.models);
    renderChart(data.recent);
    renderRecent(data.recent);
    $("#statAnalyses").textContent = data.summary.analyses;
    $("#statPlaced").textContent = data.summary.placed;
    $("#statProbability").textContent = data.summary.analyses ? Number(data.summary.average_probability).toFixed(1) : "—";
    $("#statSalary").textContent = data.summary.average_salary ? formatINR(data.summary.average_salary) : "—";
    await loadSettings();
    if (!modelsReady(data.models)) toast("Model datasets need attention. Open Settings to upload valid CSV or Excel files.", "error");
  } catch (error) {
    showWelcome();
    toast(`Could not connect to the local server: ${error.message}`, "error");
  }
}
function modelsReady(model) { return Boolean(model && model.placement && model.salary); }
init();
