const EMPTY_OBJECT_KEYS = [
  "assessments",
  "controlChecks",
  "controlEvidence",
  "domainChecks",
  "domainTouched",
  "questChecks",
  "inputConfidence",
  "reportReview",
];

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createSessionId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `diagnosis-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function emptySessionData() {
  return {
    assessments: {},
    controlChecks: {},
    controlEvidence: {},
    domainChecks: {},
    domainTouched: {},
    questChecks: {},
    inputConfidence: {},
    reportReview: {},
    analysisHistory: [],
    organizationProfile: null,
    sessionSelectedControlId: null,
  };
}

export function normalizeSessionData(value) {
  const source = objectOrEmpty(value);
  const normalized = emptySessionData();
  EMPTY_OBJECT_KEYS.forEach((key) => {
    normalized[key] = cloneJson(objectOrEmpty(source[key]));
  });
  // controlEvidence: { [controlId]: EvidenceItem[] }
  const evidenceRoot = objectOrEmpty(source.controlEvidence);
  const evidence = {};
  Object.entries(evidenceRoot).forEach(([controlId, rows]) => {
    if (!Array.isArray(rows)) return;
    evidence[controlId] = rows
      .filter((row) => row && typeof row === "object" && String(row.title || "").trim())
      .map((row) => ({
        id: String(row.id || `ev-${controlId}-${Math.random().toString(36).slice(2, 8)}`),
        title: String(row.title || "").trim(),
        url: String(row.url || "").trim(),
        note: String(row.note || "").trim(),
        createdAt: String(row.createdAt || new Date().toISOString()),
      }));
  });
  normalized.controlEvidence = evidence;
  normalized.analysisHistory = Array.isArray(source.analysisHistory)
    ? cloneJson(source.analysisHistory.slice(0, 8))
    : [];
  normalized.organizationProfile = cloneJson(objectOrEmpty(source.organizationProfile));
  if (!Object.keys(normalized.organizationProfile).length) {
    normalized.organizationProfile = null;
  }
  normalized.sessionSelectedControlId = typeof source.sessionSelectedControlId === "string"
    ? source.sessionSelectedControlId.trim() || null
    : null;
  return normalized;
}

export const SESSION_NAME_MAX_LENGTH = 48;

export function normalizeDiagnosisSessionName(value, fallback = "진단") {
  const name = String(value || "").replace(/\s+/g, " ").trim().slice(0, SESSION_NAME_MAX_LENGTH);
  return name || fallback;
}

export function createDiagnosisSession({
  id = createSessionId(),
  name = "새 진단",
  now = new Date().toISOString(),
  data = emptySessionData(),
} = {}) {
  return {
    id,
    name: normalizeDiagnosisSessionName(name),
    createdAt: now,
    updatedAt: now,
    data: normalizeSessionData(data),
  };
}

export function duplicateDiagnosisSession(session, {
  id = createSessionId(),
  now = new Date().toISOString(),
} = {}) {
  return createDiagnosisSession({
    id,
    name: `${session?.name || "진단"} 복사본`,
    now,
    data: normalizeSessionData(session?.data),
  });
}

export function diagnosisProgress(session, totalControls = 101) {
  const assessments = objectOrEmpty(session?.data?.assessments);
  const levels = Object.values(assessments);
  const na = levels.filter((level) => level === "na").length;
  const reviewed = levels.filter(
    (level) => level && level !== "unknown" && level !== "na",
  ).length;
  const applicable = Math.max(totalControls - na, 0);
  const percent = applicable ? Math.round((reviewed / applicable) * 100) : 0;
  return { reviewed, applicable, na, percent };
}

export function normalizeSessionStore(value) {
  const source = objectOrEmpty(value);
  const sessions = Array.isArray(source.sessions)
    ? source.sessions
      .filter((session) => session?.id)
      .map((session) => {
        const normalized = createDiagnosisSession({
          id: String(session.id),
          name: String(session.name || "진단"),
          now: String(session.createdAt || session.updatedAt || new Date().toISOString()),
          data: session.data,
        });
        normalized.updatedAt = String(session.updatedAt || normalized.createdAt);
        return normalized;
      })
    : [];
  return { version: 1, sessions, activeSessionId: resolveActiveSessionId(source, sessions) };
}

function resolveActiveSessionId(source, sessions) {
  const candidate = typeof source?.activeSessionId === "string" ? source.activeSessionId : null;
  if (!candidate) return null;
  return sessions.some((session) => session.id === candidate) ? candidate : null;
}
