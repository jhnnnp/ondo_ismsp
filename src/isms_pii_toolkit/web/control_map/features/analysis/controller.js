import { el, fetchJson, showToast } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { saveAssessments } from "../../core/storage.js";
import {
  renderAnalysisHistory,
  renderVerbalizeStatus,
  saveAnalysisHistory,
  streamExecutiveReport,
  syncAiReportChrome,
  syncExecutiveReportStream,
  switchAnalyzeSection,
} from "./presentation.js";
import { renderReportReview } from "./report-review.js";

let activeAnalysisPromise = null;
let activeAnalysisAbortController = null;
let activeAiReportPromise = null;
let activeAiReportAbortController = null;

function buildAnalyzePayload(domainChecksPayload) {
  return {
    assessments: state.assessments,
    scenarioId: state.analyzeScenarioId || null,
    sessionBundleMode: state.sessionBundleMode || "chain",
    controlChecks: state.controlChecks,
    domainChecks: domainChecksPayload(),
    questChecks: state.questChecks || {},
    inputConfidence: state.inputConfidence || {},
    organizationProfile: state.organizationProfile,
    view: "full",
  };
}

export function executeAnalysis(switchToAnalyze, options = {}, dependencies) {
  if (activeAnalysisPromise) {
    showToast("확인 목록을 이미 갱신하고 있습니다.");
    return activeAnalysisPromise;
  }
  activeAnalysisAbortController = new AbortController();
  const runPromise = executeAnalysisOnce(
    switchToAnalyze,
    options,
    dependencies,
    activeAnalysisAbortController.signal,
  );
  const trackedPromise = runPromise.finally(() => {
    if (activeAnalysisPromise === trackedPromise) {
      activeAnalysisPromise = null;
      activeAnalysisAbortController = null;
    }
  });
  activeAnalysisPromise = trackedPromise;
  return activeAnalysisPromise;
}

export function cancelActiveAnalysis() {
  activeAnalysisAbortController?.abort();
  activeAiReportAbortController?.abort();
  state.reportStreamToken = (state.reportStreamToken || 0) + 1;
  state.aiReportWriting = false;
  syncAiReportChrome();
}

export function executeAiReport(dependencies = {}) {
  if (activeAiReportPromise) {
    showToast("AI 리포트를 이미 진행하고 있습니다.");
    return activeAiReportPromise;
  }
  if (!state.analysis || !state.organizationProfile) {
    showToast("먼저 확인 목록을 갱신한 뒤 보고서를 작성하세요.");
    return Promise.resolve();
  }
  if (state.analysisStale) {
    showToast("진단이 변경되었습니다. 확인 목록을 먼저 갱신하세요.");
    return Promise.resolve();
  }

  activeAiReportAbortController = new AbortController();
  const runPromise = executeAiReportOnce(dependencies, activeAiReportAbortController.signal);
  const trackedPromise = runPromise.finally(() => {
    if (activeAiReportPromise === trackedPromise) {
      activeAiReportPromise = null;
      activeAiReportAbortController = null;
    }
  });
  activeAiReportPromise = trackedPromise;
  return activeAiReportPromise;
}

async function executeAiReportOnce({ domainChecksPayload, renderAnalyzeView }, signal) {
  const sessionId = state.activeSessionId;
  const isCurrentRequest = () => !signal.aborted && state.activeSessionId === sessionId;
  state.aiReportWriting = true;
  syncAiReportChrome();
  const reportStream = el("executiveReportStream");
  if (reportStream) {
    reportStream.dataset.userEdited = "0";
  }
  renderVerbalizeStatus({
    requested: true,
    applied: false,
    provider: "pending",
    mode: "pending",
    confidence: 0,
    reasons: ["확정된 체크 결과를 바탕으로 문장을 다듬고 있습니다."],
  });

  try {
    const report = await fetchJson("/controls/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildAnalyzePayload(domainChecksPayload)),
      signal,
    });
    if (!isCurrentRequest()) return;
    report.clientAnalyzedAt = Date.now();
    state.analysis = report;
    state.lastAiExecutiveReport = report.executiveReport || "";
    state.aiReportStale = false;
    state.analysisStale = false;
    [el("analysisStaleNoticeInline")].filter(Boolean).forEach((notice) => { notice.hidden = true; });
    saveAnalysisHistory(report);
    renderAnalyzeView?.(true);
    renderAnalysisHistory();
    renderReportReview(report);
    renderVerbalizeStatus(report.verbalizeMeta);
    state.aiReportWriting = false;
    syncAiReportChrome();
    if (report.executiveReport) {
      await streamExecutiveReport(report.executiveReport);
    } else {
      syncExecutiveReportStream();
    }
    showToast("AI 리포트를 마쳤습니다.");
  } catch (error) {
    if (error.name === "AbortError" || !isCurrentRequest()) return;
    console.warn(error);
    renderVerbalizeStatus({
      requested: true,
      applied: false,
      provider: "fallback",
      mode: "template",
      confidence: 0,
      reasons: ["AI 리포트 실패 — 진단 기반 초안을 유지합니다."],
    });
    syncExecutiveReportStream();
    syncAiReportChrome();
    showToast(`AI 리포트 실패: ${error.message}`);
  } finally {
    if (isCurrentRequest()) {
      state.aiReportWriting = false;
      syncAiReportChrome();
    }
  }
}

async function executeAnalysisOnce(switchToAnalyze, options = {}, {
  showProfileWizard,
  switchView,
  domainChecksPayload,
  renderProfileContext,
  renderStats,
  syncAssessmentsFromApplicability,
  renderAnalyzeView,
}, signal) {
  if (!state.organizationProfile) {
    showProfileWizard();
    showToast("먼저 점검 범위를 적용한 뒤 확인 목록을 만드세요.");
    return;
  }
  const sessionId = state.activeSessionId;
  const isCurrentRequest = () => !signal.aborted && state.activeSessionId === sessionId;
  const reportPanel = el("analysisReportPanel");
  const content = el("analyzeContent");
  const loadingSkeleton = el("workspaceLoadingSkeleton");
  const analyzeRoot = el("view-analyze");
  // 확인 목록 갱신은 규칙 엔진만 사용. AI 리포트는 별도 버튼에서만 호출.
  if (switchToAnalyze !== false) {
    switchView("analyze", { skipAutoAnalyze: true });
    content.style.display = "none";
    if (reportPanel) reportPanel.style.display = "none";
    if (loadingSkeleton) {
      loadingSkeleton.hidden = false;
      loadingSkeleton.dataset.analysisLoading = "true";
      loadingSkeleton.dataset.loadingSessionId = sessionId || "";
    }
    analyzeRoot?.classList.add("is-workspace-loading");
    analyzeRoot?.setAttribute("aria-busy", "true");
  }
  try {
    const data = await fetchJson("/controls/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildAnalyzePayload(domainChecksPayload)),
      signal,
    });
    if (!isCurrentRequest()) return;
    const hadAiReport = Boolean(state.lastAiExecutiveReport);
    data.clientAnalyzedAt = Date.now();
    state.analysis = data;
    state.reportReview = {};
    state.analysisStale = false;
    state.aiReportStale = hadAiReport;
    [el("analysisStaleNoticeInline")].filter(Boolean).forEach((notice) => { notice.hidden = true; });
    state.scopeDraft = data.scopeDraft || state.scopeDraft;
    renderProfileContext();
    // 엔진의 N/A 판정을 먼저 반영해야 화면의 적용 통제 수가 응답과 일치합니다.
    syncAssessmentsFromApplicability(data);
    saveAssessments();
    renderStats();

    state.analyzeSection = "actions";
    switchAnalyzeSection("actions");

    if (content) {
      content.style.display = "";
      content.classList.add("analyze-content-fade");
    }
    renderAnalyzeView(true);
    if (!isCurrentRequest()) return;

    saveAnalysisHistory(data);
    renderAnalysisHistory();
    if (reportPanel) {
      reportPanel.style.display = "";
      renderReportReview(data);
      renderVerbalizeStatus(data.verbalizeMeta);
      syncExecutiveReportStream({ preferTemplate: !hadAiReport });
      syncAiReportChrome();
    }

    if (!isCurrentRequest()) return;
    if (switchToAnalyze !== false) {
      switchView("analyze", { skipAutoAnalyze: true });
    }
    if (options.successToast) {
      showToast(options.successToast);
    }
  } catch (error) {
    if (error.name === "AbortError" || !isCurrentRequest()) return;
    if (content) content.style.display = "";
    if (reportPanel) reportPanel.style.display = "none";
    showToast("확인 목록 생성 실패: " + error.message);
  } finally {
    if (loadingSkeleton?.dataset.loadingSessionId === (sessionId || "")) {
      loadingSkeleton.hidden = true;
      delete loadingSkeleton.dataset.analysisLoading;
      delete loadingSkeleton.dataset.loadingSessionId;
      analyzeRoot?.classList.remove("is-workspace-loading");
      analyzeRoot?.removeAttribute("aria-busy");
    }
  }
}
