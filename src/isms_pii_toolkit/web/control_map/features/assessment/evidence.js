import { state } from "../../core/state.js";

function newEvidenceId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `ev-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function listControlEvidence(controlId) {
  const rows = state.controlEvidence?.[controlId];
  return Array.isArray(rows) ? rows : [];
}

export function hasRegisteredEvidence(controlId) {
  return listControlEvidence(controlId).length > 0;
}

export function ensureEvidenceBucket(controlId) {
  if (!state.controlEvidence) state.controlEvidence = {};
  if (!Array.isArray(state.controlEvidence[controlId])) {
    state.controlEvidence[controlId] = [];
  }
  return state.controlEvidence[controlId];
}

export function addControlEvidence(controlId, { title, url = "", note = "" } = {}) {
  const cleanedTitle = String(title || "").trim();
  if (!cleanedTitle) {
    return { ok: false, reason: "empty_title" };
  }
  const cleanedUrl = String(url || "").trim();
  const cleanedNote = String(note || "").trim();
  const row = {
    id: newEvidenceId(),
    title: cleanedTitle,
    url: cleanedUrl,
    note: cleanedNote,
    createdAt: new Date().toISOString(),
  };
  ensureEvidenceBucket(controlId).push(row);
  return { ok: true, item: row };
}

export function removeControlEvidence(controlId, evidenceId) {
  const rows = ensureEvidenceBucket(controlId);
  const next = rows.filter((row) => row.id !== evidenceId);
  state.controlEvidence[controlId] = next;
  return next.length;
}
