import { AREA_SHORT, CHECK_LABEL, INPUT_CONF_LABEL, LEVEL_LABEL } from "../../core/constants.js";
import { confirmAction, el, escapeHtml, fetchJson, showToast } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { saveAssessments } from "../../core/storage.js";
import { navigateTo } from "../../core/routes.js";
import {
  addControlEvidence as pushEvidence,
  hasRegisteredEvidence,
  listControlEvidence,
  removeControlEvidence as dropEvidence,
} from "./evidence.js";
import { filteredChecklist, navChecklist, reviewedCount, applicableControlCount } from "./filter.js";
import { categoryProgress, checksFromLevel, compareDotId, getAssessment, groupControlsByCategory } from "./model.js";
import {
  renderAssessCategoryNav,
  renderAssessRailFilterHint as renderAssessmentFilterHint,
  renderAssessToolbar,
  renderControlAssessRow as renderAssessmentControlRow,
  renderLegalBasisContent,
  levelPill,
} from "./view.js";
import {
  applyChecksToControl,
  ensureChecks,
  ensureDomainChecks,
  promoteConfidenceAssumed,
  setDomainCheck,
} from "./actions.js";
let hooks = {};
let lawDialogTrigger = null;

function safeOfficialLawUrl(value) {
  try {
    const url = new URL(value || "");
    return url.protocol === "https:" && ["law.go.kr", "www.law.go.kr"].includes(url.hostname)
      ? url.href
      : "";
  } catch (_) {
    return "";
  }
}

function legalArticleHtml(rawText) {
  return String(rawText || "").split(/\n+/).map((line) => line.trim()).filter(Boolean).map((line) => {
    const safe = escapeHtml(line);
    if (/^제\d+조(?:의\d+)?(?:\(|$)/.test(line)) return `<h3 class="legal-text-heading">${safe}</h3>`;
    if (/^[①②③④⑤⑥⑦⑧⑨⑩]/.test(line)) return `<p class="legal-text-clause">${safe}</p>`;
    if (/^\d+[.．]\s*/.test(line)) return `<p class="legal-text-item">${safe}</p>`;
    if (/^[가-하][.．]\s*/.test(line)) return `<p class="legal-text-subitem">${safe}</p>`;
    return `<p>${safe}</p>`;
  }).join("");
}

function ensureLawArticleDialog() {
  let dialog = document.querySelector("#lawArticleDialog");
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.id = "lawArticleDialog";
  dialog.className = "app-modal legal-article-dialog";
  dialog.setAttribute("aria-labelledby", "lawArticleDialogTitle");
  dialog.innerHTML = `
    <div class="app-modal-shell legal-dialog-shell">
      <header class="app-modal-header legal-dialog-header">
        <div>
          <span class="legal-dialog-eyebrow">관련 법령 조문</span>
          <h2 id="lawArticleDialogTitle"></h2>
          <p class="legal-dialog-subtitle"></p>
        </div>
        <button type="button" class="app-modal-close legal-dialog-close" data-law-dialog-close aria-label="조문 창 닫기">×</button>
      </header>
      <div class="app-modal-scroll legal-dialog-scroll">
        <div class="legal-dialog-meta" aria-label="법령 정보"></div>
        <article class="legal-dialog-body"></article>
        <footer class="legal-dialog-footer"></footer>
      </div>
    </div>
  `;
  dialog.querySelector("[data-law-dialog-close]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    lawDialogTrigger?.focus();
    lawDialogTrigger = null;
  });
  document.body.append(dialog);
  return dialog;
}

function openLawArticleDialog(controlId, lawIndex, trigger) {
  const law = state.legalBasisCache?.[controlId]?.data?.laws?.[lawIndex];
  if (!law?.articleText) {
    showToast("표시할 조문 본문이 없습니다.");
    return;
  }
  const dialog = ensureLawArticleDialog();
  const title = [law.lawName || "관련 법령", law.article].filter(Boolean).join(" ");
  const metadata = [
    law.documentType,
    law.currentStatus,
    law.effectiveDate ? `시행 ${law.effectiveDate}` : "",
    law.ministry,
    law.basisType === "COMMON_CERTIFICATION_BASIS" ? "제도 공통 근거" : "통제 직접 근거",
  ].filter(Boolean);
  const sourceUrl = safeOfficialLawUrl(law.sourceUrl);
  dialog.querySelector("#lawArticleDialogTitle").textContent = title;
  dialog.querySelector(".legal-dialog-subtitle").textContent = law.articleTitle || "현행 조문 본문";
  dialog.querySelector(".legal-dialog-meta").innerHTML = metadata
    .map((item) => `<span>${escapeHtml(item)}</span>`)
    .join("");
  dialog.querySelector(".legal-dialog-body").innerHTML = legalArticleHtml(law.articleText);
  dialog.querySelector(".legal-dialog-footer").innerHTML = sourceUrl
    ? `<a class="legal-dialog-source" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">국가법령정보센터에서 원문 보기 ↗</a>`
    : "";
  lawDialogTrigger = trigger;
  dialog.showModal();
}

function bindLegalBasisActions(node) {
  node.querySelectorAll("[data-open-law-article]").forEach((button) => {
    button.addEventListener("click", () => {
      openLawArticleDialog(button.dataset.lawControl, Number(button.dataset.openLawArticle), button);
    });
  });
}

export async function loadLegalBasis(controlId, { force = false } = {}) {
  const current = state.legalBasisCache?.[controlId];
  if (!force && current?.status === "ready") {
    updateLegalBasisNode(controlId);
    return;
  }
  if (!force && current?.status === "loading") return;
  state.legalBasisCache[controlId] = { status: "loading" };
  updateLegalBasisNode(controlId);
  try {
    const data = await fetchJson(`/controls/${encodeURIComponent(controlId)}/legal-basis`);
    state.legalBasisCache[controlId] = { status: "ready", data };
  } catch (error) {
    state.legalBasisCache[controlId] = { status: "error", error: String(error?.message || error) };
  }
  updateLegalBasisNode(controlId);
}

function updateLegalBasisNode(controlId) {
  const node = document.querySelector(`[data-legal-basis="${CSS.escape(controlId)}"]`);
  if (!node) return;
  node.innerHTML = renderLegalBasisContent(controlId);
  node.querySelector("[data-retry-legal]")?.addEventListener("click", () => {
    loadLegalBasis(controlId, { force: true });
  });
  bindLegalBasisActions(node);
}

export function configureAssessmentController(nextHooks) {
  hooks = { ...nextHooks };
}

export function assumeUnsetConfidence() {
  let count = 0;
  Object.entries(state.assessments || {}).forEach(([controlId, level]) => {
    if (level === "unknown" || level === "na") return;
    const cur = state.inputConfidence?.[controlId] || "unknown";
    if (cur !== "unknown") return;
    state.inputConfidence[controlId] = "assumed";
    count += 1;
  });
  saveAssessments();
  if (state.currentView === "assess") renderAssessList();
  if (state.analysis) {
    hooks.renderConfirmationActions(state.analysis);
  }
  showToast(count ? `신뢰도 모름 → 추정: ${count}개` : "바꿀 모름 항목이 없습니다.");
  return count;
}

function refreshAfterEvidenceChange(controlId) {
  saveAssessments();
  renderAssessProgress();
  refreshAssessRowUI(controlId);
  if (state.analysis) {
    hooks.renderConfirmationActions(state.analysis);
    hooks.renderStats();
    hooks.markAnalysisStale?.();
  } else if (state.currentView === "assess") {
    renderAssessList();
  }
}

export function setControlCheck(controlId, key, checked) {
  if (key === "evidence" && checked && !hasRegisteredEvidence(controlId)) {
    showToast("증적 링크/메모를 먼저 등록하세요.");
    refreshAfterEvidenceChange(controlId);
    return;
  }
  if (key === "evidence" && !checked && hasRegisteredEvidence(controlId)) {
    showToast("등록된 증적이 있습니다. 목록에서 삭제한 뒤 해제하세요.");
    refreshAfterEvidenceChange(controlId);
    return;
  }
  const checks = { ...ensureChecks(controlId), [key]: checked };
  applyChecksToControl(controlId, checks);
  refreshAfterEvidenceChange(controlId);
}

export function registerControlEvidence(controlId, payload, { quiet = false } = {}) {
  const result = pushEvidence(controlId, payload);
  if (!result.ok) {
    showToast("증적 제목을 입력하세요.");
    return false;
  }
  applyChecksToControl(controlId, { ...ensureChecks(controlId), evidence: true });
  state.sessionSelectedControlId = controlId;
  refreshAfterEvidenceChange(controlId);
  if (!quiet) showToast(`${controlId} 증적을 등록했습니다.`);
  return true;
}

export function deleteControlEvidence(controlId, evidenceId) {
  dropEvidence(controlId, evidenceId);
  applyChecksToControl(controlId, { ...ensureChecks(controlId), evidence: hasRegisteredEvidence(controlId) });
  state.sessionSelectedControlId = controlId;
  refreshAfterEvidenceChange(controlId);
  showToast(hasRegisteredEvidence(controlId) ? "증적을 삭제했습니다." : "증적을 삭제해 부분 이행으로 조정됩니다.");
  return true;
}

export { listControlEvidence, hasRegisteredEvidence };

function refreshAssessRowUI(controlId) {
  const row = document.querySelector(`#assessList .assess-row[data-control="${controlId}"]`);
  if (!row) {
    if (state.currentView === "assess") renderAssessList();
    return;
  }
  const level = getAssessment(controlId);
  const checks = ensureChecks(controlId);
  row.classList.toggle("is-reviewed", level !== "unknown" && level !== "na");
  row.classList.toggle("is-risk", level === "none");
  const pill = row.querySelector(".assess-row-meta-line .status-pill");
  if (pill) {
    const wrap = document.createElement("div");
    wrap.innerHTML = levelPill(level);
    pill.replaceWith(wrap.firstElementChild);
  }
  Object.keys(CHECK_LABEL).forEach((checkKey) => {
    const input = row.querySelector(`input[data-check-control="${controlId}"][data-check-key="${checkKey}"]`);
    if (input) input.checked = !!checks[checkKey];
  });
  const group = row.closest(".assess-category-group");
  if (group) {
    const ids = [...group.querySelectorAll(".assess-row")].map((el) => el.dataset.control);
    const total = ids.length;
    const reviewed = ids.filter((id) => getAssessment(id) !== "unknown").length;
    const pct = total ? Math.round((reviewed / total) * 100) : 0;
    const strong = group.querySelector(".assess-category-progress strong");
    const bar = group.querySelector(".assess-category-bar i");
    if (strong) strong.textContent = `${reviewed}/${total}`;
    if (bar) bar.style.width = `${pct}%`;
  }
}

function bulkApplyToFiltered(buildChecks) {
  const items = filteredChecklist();
  if (!items.length) {
    showToast("현재 필터에 해당하는 통제가 없습니다.");
    return 0;
  }
  items.forEach((control) => {
    applyChecksToControl(control.id, buildChecks(ensureChecks(control.id)));
  });
  saveAssessments();
  renderAssessProgress();
  renderAssessList();
  return items.length;
}

export function bulkSetCheckForFiltered(key, checked) {
  const count = bulkApplyToFiltered((checks) => {
    const next = { ...checks, [key]: checked };
    if (key !== "reviewed" && checked) next.reviewed = true;
    if (key === "reviewed" && !checked) {
      next.policy = false;
      next.implemented = false;
      next.evidence = false;
    }
    if (key === "evidence" && checked) {
      next.policy = true;
      next.implemented = true;
    }
    return next;
  });
  if (count) {
    showToast(`${CHECK_LABEL[key]} ${checked ? "체크" : "해제"}: ${count}개`);
  }
}

export function bulkSetPresetForFiltered(preset) {
  const presets = {
    all: { reviewed: true, policy: true, implemented: true, evidence: true },
    none: { reviewed: false, policy: false, implemented: false, evidence: false },
    reviewed: { reviewed: true, policy: false, implemented: false, evidence: false },
  };
  const template = presets[preset];
  if (!template) return;
  const count = bulkApplyToFiltered(() => ({ ...template }));
  if (!count) return;
  const labels = {
    all: "전체 체크",
    none: "전체 해제",
    reviewed: "검토만 체크",
  };
  showToast(`${labels[preset]}: ${count}개`);
}

export function resetAssessFilters({ keepArea = true } = {}) {
  state.levelFilter = "all";
  state.assessSearch = "";
  if (el("assessSearch")) el("assessSearch").value = "";
  if (!keepArea) state.areaFilter = "all";
  state.categoriesBootstrapped = false;
  renderAssessList();
}

function getBulkCheckState(key) {
  const items = filteredChecklist();
  if (!items.length) return { checked: false, indeterminate: false };
  const checkedCount = items.filter((control) => ensureChecks(control.id)[key]).length;
  return {
    checked: checkedCount === items.length,
    indeterminate: checkedCount > 0 && checkedCount < items.length,
  };
}

function renderAssessListHead() {
  const items = filteredChecklist();
  const summary = el("assessFilterSummary");
  const bulk = el("assessColBulk");
  if (!summary || !bulk) return;

  const areaLabel = state.areaFilter === "all"
    ? "전체 영역"
    : (AREA_SHORT[state.areaFilter] || `영역 ${state.areaFilter}`);
  const levelLabel = state.levelFilter === "all"
    ? "전체 상태"
    : LEVEL_LABEL[state.levelFilter];
  const searchLabel = state.assessSearch.trim()
    ? ` / 검색 "${state.assessSearch.trim()}"`
    : "";

  summary.innerHTML = `<strong>${items.length}개</strong> 표시 / ${areaLabel} / ${levelLabel}${searchLabel}`;

  bulk.innerHTML = Object.keys(CHECK_LABEL).map((key) => `
    <label class="bulk-check-toggle" title="현재 목록 ${CHECK_LABEL[key]} 전체">
      <input type="checkbox" data-bulk-check="${key}">
      <span>${CHECK_LABEL[key]} 전체</span>
    </label>
  `).join("");

  bulk.querySelectorAll("[data-bulk-check]").forEach((checkbox) => {
    const key = checkbox.dataset.bulkCheck;
    const bulkState = getBulkCheckState(key);
    checkbox.checked = bulkState.checked;
    checkbox.indeterminate = bulkState.indeterminate;
    checkbox.addEventListener("change", () => {
      bulkSetCheckForFiltered(key, checkbox.checked);
    });
  });
}

export function renderAssessProgress() {
  const label = el("assessProgressLabel");
  const pctEl = el("assessProgressPct");
  const fill = el("assessProgressFill");
  const summary = el("levelSummary");
  if (!label && !pctEl && !fill && !summary) return;

  const reviewed = state.checklist.length
    ? state.checklist.filter((c) => {
      const level = getAssessment(c.id);
      return level !== "unknown" && level !== "na";
    }).length
    : reviewedCount();
  const applicable = state.checklist.length
    ? state.checklist.filter((c) => getAssessment(c.id) !== "na").length
    : applicableControlCount();
  const pct = applicable ? Math.round((reviewed / applicable) * 100) : 0;
  if (label) label.textContent = `응답 진행: ${reviewed} / ${applicable}`;
  if (pctEl) pctEl.textContent = `${pct}%`;
  if (fill) fill.style.width = `${pct}%`;
  const counts = Object.keys(LEVEL_LABEL).reduce((acc, key) => {
    acc[key] = 0;
    return acc;
  }, {});
  (state.checklist.length ? state.checklist : state.allControls).forEach((control) => {
    const level = getAssessment(control.id);
    counts[level] = (counts[level] || 0) + 1;
  });
  if (summary) {
    summary.innerHTML = Object.keys(LEVEL_LABEL).map((level) => `
      <div class="level-summary-item">
        <span class="level-${level}">${LEVEL_LABEL[level]}</span>
        <strong>${counts[level] || 0}</strong>
      </div>
    `).join("");
  }
}

function renderControlAssessRow(control) {
  return renderAssessmentControlRow(control, { ensureChecks, ensureDomainChecks });
}

function renderAssessRailFilterHint(visibleCount, navTotal) {
  renderAssessmentFilterHint(visibleCount, navTotal, () => {
    resetAssessFilters({ keepArea: true });
  });
}

export function renderAssessList() {
  const container = el("assessList");
  if (!container) return;
  renderAssessToolbar();
  renderAssessListHead();
  const navGroups = groupControlsByCategory(navChecklist());
  if (!state.checklist.length) {
    container.innerHTML = `<p class="detail-empty">체크리스트를 불러오는 중...</p>`;
    renderAssessRailFilterHint(0, 0);
    renderAssessCategoryNav([], new Set());
    return;
  }
  const items = filteredChecklist();
  const visibleIds = new Set(items.map((c) => c.id));
  renderAssessRailFilterHint(items.length, navChecklist().length);
  if (!items.length) {
    container.innerHTML = `<p class="detail-empty">조건에 맞는 통제가 없습니다. 영역/상태 필터 또는 검색어를 바꿔 보세요.</p>`;
    renderAssessCategoryNav(navGroups, visibleIds);
    return;
  }
  const groups = groupControlsByCategory(items);
  if (!state.categoriesBootstrapped && navGroups.length) {
    state.collapsedCategories = new Set(navGroups.slice(1).map((group) => group.categoryId));
    state.activeCategoryId = navGroups[0].categoryId;
    state.categoriesBootstrapped = true;
  }
  renderAssessCategoryNav(navGroups, visibleIds);
  container.innerHTML = groups.map((group, index) => {
    const progress = categoryProgress(group.controls);
    const collapsed = state.collapsedCategories.has(group.categoryId);
    return `
      <section class="assess-category-group${collapsed ? " collapsed" : ""}" data-category-group="${group.categoryId}" style="animation-delay:${Math.min(index * 0.02, 0.2)}s">
        <button type="button" class="assess-category-head" data-toggle-category="${group.categoryId}" aria-expanded="${collapsed ? "false" : "true"}">
          <span class="assess-category-id">${group.categoryId}</span>
          <span class="assess-category-title">
            <strong>${group.categoryName}</strong>
            <span>${group.areaName} / ${group.controls.length}개 통제</span>
          </span>
          <span class="assess-category-progress">
            <strong>${progress.reviewed}/${progress.total}</strong>
            <span class="assess-category-bar" aria-hidden="true"><i style="width:${progress.pct}%"></i></span>
          </span>
          <span class="assess-category-chevron" aria-hidden="true">▾</span>
        </button>
        <div class="assess-category-body">
          <div class="assess-category-grid">
            ${group.controls.map((control) => renderControlAssessRow(control)).join("")}
          </div>
        </div>
      </section>
    `;
  }).join("");

  container.querySelectorAll("[data-toggle-category]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const categoryId = btn.dataset.toggleCategory;
      const group = btn.closest(".assess-category-group");
      const willCollapse = !state.collapsedCategories.has(categoryId);
      if (willCollapse) state.collapsedCategories.add(categoryId);
      else state.collapsedCategories.delete(categoryId);
      state.activeCategoryId = categoryId;
      if (group) group.classList.toggle("collapsed", willCollapse);
      btn.setAttribute("aria-expanded", willCollapse ? "false" : "true");
      document.querySelectorAll("#assessCategoryNav [data-jump-category]").forEach((navBtn) => {
        navBtn.classList.toggle("active", navBtn.dataset.jumpCategory === categoryId);
      });
    });
  });

  container.querySelectorAll(".assess-row-head").forEach((head) => {
    head.addEventListener("click", (event) => {
      if (event.target.closest("label.audit-check, input[type=checkbox], .domain-check-item, .assess-confidence, select[data-row-confidence]")) return;
      const row = head.closest(".assess-row");
      const id = row.dataset.control;
      const willExpand = !state.expandedRows.has(id);
      if (willExpand) state.expandedRows.add(id);
      else state.expandedRows.delete(id);
      renderAssessList();
      if (willExpand) loadLegalBasis(id);
    });
  });

  container.querySelectorAll("[data-legal-basis]").forEach((node) => {
    loadLegalBasis(node.dataset.legalBasis);
  });

  container.querySelectorAll("[data-row-confidence]").forEach((node) => {
    node.addEventListener("click", (event) => event.stopPropagation());
    node.addEventListener("change", (event) => {
      event.stopPropagation();
      const controlId = node.getAttribute("data-row-confidence");
      if (!controlId) return;
      state.inputConfidence[controlId] = node.value;
      saveAssessments();
      showToast(`${controlId} 신뢰도를 ${INPUT_CONF_LABEL[node.value] || node.value}로 저장했습니다.`);
      if (state.analysis) hooks.renderConfirmationActions(state.analysis);
    });
  });

  container.querySelectorAll("[data-check-control]").forEach((checkbox) => {
    checkbox.addEventListener("click", (event) => {
      event.stopPropagation();
    });
    checkbox.addEventListener("change", (event) => {
      event.stopPropagation();
      setControlCheck(
        checkbox.dataset.checkControl,
        checkbox.dataset.checkKey,
        checkbox.checked
      );
    });
  });

  container.querySelectorAll("[data-domain-control]").forEach((checkbox) => {
    checkbox.addEventListener("click", (event) => event.stopPropagation());
    checkbox.addEventListener("change", (event) => {
      event.stopPropagation();
      setDomainCheck(
        checkbox.dataset.domainControl,
        checkbox.dataset.domainItem,
        checkbox.checked
      );
    });
  });
}

export async function loadChecklist(prefetchedData = null) {
  const data = prefetchedData || await fetchJson("/controls/checklist");
  state.checklist = data.controls;
  const before = JSON.stringify([state.assessments, state.controlChecks]);
  state.checklist.forEach((c) => {
    if (!(c.id in state.assessments)) state.assessments[c.id] = "unknown";
    ensureChecks(c.id);
  });
  if (before !== JSON.stringify([state.assessments, state.controlChecks])) {
    saveAssessments();
  }
  renderAssessProgress();
  renderAssessList();
}

export async function bootstrapAssessment() {
  const data = await fetchJson("/controls/bootstrap-assessment");
  state.assessments = { ...state.assessments, ...data.assessments };
  Object.entries(data.assessments).forEach(([controlId, level]) => {
    state.controlChecks[controlId] = checksFromLevel(level);
    if (level !== "unknown" && level !== "na") promoteConfidenceAssumed(controlId);
  });
  saveAssessments();
  renderAssessProgress();
  renderAssessList();
  showToast("101개 통제를 구현 기준으로 채웠습니다. (미응답 없음 / 신뢰도 추정)");
}

export async function resetAssessment() {
  const confirmed = await confirmAction({
    title: "자가진단 상태를 초기화할까요?",
    message: "모든 통제의 진단 상태와 등록된 증적이 초기화됩니다. 이 작업은 되돌릴 수 없습니다.",
    confirmLabel: "전체 초기화",
    tone: "danger",
  });
  if (!confirmed) return;
  state.assessments = {};
  state.controlChecks = {};
  state.controlEvidence = {};
  state.domainChecks = {};
  state.domainTouched = {};
  state.checklist.forEach((control) => {
    state.assessments[control.id] = "unknown";
    state.controlChecks[control.id] = checksFromLevel("unknown");
  });
  state.analysis = null;
  state.expandedGaps.clear();
  state.gapSearch = "";
  const gapSearch = el("gapSearch");
  if (gapSearch) gapSearch.value = "";
  saveAssessments();
  renderAssessProgress();
  renderAssessList();
  hooks.renderStats();
  showToast("셀프진단을 초기화했습니다.");
}

export function diagnoseControl(controlId, level) {
  let applied = level === "evidenced" ? "done" : level;
  let guarded = false;
  if (applied === "done" && !hasRegisteredEvidence(controlId)) {
    // 세션 UI에서 한 줄 입력을 먼저 받는 것이 기본. 여기로 오면 부분 이행으로 강등.
    applied = "partial";
    guarded = true;
  }
  state.pendingDoneEvidenceControlId = null;
  applyChecksToControl(controlId, checksFromLevel(applied));
  if (applied === "done") {
    applyChecksToControl(controlId, { ...ensureChecks(controlId), evidence: true });
  }
  if (applied === "unknown") {
    state.inputConfidence[controlId] = "unknown";
  } else {
    state.inputConfidence[controlId] = "confirmed";
  }
  state.sessionSelectedControlId = controlId;
  saveAssessments();
  showToast(
    guarded
      ? "증적 없이 부분 이행으로 저장했습니다."
      : `${controlId} 진단: ${LEVEL_LABEL[applied] || applied}`,
  );
  if (state.analysis) {
    hooks.renderConfirmationActions(state.analysis);
    hooks.renderStats();
    hooks.markAnalysisStale?.();
  }
}

export function renderReportReturnBar() {
  const bar = el("reportReturnBar");
  if (!bar) return;
  const context = state.reportReturn;
  bar.hidden = !context;
  if (!context) return;
  const title = el("reportReturnTitle");
  const status = el("reportReturnStatus");
  if (title) {
    const control = [context.controlId, context.controlTitle].filter(Boolean).join(" ");
    title.textContent = [context.itemTitle, control].filter(Boolean).join(" · ");
  }
  if (status) {
    status.textContent = state.analysisStale
      ? "진단이 변경되었습니다. 돌아간 뒤 확인 목록을 갱신하세요."
      : "이 통제를 점검한 뒤 원래 카드로 돌아갈 수 있습니다.";
  }
}

function scrollToSessionDiagnosis(controlId) {
  const card = (controlId
    ? document.querySelector(`.session-detail-card[data-today-control="${CSS.escape(controlId)}"]`)
    : null)
    || document.querySelector(".session-detail-card")
    || el("sessionDetailPane");
  if (!card) return;

  const anchor = card.querySelector(".today-card-top")
    || card.querySelector(".today-question")
    || card;
  anchor.scrollIntoView({ behavior: "smooth", block: "start" });

  if (!controlId) return;
  const tree = el("sessionMasterTree");
  const treeItem = tree?.querySelector(`[data-select-control="${CSS.escape(controlId)}"]`);
  if (treeItem && tree) {
    const itemTop = treeItem.offsetTop;
    const itemBottom = itemTop + treeItem.offsetHeight;
    const viewTop = tree.scrollTop;
    const viewBottom = viewTop + tree.clientHeight;
    if (itemTop < viewTop || itemBottom > viewBottom) {
      tree.scrollTop = Math.max(0, itemTop - tree.clientHeight / 3);
    }
  }
}

export async function navigateToControl(controlId) {
  if (!controlId) return;
  // 자가진단에 안내서·체크가 합쳐졌으므로, 분석이 있으면 세션 카드로 이동
  if (state.analysis && state.organizationProfile) {
    state.sessionSelectedControlId = controlId;
    hooks.switchView?.("analyze");
    hooks.switchAnalyzeSection?.("actions");
    const content = el("analyzeContent");
    if (content) content.style.display = "";
    // 확인 목록 리포트는 숨기지 않고 유지 (스크롤만 이동)
    hooks.renderConfirmationActions?.(state.analysis);
    renderReportReturnBar();
    // 카드 렌더 후 「지금 진단」질문/상태 버튼 높이로 이동
    window.requestAnimationFrame(() => {
      window.setTimeout(() => scrollToSessionDiagnosis(controlId), 80);
    });
    return;
  }

  navigateTo("assessment");
  showToast("먼저 점검 범위를 적용하고 진단을 시작하세요.");
}
