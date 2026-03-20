/**
 * Support Intake AI — Frontend Orchestrator
 */

import { analyzeFile, fetchHistory, updateHistoryItem } from "./api/api.js";
import { store } from "./state/store.js";
import { renderResults, updateDashboardUI, showToast, escapeHtml } from "./ui/render.js";

// ── DOM refs ──────────────────────────────────────────────────────────────────
const dropZone        = document.getElementById("dropZone");
const fileInput       = document.getElementById("fileInput");
const filePreview     = document.getElementById("filePreview");
const fileName        = document.getElementById("fileName");
const fileSize        = document.getElementById("fileSize");
const fileTypeIcon    = document.getElementById("fileTypeIcon");
const clearFileBtn    = document.getElementById("clearFile");
const analyzeBtn      = document.getElementById("analyzeBtn");

const uploadSection   = document.getElementById("uploadSection");
const processingSection = document.getElementById("processingSection");
const resultsSection  = document.getElementById("resultsSection");
const newAnalysisBtn  = document.getElementById("newAnalysisBtn");

const headerChartArea = document.getElementById("headerChartArea");
const currentViewTitle = document.getElementById("currentViewTitle");

// Sidebar & Tabs
const sidebarEl       = document.getElementById("sidebar");
const menuToggleBtn   = document.getElementById("menuToggle");
const sidebarOverlay  = document.getElementById("sidebarOverlay");
const sidebarBtns     = document.querySelectorAll(".sidebar-btn");
const tabDashboard    = document.getElementById("tabDashboard");
const tabUpload       = document.getElementById("tabUpload");
const viewDashboard   = document.getElementById("viewDashboard");
const viewUpload      = document.getElementById("viewUpload");

// Search & KPIs
const searchInput     = document.getElementById("historySearch");
const kpiCards        = document.querySelectorAll(".kpi-card");
const historyTableBody = document.getElementById("historyTableBody");

// Edit Modal
const editModal       = document.getElementById("editModal");
const closeModalBtn   = document.getElementById("closeModal");
const cancelEditBtn   = document.getElementById("cancelEdit");
const saveEditBtn     = document.getElementById("saveEdit");
const editReporter    = document.getElementById("editReporter");
const editDevice      = document.getElementById("editDevice");
const editDescription = document.getElementById("editDescription");
const editPriority    = document.getElementById("editPriority");
const editStatus      = document.getElementById("editStatus");


let selectedFile = null;
let currentEditIndex = null;
const STEPS = ["step1", "step2", "step3", "step4"];


// ── File Selection ────────────────────────────────────────────────────────────
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function getFileIcon(ext) {
  const icons = { pdf: "📕", png: "🖼️", jpg: "🖼️", jpeg: "🖼️", txt: "📄" };
  return icons[ext.replace(".", "")] || "📎";
}

function validateFile(file) {
  const ALLOWED = [".pdf", ".png", ".jpg", ".jpeg", ".txt"];
  const MAX_SIZE = 5 * 1024 * 1024;
  const ext = "." + file.name.split(".").pop().toLowerCase();

  if (!ALLOWED.includes(ext)) {
    return `Tipo de archivo no permitido: "${ext}". Formatos aceptados: PDF, PNG, JPG, TXT.`;
  }
  if (file.size > MAX_SIZE) {
    return `El archivo es demasiado grande (${formatBytes(file.size)}). Máximo: 5 MB.`;
  }
  if (file.size === 0) {
    return "El archivo está vacío. Por favor selecciona un archivo válido.";
  }
  if (file.name.includes("..") || file.name.includes("/") || file.name.includes("\\")) {
    return "El nombre del archivo contiene caracteres no permitidos.";
  }
  return null;
}

function showClientError(errText) {
  let ce = document.getElementById("clientError");
  if (!ce) {
    ce = document.createElement("div");
    ce.id = "clientError";
    ce.style.color = "var(--error)";
    ce.style.fontSize = "0.85rem";
    ce.style.marginTop = "8px";
    dropZone.parentNode.insertBefore(ce, dropZone.nextSibling);
  }
  ce.textContent = `⚠️ ${errText}`;
}

function setFile(file) {
  const error = validateFile(file);
  const ce = document.getElementById("clientError");
  if (ce) ce.remove();

  if (error) {
    showClientError(error);
    return;
  }

  selectedFile = file;
  const ext = "." + file.name.split(".").pop().toLowerCase();

  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  fileTypeIcon.textContent = getFileIcon(ext);

  filePreview.classList.remove("hidden");
  analyzeBtn.disabled = false;
}

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  filePreview.classList.add("hidden");
  analyzeBtn.disabled = true;
  if (viewUpload && viewUpload.classList.contains("active")) {
    uploadSection.scrollIntoView({ behavior: "smooth" });
  }
}

// Drag & Drop
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });
fileInput.addEventListener("change", (e) => { if (e.target.files.length) setFile(e.target.files[0]); });
dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const files = e.dataTransfer?.files;
  if (files && files.length) setFile(files[0]);
});
clearFileBtn.addEventListener("click", clearFile);


// ── Processing Steps ──────────────────────────────────────────────────────────
function setStepStatus(stepId, status) {
  const step = document.getElementById(stepId);
  if (!step) return;
  step.className = "step " + (status === "done" ? "done" : status === "running" ? "active" : "");
  const statusEl = step.querySelector(".step-status");
  statusEl.className = "step-status " + status;
  const labels = { pending: "Pendiente", running: "Procesando...", done: "✓ Completado", error: "Error" };
  statusEl.textContent = labels[status] || status;
}

async function animateSteps() {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const delays = [200, 600, 1200, 1900];
  for (let i = 0; i < STEPS.length; i++) {
    await sleep(delays[i]);
    setStepStatus(STEPS[i], "running");
  }
}

function completeSteps(isError) {
  STEPS.forEach((s) => setStepStatus(s, isError ? "error" : "done"));
}

function resetToUpload() {
  clearFile();
  resultsSection.classList.add("hidden");
  processingSection.classList.add("hidden");
  switchTab("upload");
  uploadSection.scrollIntoView({ behavior: "smooth" });
  STEPS.forEach((s) => setStepStatus(s, "pending"));
}
newAnalysisBtn.addEventListener("click", resetToUpload);


// ── Analyze Action ────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  const ce = document.getElementById("clientError");
  if (ce) ce.remove();

  uploadSection.classList.add("hidden");
  resultsSection.classList.add("hidden");
  processingSection.classList.remove("hidden");
  STEPS.forEach((s) => setStepStatus(s, "pending"));
  animateSteps();

  let data = null;
  let fetchError = false;

  try {
    data = await analyzeFile(selectedFile);
  } catch (err) {
    fetchError = true;
    data = {
      status: "error",
      document_type: "unknown",
      summary: "No se pudo conectar con el servidor.",
      extracted_data: {},
      warnings: [`Error de conexión: ${err.message}`],
      needs_clarification: false,
      clarifying_questions: [],
      tool_trace: [],
    };
  }

  completeSteps(fetchError || data.status === "error");
  renderResults(data);

  if (!fetchError && data.status !== "error") {
    showToast("success", "Análisis Exitoso", "El ticket ha sido procesado correctamente.");
  } else if (data.status === "error") {
    showToast("error", "Error", "Hubo un problema procesando el ticket.");
  }

  processingSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth" });

  loadHistory();
});


// ── Dashboard Loading ─────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const data = await fetchHistory();
    store.setHistory(Array.isArray(data) ? data : (data.history || []));
  } catch (err) {
    console.error("Error loading history:", err);
    showToast("error", "Error", "No se pudo cargar el dashboard de historial.");
  }
}

store.subscribe(() => {
  updateDashboardUI();
});


// ── Search & Filter Events ────────────────────────────────────────────────────
if (searchInput) {
  searchInput.addEventListener("input", (e) => store.setSearch(e.target.value));
}

kpiCards.forEach(card => {
  card.addEventListener('click', () => {
    store.setFilter(card.getAttribute('data-filter'));
  });
});


// ── Edit Logic ────────────────────────────────────────────────────────────────
function openEditModal(index) {
  const item = store.getHistory()[index];
  if (!item) return;

  currentEditIndex = index;
  editReporter.value = item.extracted_data?.reporter_name || "";
  editDevice.value = item.extracted_data?.device_or_system || "";
  editDescription.value = item.extracted_data?.problem_description || "";
  editPriority.value = item.extracted_data?.priority || "Media";
  editStatus.value = item.status || "success";

  editModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeEditModal() {
  editModal.classList.add("hidden");
  document.body.style.overflow = "auto";
  currentEditIndex = null;
}

if (closeModalBtn) closeModalBtn.addEventListener("click", closeEditModal);
if (cancelEditBtn) cancelEditBtn.addEventListener("click", closeEditModal);
window.addEventListener("click", (e) => { if (e.target === editModal) closeEditModal(); });

// Event delegation for dynamically created "Corregir" buttons in table
if (historyTableBody) {
  historyTableBody.addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON" && e.target.classList.contains("btn-edit")) {
      const idx = e.target.getAttribute("data-index");
      if (idx !== null) openEditModal(parseInt(idx, 10));
    }
  });
}

if (saveEditBtn) saveEditBtn.addEventListener("click", async () => {
  if (currentEditIndex === null) return;

  const historyData = store.getHistory();
  const updatedData = {
    status: editStatus.value,
    extracted_data: {
      ...historyData[currentEditIndex].extracted_data,
      reporter_name: editReporter.value,
      device_or_system: editDevice.value,
      problem_description: editDescription.value,
      priority: editPriority.value
    },
    needs_clarification: editStatus.value === "needs_review",
    clarifying_questions: editStatus.value === "needs_review" ? historyData[currentEditIndex].clarifying_questions : []
  };

  saveEditBtn.disabled = true;
  saveEditBtn.textContent = "Guardando...";

  try {
    await updateHistoryItem(currentEditIndex, updatedData);
    showToast("success", "Actualizado", "El ticket ha sido corregido manualmente.");
    closeEditModal();
    loadHistory();
  } catch (err) {
    console.error("Error saving changes:", err);
    showToast("error", "Error", "No se pudo guardar la corrección.");
  } finally {
    saveEditBtn.disabled = false;
    saveEditBtn.textContent = "Guardar Cambios";
  }
});


// ── Navigation & Sidebar ──────────────────────────────────────────────────────
function switchTab(tabId) {
  if (tabId === "dashboard") {
    tabDashboard.classList.add("active");
    tabUpload.classList.remove("active");
    viewDashboard.classList.add("active");
    viewUpload.classList.remove("active");
    uploadSection.classList.add("hidden");
    
    currentViewTitle.textContent = "Dashboard Informativo";
    headerChartArea.classList.remove("hidden");
    
    // Auto-load history on dashboard enter if empty
    if (store.getHistory().length === 0) loadHistory();
  } else {
    tabUpload.classList.add("active");
    tabDashboard.classList.remove("active");
    viewUpload.classList.add("active");
    viewDashboard.classList.remove("active");
    if (resultsSection && !resultsSection.classList.contains("hidden")) {
      uploadSection.classList.add("hidden");
    } else {
      uploadSection.classList.remove("hidden");
    }
    
    currentViewTitle.textContent = "Nuevo Análisis";
    headerChartArea.classList.add("hidden");
  }
}

if (sidebarBtns.length) {
  sidebarBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab(btn.id === "tabDashboard" ? "dashboard" : "upload");
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
}

function openSidebar() {
  if (!sidebarEl || !menuToggleBtn || !sidebarOverlay) return;
  sidebarEl.classList.add("open");
  menuToggleBtn.classList.add("open");
  menuToggleBtn.setAttribute("aria-expanded", "true");
  sidebarOverlay.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeSidebar() {
  if (!sidebarEl || !menuToggleBtn || !sidebarOverlay) return;
  sidebarEl.classList.remove("open");
  menuToggleBtn.classList.remove("open");
  menuToggleBtn.setAttribute("aria-expanded", "false");
  sidebarOverlay.classList.remove("active");
  if (editModal && editModal.classList.contains("hidden")) {
    document.body.style.overflow = "";
  }
}

if (menuToggleBtn) menuToggleBtn.addEventListener("click", () => sidebarEl.classList.contains("open") ? closeSidebar() : openSidebar());
if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebar);

// ── App Init ──────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  loadHistory();
});
