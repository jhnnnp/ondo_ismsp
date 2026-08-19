import { LEVEL_LABEL } from "../../core/constants.js";
import { el, escapeHtml } from "../../core/dom.js";
import { state } from "../../core/state.js";
import {
  formatNarrativeReport,
  gapClusterEmptyMarkup,
  levelBadge,
  liveControlLevel,
  setPanelEmptyState,
  shortRiskTip,
} from "./utils.js";

function renderInlineCascadeList(items) {
  if (!items?.length) return `<p class="detail-empty">연결된 연쇄가 없습니다.</p>`;
  return `<div class="gap-inline-list">${items.map((item) => `
    <article class="gap-inline-item severity-${escapeHtml(item.severity || "medium")}">
      <strong>${escapeHtml(item.sourceControlId || "")} → ${escapeHtml(item.targetControlId || "")} ${escapeHtml(item.targetTitle || "")}</strong>
      <p>${escapeHtml(item.impact || item.connectionReason || "")}</p>
    </article>
  `).join("")}</div>`;
}

function renderInlineOverlapList(items) {
  if (!items?.length) return `<p class="detail-empty">겹치는 패턴이 없습니다.</p>`;
  return `<div class="gap-inline-list">${items.map((item) => {
    const co = (item.coGapControls || []).slice(0, 6)
      .map((c) => escapeHtml(c.controlId || c))
      .join(", ");
    return `
      <article class="gap-inline-item">
        <strong>${escapeHtml(item.title || item.theme || "겹침")}</strong>
        <p>${escapeHtml(item.summary || item.excerpt || "")}</p>
        ${co ? `<p class="gap-inline-meta">동시 미흡: ${co}</p>` : ""}
      </article>
    `;
  }).join("")}</div>`;
}

function renderEvidencePanel(gap) {
  const needed = gap.auditEvidenceNeeded || [];
  return `
    ${gap.evidenceNote ? `
      <div class="meta-card" style="margin-bottom:10px;">
        <h4>구현/증적 연결</h4>
        <p>${escapeHtml(gap.evidenceNote)}</p>
      </div>
    ` : ""}
    <div class="meta-card">
      <h4>심사 전 필요 증적</h4>
      <ul>${needed.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>정책/지침/운영 기록을 준비하세요.</li>"}</ul>
      <p class="gap-evidence-note">판정·증적 등록은 「지금 진단」 카드에서 하세요.</p>
    </div>
  `;
}

function ensureDefectEvidenceDialog() {
  let dialog = document.getElementById("defectEvidenceDialog");
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.id = "defectEvidenceDialog";
  dialog.className = "app-modal defect-evidence-dialog";
  dialog.setAttribute("aria-labelledby", "defectEvidenceTitle");
  dialog.innerHTML = `<div class="app-modal-shell defect-dialog-shell"><header class="app-modal-header"><div><span class="app-modal-eyebrow">우선순위 산정 근거</span><h3 id="defectEvidenceTitle"></h3><p>선정 근거와 참고 사례를 구분해 확인하세요.</p></div><button type="button" class="app-modal-close" data-close-defect-dialog aria-label="우선순위 근거 창 닫기">×</button></header><div id="defectEvidenceBody" class="app-modal-scroll defect-dialog-body"></div></div>`;
  document.body.appendChild(dialog);
  dialog.querySelector("[data-close-defect-dialog]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  return dialog;
}

function openDefectEvidenceDialog(primary) {
  const evidence = primary?.defectEvidence;
  if (!evidence) return;
  const dialog = ensureDefectEvidenceDialog();
  const title = dialog.querySelector("#defectEvidenceTitle");
  const body = dialog.querySelector("#defectEvidenceBody");
  if (title) title.textContent = `${primary.controlId} ${primary.title}`;
  if (body) body.innerHTML = `
    <section><h4>과거 결함현황 매핑</h4><p>현행 통제에 연결된 과거 결함 <strong>${evidence.defectCount || 0}건</strong>${evidence.caseCount ? ` · 사례집 결함 유형 ${evidence.caseCount}건` : ""}</p>
      ${(evidence.mappedSources || []).length ? `<ul>${evidence.mappedSources.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
    </section>
    <section><h4>공식 안내서 결함 사례</h4>
      ${(evidence.examples || []).length ? `<ol>${evidence.examples.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>` : `<p class="detail-empty">이 통제에 수록된 결함 사례 문구가 없습니다.</p>`}
      ${evidence.sourceDoc ? `<p class="defect-dialog-source">출처: ${escapeHtml(evidence.sourceDoc)}${(evidence.pages || []).length ? ` · ${evidence.pages.map((page) => `${page}쪽`).join(", ")}` : ""}</p>` : ""}
    </section>
    <p class="defect-dialog-caution">과거 결함 빈도는 점검 순서를 정하기 위한 참고 근거입니다. 현재 조직에서 같은 결함이 발생했다는 판정은 아닙니다.</p>`;
  dialog.showModal();
}

export function renderGapClusters(clusters) {
  const panel = el("gapClustersPanel");
  const container = el("gapClusters");
  const empty = el("gapClustersEmpty");
  const count = el("gapClustersCount");
  if (!panel || !container) return;
  if (count) count.textContent = `${(clusters || []).length}개 묶음`;
  if (!clusters || !clusters.length) {
    setPanelEmptyState(panel, empty, true, [container]);
    if (empty) empty.innerHTML = gapClusterEmptyMarkup(state.analysis || {});
    container.innerHTML = "";
    return;
  }
  setPanelEmptyState(panel, empty, false, [container]);
  container.innerHTML = clusters.map((cluster) => {
    const controls = cluster.controls || [];
    const primary = cluster.primaryControl || controls[0] || null;
    const related = controls.filter((item) => item.controlId !== primary?.controlId);
    return `
      <article class="gap-cluster-card">
        <h4>${escapeHtml(cluster.theme)} <span class="severity-badge ${escapeHtml(cluster.severity || "medium")}">미흡 ${cluster.gapCount}개</span></h4>
        <div class="gap-cluster-status" aria-label="미흡 상태 구성">
          ${cluster.noneCount ? `<span class="level-none">미이행 ${cluster.noneCount}개</span>` : ""}
          ${cluster.partialCount ? `<span class="level-partial">부분 이행 ${cluster.partialCount}개</span>` : ""}
        </div>
        ${primary ? `
          <div class="gap-cluster-primary">
            <span>우선 보완</span>
            <strong>${escapeHtml(primary.controlId)} ${escapeHtml(primary.title)}</strong>
            <div class="gap-cluster-basis">
              <b>선정 근거</b>
              <ul>${(primary.selectionReasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join("") || "<li>현재 상태와 통제 우선순위를 기준으로 선정했습니다.</li>"}</ul>
            </div>
            ${primary.riskIfMissing ? `<p class="gap-cluster-risk"><b>미흡 시 영향</b>${escapeHtml(primary.riskIfMissing)}</p>` : ""}
            <p class="gap-cluster-next"><b>다음 조치</b>${escapeHtml(primary.nextAction || "진단 상태와 필요한 증적을 확인하세요.")}</p>
            <div class="gap-cluster-actions">
              ${primary.defectEvidence ? `<button type="button" class="gap-evidence-button" data-open-defect-evidence="${escapeHtml(primary.controlId)}">매핑 근거·사례 보기</button>` : ""}
              <button type="button" class="gap-check-button" data-jump-control="${escapeHtml(primary.controlId)}">이 통제 점검하기</button>
            </div>
          </div>
        ` : `<p>${escapeHtml(cluster.summary)}</p>`}
        ${related.length ? `
          <div class="gap-cluster-related">
            <span>함께 확인</span>
            <div class="related-chips">
              ${related.map((item) => {
                const tip = `${item.controlId} ${item.title} · ${item.levelLabel}. ${item.nextAction || "클릭하면 해당 통제로 이동합니다."}`;
                return `<button type="button" class="related-chip ui-tip" data-jump-control="${escapeHtml(item.controlId)}" data-tip="${escapeHtml(shortRiskTip(tip))}" title="${escapeHtml(shortRiskTip(tip))}">${escapeHtml(item.controlId)}</button>`;
              }).join("")}
            </div>
          </div>
        ` : ""}
      </article>
    `;
  }).join("");
  container.querySelectorAll("[data-open-defect-evidence]").forEach((button) => {
    button.addEventListener("click", () => {
      const primary = clusters.find((cluster) => cluster.primaryControl?.controlId === button.dataset.openDefectEvidence)?.primaryControl;
      openDefectEvidenceDialog(primary);
    });
  });
}

function renderChecklistCards(items) {
  if (!items || !items.length) {
    return `<p class="detail-empty">확인 포인트가 없습니다.</p>`;
  }
  const rows = items.filter((row) => row.unmet !== false);
  const source = rows.length ? rows : items;
  return `<div class="checklist-cards checklist-cards--compact">${source.map((row, index) => `
    <article class="check-card is-unmet">
      <h5>${escapeHtml(row.checklistItemId || String(index + 1))}. ${escapeHtml(row.item)}</h5>
      ${row.remediation ? `<p class="check-card-remediation">${escapeHtml(row.remediation)}</p>` : ""}
    </article>
  `).join("")}</div>`;
}

function renderSummaryPanel(gap) {
  const narrative = gap.detailNarrative || gap.narrativeReport || "";
  const basis = String(gap.logicalBasis || gap.riskIfMissing || "").trim();
  const risk = String(gap.expectedIssue || gap.riskIfMissing || "").trim();
  const shortTip = shortRiskTip(gap.detailNarrativeTip || gap.organicAnalysis || gap.problem || "", "");
  const showBasis = basis && basis !== shortTip && !narrative.includes(basis);
  const showRisk = risk && risk !== basis && risk !== shortTip;

  if (narrative) {
    return `
      <div class="ai-detail-narrative meta-card" style="margin-bottom:${showBasis || showRisk ? "14px" : "0"};">
        <h4>공식 안내 기반 해설</h4>
        ${formatNarrativeReport(narrative)}
        ${(gap.detailNarrativeSources || []).length ? `
          <p class="ai-detail-sources">근거: ${gap.detailNarrativeSources.map((s) => escapeHtml(s)).join(" · ")}</p>
        ` : ""}
      </div>
      ${(showBasis || showRisk) ? `
        <div class="meta-grid">
          ${showBasis ? `
            <div class="meta-card">
              <h4>판단 근거</h4>
              <p>${escapeHtml(basis)}</p>
            </div>
          ` : ""}
          ${showRisk ? `
            <div class="meta-card">
              <h4>방치 시 리스크</h4>
              <p>${escapeHtml(risk)}</p>
            </div>
          ` : ""}
        </div>
      ` : ""}
    `;
  }

  const fallback = gap.detailedSummary || gap.organicAnalysis || gap.problem || "";
  return `
    ${fallback ? `<div class="gap-summary-box">${escapeHtml(fallback)}</div>` : `<p class="detail-empty">추가 해설이 없습니다.</p>`}
    ${(showBasis || showRisk) ? `
      <div class="meta-grid">
        ${showBasis ? `
          <div class="meta-card">
            <h4>판단 근거</h4>
            <p>${escapeHtml(basis)}</p>
          </div>
        ` : ""}
        ${showRisk ? `
          <div class="meta-card">
            <h4>방치 시 리스크</h4>
            <p>${escapeHtml(risk)}</p>
          </div>
        ` : ""}
      </div>
    ` : ""}
  `;
}

function renderGapAccordion(gap) {
  const open = state.expandedGaps.has(gap.controlId);
  const liveLevel = liveControlLevel(gap.controlId, gap.level);
  const liveLabel = LEVEL_LABEL[liveLevel] || gap.levelLabel || liveLevel;
  const checklistCount = (gap.checklistBreakdown || []).filter((row) => row.unmet !== false).length
    || (gap.checklistBreakdown || []).length;
  const tabs = [
    { id: "summary", label: "해설" },
    { id: "checklist", label: `확인 포인트 (${checklistCount})` },
    { id: "evidence", label: "필요 증적" },
  ];
  const actions = gap.immediateActions || gap.recommendedActions || [];
  const tip = shortRiskTip(gap.detailNarrativeTip || gap.organicAnalysis || gap.problem || "");
  const firstAction = actions[0] ? shortRiskTip(actions[0], "") : "";
  const cascades = gap.cascadeRisks || [];
  const overlaps = gap.overlappingRisks || [];
  const cascadeCount = cascades.length;
  const overlapCount = overlaps.length;
  const inlineKey = state.expandedGapInline?.[gap.controlId] || "";

  return `
    <article class="gap-accordion level-${escapeHtml(liveLevel)} severity-${gap.severity}${open ? " open" : ""}${state.gapRevealPending ? " pending-reveal" : ""}" data-gap-id="${gap.controlId}" data-live-level="${escapeHtml(liveLevel)}">
      <button type="button" class="gap-accordion-head" aria-expanded="${open}">
        <div class="gap-head-main">
          <div class="gap-head-top">
            ${levelBadge(liveLevel, liveLabel)}
            <span class="gap-id">${gap.controlId}</span>
            ${gap.scenarioRelevant ? `<span class="scenario-gap-badge">시나리오</span>` : ""}
          </div>
          <div class="gap-title-text">${escapeHtml(gap.title)}</div>
          <div class="gap-head-meta">${escapeHtml(gap.areaName)} / ${escapeHtml(gap.categoryName)}</div>
          <p class="gap-head-summary">${escapeHtml(tip)}</p>
          ${firstAction ? `<p class="gap-head-action">다음 · ${escapeHtml(firstAction)}</p>` : ""}
        </div>
        <span class="gap-chevron" aria-hidden="true">${open ? "▴" : "▾"}</span>
      </button>
      <div class="gap-accordion-body">
        <div class="gap-detail-layout">
          <div class="gap-detail-primary">
        ${(gap.causalBasis || []).length ? `
          <div class="meta-card" style="margin-bottom:12px;">
            <h4>때문에 (체크 근거)</h4>
            <ul>${gap.causalBasis.slice(0, 6).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
          </div>
        ` : ""}
        ${actions.length ? `
          <div class="meta-card" style="margin-bottom:12px;">
            <h4>즉시 보완 액션</h4>
            <div class="action-list">${actions.slice(0, 4).map((action, i) => `
              <div class="action-list-item"><span>${i + 1}</span><div>${escapeHtml(action)}</div></div>
            `).join("")}</div>
          </div>
        ` : ""}
        ${(cascadeCount || overlapCount) ? `
          <div class="gap-crossref-note">
            ${cascadeCount ? `<button type="button" class="detail-inline-toggle${inlineKey === "cascade" ? " active" : ""}" data-inline-panel="cascade" aria-expanded="${inlineKey === "cascade"}">연쇄 ${cascadeCount}건</button>` : ""}
            ${overlapCount ? `<button type="button" class="detail-inline-toggle${inlineKey === "overlap" ? " active" : ""}" data-inline-panel="overlap" aria-expanded="${inlineKey === "overlap"}">겹침 ${overlapCount}건</button>` : ""}
          </div>
          <div class="gap-inline-panel${inlineKey === "cascade" ? " open" : ""}" data-inline-host="cascade"${inlineKey === "cascade" ? "" : " hidden"}>
            <h4>연쇄 리스크</h4>
            ${renderInlineCascadeList(cascades)}
          </div>
          <div class="gap-inline-panel${inlineKey === "overlap" ? " open" : ""}" data-inline-host="overlap"${inlineKey === "overlap" ? "" : " hidden"}>
            <h4>겹치는 문제</h4>
            ${renderInlineOverlapList(overlaps)}
          </div>
        ` : ""}
          </div>
          <div class="gap-detail-secondary">
        <nav class="gap-tabs" role="tablist">
          ${tabs.map((tab, i) => `
            <button type="button" class="gap-tab${i === 0 ? " active" : ""}" data-gap-tab="${gap.controlId}" data-tab="${tab.id}">${tab.label}</button>
          `).join("")}
        </nav>
        <div class="gap-tab-panel active" data-gap-panel="${gap.controlId}" data-panel="summary">
          ${renderSummaryPanel(gap)}
        </div>
        <div class="gap-tab-panel" data-gap-panel="${gap.controlId}" data-panel="checklist">
          ${renderChecklistCards(gap.checklistBreakdown)}
        </div>
        <div class="gap-tab-panel" data-gap-panel="${gap.controlId}" data-panel="evidence">
          ${renderEvidencePanel(gap)}
        </div>
          </div>
        </div>
        ${gap.projectHint ? `<div class="project-hint">${escapeHtml(gap.projectHint)}</div>` : ""}
      </div>
    </article>
  `;
}

export function filteredGaps(gaps) {
  let items = gaps || [];
  const q = state.gapSearch.trim().toLowerCase();
  if (q) {
    items = items.filter((gap) =>
      gap.controlId.includes(q)
      || gap.title.toLowerCase().includes(q)
      || (gap.categoryName || "").toLowerCase().includes(q)
    );
  }
  if (state.gapLevelFilter !== "all") {
    items = items.filter((gap) => liveControlLevel(gap.controlId, gap.level) === state.gapLevelFilter);
  }
  return items;
}

function bindGapInteractions() {
  const container = el("criticalGaps");
  if (!container) return;
  if (!state.expandedGapInline) state.expandedGapInline = {};
  container.querySelectorAll(".gap-accordion-head").forEach((head) => {
    head.addEventListener("click", (event) => {
      if (event.target.closest("[data-gap-tab], [data-jump-control], [data-inline-panel]")) return;
      const accordion = head.closest(".gap-accordion");
      if (!accordion) return;
      const id = accordion.dataset.gapId;
      const open = !state.expandedGaps.has(id);
      if (open) state.expandedGaps.add(id);
      else state.expandedGaps.delete(id);
      accordion.classList.toggle("open", open);
      head.setAttribute("aria-expanded", open ? "true" : "false");
      const chevron = head.querySelector(".gap-chevron");
      if (chevron) chevron.textContent = open ? "▴" : "▾";
    });
  });
  container.querySelectorAll("[data-gap-tab]").forEach((tabBtn) => {
    tabBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const gapId = tabBtn.dataset.gapTab;
      const tab = tabBtn.dataset.tab;
      const accordion = container.querySelector(`.gap-accordion[data-gap-id="${gapId}"]`);
      if (!accordion) return;
      accordion.querySelectorAll(".gap-tab").forEach((t) => t.classList.toggle("active", t === tabBtn));
      accordion.querySelectorAll("[data-gap-panel]").forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.panel === tab);
      });
    });
  });
  container.querySelectorAll("[data-inline-panel]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const accordion = btn.closest(".gap-accordion");
      if (!accordion) return;
      const gapId = accordion.dataset.gapId;
      const panelId = btn.dataset.inlinePanel;
      const current = state.expandedGapInline[gapId];
      const next = current === panelId ? "" : panelId;
      state.expandedGapInline[gapId] = next;
      accordion.querySelectorAll("[data-inline-panel]").forEach((toggle) => {
        const on = toggle.dataset.inlinePanel === next;
        toggle.classList.toggle("active", on);
        toggle.setAttribute("aria-expanded", on ? "true" : "false");
      });
      accordion.querySelectorAll("[data-inline-host]").forEach((panel) => {
        const on = panel.dataset.inlineHost === next;
        panel.hidden = !on;
        panel.classList.toggle("open", on);
      });
    });
  });
}

export function renderAnalyzeGaps() {
  const a = state.analysis;
  if (!a) return;
  const gapsToShow = (a.topGaps && a.topGaps.length) ? a.topGaps : (a.criticalGaps || []);
  const filtered = filteredGaps(gapsToShow);
  const container = el("criticalGaps");
  const countLabel = el("gapCountLabel");
  const hint = el("gapFilterHint");
  if (countLabel) {
    countLabel.textContent = `표시 ${filtered.length} / 확인된 미흡 ${a.gapCount}건`;
  }
  if (hint) {
    if (!filtered.length && gapsToShow.length) {
      const counts = { none: 0, partial: 0 };
      gapsToShow.forEach((gap) => {
        const lvl = liveControlLevel(gap.controlId, gap.level);
        if (lvl === "none" || lvl === "partial") counts[lvl] += 1;
      });
      hint.style.display = "";
      hint.innerHTML = `현재 필터에 맞는 미흡 통제가 없습니다. 미이행 <strong>${counts.none}</strong>건, 부분 이행 <strong>${counts.partial}</strong>건입니다. 필터를 바꿔 보세요.`;
    } else {
      hint.style.display = "none";
    }
  }
  if (!container) return;
  if (!state.expandedGapInline) state.expandedGapInline = {};
  container.innerHTML = filtered.length
    ? filtered.map(renderGapAccordion).join("")
    : `<p class="detail-empty">표시할 미흡 통제가 없습니다.</p>`;
  container.querySelectorAll(".gap-accordion-body").forEach((body) => {
    const primary = body.querySelector(".gap-detail-primary");
    const metaCards = Array.from(primary?.querySelectorAll(":scope > .meta-card") || []);
    const causalCard = metaCards.find((card) => card.querySelector("h4")?.textContent.includes("때문에"));
    const actionCard = metaCards.find((card) => card.querySelector("h4")?.textContent.includes("즉시 보완"));
    if (causalCard) {
      causalCard.classList.add("causal-basis-card");
      const list = causalCard.querySelector("ul");
      const firstLine = list?.querySelector("li")?.textContent?.trim();
      if (list && firstLine) {
        const preview = document.createElement("p");
        preview.className = "causal-basis-preview";
        preview.textContent = firstLine;
        const more = document.createElement("details");
        more.className = "causal-basis-more";
        const summary = document.createElement("summary");
        summary.textContent = "근거 더보기";
        more.append(summary, list);
        causalCard.append(preview, more);
      }
    }
    if (actionCard && causalCard) primary.insertBefore(actionCard, causalCard);
  });
  bindGapInteractions();
  state.gapRevealPending = false;
}
