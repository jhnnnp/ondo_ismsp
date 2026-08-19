import { ANALYSIS_HISTORY_KEY } from "../../core/constants.js";
import { el, escapeHtml, showToast, sleep } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { persistActiveDiagnosisSession } from "../../core/storage.js";
import { ensureAccessPass } from "../../core/access-pass.js";
import { qualitativeLabelFromPercent, remapScoreTerminology } from "./utils.js";

const ANALYSIS_HISTORY_PAGE_SIZE = 5;
let analysisHistoryPage = 1;
let pendingReportRewrite = null;

function setReportEditorValue(editor, value, edited = false) {
  if (!editor) return;
  editor.value = String(value || "");
  editor.dataset.userEdited = edited ? "1" : "0";
  editor.dispatchEvent(new CustomEvent("report-editor:set", {
    detail: { value: editor.value, edited },
  }));
}

function reportSourceText() {
  const source = state.lastAiExecutiveReport || state.analysis?.executiveReport || "";
  return remapScoreTerminology(source);
}

function hasReportBody() {
  return Boolean(String(state.lastAiExecutiveReport || state.analysis?.executiveReport || "").trim());
}

function reportSourceKind() {
  const editor = el("executiveReportStream");
  if (editor?.dataset.userEdited === "1") return "edited";
  if (state.lastAiExecutiveReport) return "ai";
  if (state.analysis?.executiveReport) return "rule";
  return "empty";
}

function setReportEditorState(text, dirty = false) {
  const status = el("reportEditorState");
  if (!status) return;
  status.textContent = text;
  status.classList.toggle("is-dirty", dirty);
  status.classList.toggle("is-ai", !dirty && reportSourceKind() === "ai");
}

function syncReportWordCount() {
  const countEl = el("reportWordCount");
  const editor = el("executiveReportStream");
  if (!countEl || !editor) return;
  if (editor.dataset.reactEditor === "1") return;
  const length = String(editor.value || "").length;
  countEl.textContent = `공백 포함 ${length.toLocaleString("ko-KR")}자`;
}

function syncReportOverlay() {
  const overlay = el("reportComposeOverlay");
  const page = el("reportPage");
  const editor = el("executiveReportStream");
  if (!overlay) return;
  const emptyCard = overlay.querySelector('[data-overlay-state="empty"]');
  const writingCard = overlay.querySelector('[data-overlay-state="writing"]');
  const writing = Boolean(state.aiReportWriting);
  const empty = !hasReportBody() && !writing;
  overlay.hidden = !(writing || empty);
  if (emptyCard) emptyCard.hidden = !empty;
  if (writingCard) writingCard.hidden = !writing;
  page?.classList.toggle("is-writing", writing);
  page?.setAttribute("aria-busy", writing ? "true" : "false");
  if (editor) editor.readOnly = writing;
}

function syncReportFlow() {
  const kind = reportSourceKind();
  const writing = Boolean(state.aiReportWriting);
  const steps = {
    basis: Boolean(state.analysis) || writing,
    draft: kind === "ai" || kind === "edited" || writing,
    edit: kind === "edited" || (kind === "ai" && !writing),
    export: kind === "ai" || kind === "edited" || kind === "rule",
  };
  const active = writing
    ? "draft"
    : kind === "edited"
      ? "edit"
      : kind === "ai"
        ? "edit"
        : kind === "rule"
          ? "draft"
          : "basis";
  document.querySelectorAll("[data-report-flow]").forEach((item) => {
    const key = item.getAttribute("data-report-flow");
    item.classList.toggle("is-done", Boolean(steps[key]) && key !== active);
    item.classList.toggle("is-active", key === active);
  });
}

export function bindReportEditor() {
  const editor = el("executiveReportStream");
  if (!editor || editor.dataset.editorBound === "1") return;
  editor.dataset.editorBound = "1";
  editor.addEventListener("input", () => {
    editor.dataset.userEdited = "1";
    setReportEditorState("편집 중", true);
    syncReportWordCount();
    syncReportFlow();
    const badge = el("reportSourceBadge");
    if (badge) badge.textContent = "직접 편집";
    window.clearTimeout(Number(editor.dataset.saveTimer || 0));
    const timer = window.setTimeout(() => {
      editor.dataset.savedValue = editor.value;
      setReportEditorState("편집 내용 유지됨", false);
    }, 450);
    editor.dataset.saveTimer = String(timer);
  });
  editor.addEventListener("compositionend", syncReportWordCount);
  editor.addEventListener("change", syncReportWordCount);
  window.addEventListener("report-editor:toast", (event) => showToast(event.detail || "보고서 편집 내용을 확인하세요."));
  syncAiReportChrome();
}

function markReportEdited(editor, message = "편집 내용 유지됨") {
  editor.dataset.userEdited = "1";
  editor.dataset.savedValue = editor.value;
  setReportEditorState(message, false);
  syncReportWordCount();
  syncReportFlow();
  const badge = el("reportSourceBadge");
  if (badge) badge.textContent = "직접 편집";
}

function closeReportRewrite() {
  pendingReportRewrite = null;
  const preview = el("reportRewritePreview");
  if (preview) preview.hidden = true;
}

export function bindReportRewrite() {
  const editor = el("executiveReportStream");
  const requestBtn = el("reportRewriteBtn");
  const acceptBtn = el("reportRewriteAcceptBtn");
  const rejectBtn = el("reportRewriteRejectBtn");
  const closeBtn = el("reportRewriteCloseBtn");
  if (!editor || !requestBtn || requestBtn.dataset.bound === "1") return;
  requestBtn.dataset.bound = "1";

  requestBtn.addEventListener("click", async () => {
    if (!(await ensureAccessPass())) return;
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    const selected = editor.value.slice(start, end).trim();
    if (!selected) {
      showToast("보고서 본문에서 개선할 문장을 먼저 선택하세요.");
      editor.focus();
      return;
    }
    if (selected.length > 8000) {
      showToast("선택 문장은 8,000자 이하로 줄여주세요.");
      return;
    }

    requestBtn.disabled = true;
    requestBtn.textContent = "개선 중…";
    closeReportRewrite();
    try {
      const response = await fetch("/controls/report/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: selected, mode: el("reportRewriteMode")?.value || "professional" }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "문장 개선 요청에 실패했습니다.");
      }
      const result = await response.json();
      pendingReportRewrite = {
        start,
        end,
        original: editor.value.slice(start, end),
        suggestion: String(result.suggestion || ""),
      };
      el("reportRewriteBefore").textContent = pendingReportRewrite.original;
      el("reportRewriteAfter").textContent = pendingReportRewrite.suggestion;
      el("reportRewriteStatus").textContent = result.reason || "개선안을 확인하세요.";
      el("reportRewritePreview").hidden = false;
      acceptBtn.disabled = !result.applied || pendingReportRewrite.suggestion === pendingReportRewrite.original;
      closeBtn?.focus();
    } catch (error) {
      showToast(`문장 개선 실패: ${error.message}`);
    } finally {
      requestBtn.disabled = false;
      requestBtn.textContent = "선택 문장 개선";
    }
  });

  acceptBtn?.addEventListener("click", () => {
    if (!pendingReportRewrite) return;
    const { start, end, original, suggestion } = pendingReportRewrite;
    if (editor.value.slice(start, end) !== original) {
      showToast("본문이 변경되어 개선안을 적용할 수 없습니다. 문장을 다시 선택하세요.");
      closeReportRewrite();
      return;
    }
    editor.value = `${editor.value.slice(0, start)}${suggestion}${editor.value.slice(end)}`;
    editor.setSelectionRange(start, start + suggestion.length);
    markReportEdited(editor, "개선안 적용됨");
    closeReportRewrite();
    editor.focus();
    showToast("선택 문장에 개선안을 적용했습니다.");
  });
  rejectBtn?.addEventListener("click", () => {
    closeReportRewrite();
    showToast("개선안을 적용하지 않았습니다.");
  });
  closeBtn?.addEventListener("click", closeReportRewrite);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !el("reportRewritePreview")?.hidden) {
      closeReportRewrite();
      editor.focus();
    }
  });
}

export function resetReportEditor() {
  const editor = el("executiveReportStream");
  if (!editor) return;
  setReportEditorValue(editor, reportSourceText() || "확인 목록을 갱신하면 초안이 여기에 표시됩니다.");
  editor.dataset.sourceValue = editor.value;
  editor.dataset.userEdited = "0";
  closeReportRewrite();
  setReportEditorState("원문 복원됨", false);
  syncAiReportChrome();
  showToast("자동 생성 원문으로 복원했습니다.");
}

function readAnalysisHistory() {
  if (state.activeSessionId) return state.analysisHistory || [];
  try {
    return JSON.parse(localStorage.getItem(ANALYSIS_HISTORY_KEY) || "[]");
  } catch (_) {
    return [];
  }
}

export function renderVerbalizeStatus(_meta) {
  /* reportStatus UI removed — keep no-op for existing call sites */
}

export function syncAiReportChrome() {
  const hasAi = Boolean(state.lastAiExecutiveReport);
  const writing = Boolean(state.aiReportWriting);
  const canWrite = Boolean(state.analysis) && !state.analysisStale && !writing;
  const kind = reportSourceKind();
  const sourceLabels = {
    empty: "초안 없음",
    rule: "진단 초안",
    ai: "AI 초안",
    edited: "직접 편집",
  };
  const badge = el("reportSourceBadge");
  if (badge) badge.textContent = writing ? "작성 중" : sourceLabels[kind];
  document.querySelectorAll("[data-write-ai-report]").forEach((btn) => {
    btn.disabled = !canWrite;
    if (btn.id === "writeAiReportBtn") {
      btn.textContent = writing
        ? "작성 중…"
        : (hasAi ? "AI로 다시 작성" : (hasReportBody() ? "AI로 재작성" : "AI로 초안 작성"));
      btn.classList.toggle("primary", !hasAi || writing);
    }
  });
  const docxBtn = el("exportReportDocxBtn");
  if (docxBtn) docxBtn.classList.toggle("primary", hasAi && !writing);
  const resetBtn = el("resetReportBtn");
  if (resetBtn) resetBtn.disabled = writing || !hasReportBody();
  syncReportOverlay();
  syncReportFlow();
  syncReportWordCount();
  const status = el("aiReportStatus");
  if (!status) return;
  status.classList.remove("is-ready", "is-pending");
  if (writing) {
    status.hidden = true;
    return;
  }
  if (state.analysisStale) {
    status.hidden = false;
    status.classList.add("is-pending");
    status.textContent = "진단이 바뀌었습니다. 확인 목록을 먼저 갱신하세요.";
    return;
  }
  if (hasAi && state.aiReportStale) {
    status.hidden = false;
    status.classList.add("is-pending");
    status.textContent = "확인 목록이 바뀌었습니다. 아래는 이전 AI 문장입니다.";
    return;
  }
  if (hasAi) {
    status.hidden = false;
    status.classList.add("is-ready");
    status.textContent = "AI 초안입니다. 본문을 직접 고친 뒤 Word로 내보내세요.";
    return;
  }
  if (kind === "rule") {
    status.hidden = false;
    status.classList.add("is-pending");
    status.textContent = "지금은 진단 기반 초안입니다. AI로 문장을 재작성할 수 있습니다.";
    return;
  }
  status.hidden = true;
}

export function syncExecutiveReportStream(options = {}) {
  const streamEl = el("executiveReportStream");
  if (!streamEl) return;
  const basis = el("reportEditorBasis");
  if (basis) {
    basis.textContent = `현재 진단 ${Number(state.analysis?.reviewedControlCount) || 0}/${Number(state.analysis?.applicableControlCount) || 0} 기준`;
  }
  if (streamEl.classList.contains("typing") || state.aiReportWriting) return;
  const preferTemplate = Boolean(options.preferTemplate);
  if (streamEl.dataset.userEdited === "1" && !preferTemplate) return;
  const source = preferTemplate
    ? remapScoreTerminology(state.analysis?.executiveReport || reportSourceText())
    : reportSourceText();
  streamEl.dataset.historyKey = state.activeSessionId || "default";
  setReportEditorValue(streamEl, source);
  streamEl.dataset.sourceValue = source;
  streamEl.dataset.userEdited = "0";
  setReportEditorState(source ? "초안 준비됨" : "초안 대기", false);
  syncAiReportChrome();
}

export async function streamExecutiveReport(text) {
  const streamEl = el("executiveReportStream");
  if (!streamEl) return;
  const token = (state.reportStreamToken = (state.reportStreamToken || 0) + 1);
  const source = remapScoreTerminology(text);
  if (streamEl.dataset.reactEditor === "1") {
    setReportEditorValue(streamEl, source);
    streamEl.dataset.sourceValue = source;
    setReportEditorState("AI 초안 적용됨", false);
    syncAiReportChrome();
    return;
  }
  streamEl.value = "";
  streamEl.dataset.userEdited = "0";
  streamEl.classList.add("typing");
  const chunkSize = 3;
  for (let i = 0; i < source.length; i += chunkSize) {
    if (token !== state.reportStreamToken) return;
    streamEl.value += source.slice(i, i + chunkSize);
    streamEl.scrollTop = streamEl.scrollHeight;
    await sleep(14);
  }
  if (token !== state.reportStreamToken) return;
  streamEl.classList.remove("typing");
  streamEl.dataset.sourceValue = source;
  setReportEditorState("AI 초안 적용됨", false);
  syncAiReportChrome();
}

export function saveAnalysisHistory(data) {
  const entry = {
    ts: Number(data.clientAnalyzedAt || Date.now()),
    overallReadiness: data.overallReadiness,
    gapCount: data.gapCount,
    readinessLabel: data.readinessLabel,
    scenarioId: state.analyzeScenarioId || null,
  };
  analysisHistoryPage = 1;
  if (state.activeSessionId) {
    state.analysisHistory = [entry, ...(state.analysisHistory || [])].slice(0, 8);
    persistActiveDiagnosisSession();
    return;
  }
  try {
    const history = JSON.parse(localStorage.getItem(ANALYSIS_HISTORY_KEY) || "[]");
    history.unshift(entry);
    localStorage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(history.slice(0, 8)));
  } catch (_) {
    /* ignore */
  }
}

function renderHistoryItem(item) {
  const when = new Date(item.ts).toLocaleString("ko-KR");
  const band = escapeHtml(
    item.readinessLabel
    || (Number.isFinite(Number(item.overallReadiness))
      ? qualitativeLabelFromPercent(item.overallReadiness)
      : "—"),
  );
  const gaps = Number.isFinite(Number(item.gapCount)) ? item.gapCount : 0;
  return `
    <article class="analysis-history-item">
      <div class="analysis-history-item__main">
        <strong>${escapeHtml(when)}</strong>
        <span class="analysis-history-item__label">참고 구간</span>
      </div>
      <div class="analysis-history-item__stats">
        <span>전체 진행 참고 <em>${band}</em></span>
        <span>확인된 미흡 <em>${escapeHtml(String(gaps))}건</em></span>
      </div>
    </article>
  `;
}

export function renderAnalysisHistory() {
  const box = el("analysisHistory");
  const meta = el("analysisHistoryMeta");
  if (!box) return;
  try {
    const history = readAnalysisHistory();
    if (meta) {
      meta.textContent = history.length ? `${history.length}건` : "기록 없음";
    }
    if (!history.length) {
      analysisHistoryPage = 1;
      box.innerHTML = `
        <div class="analysis-history-empty" role="status">
          <strong>아직 저장된 진단 결과가 없습니다</strong>
          <p>확인 목록을 만들면 최근 결과가 여기에 쌓입니다. 인증 심사 자료가 아니라 내부 참고용입니다.</p>
        </div>
      `;
      return;
    }

    const pageCount = Math.max(1, Math.ceil(history.length / ANALYSIS_HISTORY_PAGE_SIZE));
    analysisHistoryPage = Math.min(Math.max(1, analysisHistoryPage), pageCount);
    const start = (analysisHistoryPage - 1) * ANALYSIS_HISTORY_PAGE_SIZE;
    const pageItems = history.slice(start, start + ANALYSIS_HISTORY_PAGE_SIZE);

    const pager = pageCount > 1
      ? `
        <nav class="analysis-history-pager" aria-label="이전 진단 페이지">
          ${Array.from({ length: pageCount }, (_, index) => {
        const page = index + 1;
        const active = page === analysisHistoryPage;
        return `
              <button
                type="button"
                class="analysis-history-page${active ? " is-active" : ""}"
                data-history-page="${page}"
                aria-label="${page}페이지"
                aria-current="${active ? "page" : "false"}"
              >${page}</button>
            `;
      }).join("")}
        </nav>
      `
      : "";

    box.innerHTML = `
      <div class="analysis-history-list">
        ${pageItems.map(renderHistoryItem).join("")}
      </div>
      ${pager}
    `;

    box.querySelectorAll("[data-history-page]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = Number(button.getAttribute("data-history-page"));
        if (!Number.isFinite(next) || next === analysisHistoryPage) return;
        analysisHistoryPage = next;
        renderAnalysisHistory();
        el("analysisHistoryDetails")?.setAttribute("open", "");
      });
    });
  } catch (_) {
    if (meta) meta.textContent = "기록 없음";
    box.innerHTML = "";
  }
}

export function toggleInsightCard(btn) {
  const id = btn?.dataset?.insightToggle;
  if (!id) return;
  const card = btn.closest(".insight-card");
  const set = btn.closest("#problemAnalysisContent")
    ? state.expandedProblemClusters
    : state.expandedMultigaps;
  const open = !set.has(id);
  if (open) set.add(id);
  else set.delete(id);
  if (card) {
    card.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.textContent = open ? "▴" : "▾";
  }
}

export function exportAnalysisMarkdown() {
  const a = state.analysis;
  if (!a) {
    showToast("먼저 결과 탭에서 목록을 준비하세요.");
    return;
  }
  const body = el("executiveReportStream")?.value || reportSourceText();
  const blob = new Blob([body], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `isms-p-analysis-${Date.now()}.md`;
  link.click();
  URL.revokeObjectURL(url);
  showToast("Markdown 파일을 저장했습니다.");
}

export async function exportAnalysisDocx() {
  if (!state.analysis) {
    showToast("먼저 진단 결과를 준비하세요.");
    return;
  }
  const body = el("executiveReportStream")?.value || reportSourceText();
  try {
    const response = await fetch("/controls/report/docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "ISMS-P 자가진단 결과 보고서", content: body }),
    });
    if (!response.ok) throw new Error("DOCX 생성 실패");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `isms-p-report-${Date.now()}.docx`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Word 보고서를 저장했습니다.");
  } catch (error) {
    showToast(`Word 내보내기 실패: ${error.message}`);
  }
}

export function switchAnalyzeSection(sectionId) {
  const aliases = {
    clusters: "overview",
    problems: "overview",
    multigap: "overview",
    deep: "overview",
    detail: "overview",
  };
  const next = aliases[sectionId] || sectionId || "actions";
  state.analyzeSection = ["actions", "overview"].includes(next) ? next : "actions";
  document.querySelectorAll("[data-analyze-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.analyzePanel === state.analyzeSection);
  });
}

export function setupAnalyzeClickDelegation({ navigateToControl }) {
  const root = el("view-analyze");
  if (!root || root.dataset.delegated === "1") return;
  root.dataset.delegated = "1";
  root.addEventListener("click", (event) => {
    const jump = event.target.closest("[data-jump-control]");
    if (jump && root.contains(jump)) {
      event.preventDefault();
      event.stopPropagation();
      navigateToControl(jump.dataset.jumpControl);
      return;
    }
    const insightBtn = event.target.closest("[data-insight-toggle]");
    if (insightBtn && root.contains(insightBtn)) {
      event.preventDefault();
      event.stopPropagation();
      toggleInsightCard(insightBtn);
    }
  });
}
