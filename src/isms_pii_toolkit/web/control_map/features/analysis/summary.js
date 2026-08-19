import { LEVEL_LABEL } from "../../core/constants.js";
import { el, escapeHtml } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { renderGapClusters } from "./gaps.js";
import { renderReportReview } from "./report-review.js";
import {
  clampPercent,
  formatPercent,
  linkedProblemEmptyMarkup,
} from "./utils.js";
import { syncExecutiveReportStream } from "./presentation.js";

export function renderAnalysisSummary(skipHero, { renderConfirmationActions }) {
  const a = state.analysis;
  if (!a) return;

  if (!skipHero) {
    el("analyzeContent").style.display = "";

    const reportPanel = el("analysisReportPanel");
    if (reportPanel && (a.executiveReport || state.lastAiExecutiveReport)) {
      reportPanel.style.display = "";
      syncExecutiveReportStream();
      renderReportReview(a);
    }
  }

  const areaCoverage = a.areaCoverage || {};

  const categoryCoverage = (a.categoryCoverage || a.weakCategories || []).map((item) => {
    const reviewed = Number(item.reviewedCount ?? 0);
    const total = Number(item.totalCount ?? item.count ?? 0);
    const rawCoverage = Number.isFinite(Number(item.coveragePercent))
      ? Number(item.coveragePercent)
      : (total > 0 ? (reviewed / total) * 100 : 0);
    const pct = clampPercent(rawCoverage);
    return { ...item, reviewed, total, pct };
  });
  const reviewedControls = categoryCoverage.reduce((sum, item) => sum + item.reviewed, 0);
  const applicableControls = categoryCoverage.reduce((sum, item) => sum + item.total, 0);
  const controlProgress = clampPercent(applicableControls > 0 ? reviewedControls / applicableControls * 100 : 0);
  const allControlsCompleted = applicableControls > 0 && reviewedControls >= applicableControls;
  const categorySummary = el("categoryCoverageSummary");
  const categoryList = el("categoryCoverageList");
  const categoryListCount = el("categoryListCount");
  if (categoryListCount) {
    categoryListCount.textContent = `중분류 ${categoryCoverage.length}개 · 스크롤하여 전체 보기`;
  }

  if (categorySummary) {
    categorySummary.classList.toggle("is-complete", allControlsCompleted);
    categorySummary.innerHTML = applicableControls ? `
      <div class="category-summary-copy" role="status">
        <strong>${allControlsCompleted ? `적용 통제 ${applicableControls}개 점검 완료` : `통제 ${reviewedControls}/${applicableControls}개 점검 완료`}</strong>
        <span>전체 점검 진행률 ${formatPercent(controlProgress)}%</span>
        <span class="category-summary-progress" role="progressbar" aria-label="전체 통제 점검 진행률" aria-valuenow="${controlProgress}" aria-valuemin="0" aria-valuemax="100"><i style="width:${controlProgress}%"></i></span>
      </div>
    ` : "";
  }

  if (categoryList) {
    const areaGroups = new Map();
    categoryCoverage.forEach((item) => {
      const areaKey = item.areaId || item.areaName || String(item.categoryId || "기타").split(".")[0];
      if (!areaGroups.has(areaKey)) {
        const areaName = item.areaName || "기타";
        areaGroups.set(areaKey, { areaName, coverage: areaCoverage[areaName] || null, items: [] });
      }
      areaGroups.get(areaKey).items.push(item);
    });
    categoryList.hidden = categoryCoverage.length === 0;
    categoryList.innerHTML = Array.from(areaGroups.values()).map((group) => {
      const sortedItems = group.items.sort((left, right) =>
        String(left.categoryId || "").localeCompare(
          String(right.categoryId || ""),
          undefined,
          { numeric: true },
        ));
      const areaReviewed = Number(group.coverage?.reviewedCount ?? sortedItems.reduce((sum, item) => sum + item.reviewed, 0));
      const areaTotal = Number(group.coverage?.totalCount ?? sortedItems.reduce((sum, item) => sum + item.total, 0));
      const areaPct = clampPercent(group.coverage?.coveragePercent ?? (areaTotal ? areaReviewed / areaTotal * 100 : 0));
      return `
        <details class="category-area-group" open>
          <summary>
            <strong>${escapeHtml(group.areaName)}</strong>
            <span class="category-area-progress" role="progressbar" aria-label="${escapeHtml(group.areaName)} 점검 완료율" aria-valuenow="${areaPct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${areaPct}%"></i></span>
            <span>${areaReviewed}/${areaTotal} · ${formatPercent(areaPct)}%</span>
          </summary>
          <div class="category-coverage-rows">
            ${sortedItems.map((item) => {
              const stateKey = item.reviewed >= item.total ? "done" : (item.reviewed > 0 ? "progress" : "idle");
              const stateLabel = stateKey === "done" ? "완료" : (stateKey === "progress" ? "진행 중" : "미점검");
              return `
                <div class="category-coverage-row ${item.pct < 100 ? "is-pending" : "is-complete"}">
                  <span class="category-coverage-id">${escapeHtml(item.categoryId || "-")}</span>
                  <strong>${escapeHtml(item.category)}</strong>
                  <span class="category-coverage-progress" role="progressbar" aria-label="${escapeHtml(item.category)} 점검 완료율" aria-valuenow="${item.pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${item.pct}%"></i></span>
                  <span class="category-coverage-count">${item.reviewed}/${item.total}</span>
                  <span class="category-coverage-state is-${stateKey}">${stateLabel}</span>
                </div>
              `;
            }).join("")}
          </div>
        </details>
      `;
    }).join("") || `<p class="detail-empty">분류별 점검 정보 없음</p>`;

    el("categoryViewActions")?.querySelectorAll("[data-category-view]").forEach((button) => {
      button.onclick = () => {
        const shouldOpen = button.dataset.categoryView === "expand";
        categoryList.querySelectorAll(".category-area-group").forEach((group) => {
          group.open = shouldOpen;
        });
      };
    });
  }

  const statusBox = el("statusBreakdown");
  if (statusBox) {
    const raw = a.statusCounts || {};
    const counts = {
      unknown: raw.unknown || 0,
      none: raw.none || 0,
      partial: raw.partial || 0,
      done: (raw.done || 0) + (raw.evidenced || 0),
      na: raw.na || 0,
    };
    const order = ["unknown", "none", "partial", "done", "na"];
    statusBox.innerHTML = order.map((key) => `
      <div class="status-breakdown-item">
        <span class="level-${key}">${LEVEL_LABEL[key]}</span>
        <strong>${counts[key] || 0}</strong>
      </div>
    `).join("");
  }

  renderConfirmationActions(a);

  const linkedProblems = a.cascadeChains || [];
  const linkedProblemsCount = el("linkedProblemsCount");
  if (linkedProblemsCount) linkedProblemsCount.textContent = `${linkedProblems.length}건`;
  const linkedProblemsSummary = el("linkedProblemsSummary");
  const ensureLinkEvidenceDialog = () => {
    let dialog = document.getElementById("linkEvidenceDialog");
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.id = "linkEvidenceDialog";
    dialog.className = "app-modal link-evidence-dialog";
    dialog.setAttribute("aria-labelledby", "linkEvidenceTitle");
    dialog.innerHTML = `<div class="app-modal-shell link-dialog-shell"><header class="app-modal-header"><div><span class="app-modal-eyebrow">통제 간 연계 점검</span><h3 id="linkEvidenceTitle"></h3><p>연계 가설과 실제 확인 항목을 분리해 검토하세요.</p></div><button type="button" class="app-modal-close" data-close-link-dialog aria-label="연계 근거 창 닫기">×</button></header><div id="linkEvidenceBody" class="app-modal-scroll link-dialog-body"></div></div>`;
    document.body.appendChild(dialog);
    dialog.querySelector("[data-close-link-dialog]")?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    return dialog;
  };
  const openLinkEvidenceDialog = (chain) => {
    const dialog = ensureLinkEvidenceDialog();
    const evidenceRefs = (chain.relationEvidence || []).flatMap((group) => (group.refs || []).filter((ref) => ref.snippet).map((ref) => ({ type: group.type, ...ref })));
    dialog.querySelector("#linkEvidenceTitle").textContent = `${chain.originControlId} ${chain.originTitle || ""} → ${chain.targetControlId} ${chain.targetTitle || ""}`;
    dialog.querySelector("#linkEvidenceBody").innerHTML = `
      <section class="link-dialog-summary"><h4>왜 같이 확인하나요?</h4><p><b>${escapeHtml(chain.originControlId)} ${escapeHtml(chain.originTitle || "선행 통제")}에서 결정한 내용이 ${escapeHtml(chain.targetControlId)} ${escapeHtml(chain.targetTitle || "후속 통제")}의 실행계획에 빠짐없이 반영됐는지 확인합니다.</b></p><p>${escapeHtml(chain.connectionReason || "")}</p><span class="link-grounding-level">${escapeHtml(chain.evidenceLabel || "실무 관계 가설")}</span></section>
      <section><h4>1. 준비할 자료</h4><div class="link-artifact-grid"><div><b>${escapeHtml(chain.originControlId)} ${escapeHtml(chain.originTitle || "")}</b><ul>${(chain.sourceArtifacts || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>선행 판단·승인 문서</li>"}</ul></div><div><b>${escapeHtml(chain.targetControlId)} ${escapeHtml(chain.targetTitle || "")}</b><ul>${(chain.targetArtifacts || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>후속 실행·점검 기록</li>"}</ul></div></div></section>
      <section><h4>2. 표본 3~5건을 이렇게 대조하세요</h4><div class="link-compare-table"><div class="link-compare-head"><b>대조 키</b><b>선행 자료</b><b>후속 자료</b><b>결함 신호</b></div>${(chain.comparisonRows || []).map((row) => `<div><b>${escapeHtml(row.key)}</b><span>${escapeHtml(row.source)}</span><span>${escapeHtml(row.target)}</span><em>${escapeHtml(row.fail)}</em></div>`).join("")}</div></section>
      <section class="link-result-guide"><h4>3. 대조 결과는 이렇게 해석하세요</h4><div><span class="is-problem">문제 있음</span><p>${escapeHtml(chain.decisionRule || "선행 결정과 후속 실행을 동일 표본으로 추적할 수 없는 경우")}</p></div><div><span class="is-clear">문제 없음</span><p>${escapeHtml(`${chain.originControlId} ${chain.originTitle || "선행 통제"}의 대상과 결정이 ${chain.targetControlId} ${chain.targetTitle || "후속 통제"} 자료에 빠짐없이 반영되고, 표본별 담당자·시점·결과까지 이어지는 경우`)}</p></div></section>
      ${evidenceRefs.length ? `<details class="link-direct-evidence"><summary>직접 연결을 뒷받침하는 사례집 문구</summary>${evidenceRefs.map((ref) => `<blockquote>${escapeHtml(ref.snippet)}</blockquote><small>${escapeHtml(ref.doc || "")}${ref.ref ? ` · ${escapeHtml(ref.ref)}` : ""}</small>`).join("")}</details>` : `<p class="link-dialog-caution">이 경로에는 직접 인용 근거가 없습니다. 공식 결함 사례는 연계를 증명하지 않으므로 표시하지 않았습니다. 반드시 위 표본 대조 결과로만 연계 문제를 판정하세요.</p>`}`;
    dialog.showModal();
  };
  const linkedPanel = el("linkedProblemsPanel");
  if (linkedPanel) linkedPanel.classList.toggle("is-empty", !linkedProblems.length);
  if (linkedProblemsSummary) {
    linkedProblemsSummary.classList.toggle("is-empty", !linkedProblems.length);
    linkedProblemsSummary.innerHTML = linkedProblems.length
      ? linkedProblems.map((chain) => `
        <article class="linked-problem-card severity-${escapeHtml(chain.severity || "medium")}">
          <header>
            <span class="linked-problem-kind">통제 간 영향 경로</span>
            <span class="linked-problem-severity">${escapeHtml(chain.severity === "critical" ? "높은 영향" : "영향 가능성")}</span>
          </header>
          <div class="linked-problem-route">
            <div class="linked-problem-node">
              <span>확인된 약점</span>
              <strong>${escapeHtml(chain.originControlId)} ${escapeHtml(chain.originTitle || "")}</strong>
              <em class="level-${escapeHtml(chain.originLevel || "unknown")}">${escapeHtml(chain.originLevelLabel || "미점검")}</em>
            </div>
            <span class="linked-problem-arrow" aria-hidden="true">→</span>
            <div class="linked-problem-node">
              <span>영향 통제</span>
              <strong>${escapeHtml(chain.targetControlId)} ${escapeHtml(chain.targetTitle || "")}</strong>
              <em class="level-${escapeHtml(chain.targetLevel || "unknown")}">${escapeHtml(chain.targetLevelLabel || "미점검")}</em>
            </div>
          </div>
          <div class="linked-problem-body">
            <section>
              <h4>왜 연결되는가</h4>
              <ol class="linked-problem-logic">
                ${((chain.logicSteps || []).length ? chain.logicSteps : [chain.connectionReason || "두 통제의 운영 및 증적이 서로 의존하는 경로입니다."])
                  .map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
              </ol>
            </section>
            <section>
              <h4>함께 확인할 증거</h4>
              <ul class="linked-problem-evidence">
                ${((chain.evidenceToCheck || []).length ? chain.evidenceToCheck : ["양쪽 통제의 기준·승인 기록과 실제 운영 기록을 함께 대조해야 합니다."])
                  .map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
              </ul>
            </section>
            <section>
              <h4>예상 영향</h4>
              <div class="linked-problem-impact">
                <p><b>운영</b>${escapeHtml(chain.operationalImpact || chain.impact || "선행 통제의 미흡이 후속 통제의 운영 범위와 일관성에 영향을 줄 수 있습니다.")}</p>
                <p><b>심사</b>${escapeHtml(chain.auditImpact || "선행 판단과 후속 실행의 증적이 연결되지 않으면 추가 소명이나 보완 요구로 이어질 수 있습니다.")}</p>
              </div>
            </section>
            <footer>
              <div><span>${escapeHtml(chain.evidenceLabel || "해석형 연결")}</span><p>${escapeHtml(chain.groundingNote || "통제 간 관계는 참고 가설이며 실제 조직의 업무 흐름과 증적으로 확인해야 합니다.")}</p></div>
              <button type="button" data-link-evidence="${escapeHtml(chain.originControlId)}::${escapeHtml(chain.targetControlId)}">연계 근거 상세</button>
            </footer>
          </div>
        </article>
      `).join("")
      : linkedProblemEmptyMarkup(a);
    linkedProblemsSummary.querySelectorAll("[data-link-evidence]").forEach((button) => {
      button.addEventListener("click", () => {
        const [sourceId, targetId] = button.dataset.linkEvidence.split("::");
        const chain = linkedProblems.find((item) => item.originControlId === sourceId && item.targetControlId === targetId);
        if (chain) openLinkEvidenceDialog(chain);
      });
    });
  }

  renderGapClusters(a.gapClusters || []);
}
