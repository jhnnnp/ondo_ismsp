import {
  AREA_SHORT,
  CHECK_LABEL,
  HERO_LEDE,
  INPUT_CONF_LABEL,
  LEVEL_LABEL,
  PAGE_KICKER,
  PAGE_TITLE,
} from "./constants.js";
import { initAccessPass, ensureAccessPass, ensureWorkspaceAccess } from "./access-pass.js";
import { confirmAction, el, escapeHtml, fetchJson, showToast } from "./dom.js";
import { state } from "./state.js";
import {
  activateDiagnosisSession,
  createStoredDiagnosisSession,
  deleteStoredDiagnosisSession,
  duplicateStoredDiagnosisSession,
  exportStoredDiagnosisSession,
  importStoredDiagnosisBackup,
  inspectStoredDiagnosisBackup,
  initializeDiagnosisSessions,
  renameStoredDiagnosisSession,
  saveAssessments,
  saveOrganizationProfile,
} from "./storage.js";
import {
  categoryProgress,
  checksFromLevel,
  compareDotId,
  deriveLevel,
  getAssessment,
  groupControlsByCategory,
  normalizeChecks,
} from "../features/assessment/model.js";
import {
  applicableControlCount,
  filteredChecklist,
  navChecklist,
  reviewedCount,
} from "../features/assessment/filter.js";
import {
  renderAssessCategoryNav,
  renderAssessRailFilterHint as renderAssessmentFilterHint,
  renderAssessToolbar,
  renderControlAssessRow as renderAssessmentControlRow,
} from "../features/assessment/view.js";
import {
  assumeUnsetConfidence,
  bootstrapAssessment,
  bulkSetCheckForFiltered,
  bulkSetPresetForFiltered,
  configureAssessmentController,
  diagnoseControl,
  loadChecklist,
  navigateToControl,
  renderAssessList,
  resetAssessment,
} from "../features/assessment/controller.js";
import {
  domainChecksPayload,
  syncAssessmentsFromApplicability,
} from "../features/assessment/actions.js";
import {
  closeProfilePanel,
  hasSelectedEnvironment,
  openProfilePanel,
  readProfileForm,
  renderProfileContext,
  renderProfileImpact,
  syncAssessLayout,
} from "../features/profile/view.js";
import { doneControls, reviewedAndApplicable, unreviewedControls } from "../features/session/model.js";
import { readinessTemperature, temperatureBand } from "../features/session/dashboard.js";
import { renderConfirmationActions as renderSessionActions } from "../features/session/view.js";
import {
  cancelActiveAnalysis,
  executeAnalysis,
  executeAiReport,
} from "../features/analysis/controller.js";
import {
  bindReportEditor,
  bindReportRewrite,
  exportAnalysisDocx,
  exportAnalysisMarkdown,
  resetReportEditor,
  setupAnalyzeClickDelegation,
  switchAnalyzeSection,
  syncAiReportChrome,
  syncExecutiveReportStream,
} from "../features/analysis/presentation.js";
import { renderAnalysisSummary } from "../features/analysis/summary.js";
import { renderReportReview } from "../features/analysis/report-review.js";
import {
  renderDiagnosisSessionPicker,
  resetDiagnosisSessionPage,
  showDiagnosisApp,
  showDiagnosisSessionPicker,
} from "../features/sessions/view.js";
import { navigateTo, parsePath, ROUTES, setRouteHandler } from "./routes.js";

let appDataLoaded = false;
let sessionOpening = false;
let reportEditorPromise = null;

function ensureReportEditorLoaded() {
  if (!reportEditorPromise) {
    if (!document.querySelector('link[data-report-editor-style]')) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = "/controls/map/assets/react-dist/report-editor.css?v=20260820-1";
      stylesheet.dataset.reportEditorStyle = "1";
      document.head.append(stylesheet);
    }
    const reportEditorUrl = "/controls/map/assets/react-dist/report-editor.js?v=20260820-1";
    reportEditorPromise = import(/* @vite-ignore */ reportEditorUrl);
  }
  return reportEditorPromise;
}
let pendingRouteId = null;

async function applyOrganizationProfile(profile, {
  toastMessage,
  runAnalyzeAfter = true,
  switchToAnalyze = true,
} = {}) {
  saveOrganizationProfile(profile);
  state.analyzeScenarioId = null;
  state.sessionBundleMode = state.sessionBundleMode || "chain";
  state.pendingProfile = null;
  state.analysis = null;
  closeProfilePanel();
  renderProfileContext();
  syncAssessLayout();
  if (runAnalyzeAfter) {
    await runAnalysis(switchToAnalyze, {
      successToast: toastMessage || false,
      loadingMode: "priority",
    });
  } else if (toastMessage) {
    showToast(toastMessage);
  }
}

function showProfileWizard() {
  navigateTo("scope");
}

function ensureAnalyzeResults(options = {}) {
  if (state.analysis || !state.organizationProfile) return null;
  return runAnalysis(true, {
    loadingMode: options.loadingMode || "priority",
    successToast: options.successToast || false,
  });
}

function markAnalysisStale() {
  if (!state.analysis) return;
  state.analysisStale = true;
  if (state.lastAiExecutiveReport) state.aiReportStale = true;
  const notice = el("analysisStaleNoticeInline");
  if (notice) notice.hidden = false;
  const returnStatus = el("reportReturnStatus");
  if (state.reportReturn && returnStatus) {
    returnStatus.textContent = "진단이 변경되었습니다. 돌아간 뒤 확인 목록을 갱신하세요.";
  }
  syncAiReportChrome();
}

function returnToReportReview() {
  const context = state.reportReturn;
  state.reportReturn = null;
  const returnBar = el("reportReturnBar");
  if (returnBar) returnBar.hidden = true;
  navigateTo("report", { replace: true });
  const content = el("analyzeContent");
  if (content) content.style.display = "";
  const report = el("analysisReportPanel");
  if (report) report.style.display = "";
  if (state.analysis) renderReportReview(state.analysis);
  window.requestAnimationFrame(() => {
    const queue = el("reportReviewQueue");
    const activeCard = [...(queue?.querySelectorAll("[data-review-item-id]") || [])]
      .find((card) => card.dataset.reviewItemId === context?.itemId);
    if (activeCard) {
      const toggle = activeCard.querySelector("[data-review-related-toggle]");
      const panel = activeCard.querySelector("[data-review-related-panel]");
      if (toggle && panel) {
        panel.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        toggle.textContent = "관련 통제 접기";
      }
      if (context?.controlId) {
        const row = activeCard.querySelector(`[data-review-open-control="${CSS.escape(context.controlId)}"]`);
        row?.classList.add("is-return-focus");
      }
    }
    const target = activeCard || queue || report;
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (activeCard) {
      activeCard.setAttribute("tabindex", "-1");
      activeCard.focus({ preventScroll: true });
    }
  });
}

function setPageHead(viewId) {
  const key = PAGE_TITLE[viewId] ? viewId : "assess";
  const kicker = el("pageKicker");
  const title = el("pageTitle");
  const lede = el("heroLede");
  if (kicker) kicker.textContent = PAGE_KICKER[key] || PAGE_KICKER.assess;
  if (title) title.textContent = PAGE_TITLE[key] || PAGE_TITLE.assess;
  if (lede) lede.textContent = HERO_LEDE[key] || HERO_LEDE.assess;
  if (el("workspaceContextTitle")) el("workspaceContextTitle").textContent = PAGE_TITLE[key] || PAGE_TITLE.assess;
  if (el("workspaceContextDetail")) {
    el("workspaceContextDetail").textContent = key === "assess" ? "진단 환경 설정" : "통제 진단 현황";
  }
}

function setAnalyzeWorkspaceMode(mode = "assessment") {
  const root = el("view-analyze");
  if (!root) return;
  const modes = ["assessment", "results", "evidence", "report"];
  const next = modes.includes(mode) ? mode : "assessment";
  if (next === "report") ensureReportEditorLoaded();
  modes.forEach((name) => root.classList.toggle(`is-${name}`, name === next));

  const pageCopy = {
    assessment: ["진단", "자가진단", "통제별 판단 기준을 확인하고 진단 결과를 저장하세요."],
    results: ["진단", "진단 결과", "확인된 미흡과 연계 리스크, 보완 우선순위를 확인하세요."],
    evidence: ["관리", "증적 관리", "통제별 증적 등록 상태를 확인하고 부족한 근거를 보완하세요."],
    report: ["관리", "보고서", "진단 초안을 검토한 뒤 본문을 수정하고 내보내세요."],
  };
  const [kickerText, titleText, ledeText] = pageCopy[next];
  if (el("pageKicker")) el("pageKicker").textContent = kickerText;
  if (el("pageTitle")) el("pageTitle").textContent = titleText;
  if (el("heroLede")) el("heroLede").textContent = ledeText;
  if (el("workspaceContextTitle")) el("workspaceContextTitle").textContent = titleText;
  const contextCopy = {
    assessment: "통제별 진단 및 판단",
    results: "보완 우선순위와 진단 결과",
    evidence: "통제별 증적 등록 현황",
    report: "진단 결과 보고서",
  };
  if (el("workspaceContextDetail")) el("workspaceContextDetail").textContent = contextCopy[next];

  if (next === "assessment" || next === "evidence") {
    switchAnalyzeSection("actions");
  } else if (next === "results") {
    switchAnalyzeSection("overview");
  }
  if (next === "report") {
    syncExecutiveReportStream();
    syncAiReportChrome();
  }
  window.scrollTo({ top: 0, behavior: "auto" });
}

function renderStats() {
  const reviewedForHead = reviewedCount();
  const applicableForHead = applicableControlCount();
  const headStatus = el("pageHeadStatus");
  if (!headStatus) return;
  const show = state.currentView === "analyze" && Boolean(state.organizationProfile);
  headStatus.hidden = !show;
  if (!show) return;
  const complete = applicableForHead > 0 && reviewedForHead >= applicableForHead;
  const doneCount = doneControls().length;
  const partialCount = (state.checklist || []).filter((control) => getAssessment(control.id) === "partial").length;
  const temperature = readinessTemperature({
    done: doneCount,
    partial: partialCount,
    applicable: applicableForHead,
  });
  const band = temperatureBand(temperature);
  headStatus.classList.toggle("is-complete", complete);
  headStatus.classList.toggle("is-temperature", true);
  headStatus.classList.remove("is-cold", "is-warming", "is-rising", "is-ready");
  headStatus.classList.add(`is-${band.key}`);
  const label = el("pageHeadStatusLabel");
  const meta = el("pageHeadStatusMeta");
  if (label) label.textContent = `${temperature}°`;
  if (meta) meta.textContent = band.label;
}

function switchView(viewId, options = {}) {
  if (
    !options.skipProfileGate
    && (viewId === "assess" || viewId === "analyze")
    && !state.organizationProfile
  ) {
    state.currentView = "assess";
    document.querySelectorAll(".view-panel").forEach((panel) => {
      const active = panel.id === "view-assess";
      panel.classList.toggle("active", active);
      panel.hidden = !active;
    });
    setPageHead("assess");
    openProfilePanel();
    showToast("먼저 점검 범위를 적용하세요.");
    return;
  }
  state.currentView = viewId;
  document.querySelectorAll(".view-panel").forEach((panel) => {
    const active = panel.id === `view-${viewId}`;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  setPageHead(viewId);
  if (viewId === "assess") {
    if (state.organizationProfile) {
      openProfilePanel({ focus: false });
    }
  }
  if (viewId === "analyze") {
    const analyzeRoot = el("view-analyze");
    const currentWorkspaceMode = ["assessment", "results", "evidence", "report"]
      .find((mode) => analyzeRoot?.classList.contains(`is-${mode}`));
    setAnalyzeWorkspaceMode(currentWorkspaceMode || "assessment");
    switchAnalyzeSection(state.analyzeSection || "actions");
    if (state.analysis) {
      renderAnalyzeView(true);
      const content = el("analyzeContent");
      const report = el("analysisReportPanel");
      if (content) content.style.display = "";
      if (report) report.style.display = "";
    } else if (!options.skipAutoAnalyze) {
      ensureAnalyzeResults();
    }
  }
  renderStats();
}

function renderConfirmationActions(analysis) {
  renderSessionActions(analysis, { diagnoseControl, markAnalysisStale });
}

function runAiReport() {
  return executeAiReport({
    domainChecksPayload,
    renderAnalyzeView,
  });
}

function runAnalysis(switchToAnalyze, options = {}) {
  return executeAnalysis(switchToAnalyze, {
    loadingMode: "priority",
    ...options,
  }, {
    showProfileWizard,
    switchView,
    domainChecksPayload,
    renderProfileContext,
    renderStats,
    syncAssessmentsFromApplicability,
    renderAnalyzeView,
  });
}

function renderAnalyzeView(skipHero) {
  renderAnalysisSummary(skipHero, { renderConfirmationActions });
}

function renderSessionManager() {
  renderDiagnosisSessionPicker({
    onOpen: openDiagnosisSession,
    onCreate: createDiagnosisSession,
    onDuplicate: duplicateDiagnosisSession,
    onRename: renameDiagnosisSession,
    onExport: exportDiagnosisSession,
    onImport: importDiagnosisSession,
    onDelete: deleteDiagnosisSession,
  });
}

function showSessionManager() {
  navigateTo("sessions");
}

function syncDocumentTitle(routeId) {
  const route = ROUTES[routeId] || ROUTES.sessions;
  document.title = "ONDO°";
}

function syncSidebar(routeId) {
  document.querySelectorAll(".sidebar-nav a[data-route]").forEach((item) => {
    const active = item.dataset.route === routeId;
    item.classList.toggle("is-active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
}

function syncHistory(routeId, { replace = false, skipHistory = false } = {}) {
  const route = ROUTES[routeId] || ROUTES.sessions;
  if (skipHistory) return;
  const current = parsePath(window.location.pathname);
  if (current?.id === route.id && !replace) return;
  const method = replace || !current ? "replaceState" : "pushState";
  window.history[method]({ routeId: route.id }, "", route.path);
}

function defaultRouteAfterOpen() {
  const current = parsePath(window.location.pathname);
  if (current && current.id !== "sessions") return current.id;
  return state.organizationProfile ? "assessment" : "scope";
}

function applyRoute(routeId, options = {}) {
  const route = ROUTES[routeId] || ROUTES.sessions;
  syncHistory(route.id, options);
  syncDocumentTitle(route.id);
  syncSidebar(route.id);

  if (route.id === "sessions") {
    pendingRouteId = null;
    cancelActiveAnalysis();
    renderSessionManager();
    showDiagnosisSessionPicker();
    window.scrollTo({ top: 0, behavior: "auto" });
    return;
  }

  if (!state.activeSessionId) {
    pendingRouteId = route.id;
    renderSessionManager();
    showDiagnosisSessionPicker();
    window.scrollTo({ top: 0, behavior: "auto" });
    return;
  }

  pendingRouteId = null;
  showDiagnosisApp();
  if (route.id === "scope") {
    switchView("assess", { skipProfileGate: true });
    openProfilePanel();
    window.scrollTo({ top: 0, behavior: "auto" });
    return;
  }
  if (!state.organizationProfile) {
    showToast("먼저 점검 범위를 적용하세요.");
    applyRoute("scope", { replace: true });
    return;
  }
  setAnalyzeWorkspaceMode(route.workspace || "assessment");
  switchView("analyze");
}

async function openDiagnosisSession(sessionId) {
  if (sessionOpening) return;
  cancelActiveAnalysis();
  const session = activateDiagnosisSession(sessionId);
  if (!session) {
    showToast("선택한 진단을 찾을 수 없습니다.");
    renderSessionManager();
    return;
  }

  sessionOpening = true;
  const loadingSkeleton = el("workspaceLoadingSkeleton");
  try {
    showDiagnosisApp();
    syncAssessLayout();
    closeProfilePanel();

    const targetRoute = pendingRouteId && pendingRouteId !== "sessions"
      ? pendingRouteId
      : defaultRouteAfterOpen();
    if (state.organizationProfile && targetRoute !== "scope") {
      const route = ROUTES[targetRoute] || ROUTES.assessment;
      setAnalyzeWorkspaceMode(route.workspace || "assessment");
      switchView("analyze", { skipAutoAnalyze: true });
      if (!appDataLoaded && loadingSkeleton) {
        loadingSkeleton.hidden = false;
        el("view-analyze")?.setAttribute("aria-busy", "true");
      }
    }

    if (!appDataLoaded) {
      const [dashboard, checklist] = await Promise.all([
        fetchJson("/controls/dashboard"),
        fetchJson("/controls/checklist?compact=true"),
      ]);
      state.dashboard = dashboard;
      state.allControls = checklist.controls;
      await loadChecklist(checklist);
      appDataLoaded = true;
    }

    renderProfileContext();
    renderStats();
    applyRoute(targetRoute, { replace: true });
    window.scrollTo({ top: 0, behavior: "auto" });
  } catch (error) {
    showSessionManager();
    showToast(`진단을 불러오지 못했습니다: ${error.message}`);
  } finally {
    if (loadingSkeleton) loadingSkeleton.hidden = true;
    el("view-analyze")?.removeAttribute("aria-busy");
    sessionOpening = false;
  }
}

function createDiagnosisSession() {
  const session = createStoredDiagnosisSession();
  openDiagnosisSession(session.id);
}

function duplicateDiagnosisSession(sessionId) {
  const duplicate = duplicateStoredDiagnosisSession(sessionId);
  if (!duplicate) return;
  resetDiagnosisSessionPage();
  renderSessionManager();
}

function renameDiagnosisSession(sessionId, name) {
  const session = state.diagnosisSessions.find((item) => item.id === sessionId);
  if (!session) return false;
  const renamed = renameStoredDiagnosisSession(sessionId, name);
  if (!renamed) return false;
  renderSessionManager();
  if (renamed.name !== session.name) {
    showToast(`진단 이름을 “${renamed.name}”(으)로 바꿨습니다.`);
  }
  return true;
}

function safeBackupFilename(value) {
  const base = String(value || "진단")
    .replace(/[\\/:*?"<>|]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 60) || "진단";
  return `${base}-백업.json`;
}

function exportDiagnosisSession(sessionId) {
  try {
    const backup = exportStoredDiagnosisSession(sessionId);
    const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = safeBackupFilename(backup.session.name);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast("진단 백업을 저장했습니다. 다른 브라우저에서 ‘백업 가져오기’를 사용하세요.");
  } catch (error) {
    showToast(`백업을 만들지 못했습니다: ${error.message}`);
  }
}

async function importDiagnosisSession(file) {
  if (file.size > 5 * 1024 * 1024) {
    showToast("백업 파일은 5MB 이하만 가져올 수 있습니다.");
    return;
  }
  try {
    const backup = inspectStoredDiagnosisBackup(await file.text());
    const confirmed = await confirmAction({
      title: `“${backup.name}” 진단을 가져올까요?`,
      message: `점검 ${backup.progress.reviewed}/${backup.progress.applicable}개가 포함되어 있습니다. 기존 진단은 유지되고 새 진단으로 추가됩니다.`,
      confirmLabel: "새 진단으로 가져오기",
    });
    if (!confirmed) return;
    const imported = importStoredDiagnosisBackup(backup);
    resetDiagnosisSessionPage();
    renderSessionManager();
    showToast(`${imported.name}을(를) 가져왔습니다.`);
  } catch (error) {
    showToast(`백업을 가져오지 못했습니다: ${error.message}`);
  }
}

async function deleteDiagnosisSession(sessionId) {
  const session = state.diagnosisSessions.find((item) => item.id === sessionId);
  if (!session) return;
  const confirmed = await confirmAction({
    title: `${session.name} 진단을 삭제할까요?`,
    message: "진단 상태와 증적 정보가 함께 삭제되며 되돌릴 수 없습니다.",
    confirmLabel: "진단 삭제",
    tone: "danger",
  });
  if (!confirmed) return;
  deleteStoredDiagnosisSession(sessionId);
  renderSessionManager();
  showToast("진단을 삭제했습니다.");
}

function bindEvents() {
  bindReportEditor();
  bindReportRewrite();
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-route]");
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    navigateTo(link.dataset.route);
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-run-analysis]")) {
      runAnalysis(true, {
        loadingMode: "priority",
        successToast: "확인 목록을 갱신했습니다.",
      });
    }
  });
  document.querySelectorAll("[data-write-ai-report]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!(await ensureAccessPass())) return;
      const editor = el("executiveReportStream");
      if (editor?.dataset.userEdited === "1") {
        const confirmed = await confirmAction({
          title: "AI 초안으로 바꿀까요?",
          message: "직접 고친 본문이 AI 초안으로 대체됩니다.",
          confirmLabel: "다시 작성",
          cancelLabel: "편집 유지",
        });
        if (!confirmed) return;
      }
      runAiReport();
    });
  });
  el("profileForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!hasSelectedEnvironment()) {
      showToast("클라우드 또는 자체 인프라를 하나 이상 선택하세요.");
      el("profileCloud")?.focus();
      return;
    }
    const button = el("applyProfileBtn");
    if (button) button.disabled = true;
    try {
      await applyOrganizationProfile(readProfileForm(), {
        runAnalyzeAfter: true,
        switchToAnalyze: true,
      });
      navigateTo("assessment", { replace: true });
    } catch (error) {
      showToast("환경 적용 실패: " + error.message);
    } finally {
      if (button) button.disabled = !hasSelectedEnvironment();
    }
  });
  ["profileCloud", "profileOnPrem"].forEach((id) => {
    el(id)?.addEventListener("change", renderProfileImpact);
  });
  el("returnToReportBtn")?.addEventListener("click", returnToReportReview);
  setupAnalyzeClickDelegation({ navigateToControl });

  el("exportReportBtn")?.addEventListener("click", exportAnalysisMarkdown);
  el("exportReportDocxBtn")?.addEventListener("click", exportAnalysisDocx);
  el("resetReportBtn")?.addEventListener("click", resetReportEditor);

  window.addEventListener("popstate", () => {
    const route = parsePath(window.location.pathname);
    applyRoute(route?.id || "sessions", { skipHistory: true });
  });
}

export async function bootstrap() {
  configureAssessmentController({
    markAnalysisStale,
    renderConfirmationActions,
    renderStats,
    runAnalysis,
    switchView,
    switchAnalyzeSection,
  });
  setRouteHandler(applyRoute);
  initializeDiagnosisSessions();
  initAccessPass();
  bindEvents();
  await ensureWorkspaceAccess();
  const initial = parsePath(window.location.pathname);
  const routeId = initial?.id || "sessions";
  if (state.activeSessionId && routeId !== "sessions") {
    pendingRouteId = routeId;
    await openDiagnosisSession(state.activeSessionId);
    return;
  }
  applyRoute(routeId, { replace: true });
}
