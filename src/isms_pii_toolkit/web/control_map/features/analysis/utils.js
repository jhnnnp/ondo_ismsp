import { AREA_SHORT, LEVEL_LABEL } from "../../core/constants.js";
import { escapeHtml } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { getAssessment } from "../assessment/model.js";

export function setPanelEmptyState(panel, emptyEl, isEmpty, contentEls = []) {
  if (!panel) return;
  panel.style.display = "";
  if (emptyEl) emptyEl.style.display = isEmpty ? "" : "none";
  contentEls.forEach((node) => {
    if (!node) return;
    node.style.display = isEmpty ? "none" : "";
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
