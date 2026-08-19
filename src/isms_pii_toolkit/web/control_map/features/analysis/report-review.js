import { el, escapeHtml, showToast } from "../../core/dom.js";
import { state } from "../../core/state.js";
import { navigateToControl, renderReportReturnBar } from "../assessment/controller.js";
import { switchAnalyzeSection } from "./presentation.js";
import { findControlTitle, liveControlLevel, levelBadge, qualitativeLabelFromPercent, remapScoreTerminology } from "./utils.js";
import { AREA_SHORT, LEVEL_LABEL } from "../../core/constants.js";

function normalizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function stableId(value) {
  let hash = 5381;
  for (const char of value) {
    hash = ((hash << 5) + hash) ^ char.charCodeAt(0);
  }
  return (hash >>> 0).toString(36);
}

function reviewTitle(text) {
  if (text.startsWith("전체 준비도")) return "전체 준비도";
  if (text.startsWith("가장 취약한 분야")) return "취약 분야";
  if (text.startsWith("연쇄 리스크")) return "연쇄 리스크";
  if (text.startsWith("다중 갭")) return "다중 갭";
  if (text.startsWith("추가 겹침")) return "추가 겹침 패턴";
  if (text.startsWith("최우선 점검 통제")) return "최우선 점검";
  if (text.startsWith("상위 갭")) return "상위 갭";
  return "확인 항목";
}

export function parseInsightCard(text) {
  const title = reviewTitle(text);
  const readiness = text.match(
    /^전체 준비도\s+([\d.]+)%\s*[—\-]\s*(.+?)\.\s*갭\s+(\d+)건\s+중\s+미이행\s+(\d+)건,\s*미점검\s+(\d+)건,\s*부분 이행\s+(\d+)건/
  );
  if (readiness) {
    return {
      title,
      kind: "readiness",
      metric: readiness[1],
      metricUnit: "%",
      headline: readiness[2],
      question: `현재 준비도 ${readiness[1]}%와 갭 ${readiness[3]}건의 구성을 확인했나요?`,
      explanation: "현재 입력된 통제 상태를 합산한 전체 진단 요약입니다. 수치와 단계가 현재 상황에 맞는지 확인하세요.",
      stats: [
        { label: "갭", value: readiness[3] },
        { label: "미이행", value: readiness[4], tone: "danger" },
        { label: "미점검", value: readiness[5], tone: "warn" },
        { label: "부분 이행", value: readiness[6], tone: "mid" },
      ],
      body: "",
    };
  }

  const weak = text.match(
    /^가장 취약한 분야는\s+'([^']+)'\(준비도\s+([\d.]+)%,\s*통제\s+(\d+)개\)입니다\.\s*(.*)$/
  );
  if (weak) {
    return {
      title,
      kind: "weak",
      metric: weak[2],
      metricUnit: "%",
      headline: weak[1],
      question: `'${weak[1]}' 분야를 우선 보완 대상으로 검토할까요?`,
      explanation: `준비도가 가장 낮은 분야입니다. 관련 통제 ${weak[3]}개의 담당자와 증적 보완 순서를 확인하세요.`,
      stats: [{ label: "통제", value: weak[3], tone: "warn" }],
      body: weak[4] || text,
    };
  }

  const cascade = text.match(/^연쇄 리스크 경로:\s*(.+?)\s*[—\-]\s*(.*)$/);
  if (cascade) {
    const path = cascade[1].split(/\s*→\s*/).map((part) => part.trim()).filter(Boolean);
    return {
      title,
      kind: "cascade",
      path,
      headline: path.length > 1 ? `${path[0]} → ${path[path.length - 1]}` : cascade[1],
      question: "이 통제 간 연쇄 위험을 실제 대응 범위에 포함할까요?",
      explanation: "앞 단계의 미흡이 뒤 통제의 운영·심사 위험으로 이어지는 경로입니다. 연결 관계가 실제 환경과 맞는지 확인하세요.",
      body: cascade[2] || text,
    };
  }

  const overlap = text.match(/^다중 갭 겹침:\s*'([^']+)'\s*[—\-]\s*(.+?)\.\s*(.*)$/);
  if (overlap) {
    const ids = [...overlap[2].matchAll(/\b\d+(?:\.\d+){1,3}\b/g)].map((match) => match[0]);
    return {
      title,
      kind: "overlap",
      headline: overlap[1],
      chips: ids,
      question: "동시에 미흡한 통제를 하나의 보완 과제로 묶을까요?",
      explanation: "개별 조치보다 공통 원인과 증적을 함께 정비할 때 효율적인 복합 갭 후보입니다.",
      body: `${overlap[2]}. ${overlap[3]}`.trim(),
    };
  }

  const priority = text.match(/^최우선 점검 통제:\s*(\d+(?:\.\d+){1,3})\s+(.+)$/);
  if (priority) {
    const detail = priority[2].trim();
    const withBadge = detail.match(/^(.+)\(([^()]*)\)\.\s*(.*)$/);
    const withoutBadge = detail.match(/^(.+?)\.\s+(.*)$/);
    const headline = (withBadge?.[1] || withoutBadge?.[1] || detail).trim();
    const badge = withBadge?.[2]?.trim() || "";
    const body = (withBadge?.[3] || withoutBadge?.[2] || "").trim();
    return {
      title,
      kind: "priority",
      chips: [priority[1]],
      headline,
      badge,
      question: `${priority[1]} 통제를 최우선 점검 대상으로 확인할까요?`,
      explanation: "위험도와 연결 영향을 기준으로 먼저 확인할 통제입니다. 담당자·정책·증적 상태를 우선 점검하세요.",
      body,
    };
  }

  return {
    title,
    kind: "generic",
    headline: text.length > 72 ? `${text.slice(0, 70)}…` : text,
    question: "이 인사이트를 현재 확인 목록에 반영할까요?",
    explanation: "분석 결과가 실제 조직 상황과 맞는지 검토한 뒤 처리하세요.",
    body: text,
  };
}

const DEFAULT_OVERALL_SCORE_TOOLTIP = [
  "전체 진행 참고는 적용 통제 전체를 본 참고 구간입니다.",
  "· 아직 안 본 통제도 미흡 쪽으로 반영합니다",
  "· 표시: 양호 · 보통 · 보완 필요 · 기초 보완 필요",
  "· 인증 배점·신뢰도가 아닌 점검 진행 참고용입니다",
].join("\n");

const DEFAULT_ASSESSED_SCORE_TOOLTIP = [
  "점검분 이행 참고는 이미 점검한 통제만 본 참고 구간입니다.",
  "· 미점검은 빼고 봅니다",
  "· 표시: 양호 · 보통 · 보완 필요 · 기초 보완 필요",
  "· 인증 배점·신뢰도가 아닌 이행 수준 참고용입니다",
].join("\n");

/** 이전 분석 스냅샷/AI 리포트에 남은 옛 점수 이름을 새 표기로 치환 */
export { remapScoreTerminology, qualitativeLabelFromPercent } from "./utils.js";

function normalizeScoreLabel(label) {
  const raw = String(label || "");
  if (
    raw.includes("내부 참고")
    || raw.includes("전체 진행 반영")
    || raw === "전체 진행 참고"
    || raw === "전체 진행 반영 점수"
  ) {
    return "전체 진행 참고";
  }
  if (
    raw.includes("평가분")
    || raw.includes("점검분만")
    || raw.includes("점검분 이행")
    || raw === "점검분 이행 참고"
    || raw === "점검분만 이행 점수"
  ) {
    return "점검분 이행 참고";
  }
  return remapScoreTerminology(raw);
}

function resolveStatTooltip(stat, analysis) {
  const rawLabel = String(stat?.label || "");
  const label = normalizeScoreLabel(rawLabel);
  if (
    label === "전체 진행 참고"
    || rawLabel.includes("내부 참고")
    || rawLabel.includes("전체 진행")
  ) {
    return remapScoreTerminology(
      String(analysis?.overallScoreTooltip || DEFAULT_OVERALL_SCORE_TOOLTIP).trim(),
    );
  }
  if (
    label === "점검분 이행 참고"
    || rawLabel.includes("평가분")
    || rawLabel.includes("점검분")
  ) {
    return remapScoreTerminology(
      String(analysis?.assessedScoreTooltip || DEFAULT_ASSESSED_SCORE_TOOLTIP).trim(),
    );
  }
  return remapScoreTerminology(String(stat?.tooltip || "").trim());
}

function modernizeReviewCard(item = {}, analysis = null) {
  const sourceAnalysis = analysis || reviewCtx?.analysis || state.analysis;
  const scoreLabels = new Set(["전체 진행 참고", "점검분 이행 참고"]);
  const stats = Array.isArray(item.stats)
    ? item.stats.map((stat) => {
      const label = normalizeScoreLabel(stat?.label);
      let value = stat?.value;
      if (scoreLabels.has(label)) {
        const raw = String(value ?? "");
        const pct = raw.match(/([\d.]+)\s*%/);
        value = pct ? qualitativeLabelFromPercent(pct[1]) : remapScoreTerminology(raw);
      }
      return {
        ...stat,
        label,
        value,
        tooltip: resolveStatTooltip({ ...stat, label }, sourceAnalysis),
      };
    })
    : item.stats;
  const basis = Array.isArray(item.basis)
    ? item.basis.map((line) => remapScoreTerminology(line))
    : item.basis;
  let metric = item.metric;
  let metricUnit = item.metricUnit;
  const metricLabel = remapScoreTerminology(item.metricLabel);
  if (
    metricLabel === "점검분 이행 참고"
    || metricLabel === "전체 진행 참고"
    || String(item.metricUnit || "") === "%"
  ) {
    const asNumber = Number(metric);
    if (Number.isFinite(asNumber) && (metricLabel.includes("참고") || metricLabel.includes("점수"))) {
      metric = qualitativeLabelFromPercent(asNumber);
      metricUnit = "";
    }
  }
  return {
    ...item,
    title: remapScoreTerminology(item.title),
    headline: remapScoreTerminology(item.headline),
    explanation: remapScoreTerminology(item.explanation),
    question: remapScoreTerminology(item.question),
    metricLabel,
    metric,
    metricUnit,
    body: remapScoreTerminology(item.body),
    nextAction: remapScoreTerminology(item.nextAction),
    stats,
    basis,
  };
}

function renderStatTiles(stats = []) {
  if (!stats.length) return "";
  const analysis = reviewCtx?.analysis || state.analysis;
  return `
    <div class="report-review-stat-pills" aria-label="핵심 수치">
      ${stats.map((stat, index) => {
        const label = normalizeScoreLabel(stat.label);
        const tip = resolveStatTooltip({ ...stat, label }, analysis);
        const tipId = `review-stat-tip-${index}-${stableId(label)}`;
        const tipHtml = tip
          ? `
            <button
              type="button"
              class="report-review-pill-help"
              aria-describedby="${tipId}"
              aria-label="${escapeHtml(label)} 계산 방법"
            >?</button>
            <span role="tooltip" id="${tipId}" class="report-review-pill-tooltip">${escapeHtml(tip)}</span>
          `
          : "";
        return `
        <span class="report-review-pill${stat.tone ? ` is-${stat.tone}` : ""}${stat.secondary ? " is-secondary" : ""}${tip ? " has-tooltip" : ""}">
          <em>${escapeHtml(label)}</em>
          <strong>${escapeHtml(String(stat.value))}</strong>
          ${tipHtml}
        </span>
      `;
      }).join("")}
    </div>
  `;
}

function renderCoverage(percent) {
  if (!Number.isFinite(Number(percent))) return "";
  const value = Math.max(0, Math.min(100, Number(percent)));
  return `
    <div class="report-review-coverage" aria-label="분야 점검 완료율 ${value}%">
      <span>분야 점검 완료율 <strong>${escapeHtml(String(value))}%</strong></span>
      <div class="report-review-coverage-track" role="progressbar" aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="100">
        <i style="width:${value}%"></i>
      </div>
    </div>
  `;
}

function renderEvidenceSection(innerHtml, label = "근거 데이터") {
  return `
    <section class="report-review-evidence" aria-label="${escapeHtml(label)}">
      <span class="report-review-evidence-label">${escapeHtml(label)}</span>
      ${innerHtml}
    </section>
  `;
}

function renderPath(path = [], pathNodes = [], relationLabel = "") {
  if (pathNodes.length) {
    return `
      <div class="report-review-path-map" aria-label="통제 영향 관계">
        ${pathNodes.map((node, index) => `
          ${index ? `
            <div class="report-review-path-connector" aria-label="${escapeHtml(relationLabel || "영향 연결")}">
              <span>${escapeHtml(relationLabel || "영향 연결")}</span>
              <i aria-hidden="true"></i>
            </div>
          ` : ""}
          <button
            type="button"
            class="report-review-path-card"
            data-review-open-control="${escapeHtml(node.controlId || "")}"
            aria-label="${escapeHtml(`${node.controlId || ""} ${node.title || ""} 지금 진단에서 열기`)}"
          >
            <span class="report-review-path-role">${escapeHtml(node.role || "관련 통제")}</span>
            <strong>${escapeHtml(node.title || node.controlId || "")}</strong>
            <div class="report-review-path-meta">
              <code>${escapeHtml(node.controlId || "")}</code>
              <span class="report-review-node-status is-${escapeHtml(node.level || "unknown")}">
                ${escapeHtml(node.levelLabel || "미점검")}
              </span>
            </div>
          </button>
        `).join("")}
      </div>
    `;
  }
  if (!path.length) return "";
  return `
    <div class="report-review-path" aria-label="연쇄 경로">
      ${path.map((node, index) => `
        ${index ? '<span class="report-review-path-sep" aria-hidden="true"></span>' : ""}
        <span class="report-review-path-node">${escapeHtml(node)}</span>
      `).join("")}
    </div>
  `;
}

function resolveControlMeta(controlId, fallback = {}) {
  const id = String(controlId || "").trim();
  const control = (state.checklist || []).find((row) => row.id === id)
    || (state.allControls || []).find((row) => row.id === id);
  const gap = (state.analysis?.topGaps || state.analysis?.criticalGaps || [])
    .find((item) => item.controlId === id);
  const live = liveControlLevel(id, fallback.level || gap?.level || "unknown");
  const rawTitle = String(
    fallback.title
    || control?.title
    || gap?.title
    || findControlTitle(id)
    || "",
  ).trim();
  const title = rawTitle && rawTitle !== id ? rawTitle : (rawTitle || id);
  const areaName = String(
    control?.areaName
    || fallback.areaName
    || gap?.areaName
    || AREA_SHORT[id.split(".")[0]]
    || "",
  ).trim();
  const categoryName = String(
    control?.categoryName
    || fallback.categoryName
    || gap?.categoryName
    || "",
  ).trim();
  const tip = String(
    fallback.tip
    || gap?.detailNarrativeTip
    || gap?.organicAnalysis
    || gap?.problem
    || "",
  ).replace(/\s+/g, " ").trim();
  return {
    controlId: id,
    title,
    role: String(fallback.role || "").trim(),
    areaName,
    categoryName,
    tip: tip.length > 96 ? `${tip.slice(0, 94)}…` : tip,
    level: live,
    levelLabel: LEVEL_LABEL[live] || fallback.levelLabel || gap?.levelLabel || live,
  };
}

function relatedControlNodes(card = {}) {
  const nodes = [];
  const seen = new Set();
  const push = (node) => {
    const id = String(node?.controlId || node || "").trim();
    if (!id || seen.has(id)) return;
    seen.add(id);
    nodes.push(resolveControlMeta(id, typeof node === "object" ? node : {}));
  };
  [...(card.controlNodes || []), ...(card.pathNodes || [])].forEach(push);
  (card.chips || []).forEach((chip) => push({ controlId: chip }));
  if (!nodes.length && card.action?.controlId) {
    push({ controlId: card.action.controlId });
  }
  return nodes;
}

function renderRelatedOpenList(nodes = []) {
  if (!nodes.length) return `<p class="detail-empty">연결할 통제가 없습니다.</p>`;
  return `
    <div class="report-review-related-list" aria-label="지금 진단에서 열 통제">
      ${nodes.map((node) => {
        const context = [node.areaName, node.categoryName].filter(Boolean).join(" / ");
        return `
        <div class="report-review-related-row level-${escapeHtml(node.level)}" data-review-open-control="${escapeHtml(node.controlId)}">
          <div class="report-review-related-main">
            <div class="report-review-related-title">
              <code>${escapeHtml(node.controlId)}</code>
              <strong>${escapeHtml(node.title)}</strong>
              ${levelBadge(node.level, node.levelLabel)}
            </div>
            ${context ? `<span class="report-review-related-meta">${escapeHtml(context)}</span>` : ""}
            ${node.tip ? `<span class="report-review-related-tip">${escapeHtml(node.tip)}</span>` : ""}
            ${node.role && node.role !== context ? `<span class="report-review-related-role">${escapeHtml(node.role)}</span>` : ""}
          </div>
          <button type="button" class="report-review-open-btn" data-review-open-control="${escapeHtml(node.controlId)}">
            지금 진단에서 열기
          </button>
        </div>
      `;
      }).join("")}
    </div>
  `;
}

function renderControlNodes(nodes = []) {
  if (!nodes.length) return "";
  return `
    <div class="report-review-control-list" aria-label="관련 통제 목록">
      ${nodes.map((raw) => {
        const node = resolveControlMeta(raw.controlId, raw);
        return `
        <div class="report-review-control-row level-${escapeHtml(node.level)}">
          <code>${escapeHtml(node.controlId || "")}</code>
          <div class="report-review-control-copy">
            <strong>${escapeHtml(node.title)}</strong>
            ${node.tip ? `<span>${escapeHtml(node.tip)}</span>` : ""}
          </div>
          <span class="report-review-node-status is-${escapeHtml(node.level)}">${escapeHtml(node.levelLabel)}</span>
        </div>
      `;
      }).join("")}
    </div>
  `;
}

function renderChips(chips = []) {
  if (!chips.length) return "";
  return `
    <div class="report-review-chips">
      ${chips.map((chip) => `<span class="report-review-chip">${escapeHtml(chip)}</span>`).join("")}
    </div>
  `;
}

function renderGuidance(card) {
  const basis = Array.isArray(card.basis) ? card.basis.filter(Boolean) : [];
  const classification = {
    fact: "입력 사실",
    verified_finding: "확인된 판정",
    hypothesis: "확인 전 분석",
    action_required: "추가 진단 필요",
  }[card.classification] || "분석 참고";
  return `
    <aside class="report-review-guidance">
      <div class="report-review-trust-row">
        <span class="report-review-guidance-label">${escapeHtml(classification)}</span>
        <span class="report-review-confidence is-${escapeHtml(card.confidenceLevel || "medium")}">
          ${escapeHtml(card.confidenceLabel || "근거 확인 필요")}
        </span>
      </div>
      <strong>${escapeHtml(card.question || "이 분석 결과를 확인했나요?")}</strong>
      <p>${escapeHtml(card.explanation || "실제 조직 상황과 분석 결과가 일치하는지 확인하세요.")}</p>
      ${basis.length ? `
        <div class="report-review-basis">
          <span>판단 근거</span>
          <ul>${basis.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      ` : ""}
    </aside>
  `;
}

function renderActiveCardBody(card) {
  const bodyHtml = card.body
    ? `<p class="report-review-body">${escapeHtml(card.body)}</p>`
    : "";

  if (["readiness", "coverage", "finding", "unreviewed", "weak"].includes(card.kind)) {
    const evidence = `
      <div class="report-review-hero">
        <div class="report-review-metric-block">
          <span class="report-review-metric-label">${escapeHtml(card.metricLabel || card.title)}</span>
          <strong class="report-review-metric-value">
            ${escapeHtml(String(card.metric ?? ""))}<small>${escapeHtml(card.metricUnit || "")}</small>
          </strong>
          ${card.kind === "weak" ? '<span class="report-review-metric-hint">분야 점검 진행</span>' : ""}
        </div>
        <div class="report-review-hero-copy">
          <span>${escapeHtml(card.kind === "weak" ? "취약 분야" : "분석 대상")}</span>
          <p class="report-review-headline">${escapeHtml(card.headline || "")}</p>
          ${bodyHtml}
        </div>
      </div>
      ${card.kind === "weak" ? renderCoverage(card.coveragePercent) : ""}
      ${renderStatTiles(card.stats)}
    `;
    return `
      <div class="report-review-main report-review-main--decide">
        ${renderGuidance(card)}
        ${renderEvidenceSection(evidence)}
      </div>
    `;
  }

  if (card.kind === "cascade") {
    const evidence = `
      <span class="report-review-route-label">${escapeHtml(card.routeLabel || "통제 간 영향 경로")}</span>
      ${renderPath(card.path, card.pathNodes, card.relationLabel)}
      <div class="report-review-cascade-summary">
        <span>이 관계의 의미</span>
        <strong>${escapeHtml(card.headline || "")}</strong>
        ${card.nextAction ? `<p><b>다음 행동</b>${escapeHtml(card.nextAction)}</p>` : ""}
      </div>
      ${bodyHtml}
    `;
    return `
      <div class="report-review-main report-review-main--decide">
        ${renderGuidance(card)}
        ${renderEvidenceSection(evidence, "연결 근거")}
      </div>
    `;
  }

  if (card.kind === "overlap") {
    const evidence = `
      <p class="report-review-headline">${escapeHtml(card.headline || "")}</p>
      ${renderStatTiles(card.stats)}
      ${renderControlNodes(card.controlNodes)}
      ${bodyHtml}
    `;
    return `
      <div class="report-review-main report-review-main--decide">
        ${renderGuidance(card)}
        ${renderEvidenceSection(evidence, "관련 통제")}
      </div>
    `;
  }

  if (card.kind === "priority") {
    const evidence = `
      <p class="report-review-headline">
        ${escapeHtml(card.headline || "")}
        ${card.badge ? `<span class="report-review-inline-badge">${escapeHtml(card.badge)}</span>` : ""}
      </p>
      ${renderChips(card.chips)}
      ${bodyHtml}
    `;
    return `
      <div class="report-review-main report-review-main--decide">
        ${renderGuidance(card)}
        ${renderEvidenceSection(evidence)}
      </div>
    `;
  }

  return `
    <div class="report-review-main report-review-main--decide">
      ${renderGuidance(card)}
      ${renderEvidenceSection(bodyHtml || `<p class="report-review-body">${escapeHtml(card.headline || "")}</p>`)}
    </div>
  `;
}

export function buildReportReviewItems(analysis) {
  const hasStructuredItems = Object.prototype.hasOwnProperty.call(analysis || {}, "reviewItems");
  if (hasStructuredItems && Array.isArray(analysis?.reviewItems)) {
    return analysis.reviewItems.map((item, index) => {
      const id = normalizeText(item?.id) || `structured-${index}`;
      const card = modernizeReviewCard({
        ...item,
        title: normalizeText(item?.title) || "확인 항목",
        kind: normalizeText(item?.kind) || "generic",
        headline: normalizeText(item?.headline),
        explanation: normalizeText(item?.explanation),
        question: normalizeText(item?.question),
      }, analysis);
      return {
        id: stableId(id),
        title: card.title,
        text: card.headline,
        card,
      };
    });
  }

  const card = {
    title: "분석 데이터 갱신 필요",
    kind: "compatibility",
    classification: "action_required",
    headline: "실행 중인 서버가 최신 확인 목록 형식을 제공하지 않습니다.",
    question: "서버를 최신 코드로 재시작한 뒤 확인 목록을 다시 만들까요?",
    explanation: "구형 문장 분석은 잘못된 갭 수와 카드 제목을 만들 수 있어 표시하지 않았습니다.",
    basis: ["필수 응답 필드 reviewItems 누락", "구형 서버와 최신 프론트엔드의 버전 불일치"],
    confidenceLevel: "high",
    confidenceLabel: "버전 불일치",
    body: "",
  };
  return [{
    id: stableId("analysis-contract-mismatch"),
    title: card.title,
    text: card.headline,
    card,
  }];
}

export function reviewFingerprint(analysis, items) {
  const readiness = Number(analysis?.overallReadiness);
  const basis = [
    Number.isFinite(readiness) ? readiness.toFixed(1) : "na",
    Number(analysis?.gapCount) || 0,
    ...items.map((item) => `${item.id}:${stableId(JSON.stringify(item.card || {}))}`),
  ].join("|");
  return `report-${stableId(basis)}`;
}

function reviewState(fingerprint) {
  if (!state.reportReview[fingerprint]) {
    state.reportReview[fingerprint] = { confirmed: [], ignored: [] };
  }
  return state.reportReview[fingerprint];
}

let reviewCtx = null;

function persistDecision(fingerprint, itemId, decision) {
  const current = reviewState(fingerprint);
  current.confirmed = current.confirmed.filter((id) => id !== itemId);
  current.ignored = current.ignored.filter((id) => id !== itemId);
  current[decision].push(itemId);

  const fingerprints = Object.keys(state.reportReview);
  fingerprints.slice(0, Math.max(0, fingerprints.length - 8)).forEach((key) => {
    delete state.reportReview[key];
  });
}

function openControlFromReview(controlId) {
  const ctx = reviewCtx;
  if (!controlId || !ctx) return;
  const card = ctx.active?.card || {};
  const node = relatedControlNodes(card).find((item) => item.controlId === controlId);
  state.reportReturn = {
    itemId: ctx.active?.id || "",
    itemTitle: card.title || ctx.active?.title || "확인 항목",
    controlId,
    controlTitle: node?.title || "",
  };
  const content = el("analyzeContent");
  if (content) content.style.display = "";
  // 확인 목록 리포트는 유지하고, 지금 진단 카드 높이로만 이동
  switchAnalyzeSection("actions");
  renderReportReturnBar();
  navigateToControl(controlId);
  showToast(`${controlId} 지금 진단으로 이동했습니다.`);
}

function ensureReviewDelegation(container) {
  if (container.dataset.reviewBound === "1") return;
  container.dataset.reviewBound = "1";

  const closeScoreTips = (except = null) => {
    container.querySelectorAll(".report-review-pill.is-tip-open").forEach((pill) => {
      if (except && pill === except) return;
      pill.classList.remove("is-tip-open");
    });
  };

  container.addEventListener("pointerover", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const pill = target.closest(".report-review-pill.has-tooltip");
    if (!pill || !container.contains(pill)) return;
    if (pill.classList.contains("is-tip-open")) return;
    closeScoreTips(pill);
    pill.classList.add("is-tip-open");
  });

  container.addEventListener("pointerout", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const pill = target.closest(".report-review-pill.has-tooltip");
    if (!pill || !container.contains(pill)) return;
    const related = event.relatedTarget instanceof Element ? event.relatedTarget : null;
    if (related && pill.contains(related)) return;
    pill.classList.remove("is-tip-open");
  });

  container.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const jumpActions = target.closest("[data-jump-actions]");
    if (jumpActions && container.contains(jumpActions)) {
      const content = el("analyzeContent");
      if (content) content.style.display = "";
      switchAnalyzeSection("actions");
      el("sessionMasterDetail")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const ctx = reviewCtx;
    if (!ctx) return;

    if (target.closest(".report-review-pill-help")) {
      event.preventDefault();
      event.stopPropagation();
      const pill = target.closest(".report-review-pill.has-tooltip");
      if (pill) {
        const open = !pill.classList.contains("is-tip-open");
        closeScoreTips(open ? pill : null);
        pill.classList.toggle("is-tip-open", open);
      }
      return;
    }

    closeScoreTips();

    const relatedToggle = target.closest("[data-review-related-toggle]");
    if (relatedToggle && container.contains(relatedToggle)) {
      event.preventDefault();
      event.stopPropagation();
      const card = relatedToggle.closest("[data-review-item-id]");
      const panel = card?.querySelector("[data-review-related-panel]");
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      relatedToggle.setAttribute("aria-expanded", open ? "true" : "false");
      relatedToggle.textContent = open ? "관련 통제 접기" : "관련 통제 펼치기";
      if (open) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    const openControl = target.closest("[data-review-open-control]");
    if (openControl && container.contains(openControl)) {
      event.preventDefault();
      event.stopPropagation();
      openControlFromReview(openControl.dataset.reviewOpenControl || "");
      return;
    }

    const decisionBtn = target.closest("[data-review-decision]");
    if (decisionBtn && container.contains(decisionBtn) && ctx.active?.id) {
      persistDecision(ctx.fingerprint, ctx.active.id, decisionBtn.dataset.reviewDecision);
      renderReportReview(ctx.analysis);
      return;
    }

    const restoreBtn = target.closest("[data-review-restore]");
    if (restoreBtn && container.contains(restoreBtn)) {
      ctx.current.ignored = [];
      renderReportReview(ctx.analysis);
      return;
    }

    const resetBtn = target.closest("[data-review-reset]");
    if (resetBtn && container.contains(resetBtn)) {
      ctx.current.confirmed = [];
      ctx.current.ignored = [];
      renderReportReview(ctx.analysis);
      return;
    }

  });
}

function renderNoFindingsOverview(analysis) {
  const applicable = Math.max(0, Number(analysis?.applicableControlCount) || 0);
  const reviewed = Math.max(0, Number(analysis?.reviewedControlCount) || 0);
  const unreviewed = Math.max(0, Number(analysis?.unreviewedControlCount) || Math.max(0, applicable - reviewed));
  const completion = applicable ? Math.round((reviewed / applicable) * 100) : 0;
  const status = analysis?.statusCounts || {};
  const implemented = Math.max(0, Number(status.done) || 0) + Math.max(0, Number(status.evidenced) || 0);
  const nextCategories = (Array.isArray(analysis?.categoryCoverage) ? analysis.categoryCoverage : [])
    .map((category) => ({
      name: normalizeText(category?.category) || "미점검 분야",
      remaining: Math.max(0, (Number(category?.totalCount) || 0) - (Number(category?.reviewedCount) || 0)),
    }))
    .filter((category) => category.remaining > 0)
    .sort((a, b) => b.remaining - a.remaining)
    .slice(0, 3);
  const categoryMarkup = nextCategories.length
    ? nextCategories.map((category) => `<li><span>${escapeHtml(category.name)}</span><strong>${category.remaining}개 남음</strong></li>`).join("")
    : `<li><span>남은 통제</span><strong>${unreviewed}개</strong></li>`;

  return `<article class="report-review-empty report-review-empty--overview" role="status">
    <header class="report-review-empty-head">
      <div><span>진단 진행 현황</span><strong>${reviewed} / ${applicable}개 점검 완료</strong></div>
      <em>${completion}%</em>
    </header>
    <div class="report-review-empty-track" aria-label="진단 진행률 ${completion}%"><i style="width:${completion}%"></i></div>
    <div class="report-review-empty-sections">
      <section>
        <span>현재 확인 결과</span>
        <strong>점검한 ${reviewed}개에서 확인된 미흡 없음</strong>
        <p>이행으로 기록된 통제는 ${implemented}개입니다. 이 결과는 전체가 아니라 현재까지 점검한 범위에 한정됩니다.</p>
      </section>
      <section>
        <span>다음 검토 대상</span>
        <ul>${categoryMarkup}</ul>
        <p>미점검 ${unreviewed}개는 아직 판단되지 않았으며 취약점으로 집계하지 않습니다.</p>
      </section>
    </div>
    <footer>
      <p>진단을 이어가면 확인된 미이행·부분 이행과 참고용 연계 분석이 이곳에 추가됩니다.</p>
      <button type="button" class="primary" data-jump-actions>자가진단 이어가기</button>
    </footer>
  </article>`;
}

function ensureReviewShell(container) {
  if (container.dataset.shell === "active") {
    return {
      step: container.querySelector("[data-review-step]"),
      label: container.querySelector("[data-review-label]"),
      track: container.querySelector("[data-review-track-fill]"),
      host: container.querySelector("[data-review-card-host]"),
    };
  }
  container.dataset.shell = "active";
  container.innerHTML = `
    <div class="report-review-progress" aria-label="확인 목록 검토 진행">
      <div class="report-review-progress-meta">
        <span class="report-review-step" data-review-step></span>
        <span class="report-review-progress-label" data-review-label></span>
      </div>
      <div class="report-review-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-label="검토 완료율">
        <i data-review-track-fill></i>
      </div>
    </div>
    <div class="report-review-card-host" data-review-card-host></div>
  `;
  return {
    step: container.querySelector("[data-review-step]"),
    label: container.querySelector("[data-review-label]"),
    track: container.querySelector("[data-review-track-fill]"),
    host: container.querySelector("[data-review-card-host]"),
  };
}

function renderCardMarkup(card, active, pendingCount) {
  const related = relatedControlNodes(card);
  return `
    <article class="report-review-card is-${escapeHtml(card.kind)}" data-review-item-id="${escapeHtml(active.id)}">
      <header class="report-review-card-head">
        <span class="report-review-kicker">${escapeHtml(card.title)}</span>
        <div class="report-review-head-actions">
          <span class="report-review-remain">남은 ${pendingCount}건</span>
        </div>
      </header>
      ${renderActiveCardBody(card)}
      <footer class="report-review-card-footer">
        <p class="report-review-hint" title="이 확인은 참고 항목의 읽음 상태만 기록합니다. 실제 판정은 통제 점검에서 변경하세요.">
          참고 분석의 읽음 상태만 기록합니다. 실제 판정은 통제 점검에서 변경하세요.
        </p>
        <div class="report-review-actions">
          <button type="button" class="ghost" data-review-decision="ignored">이 참고 항목 숨기기</button>
          ${related.length
            ? `<button type="button" data-review-related-toggle aria-expanded="false">관련 통제 펼치기</button>`
            : ""}
          <button type="button" class="primary" data-review-decision="confirmed">확인 완료</button>
        </div>
        ${related.length ? `
          <div class="report-review-related" data-review-related-panel hidden>
            <div class="report-review-related-head">
              <h4>관련 통제 ${related.length}개</h4>
              <p>점검할 통제를 고르면 「지금 진단」으로 이동합니다. 확인 목록으로 언제든 돌아올 수 있습니다.</p>
            </div>
            ${renderRelatedOpenList(related)}
          </div>
        ` : ""}
      </footer>
    </article>
  `;
}

export function renderReportReview(analysis) {
  const container = el("reportReviewQueue");
  if (!container) return;
  ensureReviewDelegation(container);

  const items = buildReportReviewItems(analysis);
  if (!items.length) {
    container.dataset.shell = "empty";
    reviewCtx = null;
    container.innerHTML = renderNoFindingsOverview(analysis);
    return;
  }

  const fingerprint = reviewFingerprint(analysis, items);
  const current = reviewState(fingerprint);
  const confirmed = new Set(current.confirmed);
  const ignored = new Set(current.ignored);
  const pending = items.filter((item) => !confirmed.has(item.id) && !ignored.has(item.id));
  const resolvedCount = items.length - pending.length;
  const active = pending[0];
  const pct = items.length ? Math.round((resolvedCount / items.length) * 100) : 0;
  const currentIndex = Math.min(resolvedCount + 1, items.length);

  if (!active) {
    container.dataset.shell = "complete";
    reviewCtx = { analysis, fingerprint, current, active: null };
    container.innerHTML = `
      <div class="report-review-progress" aria-label="확인 목록 검토 진행">
        <div class="report-review-progress-meta">
          <span class="report-review-step">완료 ${items.length}<em> / ${items.length}</em></span>
          <span class="report-review-progress-label">검토 완료 · 완료율 100%</span>
        </div>
        <div class="report-review-track" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" aria-label="검토 완료율">
          <i style="width:100%"></i>
        </div>
      </div>
      <div class="report-review-card-host">
        <article class="report-review-card is-complete" role="status">
          <header class="report-review-card-head">
            <span class="report-review-kicker">검토 완료</span>
            <div class="report-review-head-actions">
              <span class="report-review-remain">남은 0건</span>
            </div>
          </header>
          <div class="report-review-main report-review-main--decide">
            <aside class="report-review-guidance">
              <div class="report-review-trust-row">
                <span class="report-review-guidance-label">입력 사실</span>
                <span class="report-review-confidence is-high">검토 종료</span>
              </div>
              <strong>확인 목록 검토를 마쳤습니다</strong>
              <p>판정 숫자와 통제 ID는 그대로입니다. 다음 통제 진단으로 이어가세요.</p>
              <div class="report-review-basis">
                <span>검토 결과</span>
                <ul>
                  <li>전체 ${items.length}건</li>
                  <li>내용 확인 ${confirmed.size}건</li>
                  <li>무시 ${ignored.size}건</li>
                </ul>
              </div>
            </aside>
            <section class="report-review-evidence" aria-label="근거 데이터">
              <span class="report-review-evidence-label">근거 데이터</span>
              <div class="report-review-stat-pills" aria-label="핵심 수치">
                <span class="report-review-pill">
                  <em>전체</em><strong>${items.length}</strong>
                </span>
                <span class="report-review-pill is-ok">
                  <em>내용 확인</em><strong>${confirmed.size}</strong>
                </span>
                <span class="report-review-pill${ignored.size ? " is-warn" : ""}">
                  <em>무시</em><strong>${ignored.size}</strong>
                </span>
              </div>
              <p class="report-review-headline">확인 목록 검토는 읽음 기록입니다. 실제 보완은 지금 진단에서 이어가세요.</p>
            </section>
          </div>
          <footer class="report-review-card-footer">
            <p class="report-review-hint">내용 확인은 읽음 기록만 남깁니다. 판정 변경은 통제 점검에서 하세요.</p>
            <div class="report-review-actions">
              ${ignored.size
                ? '<button type="button" class="ghost" data-review-restore>무시한 항목 다시 보기</button>'
                : '<button type="button" class="ghost" data-review-reset>처음부터 다시 검토</button>'}
              <button type="button" class="primary" data-jump-actions>지금 진단으로 이동</button>
            </div>
          </footer>
        </article>
      </div>
    `;
    return;
  }

  const card = modernizeReviewCard(active.card || parseInsightCard(active.text), analysis);
  // 카드 렌더 전에 컨텍스트를 두어 점수 툴팁 보강이 analysis를 참조할 수 있게 한다.
  reviewCtx = { analysis, fingerprint, current, active: { ...active, card } };

  const shell = ensureReviewShell(container);
  if (shell.step) shell.step.innerHTML = `완료 ${resolvedCount}<em> / ${items.length}</em>`;
  if (shell.label) shell.label.textContent = `지금 ${currentIndex}번째 · 완료율 ${pct}%`;
  if (shell.track) {
    const track = shell.track.parentElement;
    if (track) track.setAttribute("aria-valuenow", String(pct));
    shell.track.style.width = `${pct}%`;
  }

  if (shell.host) {
    const relatedOpen = !!shell.host.querySelector("[data-review-related-panel]:not([hidden])");
    shell.host.innerHTML = renderCardMarkup(card, active, pending.length);
    if (relatedOpen) {
      const panel = shell.host.querySelector("[data-review-related-panel]");
      const toggle = shell.host.querySelector("[data-review-related-toggle]");
      if (panel) panel.hidden = false;
      if (toggle) {
        toggle.setAttribute("aria-expanded", "true");
        toggle.textContent = "관련 통제 접기";
      }
    }
  }
}
