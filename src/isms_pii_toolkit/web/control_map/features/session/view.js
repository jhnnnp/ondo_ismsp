import {
  AREA_SHORT,
  CHECK_LABEL,
  CHECK_LABEL_FULL,
  LEVEL_LABEL,
} from "../../core/constants.js";
import { el, escapeHtml } from "../../core/dom.js";
import { navigateTo } from "../../core/routes.js";
import { state } from "../../core/state.js";
import { persistActiveDiagnosisSession } from "../../core/storage.js";
import {
  ensureChecks,
  ensureDomainChecks,
  setDomainCheck,
} from "../assessment/actions.js";
import {
  bulkSetPresetForFiltered,
  deleteControlEvidence,
  hasRegisteredEvidence,
  listControlEvidence,
  loadLegalBasis,
  registerControlEvidence,
  setControlCheck,
} from "../assessment/controller.js";
import { categoryProgress, compareDotId, getAssessment } from "../assessment/model.js";
import { matchesControlSearch, rankControlsBySearch } from "../assessment/search.js";
import { renderLegalBasisContent } from "../assessment/view.js";
import { applyWeakReviewState, buildDashboardViewModel } from "./dashboard.js";
import {
  adjacentSessionControlId,
  backlogControls,
  doneControls,
  nextIncompleteControlId,
  reviewedAndApplicable,
  sessionCategoryGroups,
  sessionControlIds,
  unreviewedControls,
} from "./model.js";

const DIAG_LEVELS = [
  { id: "unknown", label: "미확인" },
  { id: "none", label: "미이행" },
  { id: "partial", label: "부분 이행" },
  { id: "done", label: "이행" },
];

function assessmentHeroCopy({ remaining = 0, remediationCount = 0 } = {}) {
  if (remaining > 0) {
    return {
      title: "아직 진단하지 않은 통제가 있습니다.",
      help: "미점검 항목을 이어서 진단하면 준비 온도와 보완 대상이 더 정확해집니다.",
      actionAttr: "data-progress-next",
      actionLabel: "다음 미점검 통제",
      recCount: remaining,
      recLabel: "미점검 대상",
      recHelp: "우선순위가 높은 통제부터 현재 운영 상태를 확인하세요.",
      recItems: ["미점검 통제 진단하기", "판단 근거가 되는 증적 연결"],
    };
  }
  if (remediationCount > 0) {
    return {
      title: "보완이 필요한 통제가 있습니다.",
      help: "부분 이행 항목을 중심으로 증적과 조치 상태를 우선 검토하세요.",
      actionAttr: "data-progress-weak",
      actionLabel: "우선 통제 검토",
      recCount: remediationCount,
      recLabel: "보완 대상",
      recHelp: "우선순위가 높은 통제부터 증적과 조치 상태를 확인하세요.",
      recItems: ["부족한 증적 보완", "개선 조치 계획 수립"],
    };
  }
  return {
    title: "준비 상태가 안정권에 도달했습니다.",
    help: "적용 통제 진단을 모두 반영했습니다. 증적과 보고서를 이어서 확인하세요.",
    actionAttr: "",
    actionLabel: "",
    recCount: 0,
    recLabel: "보완 대상 없음",
    recHelp: "등록한 증적과 보고서를 이어서 확인하세요.",
    recItems: ["등록 증적 점검", "진단 보고서 확인"],
  };
}

let sessionToolsBound = false;

function sessionFiltersActive() {
  return state.levelFilter !== "all" || !!state.assessSearch.trim() || state.areaFilter !== "all";
}

function filterSessionGroups(groups) {
  const query = state.assessSearch.trim().toLowerCase();
  return groups
    .map((group) => ({
      ...group,
      controls: group.controls.filter((control) => {
        if (state.areaFilter !== "all" && String(control.areaId) !== String(state.areaFilter)) {
          return false;
        }
        const level = getAssessment(control.id);
        if (state.levelFilter === "weak" && !["none", "partial"].includes(level)) {
          return false;
        }
        if (!["all", "weak"].includes(state.levelFilter) && level !== state.levelFilter) {
          return false;
        }
        if (!query) return true;
        return matchesControlSearch(control, state.assessSearch);
      }),
    }))
    .map((group) => ({
      ...group,
      controls: rankControlsBySearch(group.controls, state.assessSearch),
    }))
    .filter((group) => group.controls.length);
}

function syncSessionFilterChips() {
  document.querySelectorAll("[data-session-level]").forEach((btn) => {
    const on = btn.getAttribute("data-session-level") === (state.levelFilter || "all");
    btn.classList.toggle("is-active", on);
  });
  const search = el("sessionSearch");
  if (search && search.value !== (state.assessSearch || "")) {
    search.value = state.assessSearch || "";
  }
}

function refreshSessionView() {
  if (!state.analysis) return;
  const hooks = renderSessionDetail._hooks || {};
  renderConfirmationActions(state.analysis, {
    diagnoseControl: hooks.diagnoseControl,
    markAnalysisStale: hooks.markAnalysisStale,
  });
}

function ensureSessionToolsBound() {
  if (sessionToolsBound) return;
  const tools = el("sessionMasterTools");
  if (!tools) return;
  sessionToolsBound = true;

  el("sessionSearch")?.addEventListener("input", (event) => {
    state.assessSearch = event.target.value || "";
    refreshSessionView();
  });

  tools.querySelectorAll("[data-session-level]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const level = btn.getAttribute("data-session-level") || "all";
      state.levelFilter = level;
      refreshSessionView();
    });
  });

  tools.querySelectorAll("[data-session-bulk-preset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const preset = btn.getAttribute("data-session-bulk-preset");
      if (!preset) return;
      // 일괄은 현재 필터(검색·상태)에 보이는 통제에 적용
      bulkSetPresetForFiltered(preset);
      refreshSessionView();
      renderSessionDetail._hooks?.markAnalysisStale?.();
    });
  });

}

function actionLookup(rawActions = []) {
  const map = new Map();
  rawActions.forEach((action) => {
    if (!action?.controlId) return;
    if (action.slotId || String(action.actionId || "").startsWith("evidence-")) return;
    if (!map.has(action.controlId)) map.set(action.controlId, action);
  });
  return map;
}

function priorityIds(rawActions = []) {
  return rawActions
    .filter((action) => {
      if (!action?.controlId) return false;
      if (action.slotId || String(action.actionId || "").startsWith("evidence-")) return false;
      const level = getAssessment(action.controlId);
      return level !== "done" && level !== "evidenced" && level !== "na";
    })
    .slice(0, 10)
    .map((action) => action.controlId);
}

export function resolveSessionSelectedId(current, groups) {
  const allIds = new Set(groups.flatMap((g) => g.controls.map((c) => c.id)));
  if (current && allIds.has(current)) return current;
  return groups[0]?.controls?.[0]?.id || null;
}

function rememberSelectedControl(controlId) {
  state.sessionSelectedControlId = controlId || null;
  persistActiveDiagnosisSession();
}

function ensureCategoryExpanded(selectedId, groups) {
  if (!(state.sessionCollapsedCategories instanceof Set)) {
    state.sessionCollapsedCategories = new Set();
  }
  if (!state.sessionCollapsedCategories.size && groups.length) {
    groups.forEach((group) => state.sessionCollapsedCategories.add(group.categoryId));
  }
  const selectedGroup = groups.find((group) => group.controls.some((c) => c.id === selectedId));
  if (selectedGroup) state.sessionCollapsedCategories.delete(selectedGroup.categoryId);
}

function statusTone(level) {
  if (level === "done" || level === "evidenced") return "done"; // evidenced: 레거시
  if (level === "none") return "none";
  if (level === "partial") return "partial";
  return "unknown";
}

function renderMasterTree(groups, selectedId, prioritySet) {
  const tree = el("sessionMasterTree");
  const countEl = el("sessionMasterCount");
  if (!tree) return;

  const byArea = new Map();
  groups.forEach((group) => {
    const areaKey = String(group.areaId || group.categoryId?.split(".")[0] || "0");
    if (!byArea.has(areaKey)) {
      byArea.set(areaKey, {
        areaId: areaKey,
        areaName: AREA_SHORT[areaKey] || group.areaName || `영역 ${areaKey}`,
        groups: [],
      });
    }
    byArea.get(areaKey).groups.push(group);
  });
  const areas = Array.from(byArea.values()).sort((a, b) => compareDotId(a.areaId, b.areaId));
  const visibleCount = groups.reduce((sum, group) => sum + group.controls.length, 0);
  const unreviewed = unreviewedControls().length;
  if (countEl) {
    countEl.textContent = sessionFiltersActive()
      ? `표시 ${visibleCount} · 미완료 ${unreviewed}`
      : `미완료 ${unreviewed}`;
  }

  tree.innerHTML = areas.map((area) => {
    const areaControls = area.groups.flatMap((g) => g.controls);
    const progress = categoryProgress(areaControls);
    return `
      <div class="session-area-block">
        <div class="session-area-label">
          <span>${escapeHtml(area.areaName)}</span>
          <span>${progress.reviewed}/${progress.total}</span>
        </div>
        ${area.groups.map((group) => {
          const collapsed = state.sessionCollapsedCategories.has(group.categoryId);
          const gProgress = categoryProgress(group.controls);
          return `
            <div class="session-cat${collapsed ? " is-collapsed" : ""}" data-session-cat="${escapeHtml(group.categoryId)}">
              <button type="button" class="session-cat-head" data-toggle-session-cat="${escapeHtml(group.categoryId)}" aria-expanded="${collapsed ? "false" : "true"}">
                <span class="session-cat-title">${escapeHtml(group.categoryId)} ${escapeHtml(group.categoryName)}</span>
                <span class="session-cat-meta">${gProgress.reviewed}/${gProgress.total}</span>
              </button>
              <div class="session-cat-items">
                ${group.controls.map((control) => {
                  const level = getAssessment(control.id);
                  const tone = statusTone(level);
                  const selected = control.id === selectedId ? " is-selected" : "";
                  const priority = prioritySet.has(control.id) ? " is-priority" : "";
                  return `
                    <button type="button" class="session-item tone-${tone}${selected}${priority}" data-select-control="${escapeHtml(control.id)}">
                      <span class="session-item-status" aria-hidden="true"></span>
                      <span class="session-item-copy">
                        <strong>${escapeHtml(control.id)}</strong>
                        <span>${escapeHtml(control.title || "")}</span>
                      </span>
                      ${prioritySet.has(control.id) ? '<em class="session-item-badge">우선</em>' : ""}
                    </button>
                  `;
                }).join("")}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }).join("") || `<p class="detail-empty">표시할 통제가 없습니다.</p>`;

  tree.querySelectorAll("[data-toggle-session-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const categoryId = btn.getAttribute("data-toggle-session-cat");
      if (state.sessionCollapsedCategories.has(categoryId)) {
        state.sessionCollapsedCategories.delete(categoryId);
      } else {
        state.sessionCollapsedCategories.add(categoryId);
      }
      const block = tree.querySelector(`[data-session-cat="${categoryId}"]`);
      const collapsed = state.sessionCollapsedCategories.has(categoryId);
      block?.classList.toggle("is-collapsed", collapsed);
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    });
  });

  tree.querySelectorAll("[data-select-control]").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectSessionControl(btn.getAttribute("data-select-control"), {
        groups,
        prioritySet,
        scrollTree: true,
        scrollDetail: false,
      });
    });
  });
}

function selectSessionControl(controlId, { groups, prioritySet, scrollTree = false, scrollDetail = false } = {}) {
  if (!controlId) return;
  const categoryGroups = groups || sessionCategoryGroups();
  const actionsMap = actionLookup(state.analysis?.confirmationActions || []);
  const priorities = prioritySet || new Set(priorityIds(state.analysis?.confirmationActions || []));
  if (state.pendingDoneEvidenceControlId && state.pendingDoneEvidenceControlId !== controlId) {
    state.pendingDoneEvidenceControlId = null;
  }
  rememberSelectedControl(controlId);
  const group = categoryGroups.find((g) => g.controls.some((c) => c.id === controlId));
  if (group) state.sessionCollapsedCategories.delete(group.categoryId);
  renderSessionDetail(controlId, actionsMap, priorities);
  const tree = el("sessionMasterTree");
  if (!tree) return;
  tree.querySelectorAll(".session-item").forEach((node) => {
    node.classList.toggle("is-selected", node.getAttribute("data-select-control") === controlId);
  });
  tree.querySelectorAll(".session-cat").forEach((node) => {
    const id = node.getAttribute("data-session-cat");
    node.classList.toggle("is-collapsed", state.sessionCollapsedCategories.has(id));
  });
  if (scrollTree) {
    const treeItem = tree.querySelector(`[data-select-control="${CSS.escape(controlId)}"]`);
    if (treeItem) {
      const treeRect = tree.getBoundingClientRect();
      const itemRect = treeItem.getBoundingClientRect();
      if (itemRect.top < treeRect.top || itemRect.bottom > treeRect.bottom) {
        tree.scrollTop += itemRect.top - treeRect.top - tree.clientHeight / 3;
      }
    }
  }
  if (scrollDetail) {
    // 카드 재렌더·높이 동기화 후, sticky 헤더를 피해서 상단(Q)으로 이동
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        scrollSessionDetailToDiagnosis(controlId);
      });
    });
  }
}

function scrollSessionDetailToDiagnosis(controlId) {
  const card = (controlId
    ? document.querySelector(`.session-detail-card[data-today-control="${CSS.escape(controlId)}"]`)
    : null)
    || document.querySelector(".session-detail-card")
    || el("sessionDetailPane");
  if (!card) return;
  // today-card-top(통제 ID·제목·Q)이 보이도록. scrollIntoView는 html scroll-padding-top을 반영한다.
  const anchor = card.querySelector(".today-card-top")
    || card.querySelector(".today-question")
    || card;
  anchor.scrollIntoView({ behavior: "smooth", block: "start" });
}

function sessionCatalogEntry(controlId) {
  return state.analysis?.controlSessionDetails?.[controlId] || null;
}

function listHtml(items) {
  return (items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderDetailCard(controlId, action, prioritySet) {
  const control = (state.checklist || []).find((c) => c.id === controlId) || {};
  const catalog = sessionCatalogEntry(controlId);
  const level = getAssessment(controlId);
  const title = action?.title || catalog?.title || control.title || "";
  const question = action?.question
    || catalog?.question
    || `${title || controlId} 이행 상태를 확인했나요?`;
  const why = String(action?.whyItMatters || "").trim();
  const guide = String(action?.actionGuide || catalog?.actionGuide || "").trim();
  const whyShort = why.length > 220 ? `${why.slice(0, 217)}…` : why;
  const guideShort = guide.length > 180 ? `${guide.slice(0, 177)}…` : guide;
  const maturity = ensureChecks(controlId);
  const maturityHtml = Object.keys(CHECK_LABEL).map((key) => `
    <label class="audit-check" title="${escapeHtml(controlId)} ${CHECK_LABEL_FULL[key]}">
      <input type="checkbox" data-check-control="${escapeHtml(controlId)}" data-check-key="${key}"${maturity[key] ? " checked" : ""}>
      <span>${CHECK_LABEL[key]}</span>
    </label>
  `).join("");
  const checklistItems = control.checklistItems || [];
  const domain = ensureDomainChecks(controlId, checklistItems);
  const domainHtml = checklistItems.map((item, index) => {
    const itemId = String(index + 1);
    const checked = !!domain[itemId];
    return `
      <li class="domain-check-item">
        <label>
          <input type="checkbox" data-domain-control="${escapeHtml(controlId)}" data-domain-item="${itemId}"${checked ? " checked" : ""}>
          <span><strong>${itemId}.</strong> ${escapeHtml(item)}</span>
        </label>
      </li>
    `;
  }).join("");
  const registeredEvidence = listControlEvidence(controlId);
  const pendingDone = state.pendingDoneEvidenceControlId === controlId;
  const savedLevel = level === "evidenced" ? "done" : level;
  const buttonLevel = pendingDone ? "done" : savedLevel;
  const diagBtns = DIAG_LEVELS.map((d) => `
    <button type="button" data-diagnose-control="${escapeHtml(controlId)}" data-diagnose-level="${d.id}" class="${buttonLevel === d.id ? "is-active" : ""}" aria-pressed="${buttonLevel === d.id ? "true" : "false"}">${d.label}</button>
  `).join("");
  const evidenceGuideHtml = listHtml((control.officialEvidenceExamples || []).slice(0, 8));
  const actionsHtml = listHtml(control.recommendedActions || []);
  const registeredEvidenceHtml = registeredEvidence.length
    ? registeredEvidence.map((item) => `
        <li class="session-evidence-item" data-evidence-id="${escapeHtml(item.id)}">
          <div class="session-evidence-item-body">
            <strong>${escapeHtml(item.title)}</strong>
          </div>
          <button type="button" class="ghost session-evidence-remove" data-evidence-remove="${escapeHtml(controlId)}" data-evidence-id="${escapeHtml(item.id)}" aria-label="증적 삭제">삭제</button>
        </li>
      `).join("")
    : "";
  const ids = sessionControlIds();
  const idx = ids.indexOf(controlId);
  const prevId = adjacentSessionControlId(controlId, -1);
  const nextId = adjacentSessionControlId(controlId, 1);
  const position = idx >= 0 ? `${idx + 1} / ${ids.length}` : "";
  const navHtml = position ? `
      <div class="session-nav" role="navigation" aria-label="통제 이동">
        <button type="button" class="session-nav-btn" data-session-nav="prev" ${prevId ? "" : "disabled"} aria-label="이전 통제">이전</button>
        <span class="session-nav-pos">${escapeHtml(position)}</span>
        <button type="button" class="session-nav-btn session-nav-next" data-session-nav="next" ${nextId ? "" : "disabled"} aria-label="다음 통제">저장하고 다음 <span aria-hidden="true">→</span></button>
      </div>
  ` : "";
  const exampleHint = (control.officialEvidenceExamples || [])[0]
    ? `예: ${control.officialEvidenceExamples[0]}`
    : "예: 출입대장 캡처 / 공유폴더";
  return `
    <article class="today-card session-detail-card" data-today-control="${escapeHtml(controlId)}">
      <div class="today-card-top">
        <div class="today-card-idline">
          ${prioritySet.has(controlId) ? '<span class="today-priority">우선</span>' : ""}
          <span class="today-control-id">${escapeHtml(controlId)}</span>
          <span class="today-title">${escapeHtml(title)}</span>
        </div>
        <span class="status-pill level-${savedLevel}">${escapeHtml(LEVEL_LABEL[savedLevel] || savedLevel)}</span>
      </div>
      <p class="today-question">${escapeHtml(question)}</p>
      ${whyShort || guideShort ? `<div class="assessment-context">
        ${whyShort ? `<p>${escapeHtml(whyShort)}</p>` : ""}
        ${guideShort ? `<p>${escapeHtml(guideShort)}</p>` : ""}
      </div>` : ""}
      <section class="judgement-criteria" aria-labelledby="judgementCriteriaTitle">
        <div class="judgement-section-head">
          <h3 id="judgementCriteriaTitle">판단 기준</h3>
          <span>해당하는 항목을 확인하세요</span>
        </div>
        <ul class="domain-check-list">${domainHtml || "<li class='detail-empty'>제공된 세부 기준이 없습니다.</li>"}</ul>
      </section>
      <div class="diagnosis-decision-head">
        <h3>진단 결과</h3>
        <span>선택하면 즉시 저장됩니다</span>
      </div>
      <div class="today-diagnose" role="group" aria-label="${escapeHtml(controlId)} 진단">
        ${diagBtns}
      </div>
      ${pendingDone ? `
        <form class="session-done-evidence" data-done-evidence-form="${escapeHtml(controlId)}">
          <p class="session-done-evidence-label">이행으로 저장하려면 증적 한 줄만 남기세요</p>
          <div class="session-done-evidence-row">
            <input type="text" name="line" required maxlength="160" placeholder="${escapeHtml(exampleHint)}" autocomplete="off">
            <button type="submit" class="primary">이행으로 저장</button>
            <button type="button" class="ghost" data-done-evidence-skip="${escapeHtml(controlId)}">나중에</button>
          </div>
        </form>
      ` : `
        <p class="session-evidence-hint">이행은 증적 한 줄만 있으면 됩니다. 버튼을 누르면 입력창이 열립니다.</p>
      `}
      ${registeredEvidenceHtml ? `
        <section class="today-detail session-evidence-block" aria-label="등록된 증적">
          <h3 class="today-detail-title">등록된 증적</h3>
          <ul class="session-evidence-list">${registeredEvidenceHtml}</ul>
        </section>
      ` : ""}
      <section class="evidence-workspace" aria-label="${escapeHtml(controlId)} 증적 관리">
        <header class="evidence-workspace-head">
          <div>
            <span>통제 증적</span>
            <h3>${escapeHtml(controlId)} ${escapeHtml(title)}</h3>
            <p>이 통제의 이행을 입증할 문서·기록·캡처를 등록하세요.</p>
          </div>
          <strong>${registeredEvidence.length}<small>건 등록</small></strong>
        </header>
        <form class="evidence-register-form" data-evidence-register-form="${escapeHtml(controlId)}">
          <label for="evidenceLine-${escapeHtml(controlId)}">증적 제목</label>
          <div>
            <input id="evidenceLine-${escapeHtml(controlId)}" type="text" name="line" required maxlength="160" placeholder="${escapeHtml(exampleHint)}" autocomplete="off">
            <button type="submit" class="primary">증적 등록</button>
          </div>
        </form>
        <div class="evidence-example-line">
          <span>권장 증적</span>
          <p>${escapeHtml((control.officialEvidenceExamples || []).slice(0, 3).join(" · ") || "정책, 승인 기록, 운영 로그 등")}</p>
        </div>
        <section class="evidence-registered-panel">
          <h4>등록된 증적</h4>
          ${registeredEvidenceHtml
            ? `<ul class="session-evidence-list">${registeredEvidenceHtml}</ul>`
            : `<p class="detail-empty">아직 등록된 증적이 없습니다.</p>`}
        </section>
      </section>
      <section class="today-detail session-self-check" aria-label="자체진단 체크">
        <h3 class="today-detail-title">자체진단 체크 <span class="today-detail-badge">선택</span></h3>
        <p class="today-detail-note">필요하면 검토·정책·구현·증적을 세분화하세요. 진단 버튼만으로도 충분합니다.</p>
        <div class="audit-checks" aria-label="${escapeHtml(controlId)} 자체진단 체크 항목">
          ${maturityHtml}
        </div>
      </section>
      <details class="session-optional-block" open>
        <summary>참고자료 · 인증기준 · 법적 근거</summary>
        <div class="session-optional-body">
          <div class="session-guide-grid">
            ${control.officialRequirement ? `
              <details class="detail-block session-guide-details" open>
                <summary>인증기준 (안내서)</summary>
                <p>${escapeHtml(control.officialRequirement)}</p>
              </details>
            ` : ""}
            <details class="detail-block session-guide-details legal-basis-block" open>
              <summary>법적 근거 및 참고자료</summary>
              <p class="today-detail-note">법령은 바로 확인하고, 법령해석·공식 사례·안내서는 필요할 때 펼쳐보세요.</p>
              <div data-legal-basis="${escapeHtml(controlId)}">${renderLegalBasisContent(controlId)}</div>
            </details>
            <details class="detail-block session-guide-details" open>
              <summary>미이행 시 취약점/심사 리스크</summary>
              <p>${escapeHtml(control.riskIfMissing || "-")}</p>
            </details>
            ${evidenceGuideHtml ? `
              <details class="detail-block session-guide-details" open>
                <summary>증거자료 예시 (안내서)</summary>
                <ul>${evidenceGuideHtml}</ul>
              </details>
            ` : ""}
            ${actionsHtml ? `
              <details class="detail-block session-guide-details" open>
                <summary>권장 조치</summary>
                <ul>${actionsHtml}</ul>
              </details>
            ` : ""}
          </div>
        </div>
      </details>
      ${navHtml}
    </article>
  `;
}

function reopenSessionDetail(controlId, { diagnoseControl, groups, prioritySet } = {}) {
  const hooks = {
    ...(renderSessionDetail._hooks || {}),
    diagnoseControl: diagnoseControl || renderSessionDetail._hooks?.diagnoseControl || (() => {}),
  };
  const actionsMap = actionLookup(state.analysis?.confirmationActions || []);
  renderSessionDetail(controlId, actionsMap, prioritySet || new Set(), hooks);
  window.requestAnimationFrame(() => {
    el("sessionDetailPane")
      ?.querySelector("[data-done-evidence-form] input[name='line']")
      ?.focus();
  });
}

function bindDetailHandlers(root, { diagnoseControl, groups, prioritySet } = {}) {
  root.querySelectorAll("[data-diagnose-control]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const controlId = btn.getAttribute("data-diagnose-control");
      const level = btn.getAttribute("data-diagnose-level");
      if (!controlId || !level || !diagnoseControl) return;
      if (level === "done" && !hasRegisteredEvidence(controlId)) {
        rememberSelectedControl(controlId);
        state.pendingDoneEvidenceControlId = controlId;
        reopenSessionDetail(controlId, { diagnoseControl, groups, prioritySet });
        return;
      }
      state.pendingDoneEvidenceControlId = null;
      diagnoseControl(controlId, level);
    });
  });
  root.querySelectorAll("[data-check-control]").forEach((node) => {
    node.addEventListener("change", () => {
      const controlId = node.getAttribute("data-check-control");
      const key = node.getAttribute("data-check-key");
      if (!controlId || !key) return;
      rememberSelectedControl(controlId);
      setControlCheck(controlId, key, !!node.checked);
    });
  });
  root.querySelectorAll("[data-domain-control]").forEach((node) => {
    node.addEventListener("change", () => {
      const controlId = node.getAttribute("data-domain-control");
      const itemId = node.getAttribute("data-domain-item");
      if (!controlId || !itemId) return;
      setDomainCheck(controlId, itemId, !!node.checked);
      if (state.analysis && typeof renderSessionDetail._hooks?.markAnalysisStale === "function") {
        renderSessionDetail._hooks.markAnalysisStale();
      }
    });
  });
  root.querySelectorAll("[data-session-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dir = btn.getAttribute("data-session-nav") === "prev" ? -1 : 1;
      const currentId = state.sessionSelectedControlId;
      const targetId = adjacentSessionControlId(currentId, dir);
      if (!targetId) return;
      state.pendingDoneEvidenceControlId = null;
      selectSessionControl(targetId, {
        groups: groups || sessionCategoryGroups(),
        prioritySet,
        scrollTree: true,
        scrollDetail: true,
      });
    });
  });
  root.querySelectorAll("[data-done-evidence-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const controlId = form.getAttribute("data-done-evidence-form");
      if (!controlId || !diagnoseControl) return;
      const line = String(new FormData(form).get("line") || "").trim();
      if (!line) return;
      state.pendingDoneEvidenceControlId = null;
      const ok = registerControlEvidence(controlId, { title: line }, { quiet: true });
      if (!ok) return;
      diagnoseControl(controlId, "done");
    });
  });
  root.querySelectorAll("[data-evidence-register-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const controlId = form.getAttribute("data-evidence-register-form");
      const line = String(new FormData(form).get("line") || "").trim();
      if (!controlId || !line) return;
      const ok = registerControlEvidence(controlId, { title: line }, { quiet: true });
      if (!ok) return;
      reopenSessionDetail(controlId, { diagnoseControl, groups, prioritySet });
    });
  });
  root.querySelectorAll("[data-done-evidence-skip]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const controlId = btn.getAttribute("data-done-evidence-skip");
      if (!controlId || !diagnoseControl) return;
      state.pendingDoneEvidenceControlId = null;
      diagnoseControl(controlId, "partial");
    });
  });
  root.querySelectorAll("[data-evidence-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const controlId = btn.getAttribute("data-evidence-remove");
      const evidenceId = btn.getAttribute("data-evidence-id");
      if (!controlId || !evidenceId) return;
      deleteControlEvidence(controlId, evidenceId);
    });
  });
}

function renderSessionDetail(controlId, actionsMap, prioritySet, hooks) {
  const pane = el("sessionDetailPane");
  if (!pane) return;
  if (!controlId) {
    pane.innerHTML = `<p class="detail-empty">왼쪽 지도에서 통제를 선택하세요.</p>`;
    return;
  }
  const action = actionsMap.get(controlId) || null;
  const contextControl = (state.checklist || []).find((control) => control.id === controlId) || {};
  const contextTitle = action?.title || sessionCatalogEntry(controlId)?.title || contextControl.title || "";
  const contextDetail = el("workspaceContextDetail");
  const onControlWorkspace = el("view-analyze")?.classList.contains("is-assessment")
    || el("view-analyze")?.classList.contains("is-evidence");
  if (contextDetail && onControlWorkspace) {
    contextDetail.textContent = `${controlId} · ${contextTitle}`;
  }
  if (hooks) renderSessionDetail._hooks = hooks;
  const activeHooks = hooks || renderSessionDetail._hooks || { diagnoseControl: () => {} };
  pane.innerHTML = renderDetailCard(controlId, action, prioritySet);
  bindDetailHandlers(pane, {
    ...activeHooks,
    groups: filterSessionGroups(sessionCategoryGroups()),
    prioritySet,
  });
  loadLegalBasis(controlId);
}

export function renderConfirmationActions(analysis, { diagnoseControl, markAnalysisStale } = {}) {
  const hooks = {
    diagnoseControl: diagnoseControl || (() => {}),
    markAnalysisStale,
  };
  renderSessionDetail._hooks = hooks;
  ensureSessionToolsBound();
  syncSessionFilterChips();

  const { reviewed, applicable } = reviewedAndApplicable();
  const progressEl = el("assessmentProgressStrip");
  const rawActions = analysis?.confirmationActions || [];
  const engineMeta = analysis?.confirmationActionMeta || {};
  if (engineMeta.mode) state.sessionBundleMode = engineMeta.mode;

  const actionsMap = actionLookup(rawActions);
  const priority = priorityIds(rawActions);
  const prioritySet = new Set(priority);
  const unreviewed = unreviewedControls();
  const done = doneControls().length;
  const levelCounts = sessionControlIds().reduce((counts, controlId) => {
    const level = getAssessment(controlId);
    if (level === "none" || level === "partial") counts[level] += 1;
    return counts;
  }, { none: 0, partial: 0 });
  const groups = filterSessionGroups(sessionCategoryGroups());
  const dashboardGroups = sessionCategoryGroups();
  const selectedId = resolveSessionSelectedId(state.sessionSelectedControlId, groups);
  state.sessionSelectedControlId = selectedId;
  ensureCategoryExpanded(selectedId, groups);

  const dashboardVm = buildDashboardViewModel({
    analysis,
    controlEvidence: state.controlEvidence,
    weakControlIds: sessionControlIds().filter((controlId) => ["none", "partial"].includes(getAssessment(controlId))),
    stale: state.analysisStale,
    groups: dashboardGroups,
    getLevel: getAssessment,
    nextControls: backlogControls().map((control) => ({
      id: control.id,
      title: control.title,
      level: getAssessment(control.id),
    })),
    done,
    partial: levelCounts.partial,
    applicable,
  });

  const goToControl = (controlId = null, { weak = false } = {}) => {
    if (weak) {
      applyWeakReviewState(state, controlId, priority);
      rememberSelectedControl(state.sessionSelectedControlId);
    }
    else {
      state.levelFilter = "all";
      rememberSelectedControl(controlId || nextIncompleteControlId());
    }
    navigateTo("assessment");
    refreshSessionView();
    window.requestAnimationFrame(() => {
      el("sessionMasterDetail")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };
  const openWeakReview = (controlId = null) => goToControl(controlId, { weak: true });

  if (progressEl) {
    const readinessTemperature = dashboardVm.temperature;
    const temperatureBand = dashboardVm.band;
    const levelPercent = (count) => applicable > 0
      ? `${(count / applicable * 100).toFixed(1)}%`
      : "0%";
    const remaining = unreviewed.length;
    const remediationCount = levelCounts.none + levelCounts.partial;
    const hero = assessmentHeroCopy({ remaining, remediationCount });
    progressEl.classList.add("is-complete");
    progressEl.classList.remove("is-cold", "is-warming", "is-rising", "is-ready");
    progressEl.classList.add(`is-${temperatureBand.key}`);
    progressEl.innerHTML = `
      <div class="ap-complete-intro">
        <span class="ap-complete-eyebrow"><span aria-hidden="true"></span>자가진단 준비 온도 <b>${reviewed} / ${applicable}</b></span>
        <div class="ap-complete-body">
          <div class="ap-temperature is-${temperatureBand.key}" role="img" aria-label="자가진단 준비 온도 ${readinessTemperature}도 ${temperatureBand.label}" style="--temperature:${readinessTemperature}">
            <span><strong>${readinessTemperature}</strong><sup>°</sup></span>
          </div>
          <div class="ap-complete-copy">
            <strong>${hero.title}</strong>
            <p>${hero.help}</p>
            ${hero.actionAttr ? `<div class="ap-progress-actions ap-complete-actions">
              <button type="button" ${hero.actionAttr} class="ap-primary">${hero.actionLabel} <span aria-hidden="true">→</span></button>
            </div>` : ""}
          </div>
        </div>
      </div>
      <div class="ap-kpi-grid" aria-label="자가진단 결과">
        <article class="ap-kpi-card is-primary">
          <span>부분 이행</span>
          <strong>${levelCounts.partial}<small>건</small></strong>
          <em>${levelPercent(levelCounts.partial)}</em>
          <i aria-hidden="true"><b style="width:${levelPercent(levelCounts.partial)}"></b></i>
        </article>
        <article class="ap-kpi-card is-done">
          <span>이행</span>
          <strong>${done}<small>건</small></strong>
          <em>${levelPercent(done)}</em>
          <i aria-hidden="true"><b style="width:${levelPercent(done)}"></b></i>
        </article>
        <article class="ap-kpi-card is-none">
          <span>미이행</span>
          <strong>${levelCounts.none}<small>건</small></strong>
          <em>${levelPercent(levelCounts.none)}</em>
          <i aria-hidden="true"><b style="width:${levelPercent(levelCounts.none)}"></b></i>
        </article>
      </div>
      <aside class="ap-complete-recommendation">
        <span class="ap-complete-section-label">다음 단계 추천</span>
        <strong>${hero.recCount ? `<b>${hero.recCount}개</b> ${hero.recLabel}` : hero.recLabel}</strong>
        <p>${hero.recHelp}</p>
        <ul>
          ${hero.recItems.map((item) => `<li>${item}</li>`).join("")}
        </ul>
      </aside>
      <div class="ap-complete-footnote">
        <span>※ 비율은 적용 통제 ${applicable}개 기준입니다.</span>
        <span>자가진단은 인증 적합 판정을 대체하지 않습니다.</span>
      </div>
    `;
    progressEl.querySelector("[data-progress-next]")?.addEventListener("click", () => {
      state.levelFilter = "unknown";
      rememberSelectedControl(nextIncompleteControlId());
      refreshSessionView();
      el("sessionMasterDetail")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    progressEl.querySelectorAll("[data-progress-weak]").forEach((button) => button.addEventListener("click", () => {
      openWeakReview();
    }));
  }

  const countEl = el("confirmationActionCount");
  if (countEl) {
    countEl.textContent = `진행 ${reviewed}/${applicable}`;
  }

  renderMasterTree(groups, selectedId, prioritySet);
  renderSessionDetail(selectedId, actionsMap, prioritySet, hooks);

  const notes = analysis?.applicabilityNotes || [];
  const notesPanel = el("applicabilityNotesPanel");
  const notesList = el("applicabilityNotesList");
  if (notesPanel && notesList) {
    if (notes.length) {
      notesPanel.style.display = "";
      notesList.innerHTML = `<ul>${notes.map((n) =>
        `<li><strong>${escapeHtml(n.controlId)}</strong> — ${escapeHtml(n.reason || "")}</li>`
      ).join("")}</ul>`;
    } else {
      notesPanel.style.display = "none";
    }
  }

}
