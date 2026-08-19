#!/usr/bin/env python3
"""Rebuild compounds.json from relation_evidence + casebook snippets.

No generic filler templates (탐지/차단/추적…).
Every compound carries evidenceRefs and evidenceGrade.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isms_pii_toolkit.control_graph import (  # noqa: E402
    SCENARIOS,
    find_control,
    load_manual_relations,
    load_relation_evidence,
)

DATA_DIR = ROOT / "src/isms_pii_toolkit/data/problem_kb"
CONTROLS_DIR = DATA_DIR / "controls"
COMPOUNDS_FILE = DATA_DIR / "compounds.json"
INDEX_FILE = DATA_DIR / "index.json"
EVIDENCE_FILE = DATA_DIR / "relation_evidence.json"

FORBIDDEN_TEMPLATES = (
    "단일 결함이 아니라 연결된 업무 흐름 전체의 보호 공백",
    "탐지/차단/추적/통지/복구 중 2개 이상이 동시에 무력화",
)


def _compound_key(control_ids: tuple[str, ...]) -> str:
    return "|".join(sorted(control_ids))


def _case_snippets(control_id: str, limit: int = 2) -> list[str]:
    path = CONTROLS_DIR / f"{control_id.replace('.', '_')}.json"
    if not path.is_file():
        return []
    record = json.loads(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for item in record.get("checklistItems") or []:
        block = item.get("ifUnchecked") or {}
        for problem in block.get("problems") or []:
            text = str(problem).strip()
            if text and text not in out:
                out.append(text)
            if len(out) >= limit:
                return out
    for scenario in record.get("scenarios") or []:
        text = str(scenario).strip()
        if text and text not in out:
            out.append(text[:160])
        if len(out) >= limit:
            break
    return out


def _edge_evidence(source: str, target: str, payload: dict[str, object]) -> dict[str, object] | None:
    for edge in payload.get("edges") or []:
        if str(edge.get("source")) == source and str(edge.get("target")) == target:
            return dict(edge)
        if str(edge.get("source")) == target and str(edge.get("target")) == source:
            return dict(edge)
    return None


def _grade_for_ids(control_ids: list[str], payload: dict[str, object]) -> str:
    strengths: list[str] = []
    for left, right in zip(control_ids, control_ids[1:]):
        edge = _edge_evidence(left, right, payload)
        if edge:
            strengths.append(str(edge.get("strength") or "medium"))
    if "strong" in strengths:
        return "strong"
    if strengths:
        return "medium"
    return "weak"


def _build_compound(
    control_ids: tuple[str, ...],
    reason: str,
    *,
    payload: dict[str, object],
    matched_keys: list[str],
    scenario_note: str | None = None,
) -> dict[str, object] | None:
    ids = tuple(sorted(control_ids))
    if len(ids) < 2:
        return None

    evidence_refs: list[dict[str, object]] = []
    grounding_levels: list[str] = []
    for left, right in zip(ids, ids[1:]):
        edge = _edge_evidence(left, right, payload)
        if not edge:
            edge = _edge_evidence(control_ids[0], control_ids[1], payload) if len(control_ids) >= 2 else None
        if edge:
            gl = str(edge.get("groundingLevel") or "interpret")
            grounding_levels.append(gl)
            for block in edge.get("evidence") or []:
                for ref in block.get("refs") or []:
                    if ref not in evidence_refs:
                        evidence_refs.append(ref)
            evidence_refs.append(
                {
                    "relationKey": f"{edge.get('source')}->{edge.get('target')}",
                    "strength": edge.get("strength"),
                    "groundingLevel": gl,
                    "types": [b.get("type") for b in (edge.get("evidence") or [])],
                }
            )

    grade = _grade_for_ids(list(ids), payload)
    if grade == "weak" and not evidence_refs and not scenario_note:
        return None

    # Prefer strongest grounding among edges
    if "casebook_cite" in grounding_levels:
        primary_grounding = "casebook_cite"
    elif "category_adjacent" in grounding_levels:
        primary_grounding = "category_adjacent"
    else:
        primary_grounding = grounding_levels[0] if grounding_levels else "interpret"

    grounding_note = {
        "casebook_cite": "이 연결은 사례집 텍스트 근거가 있는 유기 연결입니다.",
        "category_adjacent": (
            "이 연결은 인증기준 분류·시나리오상 인접에 기반한 실무상 유기 연결입니다."
        ),
        "interpret": (
            "이 연결은 결함 우선순위·수동 관계를 바탕으로 한 해석형 유기 연결입니다. "
            "(결함 통계는 인과가 아니라 대응 우선순위 weight로만 사용)"
        ),
    }[primary_grounding]

    problems: list[str] = [grounding_note]
    if reason.strip() and reason.strip() not in problems:
        # Tone: connection reason is interpretation built from document fragments.
        problems.append(
            f"연결 근거(요약): {reason.strip()} "
            f"— 문서의 개별 문제 서술을 조합해 유기적 리스크로 재구성한 것입니다."
        )

    ordered = list(control_ids) if len(control_ids) >= 2 else list(ids)
    for left, right in zip(ordered, ordered[1:]):
        left_snips = _case_snippets(left, 1)
        right_snips = _case_snippets(right, 1)
        if left_snips and right_snips:
            l = left_snips[0][:72] + ("…" if len(left_snips[0]) > 72 else "")
            r = right_snips[0][:72] + ("…" if len(right_snips[0]) > 72 else "")
            bridge = (
                f"사례집에서는 {left} 미흡 시 '{l}' 문제를 지적하고, "
                f"{right}에서는 '{r}' 문제를 지적합니다. "
                f"두 통제가 동시에 미흡하면 이 문제들이 한 업무 흐름에서 겹치는 복합 리스크로 재구성됩니다."
            )
            if bridge not in problems:
                problems.append(bridge)

    if scenario_note and scenario_note not in problems:
        problems.append(scenario_note)

    problems = [p for p in problems if not any(t in p for t in FORBIDDEN_TEMPLATES)]
    if len(problems) <= 1:
        titles = " / ".join(ids)
        problems.append(
            f"{titles} 통제의 개별 문서 문제 서술을 조합하면, "
            f"동시 미흡 시 묶음 개선이 필요한 유기적 리스크로 재구성됩니다."
        )

    titles_human = []
    for cid in ids:
        control = find_control(cid)
        title = str(control["title"]) if control else cid
        titles_human.append(f"{cid} {title}")

    remediation = [
        f"{' / '.join(ids)} 통제를 하나의 증적 패키지로 묶어 분기 점검",
        "체크리스트 미충족 항목을 통제별 CAR(시정조치)로 등록",
        "관계 근거 레벨(사례집 인용/분류 인접/해석)에 따라 담당·승인·운영 로그를 연결",
    ]

    scenarios = []
    if scenario_note:
        scenarios.append(scenario_note)
    if primary_grounding == "category_adjacent":
        scenarios.append(
            f"{'/'.join(ids)}은(는) 문서가 복합 결함을 명시한 것이 아니라, "
            f"분류·시나리오상 같이 보는 것이 타당한 연결입니다."
        )
    else:
        scenarios.append(
            f"{'/'.join(ids)} 동시 미흡 시 심사에서 연결성 결함으로 확대 질의가 이어질 수 있습니다."
        )

    return {
        "compoundKey": _compound_key(ids),
        "controlIds": list(ids),
        "title": f"{' / '.join(ids)} 복합 리스크",
        "connectionReason": reason,
        "compoundProblems": problems[:6],
        "compoundScenarios": scenarios[:4],
        "integratedRemediation": remediation,
        "evidenceGrade": grade if evidence_refs else ("medium" if scenario_note else "weak"),
        "groundingLevel": primary_grounding,
        "groundingNote": grounding_note,
        "evidenceRefs": evidence_refs[:12],
        "matchedRelationKeys": matched_keys[:8],
        "controlTitles": titles_human,
    }


def build_compounds() -> list[dict[str, object]]:
    load_relation_evidence.cache_clear()
    load_manual_relations.cache_clear()
    payload = load_relation_evidence()
    if not payload.get("edges"):
        raise SystemExit(f"Missing or empty {EVIDENCE_FILE}; run build_evidence_relations.py first")

    compounds: dict[str, dict[str, object]] = {}
    relations = load_manual_relations()

    for source_id, targets in relations.items():
        for target_id, reason in targets:
            pair = (source_id, target_id)
            key = _compound_key(tuple(sorted(pair)))
            edge = _edge_evidence(source_id, target_id, payload)
            matched = [f"{source_id}->{target_id}"]
            compound = _build_compound(
                pair,
                reason,
                payload=payload,
                matched_keys=matched,
            )
            if compound and (key not in compounds or compound["evidenceGrade"] == "strong"):
                compounds[key] = compound

        # Group: source + all targets (if >=2 targets)
        if len(targets) >= 2:
            group = (source_id, *(t for t, _ in targets))
            reason = " / ".join(r for _, r in targets[:2])
            key = _compound_key(tuple(sorted(group)))
            compound = _build_compound(
                group,
                reason,
                payload=payload,
                matched_keys=[f"{source_id}->{t}" for t, _ in targets],
            )
            if compound:
                compounds[key] = compound

    # Scenario windows only when every adjacent pair has an evidenced edge
    for scenario in SCENARIOS:
        ids = list(scenario.control_ids)
        for size in (2, 3):
            for index in range(len(ids) - size + 1):
                window = tuple(ids[index : index + size])
                ok = True
                for left, right in zip(window, window[1:]):
                    if not _edge_evidence(left, right, payload):
                        ok = False
                        break
                if not ok:
                    continue
                key = _compound_key(tuple(sorted(window)))
                if key in compounds:
                    continue
                note = f"{scenario.title} 시나리오 {index + 1}~{index + size}번 구간 (근거 엣지 확인)"
                compound = _build_compound(
                    window,
                    note,
                    payload=payload,
                    matched_keys=[f"{a}->{b}" for a, b in zip(window, window[1:])],
                    scenario_note=note,
                )
                if compound:
                    compounds[key] = compound

    # Drop weak-only without evidenceRefs
    cleaned = []
    for compound in compounds.values():
        problems = [
            p
            for p in compound.get("compoundProblems") or []
            if not any(t in str(p) for t in FORBIDDEN_TEMPLATES)
        ]
        compound["compoundProblems"] = problems
        if compound.get("evidenceGrade") == "weak" and not compound.get("evidenceRefs"):
            continue
        cleaned.append(compound)

    cleaned.sort(key=lambda c: (str(c["compoundKey"]),))
    return cleaned


def main() -> None:
    compounds = build_compounds()
    COMPOUNDS_FILE.write_text(json.dumps(compounds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.is_file() else {}
    index["totalCompounds"] = len(compounds)
    index["compoundsFile"] = "compounds.json"
    index["relationEvidenceFile"] = "relation_evidence.json"
    index["compoundsEvidenceVersion"] = 2
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    forbidden = sum(
        1
        for c in compounds
        for p in c.get("compoundProblems") or []
        if any(t in str(p) for t in FORBIDDEN_TEMPLATES)
    )
    print(f"Wrote {len(compounds)} evidenced compounds to {COMPOUNDS_FILE}")
    print(f"Forbidden template hits: {forbidden}")


if __name__ == "__main__":
    main()
