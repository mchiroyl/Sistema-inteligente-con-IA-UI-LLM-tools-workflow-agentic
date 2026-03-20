/**
 * Support Intake AI — UI Rendering
 * Handles DOM updates for results, history table, KPIs, and toasts.
 */

import { store } from "../state/store.js";
import { updateTrafficLight } from "./traffic_light.js";

// ── DOM refs ──────────────────────────────────────────────────────────────────
const resultsSection  = document.getElementById("resultsSection");
const statusBanner    = document.getElementById("statusBanner");
const summaryText     = document.getElementById("summaryText");
const docTypeBadge    = document.getElementById("docTypeBadge");
const extractedData   = document.getElementById("extractedDataContainer");
const priorityInfo    = document.getElementById("priorityInfo");
const warningsList    = document.getElementById("warningsList");
const warningsCard    = document.getElementById("warningsCard");
const clarificationCard = document.getElementById("clarificationCard");
const questionsList   = document.getElementById("questionsList");
const toolTraceContainer = document.getElementById("toolTraceContainer");
const tbody           = document.getElementById("historyTableBody");
const emptyState      = document.getElementById("historyTableEmpty");

// ── Helpers ───────────────────────────────────────────────────────────────────
export function escapeHtml(str) {
  if (typeof str !== "string") str = String(str ?? "");
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function makeDataItem(label, value) {
  const div = document.createElement("div");
  div.className = "data-item";
  div.innerHTML = `
    <span class="data-label">${escapeHtml(label)}</span>
    <span class="data-value">${escapeHtml(String(value))}</span>`;
  return div;
}

function priorityEmoji(p) {
  const map = { "Crítica": "🔴", "Alta": "🟠", "Media": "🟡", "Baja": "🟢" };
  return map[p] || "⚪";
}

function formatDocType(t) {
  const map = {
    support_document: "📋 Ticket de Soporte",
    lab_result:       "🧪 Resultado de Laboratorio",
    academic_document:"📚 Documento Académico",
    medical_document: "🏥 Documento Médico",
    other:            "📄 Otro",
    unknown:          "❓ Desconocido",
  };
  return map[t] || t;
}

// ── Toasts ────────────────────────────────────────────────────────────────────
export function showToast(type, title, message) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  
  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
  
  toast.innerHTML = `
    <div style="font-size:1.2rem">${icons[type] || icons.info}</div>
    <div style="display:flex;flex-direction:column;gap:4px;">
      <strong style="font-size:0.85rem">${escapeHtml(title)}</strong>
      <span style="font-size:0.8rem;color:var(--text-secondary)">${escapeHtml(message)}</span>
    </div>
  `;
  
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast-exiting");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── Render Results ────────────────────────────────────────────────────────────
export function renderResults(data) {
  // Status banner
  const statusConfig = {
    success:      { emoji: "✅", label: "Análisis completado correctamente", cls: "success" },
    needs_review: { emoji: "⚠️", label: "El ticket requiere información adicional", cls: "needs_review" },
    error:        { emoji: "❌", label: "No se pudo procesar el documento", cls: "error" },
  };
  const cfg = statusConfig[data.status] || statusConfig.error;
  statusBanner.className = `status-banner ${cfg.cls}`;
  statusBanner.innerHTML = `<span>${cfg.emoji}</span> ${escapeHtml(cfg.label)} <strong>[${escapeHtml(data.status)}]</strong>`;

  // Summary
  summaryText.textContent = data.summary || "Sin resumen disponible.";
  docTypeBadge.textContent = formatDocType(data.document_type);

  // Extracted data
  extractedData.innerHTML = "";
  const ed = data.extracted_data || {};
  const fieldLabels = {
    reporter_name:       "Reportante",
    device_or_system:    "Dispositivo / Sistema",
    problem_description: "Descripción del problema",
    priority:            "Prioridad",
    suggested_action:    "Acción sugerida",
  };
  const orderedKeys = Object.keys(fieldLabels).filter((k) => k !== "priority" && k !== "suggested_action");
  orderedKeys.forEach((key) => {
    const val = ed[key];
    if (val !== undefined && val !== null) {
      extractedData.appendChild(makeDataItem(fieldLabels[key], val));
    }
  });
  
  Object.keys(ed).forEach((key) => {
    if (!fieldLabels[key]) {
      extractedData.appendChild(makeDataItem(key, ed[key]));
    }
  });

  // Priority card
  const priorityCard = document.getElementById("priorityCard");
  const pr = ed.priority;
  if (pr || ed.suggested_action) {
    priorityInfo.innerHTML = "";
    if (pr) {
      const badge = document.createElement("div");
      badge.className = `priority-badge ${escapeHtml(pr.toLowerCase())}`;
      badge.innerHTML = `${priorityEmoji(pr)} ${escapeHtml(pr)}`;
      priorityInfo.appendChild(badge);
    }
    if (ed.suggested_action) {
      const act = document.createElement("p");
      act.className = "action-text";
      act.textContent = ed.suggested_action;
      priorityInfo.appendChild(act);
    }
    priorityCard.classList.remove("hidden");
  } else {
    priorityCard.classList.add("hidden");
  }

  // Warnings
  warningsList.innerHTML = "";
  if (data.warnings && data.warnings.length) {
    data.warnings.forEach((w) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>⚠️</span> ${escapeHtml(w)}`;
      warningsList.appendChild(li);
    });
    warningsCard.classList.remove("hidden");
  } else {
    warningsCard.classList.add("hidden");
  }

  // Clarification
  questionsList.innerHTML = "";
  if (data.needs_clarification && data.clarifying_questions?.length) {
    data.clarifying_questions.forEach((q, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="q-num">${i + 1}.</span> ${escapeHtml(q)}`;
      questionsList.appendChild(li);
    });
    clarificationCard.classList.remove("hidden");
  } else {
    clarificationCard.classList.add("hidden");
  }

  // Tool trace
  toolTraceContainer.innerHTML = "";
  if (data.tool_trace && data.tool_trace.length) {
    data.tool_trace.forEach((t) => {
      const div = document.createElement("div");
      div.className = `trace-item ${t.success ? "success-trace" : "error-trace"}`;
      div.innerHTML = `
        <div class="trace-status-icon" aria-hidden="true">${t.success ? "✅" : "❌"}</div>
        <div class="trace-info">
          <div class="trace-tool">${escapeHtml(t.tool)}()</div>
          <div class="trace-reason">${escapeHtml(t.reason)}</div>
        </div>`;
      toolTraceContainer.appendChild(div);
    });
  } else {
    toolTraceContainer.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">No hay trazas de herramientas registradas.</p>`;
  }
}

// ── Render Dashboard / List ───────────────────────────────────────────────────
export function updateDashboardUI() {
  updateKPIs();
  updateTrafficLight();
  renderHistoryTable();
}

function updateKPIs() {
  const metrics = store.getMetrics();
  const filter = store.getFilter();
  
  document.getElementById("kpiTotal").textContent = metrics.total;
  document.getElementById("kpiSuccess").textContent = metrics.completed;
  document.getElementById("kpiReview").textContent = metrics.review;
  document.getElementById("kpiError").textContent = metrics.errors;
  document.getElementById("kpiAiDirect").textContent = metrics.aiDirect;
  document.getElementById("kpiHumanCorrected").textContent = metrics.humanCorrected;

  document.querySelectorAll('.kpi-card').forEach(card => {
    card.classList.remove('active');
    if (card.getAttribute('data-filter') === filter) {
      card.classList.add('active');
    }
  });
}

function renderHistoryTable() {
  if (!tbody || !emptyState) return;
  tbody.innerHTML = "";
  
  const filteredWithIndex = store.getFilteredHistory();

  if (filteredWithIndex.length === 0) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
    
    filteredWithIndex.forEach(({ item, originalIndex }) => {
      const tr = document.createElement("tr");

      const dateStr = new Date(item.timestamp).toLocaleString("es-ES", {
        month: "short", day: "numeric", hour: "2-digit", minute:"2-digit"
      });

      const statusMap = { success: "Completado", needs_review: "Revisión", error: "Error" };
      const statusLabel = statusMap[item.status] || item.status;
      const statusHtml = `<span class="status-badge ${item.status}">${statusLabel}</span>`;

      let priorityLabel = "-";
      if (item.status === "success" && item.extracted_data?.priority) {
        priorityLabel = item.extracted_data.priority;
      }

      tr.innerHTML = `
        <td style="color:var(--text-muted)">${dateStr}</td>
        <td>
          <div style="font-weight:600;color:var(--text-primary);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(item.filename)}</div>
          <div style="font-size:0.75rem;color:var(--text-secondary);max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:4px;">${escapeHtml(item.summary || "")}</div>
        </td>
        <td>${statusHtml}</td>
        <td style="font-weight:500">${escapeHtml(priorityLabel)}</td>
        <td style="text-align:right">
          <button class="btn-edit" data-index="${originalIndex}">Corregir</button>
        </td>
      `;
      
      if (item.edited_by_human) {
        const fileCell = tr.cells[1];
        const nameDiv = fileCell.querySelector("div");
        const badge = document.createElement("span");
        badge.className = "edited-badge";
        badge.textContent = "Corregido";
        nameDiv.appendChild(badge);
      }

      tbody.appendChild(tr);
    });
  }
}
