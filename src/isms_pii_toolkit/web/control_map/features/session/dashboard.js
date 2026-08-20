import { AREA_SHORT, LEVEL_LABEL } from "../../core/constants.js";

const SEVERITY_LABEL = {
  critical: "심각도 매우 높음",
  high: "심각도 높음",
  medium: "심각도 보통",
};

const TEMPERATURE_BANDS = [
  { min: 80, key: "ready", label: "준비 완료", hint: "핵심 영역이 준비 완료 구간에 들어왔습니다." },
  { min: 55, key: "rising", label: "안정화", hint: "핵심 영역이 안정화되고 있습니다. 남은 보완 항목을 이어서 확인하세요." },
  { min: 25, key: "warming", label: "점검 중", hint: "진단이 진행 중입니다. 다음 통제를 점검하면 온도가 올라갑니다." },
  { min: 0, key: "cold", label: "초기 단계", hint: "아직 점검 초반입니다. 미점검 통제부터 이어서 확인하세요." },
];

function evidenceStats(controlEvidence = {}) {
  const rows = Object.values(controlEvidence).filter(Array.isArray);
  return {
    itemCount: rows.reduce((sum, items) => sum + items.length, 0),
    controlCount: rows.filter((items) => items.length > 0).length,
  };
}

function levelWeight(level) {
  if (level === "done" || level === "evidenced") return 1;
  if (level === "partial") return 0.5;
  return 0;
}

export function clampTemperature(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, Math.round(n)));
}

export function readinessTemperature({ done = 0, partial = 0, applicable = 0 } = {}) {
  if (applicable <= 0) return 0;
  return clampTemperature(((Number(done) + Number(partial) * 0.5) / applicable) * 100);
}

export function assessmentSummary({ done = 0, partial = 0, none = 0, applicable = 0 } = {}) {
  const reviewed = Math.max(0, Number(done) + Number(partial) + Number(none));
  const total = Math.max(0, Number(applicable));
  const coverage = total ? clampTemperature((reviewed / total) * 100) : 0;
  const confirmedReadiness = reviewed
    ? clampTemperature(((Number(done) + Number(partial) * 0.5) / reviewed) * 100)
    : null;

  return {
    reviewed,
    total,
    coverage,
    confirmedReadiness,
    confidence: coverage >= 80 ? "high" : coverage >= 40 ? "medium" : "low",
  };
}

export function temperatureBand(value) {
  const temperature = clampTemperature(value);
  return TEMPERATURE_BANDS.find((band) => temperature >= band.min) || TEMPERATURE_BANDS.at(-1);
}

export function areaReadiness(groups = [], getLevel = () => "unknown") {
  const byArea = new Map();
  groups.forEach((group) => {
    const areaId = String(group.areaId || group.categoryId?.split(".")[0] || "0");
    if (!byArea.has(areaId)) {
      byArea.set(areaId, {
        areaId,
        label: AREA_SHORT[areaId] || group.areaName || `영역 ${areaId}`,
        controls: [],
      });
    }
    byArea.get(areaId).controls.push(...(group.controls || []));
  });

  return Array.from(byArea.values())
    .sort((left, right) => String(left.areaId).localeCompare(String(right.areaId), "en", { numeric: true }))
    .map((area) => {
      const total = area.controls.length;
      const reviewed = area.controls.filter((control) => {
        const level = getLevel(control.id);
        return level !== "unknown" && level !== "na";
      }).length;
      const score = area.controls.reduce((sum, control) => sum + levelWeight(getLevel(control.id)), 0);
      const temperature = total ? clampTemperature((score / total) * 100) : 0;
      const confirmedReadiness = reviewed ? clampTemperature((score / reviewed) * 100) : null;
      const next = area.controls.find((control) => ["unknown", "none", "partial"].includes(getLevel(control.id)));
      return {
        areaId: area.areaId,
        label: area.label,
        temperature,
        confirmedReadiness,
        coverage: total ? clampTemperature((reviewed / total) * 100) : 0,
        band: temperatureBand(temperature),
        reviewed,
        total,
        nextControlId: next?.id || "",
      };
    });
}

export function prioritySelectionReasons(gap = {}) {
  const reasons = [];
  if (gap.scenarioRelevant) reasons.push("선택 시나리오 직접 관련");
  if (gap.level === "none") reasons.push("미이행 우선");
  else if (gap.level === "partial") reasons.push("부분 이행 보완 필요");
  if (SEVERITY_LABEL[gap.severity]) reasons.push(SEVERITY_LABEL[gap.severity]);
  const profileReason = Array.isArray(gap.profileRelevance) ? gap.profileRelevance[0] : "";
  if (profileReason) reasons.push(`조직 조건 반영: ${profileReason}`);
  return reasons.slice(0, 3);
}

export function applyWeakReviewState(targetState, controlId = null, priorityIds = []) {
  const selectedControlId = controlId || priorityIds[0] || null;
  targetState.levelFilter = "weak";
  targetState.sessionSelectedControlId = selectedControlId;
  return selectedControlId;
}

export function buildDashboardViewModel({
  analysis,
  controlEvidence = {},
  weakControlIds = [],
  stale = false,
  groups = [],
  getLevel = () => "unknown",
  nextControls = [],
  done = 0,
  partial = 0,
  applicable = 0,
} = {}) {
  const evidence = evidenceStats(controlEvidence);
  const weakIds = [...new Set(weakControlIds.map(String))];
  const weakEvidenceControlCount = weakIds.filter((controlId) => (
    Array.isArray(controlEvidence[controlId]) && controlEvidence[controlId].length > 0
  )).length;
  const missingEvidenceCount = Math.max(weakIds.length - weakEvidenceControlCount, 0);
  const temperature = readinessTemperature({ done, partial, applicable });
  const summary = assessmentSummary({
    done,
    partial,
    none: weakIds.filter((id) => getLevel(id) === "none").length,
    applicable,
  });
  const band = temperatureBand(temperature);
  const areas = areaReadiness(groups, getLevel);
  const coolest = [...areas].sort((left, right) => left.temperature - right.temperature)[0] || null;
  const priorities = stale ? [] : (analysis?.topGaps || []).slice(0, 3).map((gap, index) => ({
    rank: index + 1,
    controlId: gap.controlId || gap.id || "",
    title: gap.title || gap.controlTitle || "우선 보완 통제",
    risk: gap.riskIfMissing || "미흡 시 영향을 확인하고 보완 계획을 수립하세요.",
    selectionReasons: prioritySelectionReasons(gap),
    mode: "gap",
  }));
  const queue = priorities.length
    ? []
    : nextControls.slice(0, 3).map((control, index) => {
      const level = control.level || getLevel(control.id) || "unknown";
      return {
        rank: index + 1,
        controlId: control.id || control.controlId || "",
        title: control.title || "다음 점검 통제",
        risk: "이 통제를 진단하면 준비 온도가 올라갑니다.",
        selectionReasons: [LEVEL_LABEL[level] || "미점검", "다음 점검 대상"],
        mode: "queue",
        weak: level === "none" || level === "partial",
      };
    });

  return {
    stale,
    temperature,
    band,
    summary,
    areas,
    coolest,
    queueMode: !priorities.length,
    priorities: priorities.length ? priorities : queue,
    evidence,
    signals: [
      {
        label: "증적 미등록",
        value: missingEvidenceCount,
        suffix: "개",
        help: `보완 대상 ${weakIds.length}개 중 ${weakEvidenceControlCount}개 통제에 증적이 등록되어 있습니다.`,
      },
      {
        label: "등록 증적",
        value: evidence.itemCount,
        suffix: "건",
        help: evidence.itemCount
          ? `${evidence.controlCount}개 통제에 증적이 연결되어 있습니다.`
          : "아직 등록된 증적이 없습니다. 판단 근거를 남기면 여기에 모입니다.",
      },
    ],
    categories: stale ? [] : (analysis?.gapClusters || []).slice(0, 4).map((cluster) => ({
      label: cluster.theme || "미흡 통제 묶음",
      gapCount: Number(cluster.gapCount || 0),
      controlId: String(cluster.controlIds?.[0] || cluster.primaryControl?.controlId || ""),
    })),
  };
}
