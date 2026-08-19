import {
  createDiagnosisSession,
  diagnosisProgress,
  normalizeSessionData,
} from "./session-model.js";

export const DIAGNOSIS_BACKUP_FORMAT = "isms-p-diagnosis-backup";
export const DIAGNOSIS_BACKUP_VERSION = 1;

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}

export function buildDiagnosisBackup(session, exportedAt = new Date().toISOString()) {
  if (!objectValue(session) || !String(session.id || "").trim()) {
    throw new Error("내보낼 진단을 찾을 수 없습니다.");
  }
  return {
    format: DIAGNOSIS_BACKUP_FORMAT,
    version: DIAGNOSIS_BACKUP_VERSION,
    exportedAt,
    notice: "사용자가 입력한 참고용 자가진단 백업이며 인증 적합성을 증명하지 않습니다.",
    session: {
      name: String(session.name || "진단"),
      createdAt: String(session.createdAt || exportedAt),
      updatedAt: String(session.updatedAt || exportedAt),
      data: normalizeSessionData(session.data),
    },
  };
}

export function parseDiagnosisBackup(raw, totalControls = 101) {
  let parsed;
  try {
    parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (_) {
    throw new Error("JSON 형식의 진단 백업 파일이 아닙니다.");
  }
  if (!objectValue(parsed) || parsed.format !== DIAGNOSIS_BACKUP_FORMAT) {
    throw new Error("이 프로젝트에서 만든 진단 백업 파일이 아닙니다.");
  }
  if (parsed.version !== DIAGNOSIS_BACKUP_VERSION) {
    throw new Error(`지원하지 않는 백업 버전입니다. 현재 지원 버전: ${DIAGNOSIS_BACKUP_VERSION}`);
  }
  const source = objectValue(parsed.session);
  if (!source || !objectValue(source.data)) {
    throw new Error("백업 파일에 진단 데이터가 없습니다.");
  }
  const data = normalizeSessionData(source.data);
  const preview = createDiagnosisSession({
    name: String(source.name || "가져온 진단"),
    data,
  });
  return {
    name: preview.name,
    originalCreatedAt: String(source.createdAt || ""),
    originalUpdatedAt: String(source.updatedAt || ""),
    exportedAt: String(parsed.exportedAt || ""),
    data,
    progress: diagnosisProgress(preview, totalControls),
  };
}

export function importedSessionName(sourceName, existingNames = []) {
  const names = new Set(existingNames);
  const base = `${String(sourceName || "진단").trim() || "진단"} (가져옴)`;
  if (!names.has(base)) return base;
  let sequence = 2;
  while (names.has(`${base} ${sequence}`)) sequence += 1;
  return `${base} ${sequence}`;
}

export function createImportedDiagnosisSession(backup, existingNames = [], now = new Date().toISOString()) {
  return createDiagnosisSession({
    name: importedSessionName(backup?.name, existingNames),
    now,
    data: backup?.data,
  });
}
