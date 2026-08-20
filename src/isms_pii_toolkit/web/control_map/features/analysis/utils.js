import { AREA_SHORT, LEVEL_LABEL } from "../../core/constants.js";
import { escapeHtml } from "../../core/dom.js";
import { APP_BASE } from "../../core/routes.js";
import { state } from "../../core/state.js";
import { getAssessment } from "../assessment/model.js";

export function setPanelEmptyState(panel, emptyEl, isEmpty, contentEls = []) {
  if (!panel) return;
  panel.style.display = "";
  panel.classList.toggle("is-empty", Boolean(isEmpty));
  if (emptyEl) emptyEl.style.display = isEmpty ? "" : "none";
  contentEls.forEach((node) => {
    if (!node) return;
    node.style.display = isEmpty ? "none" : "";
  });
}

const EMPTY_ICONS = {
  cluster: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="8" height="7" rx="1.6"/><rect x="13" y="4" width="8" height="7" rx="1.6"/><rect x="8" y="13" width="8" height="7" rx="1.6"/></svg>',
  link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/></svg>',
  ready: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12.4 10.7 15.2 16.2 9"/></svg>',
};

export function analysisStatusSnapshot(analysis = {}) {
  const raw = analysis.statusCounts || {};
  const unknown = Number(raw.unknown || 0);
  const none = Number(raw.none || 0);
  const partial = Number(raw.partial || 0);
  const done = Number(raw.done || 0) + Number(raw.evidenced || 0);
  const na = Number(raw.na || 0);
  const applicable = Number(analysis.applicableControlCount || 0);
  const reviewed = Number(analysis.reviewedControlCount || none + partial + done);
  return {
    unknown,
    none,
    partial,
    done,
    na,
    applicable,
    reviewed,
    weak: none + partial,
    complete: applicable > 0 && reviewed >= applicable,
  };
}

export function defaultResultEmptyStats(snapshot = {}) {
  return [
    { key: "none", label: "미이행", value: snapshot.none || 0 },
    { key: "partial", label: "부분 이행", value: snapshot.partial || 0 },
    { key: "unknown", label: "미점검", value: snapshot.unknown || 0 },
    { key: "done", label: "이행", value: snapshot.done || 0 },
  ];
}

function resultEmptyMeta(stats = []) {
  if (!stats.length) return "";
  return `<p class="result-empty-meta">${stats.map((item) => `<span class="level-${escapeHtml(item.key || "")}">${escapeHtml(item.label || "")} <b>${Number(item.value || 0)}</b></span>`).join("")}</p>`;
}

export function renderResultEmptyState({
  tone = "idle",
  icon = "cluster",
  title = "",
  body = "",
  stats = [],
  ctaLabel = "자가진단 이어가기",
  ctaHref = `${APP_BASE}/assessment`,
  ctaRoute = "assessment",
} = {}) {
  return `
    <article class="result-empty tone-${escapeHtml(tone)}" role="status">
      <div class="result-empty-icon" aria-hidden="true">${EMPTY_ICONS[icon] || EMPTY_ICONS.cluster}</div>
      <div class="result-empty-copy">
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(body)}</p>
        ${resultEmptyMeta(stats)}
      </div>
      <a class="result-empty-cta" href="${escapeHtml(ctaHref)}" data-route="${escapeHtml(ctaRoute)}">${escapeHtml(ctaLabel)}</a>
    </article>
  `;
}

export function gapClusterEmptyMarkup(analysis = {}) {
  const snapshot = analysisStatusSnapshot(analysis);
  const stats = defaultResultEmptyStats(snapshot);
  if (snapshot.complete && snapshot.weak === 0) {
    return renderResultEmptyState({
      tone: "ready",
      icon: "ready",
      title: "점검한 통제에서 묶을 미흡이 없습니다",
      body: "미이행·부분 이행이 없어 중분류 보완 묶음을 표시하지 않습니다.",
      stats,
      ctaLabel: "보고서 보기",
      ctaHref: `${APP_BASE}/report`,
      ctaRoute: "report",
    });
  }
  if (snapshot.weak > 0) {
    return renderResultEmptyState({
      tone: "wait",
      icon: "cluster",
      title: "같은 중분류에서 함께 보완할 항목이 없습니다",
      body: `미흡 ${snapshot.weak}개는 확인됐지만, 한 중분류에 2개 이상 모여야 카드가 생깁니다.`,
      stats,
    });
  }
  return renderResultEmptyState({
    tone: "idle",
    icon: "cluster",
    title: "아직 묶을 미흡 통제가 없습니다",
    body: "같은 중분류에 미이행·부분 이행이 2개 이상일 때 여기에 표시됩니다.",
    stats,
  });
}

export function linkedProblemEmptyMarkup(analysis = {}) {
  const snapshot = analysisStatusSnapshot(analysis);
  const stats = defaultResultEmptyStats(snapshot);
  if (snapshot.complete && snapshot.weak === 0) {
    return renderResultEmptyState({
      tone: "ready",
      icon: "ready",
      title: "연계할 미흡 통제가 없습니다",
      body: "미이행·부분 이행이 없어 영향 경로를 띄울 출발점이 없습니다.",
      stats,
      ctaLabel: "보고서 보기",
      ctaHref: `${APP_BASE}/report`,
      ctaRoute: "report",
    });
  }
  if (snapshot.weak > 0) {
    return renderResultEmptyState({
      tone: "wait",
      icon: "link",
      title: "확인된 미흡 통제 기준의 연계 경로가 없습니다",
      body: `미흡 ${snapshot.weak}개는 확인됐지만, 다른 통제로 이어지는 경로는 식별되지 않았습니다.`,
      stats,
    });
  }
  return renderResultEmptyState({
    tone: "idle",
    icon: "link",
    title: "아직 식별된 연계 문제가 없습니다",
    body: "미흡으로 확인된 통제가 생기면 영향 경로가 여기에 표시됩니다.",
    stats,
  });
}

export function clampPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

export function formatPercent(value) {
  const n = clampPercent(value);
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/** 내부 평균값 → 정성 구간 (백엔드 score_metrics와 동일) */
export function qualitativeLabelFromPercent(percent) {
  if (percent == null || percent === "") return "판단 보류";
  const value = Number(percent);
  if (!Number.isFinite(value)) return "판단 보류";
  if (value >= 80) return "양호";
  if (value >= 60) return "보통";
  if (value >= 35) return "보완 필요";
  return "기초 보완 필요";
}

function replaceLabeledPercents(text) {
  const labels = [
    "전체 진행 참고",
    "전체 진행 반영 점수",
    "점검분 이행 참고",
    "점검분만 이행 점수",
    "내부 참고점수",
    "내부 참고 점수",
    "평가분 이행점수",
    "평가분 이행 점수",
  ];
  let next = text;
  for (const label of labels) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    next = next.replace(
      new RegExp(`${escaped}\\s*([\\d.]+)\\s*%`, "g"),
      (_, num) => {
        const mapped = label.includes("점검") || label.includes("평가분")
          ? "점검분 이행 참고"
          : "전체 진행 참고";
        return `${mapped} '${qualitativeLabelFromPercent(num)}'`;
      },
    );
  }
  next = next.replace(/(^|\n)(- [^:\n]+):\s*([\d.]+)%/g, (_, lead, name, num) => (
    `${lead}${name}: ${qualitativeLabelFromPercent(num)}`
  ));
  next = next.replace(
    /준비도\s*([\d.]+)%/g,
    (_, num) => `참고 구간 '${qualitativeLabelFromPercent(num)}'`,
  );
  return next;
}

/** 이전 분석 스냅샷/AI 리포트에 남은 옛 점수 표기를 정성·새 라벨로 치환 */
export function remapScoreTerminology(value) {
  const text = String(value ?? "")
    .replaceAll("내부 참고점수(진행 반영)", "전체 진행 참고")
    .replaceAll("내부 참고 점수(진행 반영)", "전체 진행 참고")
    .replaceAll("전체 진행 반영 점수", "전체 진행 참고")
    .replaceAll("내부 참고점수", "전체 진행 참고")
    .replaceAll("내부 참고 점수", "전체 진행 참고")
    .replaceAll("점검분만 이행 점수", "점검분 이행 참고")
    .replaceAll("평가분 이행점수", "점검분 이행 참고")
    .replaceAll("평가분 이행 점수", "점검분 이행 참고")
    .replaceAll("점수 가중치:", "참고 구간:")
    .replaceAll("상태별 배점:", "참고 구간:")
    // 옛 배점 문장 전체를 먼저 치환 (부분 치환으로 '미이행 5'가 남지 않게)
    .replaceAll("미이행 5 · 부분 이행 45 · 이행 80 · 증적 확보 100", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("미이행 5 · 부분 이행 45 · 이행 80", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("미이행 0 · 부분 이행 50 · 이행 100", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("미이행 0 · 부분 이행 45 · 이행 80", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("미이행 5 · 부분 이행 45", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("부분 이행 45 · 이행 80", "양호 · 보통 · 보완 필요 · 기초 보완 필요")
    .replaceAll("미이행 5 · 양호", "양호")
    .replaceAll("미이행 5 · ", "")
    .replaceAll("미이행 5 ·", "")
    .replaceAll("미이행 5", "")
    .replaceAll(" · 증적 확보 100", "")
    .replaceAll("· 증적 확보 100", "")
    .replaceAll(" · 이행 80", "")
    .replaceAll("· 이행 80", "");
  return replaceLabeledPercents(text);
}

export function heatmapTone(score) {
  if (score <= 0) return "is-empty";
  if (score < 30) return "is-low";
  if (score < 70) return "is-mid";
  return "is-high";
}

export function shortRiskTip(text, fallback = "관련 리스크를 확인하세요.") {
  const raw = String(text || "").replace(/\s+/g, " ").trim();
  if (!raw) return fallback;
  return raw.length > 110 ? `${raw.slice(0, 108)}…` : raw;
}

/** 체크 ID 대신 실제 체크 문구를 짧게 보여 준다. */
export function checklistBrief(row, maxLen = 56) {
  const text = String(row?.checklistItem || row?.item || row?.problem || "").replace(/\s+/g, " ").trim();
  if (text) return text.length > maxLen ? `${text.slice(0, maxLen - 1)}…` : text;
  const id = row?.checklistItemId;
  if (id) return `체크 항목 ${id}`;
  return "체크 항목";
}

/** 지금 진단(assessments) 상태를 우선해 상세 카드와 맞춘다. */
export function liveControlLevel(controlId, fallbackLevel = "unknown") {
  const live = getAssessment(controlId);
  if (live) return live;
  return fallbackLevel || "unknown";
}

export function levelBadge(level, label) {
  const lvl = level || "unknown";
  const text = label || LEVEL_LABEL[lvl] || lvl;
  return `<span class="level-badge level-${escapeHtml(lvl)}">${escapeHtml(text)}</span>`;
}

export function severityLabel(severity) {
  if (severity === "critical") return "심각";
  if (severity === "high") return "높음";
  return "보통";
}

export function renderControlChips(entries, max = 6) {
  const list = entries || [];
  const shown = list.slice(0, max);
  const rest = list.length - shown.length;
  const chips = shown.map((item) => {
    if (typeof item === "string") {
      return `<button type="button" class="related-chip ui-tip" data-jump-control="${item}" data-tip="${escapeHtml(controlRiskTip(item))}" title="${escapeHtml(controlRiskTip(item))}">${item}</button>`;
    }
    const id = item.controlId;
    const label = item.levelLabel ? `${id} ${item.levelLabel}` : id;
    return `<button type="button" class="related-chip ui-tip" data-jump-control="${id}" data-tip="${escapeHtml(controlRiskTip(id))}" title="${escapeHtml(controlRiskTip(id))}">${escapeHtml(label)}</button>`;
  }).join("");
  return chips + (rest > 0 ? `<span class="chip-more">+${rest}</span>` : "");
}

export function findControlTitle(controlId) {
  const control = state.checklist.find((c) => c.id === controlId) || state.allControls.find((c) => c.id === controlId);
  return control?.title || "";
}

export function humanizeOverlapTitle(overlap) {
  const title = String(overlap.title || "");
  const ids = overlap.controlIds || (overlap.matchedControls || []).map((c) => c.controlId);
  if ((title.includes("→") || title.includes("연결 겹침") || title.includes("중심 연쇄")) && ids.length) {
    if (ids.length === 2) {
      return `${ids[0]} ${findControlTitle(ids[0])} ↔ ${ids[1]} ${findControlTitle(ids[1])}`.trim();
    }
    if (title.includes("중심 연쇄")) {
      return `${ids[0]} ${findControlTitle(ids[0])} 중심 연쇄`.trim();
    }
  }
  return title;
}

export function compoundDisplayTitle(syn) {
  const ids = syn.controlIds || [];
  const reasons = (syn.connectionReasons || []).map(humanizeBasis).filter(Boolean);
  if (reasons[0] && reasons[0].length <= 52) return reasons[0];
  if (ids.length <= 4) return ids.map((id) => `${id} ${findControlTitle(id)}`.trim()).join(", ");
  return `${ids.length}개 통제 동시 미흡`;
}

export function humanizeBasis(text) {
  return String(text || "")
    .replace(/통제 그래프 MANUAL_RELATIONS:\s*/gi, "")
    .replace(/MANUAL_RELATIONS 연결:\s*/gi, "연결 ")
    .replace(/시나리오 경로 3연속:\s*/gi, "시나리오 연속: ")
    .replace(/시나리오 경로 인접:\s*/gi, "시나리오 인접: ")
    .replace(/분류 .+ 심층 compoundHint/gi, "분류 심층 힌트")
    .replace(/\s+/g, " ")
    .trim();
}

export function distinctDesc(title, tip) {
  const t = String(title || "").trim();
  const d = String(tip || "").trim();
  if (!d) return "";
  if (!t) return d;
  if (d === t) return "";
  if (d.startsWith(t) || t.startsWith(d)) return "";
  return d;
}

export function compactOverlapList(items) {
  const list = items || [];
  const hubs = list.filter((item) => {
    const id = String(item.bundleId || "");
    return id.includes("-hub") || (item.controlIds || []).length >= 3;
  });
  const hubSets = hubs.map((item) => new Set(item.controlIds || []));
  return list.filter((item) => {
    const ids = item.controlIds || [];
    if (ids.length !== 2) return true;
    const bid = String(item.bundleId || "");
    if (!bid.startsWith("rel-")) return true;
    return !hubSets.some((set) => ids.every((id) => set.has(id)));
  });
}

export function renderInsightCard({
  idAttr,
  idValue,
  severityClass,
  open,
  metaHtml,
  title,
  desc,
  chipsHtml,
  detailHtml,
}) {
  return `
    <article class="insight-card ${severityClass}${open ? " open" : ""}" ${idAttr}="${idValue}">
      <div class="insight-card-head">
        <div class="insight-main">
          <div class="insight-meta">${metaHtml}</div>
          <h4 class="insight-title">${escapeHtml(title)}</h4>
          ${desc ? `<p class="insight-desc">${escapeHtml(desc)}</p>` : ""}
          <div class="insight-chips">${chipsHtml}</div>
        </div>
        <button type="button" class="insight-expand" data-insight-toggle="${idValue}" aria-expanded="${open}" aria-label="상세 펼치기">
          ${open ? "▴" : "▾"}
        </button>
      </div>
      <div class="insight-detail">${detailHtml}</div>
    </article>
  `;
}

export function controlRiskTip(controlId) {
  const gap = (state.analysis?.topGaps || state.analysis?.criticalGaps || [])
    .find((item) => item.controlId === controlId);
  if (gap?.riskIfMissing) return shortRiskTip(gap.riskIfMissing);
  if (gap?.summary) return shortRiskTip(gap.summary);
  const control = state.checklist.find((c) => c.id === controlId) || state.allControls.find((c) => c.id === controlId);
  if (control?.riskIfMissing) return shortRiskTip(control.riskIfMissing);
  return shortRiskTip(`${controlId} 미흡 시 운영/심사 리스크가 커질 수 있습니다.`);
}

export function areaLabelFromControlId(controlId) {
  const area = String(controlId || "").split(".")[0];
  return AREA_SHORT[area] || `영역 ${area || "?"}`;
}

export function categoryKeyFromControlId(controlId) {
  const parts = String(controlId || "").split(".");
  if (parts.length >= 2) return `${parts[0]}.${parts[1]}`;
  return String(controlId || "기타");
}

export function severityBadge(severity, label) {
  return `<span class="severity-badge ${severity}">${label || severity}</span>`;
}


export function formatNarrativeReport(text) {
  if (!text) return "";
  return text.split("\n").map((line) => {
    const trimmed = line.trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
      return `<h5 class="narrative-heading">${escapeHtml(trimmed)}</h5>`;
    }
    if (trimmed.startsWith("- ")) {
      return `<p class="narrative-bullet">${escapeHtml(trimmed.slice(2))}</p>`;
    }
    if (/^\d+\)/.test(trimmed) || /^\d+\./.test(trimmed)) {
      return `<p class="narrative-item">${escapeHtml(trimmed)}</p>`;
    }
    return `<p>${escapeHtml(trimmed)}</p>`;
  }).join("");
}
