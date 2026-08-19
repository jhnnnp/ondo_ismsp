import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDiagnosisBackup,
  createImportedDiagnosisSession,
  importedSessionName,
  parseDiagnosisBackup,
} from "../../src/isms_pii_toolkit/web/control_map/core/session-transfer.js";
import { createDiagnosisSession } from "../../src/isms_pii_toolkit/web/control_map/core/session-model.js";

test("diagnosis backup round trip keeps normalized diagnosis data", () => {
  const source = createDiagnosisSession({
    id: "source-id",
    name: "한빛몰 점검",
    now: "2026-08-13T01:00:00.000Z",
    data: {
      assessments: { "2.5.1": "partial" },
      controlEvidence: {
        "2.5.1": [{ id: "ev-1", title: "퇴직자 계정 목록", note: "참고용" }],
      },
    },
  });
  const backup = buildDiagnosisBackup(source, "2026-08-13T02:00:00.000Z");
  const parsed = parseDiagnosisBackup(JSON.stringify(backup), 101);

  assert.equal(parsed.name, "한빛몰 점검");
  assert.equal(parsed.progress.reviewed, 1);
  assert.equal(parsed.data.assessments["2.5.1"], "partial");
  assert.equal(parsed.data.controlEvidence["2.5.1"][0].title, "퇴직자 계정 목록");
});

test("import creates a new id and collision-safe name", () => {
  const imported = createImportedDiagnosisSession(
    { name: "한빛몰 점검", data: { assessments: { "2.5.1": "none" } } },
    ["한빛몰 점검 (가져옴)", "한빛몰 점검 (가져옴) 2"],
    "2026-08-13T03:00:00.000Z",
  );
  assert.equal(imported.name, "한빛몰 점검 (가져옴) 3");
  assert.notEqual(imported.id, "source-id");
  assert.equal(imported.data.assessments["2.5.1"], "none");
});

test("invalid and future backup formats are rejected", () => {
  assert.throws(() => parseDiagnosisBackup("not-json"), /JSON 형식/);
  assert.throws(() => parseDiagnosisBackup(JSON.stringify({ format: "other", version: 1 })), /이 프로젝트/);
  assert.throws(
    () => parseDiagnosisBackup(JSON.stringify({ format: "isms-p-diagnosis-backup", version: 99, session: {} })),
    /지원하지 않는 백업 버전/,
  );
});

test("imported name starts with a readable suffix", () => {
  assert.equal(importedSessionName("진단 4", []), "진단 4 (가져옴)");
});
