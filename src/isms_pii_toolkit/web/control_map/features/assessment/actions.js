import { CHECK_LABEL } from "../../core/constants.js";
import { state } from "../../core/state.js";
import { saveAssessments } from "../../core/storage.js";
import { checksFromLevel, deriveLevel, normalizeChecks } from "./model.js";

export function ensureChecks(controlId) {
  if (!state.controlChecks[controlId]) {
    state.controlChecks[controlId] = checksFromLevel(state.assessments[controlId] || "unknown");
  }
  return state.controlChecks[controlId];
}

export function ensureDomainChecks(controlId, checklistItems) {
  const items = checklistItems || [];
  if (!state.domainChecks[controlId]) {
    const seeded = {};
    const maturity = ensureChecks(controlId);
    const keys = Object.keys(CHECK_LABEL);
    items.forEach((item, index) => {
      const itemId = String(index + 1);
      const proxyKey = keys[index];
      seeded[itemId] = proxyKey ? !!maturity[proxyKey] : false;
    });
    state.domainChecks[controlId] = seeded;
  } else {
    items.forEach((_, index) => {
      const itemId = String(index + 1);
      if (!(itemId in state.domainChecks[controlId])) {
        state.domainChecks[controlId][itemId] = false;
      }
    });
  }
  return state.domainChecks[controlId];
}

export function setDomainCheck(controlId, itemId, checked) {
  const control = (state.checklist || []).find((c) => c.id === controlId);
  ensureDomainChecks(controlId, control?.checklistItems || []);
  if (!state.domainChecks[controlId]) state.domainChecks[controlId] = {};
  state.domainChecks[controlId][String(itemId)] = !!checked;
  state.domainTouched[controlId] = true;
  saveAssessments();
}

export function domainChecksPayload() {
  const payload = {};
  Object.keys(state.domainTouched || {}).forEach((controlId) => {
    if (state.domainChecks[controlId]) payload[controlId] = state.domainChecks[controlId];
  });
  return Object.keys(payload).length ? payload : null;
}

export function promoteConfidenceAssumed(controlId) {
  const cur = state.inputConfidence?.[controlId] || "unknown";
  if (cur === "unknown") state.inputConfidence[controlId] = "assumed";
}

export function applyChecksToControl(controlId, checks) {
  const prevLevel = state.assessments[controlId];
  const next = normalizeChecks(checks, controlId);
  state.controlChecks[controlId] = next;
  if (prevLevel === "na") {
    state.assessments[controlId] = "na";
    return;
  }
  state.assessments[controlId] = deriveLevel(next, controlId);
  if (state.assessments[controlId] !== "unknown") promoteConfidenceAssumed(controlId);
}

export function syncAssessmentsFromApplicability(data) {
  const naIds = new Set((data.applicabilityNotes || []).map((n) => n.controlId).filter(Boolean));
  Object.keys(state.assessments).forEach((id) => {
    if (state.assessments[id] === "na" && !naIds.has(id)) {
      state.assessments[id] = "unknown";
    }
  });
  naIds.forEach((id) => {
    state.assessments[id] = "na";
  });
}

