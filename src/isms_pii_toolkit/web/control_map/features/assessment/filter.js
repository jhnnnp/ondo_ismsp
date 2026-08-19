import { state } from "../../core/state.js";
import { getAssessment } from "./model.js";
import { matchesControlSearch, rankControlsBySearch } from "./search.js";

function matchesSearch(control) {
  return matchesControlSearch(control, state.assessSearch);
}

export function areaNameMap() {
  const names = {};
  state.checklist.forEach((control) => {
    if (!names[control.areaId]) names[control.areaId] = control.areaName;
  });
  return names;
}

export function countForAreaFilter(areaId) {
  return state.checklist.filter((control) => {
    if (areaId !== "all" && control.areaId !== areaId) return false;
    if (!matchesSearch(control)) return false;
    return state.levelFilter === "all" || getAssessment(control.id) === state.levelFilter;
  }).length;
}

export function countByArea() {
  return {
    all: countForAreaFilter("all"),
    1: countForAreaFilter("1"),
    2: countForAreaFilter("2"),
    3: countForAreaFilter("3"),
  };
}

export function baseFilteredChecklist() {
  return state.checklist.filter((control) => {
    if (state.areaFilter !== "all" && control.areaId !== state.areaFilter) return false;
    return matchesSearch(control);
  });
}

export function navChecklist() {
  if (state.areaFilter === "all") return state.checklist;
  return state.checklist.filter((control) => control.areaId === state.areaFilter);
}

export function assessFiltersActive() {
  return state.levelFilter !== "all" || !!state.assessSearch.trim();
}

export function countForLevelFilter(levelId) {
  return state.checklist.filter((control) => {
    if (state.areaFilter !== "all" && control.areaId !== state.areaFilter) return false;
    if (!matchesSearch(control)) return false;
    return levelId === "all" || getAssessment(control.id) === levelId;
  }).length;
}

export function countByLevel() {
  const levels = ["all", "unknown", "none", "partial", "done", "na"];
  return Object.fromEntries(levels.map((levelId) => [levelId, countForLevelFilter(levelId)]));
}

export function filteredChecklist() {
  const items = baseFilteredChecklist();
  const leveled = state.levelFilter === "all"
    ? items
    : items.filter((control) => getAssessment(control.id) === state.levelFilter);
  return rankControlsBySearch(leveled, state.assessSearch);
}

export function reviewedCount() {
  return Object.values(state.assessments).filter(
    (level) => level !== "unknown" && level !== "na"
  ).length;
}

export function applicableControlCount() {
  const total = Object.keys(state.assessments).length || 101;
  const naCount = Object.values(state.assessments).filter((level) => level === "na").length;
  return Math.max(total - naCount, 0);
}
