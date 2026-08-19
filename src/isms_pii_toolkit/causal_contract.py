"""CausalFinding product contract (because → problem → impacts).

Used by assemble/verbalize gates. Kept separate from retrieve to avoid import cycles.
"""

from __future__ import annotations

from typing import Any

CAUSAL_FINDING_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "findingId",
        "controlId",
        "title",
        "because",
        "problem",
        "impacts",
        "causalStatement",
        "source",
    }
)

CAUSAL_BECAUSE_KINDS: frozenset[str] = frozenset(
    {
        "assessment_level",
        "maturity_unchecked",
        "checklist_item",
        "weak_control",
    }
)


def assert_causal_finding_contract(finding: dict[str, Any]) -> list[str]:
    """Return contract violations for one CausalFinding (empty = ok)."""
    reasons: list[str] = []
    if not isinstance(finding, dict):
        return ["CausalFinding 은 object 여야 함"]
    missing = sorted(CAUSAL_FINDING_REQUIRED_KEYS - set(finding.keys()))
    if missing:
        reasons.append(f"CausalFinding 누락 키: {', '.join(missing)}")
    if not str(finding.get("findingId") or "").strip():
        reasons.append("findingId 비어 있음")
    if not str(finding.get("controlId") or "").strip():
        reasons.append("controlId 비어 있음")
    if not str(finding.get("problem") or "").strip():
        reasons.append("problem 비어 있음")
    if not str(finding.get("causalStatement") or "").strip():
        reasons.append("causalStatement 비어 있음")

    because = finding.get("because")
    if not isinstance(because, list) or not because:
        reasons.append("because 필수 (근거 1개 이상)")
    else:
        for index, basis in enumerate(because):
            if not isinstance(basis, dict):
                reasons.append(f"because[{index}] 형식 오류")
                continue
            kind = str(basis.get("kind") or "")
            if kind and kind not in CAUSAL_BECAUSE_KINDS:
                reasons.append(f"because[{index}] 알 수 없는 kind: {kind}")
            if kind == "checklist_item" and not str(basis.get("checklistItemId") or "").strip():
                reasons.append(f"because[{index}] checklistItemId 필수")

    impacts = finding.get("impacts")
    if impacts is None or not isinstance(impacts, list):
        reasons.append("impacts 는 list 여야 함")
    return reasons


def filter_valid_causal_findings(
    findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split findings into (valid, rejected_with_reasons)."""
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in findings:
        reasons = assert_causal_finding_contract(row)
        if reasons:
            rejected.append({"finding": row, "reasons": reasons})
        else:
            valid.append(row)
    return valid, rejected


def causal_chain_fingerprint(findings: list[dict[str, Any]]) -> frozenset[str]:
    """Stable fingerprint of because→problem chains (LLM must not invent)."""
    tokens: set[str] = set()
    for row in findings:
        finding_id = str(row.get("findingId") or "")
        problem = str(row.get("problem") or "").strip()
        because_parts: list[str] = []
        for basis in row.get("because") or []:
            if not isinstance(basis, dict):
                continue
            because_parts.append(
                "|".join(
                    [
                        str(basis.get("kind") or ""),
                        str(basis.get("checklistItemId") or ""),
                        str(basis.get("checkKey") or ""),
                        str(basis.get("level") or ""),
                    ]
                )
            )
        tokens.add(f"{finding_id}::{problem}::{';'.join(sorted(because_parts))}")
    return frozenset(tokens)
