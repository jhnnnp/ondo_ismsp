import { state } from "../../core/state.js";
import { compareDotId, getAssessment, groupControlsByCategory } from "../assessment/model.js";

export function reviewedAndApplicable() {
  const applicableControls = (state.checklist || []).filter(
    (control) => getAssessment(control.id) !== "na"
  );
  const reviewed = applicableControls.filter((control) => {
    const level = getAssessment(control.id);
    return level !== "unknown" && level !== "na";
  });
  return {
    reviewed: reviewed.length,
    applicable: applicableControls.length,
  };
}

export function applicableControls() {
  return (state.checklist || []).filter((control) => getAssessment(control.id) !== "na");
}

/** 아직 판정하지 않은 통제 (전체 진행의 여집합: applicable - reviewed). */
export function unreviewedControls() {
  return applicableControls().filter((control) => getAssessment(control.id) === "unknown");
}

/** 증적까지 갖춘 이행 통제. */
export function doneControls() {
  return applicableControls().filter((control) => {
    const level = getAssessment(control.id);
    return level === "done" || level === "evidenced";
  });
}

/** 보완·재확인이 필요한 통제 (미판정 + 미이행 + 부분 이행). 작업 큐용. */
export function incompleteControls() {
  const open = new Set(["unknown", "none", "partial"]);
  return applicableControls().filter((control) => open.has(getAssessment(control.id)));
}

export function backlogControls(excludeIds = []) {
  const excluded = new Set(excludeIds);
  const levelOrder = { unknown: 0, none: 1, partial: 2 };
  return incompleteControls()
    .filter((control) => !excluded.has(control.id))
    .sort((left, right) => (
      (levelOrder[getAssessment(left.id)] ?? 9) - (levelOrder[getAssessment(right.id)] ?? 9)
      || String(left.id).localeCompare(String(right.id))
    ));
}

export function sessionCategoryGroups() {
  return groupControlsByCategory(applicableControls());
}

export function nextIncompleteControlId(afterId = null) {
  const open = incompleteControls().sort((a, b) => compareDotId(a.id, b.id));
  if (!open.length) return null;
  if (!afterId) return open[0].id;
  const idx = open.findIndex((control) => control.id === afterId);
  if (idx >= 0 && idx + 1 < open.length) return open[idx + 1].id;
  const afterAll = open.find((control) => compareDotId(control.id, afterId) > 0);
  return afterAll?.id || open[0].id;
}

export function sessionControlIds() {
  return applicableControls()
    .slice()
    .sort((a, b) => compareDotId(a.id, b.id))
    .map((control) => control.id);
}

export function adjacentSessionControlId(currentId, direction = 1) {
  const ids = sessionControlIds();
  if (!ids.length) return null;
  const idx = ids.indexOf(currentId);
  if (idx < 0) return direction > 0 ? ids[0] : ids[ids.length - 1];
  const next = idx + direction;
  if (next < 0 || next >= ids.length) return null;
  return ids[next];
}
