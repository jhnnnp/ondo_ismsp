import { state } from "../../core/state.js";
import { hasRegisteredEvidence } from "./evidence.js";

export function getAssessment(controlId) {
  const level = state.assessments[controlId] || "unknown";
  if (level === "evidenced") return "done";
  return level;
}

export function deriveLevel(checks, controlId) {
  if (!checks || !checks.reviewed) return "unknown";
  const hasEvidence = !!checks.evidence
    && (controlId ? hasRegisteredEvidence(controlId) : true);
  if (checks.policy && checks.implemented && hasEvidence) return "done";
  if (checks.policy || checks.implemented) return "partial";
  return "none";
}

export function checksFromLevel(level) {
  if (level === "evidenced" || level === "done") {
    return { reviewed: true, policy: true, implemented: true, evidence: true };
  }
  if (level === "partial") {
    return { reviewed: true, policy: true, implemented: false, evidence: false };
  }
  if (level === "none") {
    return { reviewed: true, policy: false, implemented: false, evidence: false };
  }
  return { reviewed: false, policy: false, implemented: false, evidence: false };
}

export function normalizeChecks(checks, controlId) {
  const next = { ...checks };
  // 등록 증적이 없으면 증적 체크 불가. 목록→체크 ON은 등록 API에서 수행.
  if (controlId && !hasRegisteredEvidence(controlId)) {
    next.evidence = false;
  }
  if (next.evidence) {
    next.reviewed = true;
    next.policy = true;
    next.implemented = true;
  }
  if ((next.policy || next.implemented) && !next.reviewed) {
    next.reviewed = true;
  }
  if (!next.reviewed) {
    next.policy = false;
    next.implemented = false;
    next.evidence = false;
  }
  return next;
}

export function parseDotId(id) {
  return String(id || "").split(".").map((part) => Number(part) || 0);
}

export function compareDotId(a, b) {
  const aa = parseDotId(a);
  const bb = parseDotId(b);
  const len = Math.max(aa.length, bb.length);
  for (let i = 0; i < len; i += 1) {
    const diff = (aa[i] || 0) - (bb[i] || 0);
    if (diff) return diff;
  }
  return 0;
}

export function groupControlsByCategory(items) {
  const groups = new Map();
  items.forEach((control) => {
    const key = control.categoryId || "기타";
    if (!groups.has(key)) {
      groups.set(key, {
        categoryId: key,
        categoryName: control.categoryName || key,
        areaId: control.areaId,
        areaName: control.areaName || "",
        controls: [],
      });
    }
    groups.get(key).controls.push(control);
  });
  return Array.from(groups.values()).sort((a, b) => compareDotId(a.categoryId, b.categoryId));
}

export function categoryProgress(controls) {
  const total = controls.length;
  const reviewed = controls.filter((control) => getAssessment(control.id) !== "unknown").length;
  const pct = total ? Math.round((reviewed / total) * 100) : 0;
  return { total, reviewed, pct };
}

/** 로드/세션 전환 후 증적 목록 기준으로 판정을 다시 맞춤 */
export function rederiveAssessmentsFromChecks() {
  const ids = new Set([
    ...Object.keys(state.controlChecks || {}),
    ...Object.keys(state.assessments || {}),
    ...Object.keys(state.controlEvidence || {}),
  ]);
  ids.forEach((controlId) => {
    if (state.assessments[controlId] === "na") return;
    if (state.assessments[controlId] === "evidenced") {
      state.assessments[controlId] = "done";
    }
    const base = {
      ...(state.controlChecks[controlId]
        || checksFromLevel(state.assessments[controlId] || "unknown")),
    };
    base.evidence = hasRegisteredEvidence(controlId);
    const next = normalizeChecks(base, controlId);
    state.controlChecks[controlId] = next;
    state.assessments[controlId] = deriveLevel(next, controlId);
  });
}
