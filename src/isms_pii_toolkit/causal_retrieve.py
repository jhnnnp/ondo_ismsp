"""Structured retrieve layer for causal analysis (Method B).

Pipeline order:
  1. retrieve_control_facts / retrieve_unchecked_findings
  2. assemble_causal_findings / run_structured_retrieve
  3. project_causal_ssot_onto_gaps (gap tab ↔ problem tab alignment)
  4. analyze_problems / preview_check_impact
  5. (optional) verbalize — facts only (must not mutate causalFindings)
"""

from __future__ import annotations

from .causal_contract import (
    CAUSAL_BECAUSE_KINDS,
    CAUSAL_FINDING_REQUIRED_KEYS,
    assert_causal_finding_contract,
    causal_chain_fingerprint,
    filter_valid_causal_findings,
)
from .control_problem_engine import (
    CHECK_KEY_LABELS,
    CHECK_KEYS,
    WEAK_LEVELS,
    analyze_problems,
    assemble_causal_findings,
    extract_individual_problems,
    findings_for_control,
    preview_check_impact,
)
from .control_problem_engine import _load_control as retrieve_control_facts
from .organization_profile import OrganizationContext

__all__ = [
    "CAUSAL_BECAUSE_KINDS",
    "CAUSAL_FINDING_REQUIRED_KEYS",
    "CHECK_KEYS",
    "CHECK_KEY_LABELS",
    "WEAK_LEVELS",
    "analyze_problems",
    "assemble_causal_findings",
    "assert_causal_finding_contract",
    "causal_chain_fingerprint",
    "extract_individual_problems",
    "filter_valid_causal_findings",
    "findings_for_control",
    "index_findings_by_control",
    "preview_check_impact",
    "project_causal_ssot_onto_gap",
    "project_causal_ssot_onto_gaps",
    "retrieve_control_facts",
    "retrieve_unchecked_findings",
    "run_structured_retrieve",
]


def retrieve_unchecked_findings(
    assessments: dict[str, str],
    control_checks: dict[str, dict[str, bool]] | None = None,
    organization_context: OrganizationContext | None = None,
    domain_checks: dict[str, dict[str, bool]] | None = None,
) -> list[dict[str, object]]:
    """입력 진단에서 미충족 근거 기반 CausalFinding을 회수한다."""
    return extract_individual_problems(
        assessments, control_checks, organization_context, domain_checks
    )


def retrieve_control_checklist_items(control_id: str) -> list[dict[str, object]]:
    record = retrieve_control_facts(control_id)
    if record is None:
        return []
    return list(record.get("checklistItems") or [])


def run_structured_retrieve(
    assessments: dict[str, str],
    scenario_id: str | None = None,
    control_checks: dict[str, dict[str, bool]] | None = None,
    organization_context: OrganizationContext | None = None,
    domain_checks: dict[str, dict[str, bool]] | None = None,
) -> dict[str, object]:
    """Canonical retrieve → causal assemble → compound entry (single pass)."""
    return analyze_problems(
        assessments,
        scenario_id,
        control_checks,
        organization_context,
        domain_checks,
    )


def index_findings_by_control(
    findings: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    indexed: dict[str, list[dict[str, object]]] = {}
    for finding in findings:
        control_id = str(finding.get("controlId") or "")
        if not control_id:
            continue
        indexed.setdefault(control_id, []).append(finding)
    return indexed


def project_causal_ssot_onto_gap(
    gap: dict[str, object],
    findings: list[dict[str, object]],
) -> dict[str, object]:
    """Align gap-card prose with problem-KB CausalFinding (single source of truth).

    Insight-KB templates may still supply focus/cascade flavor, but because→problem→impact
    wording shown to users prefers problem_kb findings.
    """
    if not findings:
        return gap

    result = dict(gap)
    statements = [
        str(item.get("causalStatement") or "").strip()
        for item in findings
        if str(item.get("causalStatement") or "").strip()
    ]
    problems = [
        str(item.get("problem") or "").strip()
        for item in findings
        if str(item.get("problem") or "").strip()
    ]
    impacts: list[str] = []
    for item in findings:
        for impact in list(item.get("impacts") or [])[:2]:
            text = str(impact).strip()
            if text and text not in impacts:
                impacts.append(text)

    result["causalBasis"] = statements[:8]
    result["causalFindingIds"] = [
        str(item.get("findingId"))
        for item in findings
        if item.get("findingId")
    ][:12]

    control_id = str(result.get("controlId") or "")
    title = str(result.get("title") or "")
    level_label = str(result.get("levelLabel") or "미흡")
    if problems:
        organic = f"{control_id} {title}이(가) {level_label} 상태입니다. "
        organic += "확인된 문제: " + " / ".join(problems[:3]) + ". "
        if impacts:
            organic += "발생 가능 영향: " + " / ".join(impacts[:3]) + ". "
        cascade = list(result.get("cascadeRisks") or [])
        if cascade:
            chain = " → ".join(str(item.get("targetControlId") or "") for item in cascade[:4] if item.get("targetControlId"))
            if chain:
                organic += f"연결된 후속 통제({chain})까지 보호 체계가 약화될 수 있습니다."
        result["organicAnalysis"] = organic.strip()
        result["problem"] = problems[0]

    narrative = str(result.get("narrativeReport") or "")
    if statements and "[인과 SSOT" not in narrative:
        block = "\n\n[인과 SSOT — problem KB]\n" + "\n".join(
            f"- {line}" for line in statements[:6]
        )
        if impacts:
            block += "\n[발생 가능 영향]\n" + "\n".join(f"- {line}" for line in impacts[:4])
        result["narrativeReport"] = narrative + block
    return result


def project_causal_ssot_onto_gaps(
    gaps: list[dict[str, object]],
    findings: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_control = index_findings_by_control(findings)
    return [
        project_causal_ssot_onto_gap(gap, by_control.get(str(gap.get("controlId") or ""), []))
        for gap in gaps
    ]
