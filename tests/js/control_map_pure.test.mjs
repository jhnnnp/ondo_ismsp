import test from "node:test";
import assert from "node:assert/strict";

import {
  checksFromLevel,
  compareDotId,
  deriveLevel,
  normalizeChecks,
  parseDotId,
} from "../../src/isms_pii_toolkit/web/control_map/features/assessment/model.js";
import {
  clampPercent,
  distinctDesc,
  formatPercent,
  heatmapTone,
  severityLabel,
  shortRiskTip,
} from "../../src/isms_pii_toolkit/web/control_map/features/analysis/utils.js";
import {
  buildReportReviewItems,
  parseInsightCard,
  reviewFingerprint,
} from "../../src/isms_pii_toolkit/web/control_map/features/analysis/report-review.js";
import {
  createDiagnosisSession,
  diagnosisProgress,
  duplicateDiagnosisSession,
  normalizeDiagnosisSessionName,
  SESSION_NAME_MAX_LENGTH,
} from "../../src/isms_pii_toolkit/web/control_map/core/session-model.js";
import {
  diagnosisSessionPageNumbers,
  paginateDiagnosisSessions,
} from "../../src/isms_pii_toolkit/web/control_map/features/sessions/view.js";
import { resolveSessionSelectedId } from "../../src/isms_pii_toolkit/web/control_map/features/session/view.js";
import {
  compactSearchText,
  controlSearchScore,
  matchesControlSearch,
  queryTokens,
  rankControlsBySearch,
} from "../../src/isms_pii_toolkit/web/control_map/features/assessment/search.js";
import {
  accessPassDisplay,
  formatPassChip,
  formatPassRemaining,
  remainingFromExpires,
} from "../../src/isms_pii_toolkit/web/control_map/core/access-pass.js";
import {
  renderLegalProse,
} from "../../src/isms_pii_toolkit/web/control_map/features/assessment/view.js";
import {
  applyWeakReviewState,
  areaReadiness,
  assessmentSummary,
  buildDashboardViewModel,
  readinessTemperature,
  temperatureBand,
} from "../../src/isms_pii_toolkit/web/control_map/features/session/dashboard.js";

test("dashboard maps real analysis fields without overstating evidence or risk signals", () => {
  const currentAt = 1_700_000_000_000;
  const analysis = {
    clientAnalyzedAt: currentAt,
    gapCount: 8,
    topGaps: [{
      controlId: "1.2.3", title: "위험 평가", level: "none", severity: "high",
      scenarioRelevant: true, riskIfMissing: "위험 식별 누락으로 보호대책 근거가 약해집니다.",
    }],
    cascadeChains: Array.from({ length: 15 }, (_, index) => ({ id: index })),
    multiGapOverlaps: Array.from({ length: 25 }, (_, index) => ({ id: index })),
    gapClusters: [
      { theme: "시스템 및 서비스 보안관리", gapCount: 9 },
      { theme: "물리 보안", gapCount: 7 },
      { theme: "접근통제", gapCount: 6 },
      { theme: "운영관리", gapCount: 5 },
      { theme: "표시 범위 밖", gapCount: 4 },
    ],
  };
  const vm = buildDashboardViewModel({
    analysis,
    controlEvidence: { "1.2.3": [{ id: 1 }, { id: 2 }], "2.1.1": [{ id: 3 }], "2.2.1": [] },
    weakControlIds: ["1.2.3", "2.1.1", "2.2.1", "2.3.1"],
  });

  assert.deepEqual(vm.evidence, { itemCount: 3, controlCount: 2 });
  assert.equal(vm.priorities[0].controlId, "1.2.3");
  assert.deepEqual(vm.priorities[0].selectionReasons, ["선택 시나리오 직접 관련", "미이행 우선", "심각도 높음"]);
  assert.deepEqual(vm.signals.map(({ label, value }) => [label, value]), [
    ["증적 미등록", 2],
    ["등록 증적", 3],
  ]);
  assert.match(vm.signals[0].help, /보완 대상 4개 중 2개/);
  assert.equal(vm.categories.length, 4);
  assert.equal(vm.queueMode, false);
  assert.equal(vm.priorities[0].mode, "gap");
});

test("dashboard suppresses analysis-derived data when stale", () => {
  const vm = buildDashboardViewModel({
    stale: true,
    analysis: { topGaps: [{ controlId: "1.1.1" }], cascadeChains: [{}], multiGapOverlaps: [{}], gapClusters: [{}] },
  });
  assert.deepEqual(vm.priorities, []);
  assert.equal(vm.signals[0].label, "증적 미등록");
  assert.deepEqual(vm.categories, []);
  assert.equal(vm.queueMode, true);
});

test("dashboard temperature bands and area readiness follow live assessments", () => {
  assert.equal(temperatureBand(16).key, "cold");
  assert.equal(temperatureBand(16).label, "초기 단계");
  assert.equal(temperatureBand(40).key, "warming");
  assert.equal(temperatureBand(40).label, "점검 중");
  assert.equal(temperatureBand(70).key, "rising");
  assert.equal(temperatureBand(70).label, "안정화");
  assert.equal(temperatureBand(90).key, "ready");
  assert.equal(temperatureBand(90).label, "준비 완료");
  assert.equal(readinessTemperature({ done: 8, partial: 0, applicable: 50 }), 16);
  assert.deepEqual(assessmentSummary({ done: 8, partial: 0, none: 0, applicable: 50 }), {
    reviewed: 8,
    total: 50,
    coverage: 16,
    confirmedReadiness: 100,
    confidence: "low",
  });

  const levels = { "1.1.1": "done", "1.1.2": "partial", "2.1.1": "unknown" };
  const areas = areaReadiness([
    { areaId: "1", areaName: "관리체계 수립 및 운영", controls: [{ id: "1.1.1" }, { id: "1.1.2" }] },
    { areaId: "2", areaName: "보호대책 요구사항", controls: [{ id: "2.1.1" }] },
  ], (id) => levels[id]);
  assert.equal(areas[0].label, "관리체계");
  assert.equal(areas[0].temperature, 75);
  assert.equal(areas[0].confirmedReadiness, 75);
  assert.equal(areas[0].coverage, 100);
  assert.equal(areas[1].temperature, 0);
  assert.equal(areas[1].confirmedReadiness, null);
  assert.equal(areas[1].nextControlId, "2.1.1");
});

test("dashboard falls back to the next unreviewed queue before analysis exists", () => {
  const vm = buildDashboardViewModel({
    nextControls: [{ id: "1.1.1", title: "정책 수립", level: "unknown" }],
    applicable: 101,
  });
  assert.equal(vm.queueMode, true);
  assert.equal(vm.priorities[0].controlId, "1.1.1");
  assert.equal(vm.priorities[0].mode, "queue");
});

test("dashboard priority click state selects the requested weak control", () => {
  const targetState = { levelFilter: "all", sessionSelectedControlId: null };
  assert.equal(applyWeakReviewState(targetState, "2.5.1", ["1.2.3"]), "2.5.1");
  assert.deepEqual(targetState, { levelFilter: "weak", sessionSelectedControlId: "2.5.1" });
  assert.equal(applyWeakReviewState(targetState, null, ["1.2.3"]), "1.2.3");
});

test("assessment levels round-trip through checklist state", () => {
  assert.equal(deriveLevel(checksFromLevel("evidenced")), "done");
  for (const level of ["done", "partial", "none", "unknown"]) {
    assert.equal(deriveLevel(checksFromLevel(level)), level);
  }
});

test("check normalization enforces prerequisite checks", () => {
  assert.deepEqual(
    normalizeChecks({ reviewed: false, policy: false, implemented: false, evidence: true }),
    { reviewed: true, policy: true, implemented: true, evidence: true },
  );
  assert.deepEqual(
    normalizeChecks({ reviewed: false, policy: true, implemented: false, evidence: false }),
    { reviewed: true, policy: true, implemented: false, evidence: false },
  );
});

test("dot identifiers compare numerically", () => {
  assert.deepEqual(parseDotId("2.10.3"), [2, 10, 3]);
  assert.ok(compareDotId("2.9.9", "2.10.1") < 0);
  assert.equal(compareDotId("3.1", "3.1.0"), 0);
});

test("analysis formatting clamps and labels values", () => {
  assert.equal(clampPercent(120), 100);
  assert.equal(clampPercent("invalid"), 0);
  assert.equal(formatPercent(12.25), "12.3");
  assert.equal(heatmapTone(69), "is-mid");
  assert.equal(severityLabel("critical"), "심각");
});

test("analysis text helpers remove duplicate and excessive text", () => {
  assert.equal(distinctDesc("동일", "동일"), "");
  assert.equal(shortRiskTip("", "대체 문구"), "대체 문구");
  assert.equal(shortRiskTip("가".repeat(120)).length, 109);
});

test("report review blocks legacy analysis responses", () => {
  const [item] = buildReportReviewItems({ keyInsights: ["구형 분석 문장"] });

  assert.equal(item.title, "분석 데이터 갱신 필요");
  assert.equal(item.card.kind, "compatibility");
  assert.equal(item.card.classification, "action_required");
});

test("report review cards parse readiness metrics into structured tiles", () => {
  const card = parseInsightCard(
    "전체 준비도 31.8% — 진단/계획 단계 (정책/범위 수립 우선). 갭 82건 중 미이행 1건, 미점검 44건, 부분 이행 37건이 식별되었습니다.",
  );

  assert.equal(card.kind, "readiness");
  assert.equal(card.metric, "31.8");
  assert.equal(card.headline, "진단/계획 단계 (정책/범위 수립 우선)");
  assert.deepEqual(
    card.stats.map((stat) => [stat.label, stat.value]),
    [
      ["갭", "82"],
      ["미이행", "1"],
      ["미점검", "44"],
      ["부분 이행", "37"],
    ],
  );
});

test("priority insight parser keeps the full control title", () => {
  const card = parseInsightCard(
    "최우선 점검 통제: 2.6.4 데이터베이스 접근통제(미이행). 데이터베이스 접근 요구사항을 확인합니다.",
  );

  assert.equal(card.headline, "데이터베이스 접근통제");
  assert.equal(card.badge, "미이행");
  assert.equal(card.body, "데이터베이스 접근 요구사항을 확인합니다.");
});

test("report review prefers structured evidence-backed items", () => {
  const items = buildReportReviewItems({
    reviewItems: [
      {
        id: "assessment-coverage",
        kind: "coverage",
        classification: "fact",
        title: "진단 완성도",
        headline: "적용 통제 101개 중 3개를 점검했습니다.",
        metric: 3,
        metricUnit: "%",
        confidenceLevel: "high",
        confidenceLabel: "입력 사실",
        basis: ["적용 통제 101개", "점검 완료 3개"],
      },
    ],
    keyInsights: ["이 문장은 구조화된 항목이 있을 때 사용하지 않습니다."],
  });

  assert.equal(items.length, 1);
  assert.equal(items[0].title, "진단 완성도");
  assert.equal(items[0].card.kind, "coverage");
  assert.equal(items[0].card.classification, "fact");
  assert.deepEqual(items[0].card.basis, ["적용 통제 101개", "점검 완료 3개"]);
});

test("review fingerprint changes when control evidence changes", () => {
  const analysis = { overallReadiness: 5, gapCount: 1 };
  const first = [{
    id: "finding",
    card: { kind: "finding", chips: ["1.1.1"] },
  }];
  const second = [{
    id: "finding",
    card: { kind: "finding", chips: ["1.1.2"] },
  }];

  assert.notEqual(
    reviewFingerprint(analysis, first),
    reviewFingerprint(analysis, second),
  );
});

test("diagnosis sessions have independent identifiers and data", () => {
  const source = createDiagnosisSession({
    id: "source",
    name: "운영 진단",
    now: "2026-07-30T00:00:00.000Z",
    data: {
      assessments: { "1.1.1": "partial" },
      controlChecks: { "1.1.1": { reviewed: true, policy: false } },
      sessionSelectedControlId: "1.2.3",
    },
  });
  const copy = duplicateDiagnosisSession(source, {
    id: "copy",
    now: "2026-07-30T01:00:00.000Z",
  });

  copy.data.assessments["1.1.1"] = "done";
  copy.data.controlChecks["1.1.1"].policy = true;
  assert.equal(source.id, "source");
  assert.equal(copy.id, "copy");
  assert.equal(copy.name, "운영 진단 복사본");
  assert.equal(source.data.assessments["1.1.1"], "partial");
  assert.equal(source.data.controlChecks["1.1.1"].policy, false);
  assert.equal(copy.data.sessionSelectedControlId, "1.2.3");
});

test("assessment restores the last control and defaults to the first control", () => {
  const groups = [{ categoryId: "1.1", controls: [{ id: "1.1.1" }, { id: "1.1.2" }] }];
  assert.equal(resolveSessionSelectedId("1.1.2", groups), "1.1.2");
  assert.equal(resolveSessionSelectedId(null, groups), "1.1.1");
  assert.equal(resolveSessionSelectedId("1.2.3", groups), "1.1.1");
});

test("diagnosis session names trim, collapse spaces, and stay within length", () => {
  assert.equal(normalizeDiagnosisSessionName("  한빛몰 점검  "), "한빛몰 점검");
  assert.equal(normalizeDiagnosisSessionName("한빛몰   점검"), "한빛몰 점검");
  assert.equal(normalizeDiagnosisSessionName("   "), "진단");
  assert.equal(normalizeDiagnosisSessionName("가".repeat(SESSION_NAME_MAX_LENGTH + 8)).length, SESSION_NAME_MAX_LENGTH);
  assert.equal(createDiagnosisSession({ name: "  운영 진단  " }).name, "운영 진단");
});

test("diagnosis session picker paginates four cards per page", () => {
  const sessions = Array.from({ length: 9 }, (_, index) => ({ id: String(index + 1) }));
  const first = paginateDiagnosisSessions(sessions, 1);
  const last = paginateDiagnosisSessions(sessions, 99);
  assert.equal(first.pageCount, 3);
  assert.deepEqual(first.items.map((item) => item.id), ["1", "2", "3", "4"]);
  assert.equal(last.current, 3);
  assert.deepEqual(last.items.map((item) => item.id), ["9"]);
  assert.deepEqual(diagnosisSessionPageNumbers(1, 4), [1, 2, 3, 4]);
  assert.deepEqual(diagnosisSessionPageNumbers(8, 12), [1, 7, 8, 9, 12]);
});

test("diagnosis progress excludes not-applicable controls", () => {
  const session = createDiagnosisSession({
    data: {
      assessments: {
        "1.1.1": "done",
        "1.1.2": "partial",
        "1.1.3": "unknown",
        "1.1.4": "na",
      },
    },
  });

  assert.deepEqual(diagnosisProgress(session, 4), {
    reviewed: 2,
    applicable: 3,
    na: 1,
    percent: 67,
  });
});

const accountControl = {
  id: "2.5.1",
  title: "사용자 계정 관리",
  categoryName: "인증 및 권한관리",
  officialRequirement: "사용자 등록 해지 및 접근권한 부여·변경·말소 절차를 수립·이행한다",
  searchHints: ["불필요한 계정 제거", "미사용 계정 삭제", "휴면 계정 삭제"],
};

const patchControl = {
  id: "2.10.8",
  title: "패치관리",
  checklistItems: ["자산별 특성에 따라 패치관리 정책 및 절차를 수립 이행한다"],
  searchHints: ["주기적 보안패치 적용", "OS 패치"],
};

const execControl = {
  id: "1.1.1",
  title: "경영진의 참여",
  categoryName: "관리체계 기반",
};

const resourceControl = {
  id: "1.1.6",
  title: "자원 할당",
  searchHints: ["보안 예산", "정보보호 인력", "보안 자원 부족"],
};

test("control search matches user wording without spaces", () => {
  assert.deepEqual(queryTokens("불필요한계정제거"), ["불필요", "계정", "제거"]);
  assert.equal(compactSearchText("불필요한 계정 제거"), "불필요한계정제거");
  assert.equal(matchesControlSearch(accountControl, "불필요한계정제거"), true);
  assert.equal(matchesControlSearch(accountControl, "미사용 계정 삭제"), true);
  assert.equal(matchesControlSearch(accountControl, "2.5.1"), true);
  assert.equal(matchesControlSearch(patchControl, "주기적보안패치"), true);
  assert.equal(matchesControlSearch(execControl, "경영진"), true);
  assert.equal(matchesControlSearch(execControl, "불필요한계정제거"), false);
  assert.equal(matchesControlSearch(accountControl, "불필요한"), true);
  assert.equal(matchesControlSearch(accountControl, "불필요한, 불필요한 계정"), true);
  assert.deepEqual(queryTokens("불필요한, 불필요한 계정"), ["불필요", "계정"]);
  assert.equal(matchesControlSearch(resourceControl, "보안 예산이 부족해요"), true);
});

test("control search ranks the closest user-wording match first", () => {
  const ranked = rankControlsBySearch(
    [execControl, patchControl, accountControl],
    "불필요한계정제거",
  );
  assert.equal(ranked[0].id, "2.5.1");
  assert.ok(controlSearchScore(accountControl, "불필요한계정제거") > controlSearchScore(execControl, "불필요한계정제거"));
});

test("control search separates account residue, employment, and contractor intents", () => {
  const employmentControl = {
    id: "2.2.5", title: "퇴직 및 직무변경 관리",
    searchHints: ["퇴사자 계정 회수", "직무변경 권한 회수", "재직 여부 확인"],
    searchEntries: [{ text: "재직 여부 확인", weight: 100 }, { text: "퇴사자 계정 회수", weight: 100 }],
  };
  const contractorControl = {
    id: "2.3.4", title: "계약 변경 및 만료 시 보안",
    searchHints: ["외주인력 계정삭제", "계약 여부 확인", "계약 만료 계정 삭제"],
    searchEntries: [{ text: "계약 만료 계정 삭제", weight: 100 }],
  };
  const contextualAccount = {
    ...accountControl,
    searchHints: [...accountControl.searchHints, "계정 필요성 확인", "시스템 계정 잔존"],
    searchEntries: [{ text: "계정 필요성 확인", weight: 100 }],
  };

  const finding = "hbmops, kimjh_old, vendor 계정 필요성 및 재직/계약 여부 확인 필요";
  const candidates = [contractorControl, employmentControl, contextualAccount]
    .filter((control) => matchesControlSearch(control, finding));
  assert.deepEqual(new Set(candidates.map((control) => control.id)), new Set(["2.5.1", "2.2.5", "2.3.4"]));
  assert.ok(controlSearchScore(employmentControl, "재직 여부 확인") > controlSearchScore(contextualAccount, "재직 여부 확인"));
  assert.ok(controlSearchScore(contractorControl, "계약 만료 계정 삭제") > controlSearchScore(employmentControl, "계약 만료 계정 삭제"));
});

test("structured intents retrieve compound findings beyond account controls", () => {
  const controls = [
    {
      id: "2.9.4", title: "로그 및 접속기록 관리",
      searchIntents: [{ phrase: "접속 로그 미수집", concepts: ["접속", "로그", "미수집"], weight: 100 }],
    },
    {
      id: "2.7.1", title: "암호화 적용",
      searchIntents: [{ phrase: "전송구간 암호화", concepts: ["전송구간", "암호화"], weight: 100 }],
    },
    {
      id: "2.10.8", title: "패치관리",
      searchIntents: [{ phrase: "OS 패치", concepts: ["os", "패치"], weight: 100 }],
    },
  ];
  const finding = "인터넷 전송구간 암호화가 없고 서버 접속 로그도 미수집 상태임";
  const matched = controls.filter((control) => matchesControlSearch(control, finding));

  assert.deepEqual(matched.map((control) => control.id), ["2.9.4", "2.7.1"]);
  assert.ok(controlSearchScore(controls[0], finding) > 0);
  assert.ok(controlSearchScore(controls[1], finding) > 0);
  assert.equal(controlSearchScore(controls[2], finding), 0);
});

test("access pass remaining labels include days and hours", () => {
  assert.equal(formatPassChip((3 * 86400) + (14 * 3600) + 90), "3일 14시간");
  assert.equal(formatPassRemaining((3 * 86400) + (14 * 3600) + 90), "3일 14시간 남음");
  assert.equal(formatPassChip((5 * 3600) + (12 * 60)), "5시간");
  assert.equal(formatPassRemaining((5 * 3600) + (12 * 60)), "5시간 남음");
  assert.equal(formatPassRemaining(90), "1분 남음");
  assert.equal(formatPassRemaining(20), "1분 미만 남음");
  const now = Date.parse("2026-08-19T08:00:00Z");
  assert.equal(remainingFromExpires("2026-08-22T08:00:00+00:00", now), 3 * 86400);
  assert.equal(remainingFromExpires(null, now), 0);
});

test("active invite pass displays as registered without an expiry", () => {
  assert.deepEqual(
    accessPassDisplay({ active: true, kind: "invite", expiresAt: null }),
    { active: true, meta: "등록됨", label: "초대권이 등록되었습니다." },
  );
  assert.equal(accessPassDisplay({ active: false, kind: null, expiresAt: null }).meta, "미등록");
});

test("legal prose splits questions, hangul answers, and casebook headings", () => {
  const question = renderLegalProse(
    "「자동차관리법」 제53조의 규정에 의하여 교통안전공단이 자동차관리사업자의 전산자료 제출을 요구할 수 있는지 여부와 「정보통신망이용촉진및정보보호등에관한법률」 제50조의 규정에 의한 개인정보 수집·이용에 대한 고지 및 동의 의무의 적용 여부"
  );
  assert.match(question, /legal-reasoning-list/);
  assert.match(question, /자동차관리법/);
  assert.match(question, /정보통신망이용촉진/);
  assert.equal((question.match(/<li>/g) || []).length, 2);

  const answer = renderLegalProse(
    "가. 「자동차관리법」 제53조의 규정에 의하여 교통안전공단은 자동차관리사업자의 전산자료 제출을 요구할 수 있습니다. 나. 「정보통신망이용촉진및정보보호등에관한법률」 제50조의 규정에 의한 개인정보 수집·이용에 대한 고지 및 동의 의무는 적용되지 않습니다."
  );
  assert.match(answer, /legal-hangul-list/);
  assert.match(answer, /요구할 수 있습니다/);
  assert.match(answer, /적용되지 않습니다/);
  assert.equal((answer.match(/<li>/g) || []).length, 2);

  const reasoning = renderLegalProse("행위 주체 내용\n① 자치관리기구의 대표자인 공동주택의 관리사무소장\n② 관리업무를 인계하기 전의 사업주체\n※ 개인정보의 수집출처 고지: 전화권유판매자가 안내하는 것");
  assert.match(reasoning, /<h5>행위 주체 내용<\/h5>/);
  assert.match(reasoning, /legal-reasoning-list/);
  assert.match(reasoning, /legal-note/);
  assert.equal((reasoning.match(/<li>/g) || []).length, 2);
});

test("legal interpretation prose extracts footnotes, paragraphs, and related laws", () => {
  const question = renderLegalProse(
    "정보통신망법 제50조제1항 본문에서는 사전 동의를 받아야 한다고 규정하고 있는바, 일정한 기간 동안 계속적으로 재화등을 공급하는 계약을 체결한 경우 사전 동의를 받지 않아도 되는 기간에 거래기간이 포함되는지?"
  );
  assert.match(question, /legal-question-point/);
  assert.match(question, /legal-article-ref/);
  assert.ok((question.match(/<p/g) || []).length >= 2);

  const reasoning = renderLegalProse(
    "먼저 법령의 문언 자체가 비교적 명확한 개념으로 구성되어 있다면 다른 해석방법은 제한될 수밖에 없다고 할 것인데1)1) 대법원 2009. 4. 23. 선고 2006다81035 판결례 참조 , 정보통신망법 제50조제1항제1호에서는 사전 동의를 받지 아니한다고 규정하고 있는바, 기간의 시작일은 거래가 종료된 날이라고 볼 수 없습니다. 그리고 예외규정은 엄격하게 해석할 필요가 있습니다. 따라서 거래기간은 포함되지 않습니다. ※ 법령정비 권고사항 관련 규정을 정비할 필요가 있습니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제50조(영리목적의 광고성 정보 전송 제한) ① 누구든지 사전 동의를 받아야 한다. 1. 거래관계를 통한 경우 2. 전화권유를 하는 경우 ② 수신거부의사를 표시한 경우에는 전송하여서는 아니 된다. <관계 법령>"
  );
  assert.match(reasoning, /legal-footnotes/);
  assert.match(reasoning, /legal-fn-mark/);
  assert.match(reasoning, /2006다81035/);
  assert.match(reasoning, /legal-related-laws/);
  assert.match(reasoning, /legal-text-heading/);
  assert.match(reasoning, /legal-text-clause/);
  assert.match(reasoning, /legal-text-item/);
  assert.match(reasoning, /법령정비 권고사항/);
  assert.ok((reasoning.match(/<p/g) || []).length >= 4);
});
