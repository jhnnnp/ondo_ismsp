import {
  ANALYSIS_HISTORY_KEY,
  CHECK_STORAGE_KEY,
  CONFIDENCE_STORAGE_KEY,
  DIAGNOSIS_SESSIONS_STORAGE_KEY,
  DOMAIN_STORAGE_KEY,
  EVIDENCE_STORAGE_KEY,
  PROFILE_STORAGE_KEY,
  QUEST_STORAGE_KEY,
  REPORT_REVIEW_STORAGE_KEY,
  SME_DEFAULT_PROFILE,
  STORAGE_KEY,
} from "./constants.js";
import {
  createDiagnosisSession,
  duplicateDiagnosisSession,
  emptySessionData,
  normalizeDiagnosisSessionName,
  normalizeSessionData,
  normalizeSessionStore,
} from "./session-model.js";
import { rederiveAssessmentsFromChecks } from "../features/assessment/model.js";
import { state } from "./state.js";
import {
  buildDiagnosisBackup,
  createImportedDiagnosisSession,
  parseDiagnosisBackup,
} from "./session-transfer.js";

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (_) {
    return fallback;
  }
}

function writeSessionStore() {
  localStorage.setItem(
    DIAGNOSIS_SESSIONS_STORAGE_KEY,
    JSON.stringify({
      version: 1,
      sessions: state.diagnosisSessions,
      activeSessionId: state.activeSessionId,
    }),
  );
}

function legacySessionData() {
  return normalizeSessionData({
    assessments: readJson(STORAGE_KEY, {}),
    controlChecks: readJson(CHECK_STORAGE_KEY, {}),
    controlEvidence: readJson(EVIDENCE_STORAGE_KEY, {}),
    domainChecks: readJson(DOMAIN_STORAGE_KEY, {}),
    questChecks: readJson(QUEST_STORAGE_KEY, {}),
    inputConfidence: readJson(CONFIDENCE_STORAGE_KEY, {}),
    reportReview: {},
    analysisHistory: readJson(ANALYSIS_HISTORY_KEY, []),
    organizationProfile: readJson(PROFILE_STORAGE_KEY, null),
  });
}

function hasDiagnosisData(data) {
  return Boolean(
    data.organizationProfile
    || Object.values(data)
      .filter((value) => value && typeof value === "object")
      .some((value) => Object.keys(value).length),
  );
}

function stateSessionData() {
  return normalizeSessionData({
    assessments: state.assessments,
    controlChecks: state.controlChecks,
    controlEvidence: state.controlEvidence,
    domainChecks: state.domainChecks,
    domainTouched: state.domainTouched,
    questChecks: state.questChecks,
    inputConfidence: state.inputConfidence,
    // 검토 진행은 새로고침 후 유지하지 않음 (세션에도 저장하지 않음)
    reportReview: {},
    analysisHistory: state.analysisHistory,
    organizationProfile: state.organizationProfile,
  });
}

function applySessionData(data) {
  const next = normalizeSessionData(data);
  state.assessments = next.assessments;
  state.controlChecks = next.controlChecks;
  state.controlEvidence = next.controlEvidence;
  state.domainChecks = next.domainChecks;
  state.domainTouched = next.domainTouched;
  state.questChecks = next.questChecks;
  state.inputConfidence = next.inputConfidence;
  state.reportReview = {};
  state.analysisHistory = next.analysisHistory;
  state.organizationProfile = next.organizationProfile
    ? {
      ...SME_DEFAULT_PROFILE,
      ...next.organizationProfile,
      usesOutsourcing: false,
      usesRemoteAccess: false,
      processesRrn: false,
    }
    : null;
  state.analysis = null;
  state.analysisStale = false;
  state.lastAiExecutiveReport = null;
  state.aiReportStale = false;
  state.aiReportWriting = false;
  state.reportReturn = null;
  state.currentView = "assess";
  state.areaFilter = "all";
  state.levelFilter = "all";
  state.assessSearch = "";
  state.expandedRows = new Set();
  state.collapsedCategories = new Set();
  state.activeCategoryId = null;
  state.categoriesBootstrapped = false;
  state.analyzeSection = "actions";
  state.expandedProblemGroups = new Set();
  state.expandedProblemItems = new Set();
  state.expandedGaps = new Set();
  state.expandedMultigaps = new Set();
  state.gapSearch = "";
  state.scopeDraft = null;
  state.analyzeScenarioId = null;
  state.sessionBundleMode = "chain";
  rederiveAssessmentsFromChecks();
}

export function initializeDiagnosisSessions() {
  const stored = readJson(DIAGNOSIS_SESSIONS_STORAGE_KEY, null);
  if (stored) {
    const normalized = normalizeSessionStore(stored);
    state.diagnosisSessions = normalized.sessions;
    state.activeSessionId = normalized.activeSessionId;
    return state.diagnosisSessions;
  }

  const legacy = legacySessionData();
  state.diagnosisSessions = hasDiagnosisData(legacy)
    ? [createDiagnosisSession({ name: "기존 진단", data: legacy })]
    : [];
  state.activeSessionId = null;
  writeSessionStore();
  return state.diagnosisSessions;
}

export function activateDiagnosisSession(sessionId) {
  const session = state.diagnosisSessions.find((item) => item.id === sessionId);
  if (!session) return null;
  state.activeSessionId = session.id;
  applySessionData(session.data);
  writeSessionStore();
  return session;
}

export function createStoredDiagnosisSession() {
  const names = new Set(state.diagnosisSessions.map((session) => session.name));
  let sequence = 1;
  while (names.has(`진단 ${sequence}`)) sequence += 1;
  const session = createDiagnosisSession({
    name: `진단 ${sequence}`,
    data: emptySessionData(),
  });
  state.diagnosisSessions.unshift(session);
  writeSessionStore();
  activateDiagnosisSession(session.id);
  return session;
}

export function duplicateStoredDiagnosisSession(sessionId) {
  const source = state.diagnosisSessions.find((item) => item.id === sessionId);
  if (!source) return null;
  const duplicate = duplicateDiagnosisSession(source);
  state.diagnosisSessions.unshift(duplicate);
  writeSessionStore();
  return duplicate;
}

export function renameStoredDiagnosisSession(sessionId, name) {
  const index = state.diagnosisSessions.findIndex((item) => item.id === sessionId);
  if (index < 0) return null;
  const session = state.diagnosisSessions[index];
  const nextName = normalizeDiagnosisSessionName(name, session.name);
  if (nextName === session.name) return session;
  const updated = {
    ...session,
    name: nextName,
    updatedAt: new Date().toISOString(),
  };
  state.diagnosisSessions[index] = updated;
  writeSessionStore();
  return updated;
}

export function exportStoredDiagnosisSession(sessionId) {
  if (state.activeSessionId === sessionId) persistActiveDiagnosisSession();
  const session = state.diagnosisSessions.find((item) => item.id === sessionId);
  if (!session) throw new Error("내보낼 진단을 찾을 수 없습니다.");
  return buildDiagnosisBackup(session);
}

export function inspectStoredDiagnosisBackup(raw) {
  return parseDiagnosisBackup(raw, state.checklist?.length || 101);
}

export function importStoredDiagnosisBackup(backup) {
  const imported = createImportedDiagnosisSession(
    backup,
    state.diagnosisSessions.map((session) => session.name),
  );
  state.diagnosisSessions.unshift(imported);
  writeSessionStore();
  return imported;
}

export function deleteStoredDiagnosisSession(sessionId) {
  const before = state.diagnosisSessions.length;
  state.diagnosisSessions = state.diagnosisSessions.filter((item) => item.id !== sessionId);
  if (state.activeSessionId === sessionId) state.activeSessionId = null;
  if (state.diagnosisSessions.length === before) return false;
  writeSessionStore();
  return true;
}

export function persistActiveDiagnosisSession() {
  if (!state.activeSessionId) return;
  const index = state.diagnosisSessions.findIndex(
    (session) => session.id === state.activeSessionId,
  );
  if (index < 0) return;
  state.diagnosisSessions[index] = {
    ...state.diagnosisSessions[index],
    updatedAt: new Date().toISOString(),
    data: stateSessionData(),
  };
  writeSessionStore();
}

export function loadAssessments() {
  if (state.activeSessionId) return;
  state.assessments = readJson(STORAGE_KEY, {});
  state.controlChecks = readJson(CHECK_STORAGE_KEY, {});
  state.controlEvidence = readJson(EVIDENCE_STORAGE_KEY, {});
  state.domainChecks = readJson(DOMAIN_STORAGE_KEY, {});
  state.questChecks = readJson(QUEST_STORAGE_KEY, {});
  state.inputConfidence = readJson(CONFIDENCE_STORAGE_KEY, {});
  state.reportReview = {};
  try {
    localStorage.removeItem(REPORT_REVIEW_STORAGE_KEY);
  } catch (_) {
    /* ignore */
  }
  rederiveAssessmentsFromChecks();
}

export function saveReportReview() {
  // 검토 진행은 메모리에만 유지. 새로고침·세션 저장으로 이어지지 않음.
}

export function saveAssessments() {
  if (state.activeSessionId) {
    persistActiveDiagnosisSession();
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.assessments));
  localStorage.setItem(CHECK_STORAGE_KEY, JSON.stringify(state.controlChecks));
  localStorage.setItem(EVIDENCE_STORAGE_KEY, JSON.stringify(state.controlEvidence || {}));
  localStorage.setItem(DOMAIN_STORAGE_KEY, JSON.stringify(state.domainChecks));
  localStorage.setItem(QUEST_STORAGE_KEY, JSON.stringify(state.questChecks || {}));
  localStorage.setItem(CONFIDENCE_STORAGE_KEY, JSON.stringify(state.inputConfidence || {}));
}

export function loadOrganizationProfile() {
  if (state.activeSessionId) return;
  const storedProfile = readJson(PROFILE_STORAGE_KEY, null);
  if (!storedProfile) {
    state.organizationProfile = null;
    return;
  }
  saveOrganizationProfile({
    ...SME_DEFAULT_PROFILE,
    ...storedProfile,
    usesOutsourcing: false,
    usesRemoteAccess: false,
    processesRrn: false,
  });
}

export function saveOrganizationProfile(profile) {
  state.organizationProfile = profile;
  if (state.activeSessionId) {
    persistActiveDiagnosisSession();
    return;
  }
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}
