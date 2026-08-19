"""Dual-layer check contract: official confirmation vs casebook problems."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .official_kb import official_check_statements, official_evidence_examples

CHECK_KEYS = ("reviewed", "policy", "implemented", "evidence")
PROBLEM_KB = Path(__file__).resolve().parent / "data" / "problem_kb" / "controls"


@lru_cache(maxsize=128)
def _load_problem_control(control_id: str) -> dict[str, object] | None:
    path = PROBLEM_KB / f"{control_id.replace('.', '_')}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_official_checks(control_id: str) -> list[dict[str, object]]:
    from .official_text import clean_evidence_label, sanitize_official_text

    statements = official_check_statements(control_id)
    checks: list[dict[str, object]] = []
    for idx, label in enumerate(statements):
        key = CHECK_KEYS[min(idx, len(CHECK_KEYS) - 1)]
        checks.append(
            {
                "checkId": f"official-{idx + 1}",
                "label": sanitize_official_text(str(label)),
                "mapsToCheckKey": key,
                "sourceDoc": "ISMS-P 인증기준 안내서(2023.11.23)",
            }
        )
    for raw in official_evidence_examples(control_id):
        evidence_label = clean_evidence_label(str(raw))
        if not evidence_label:
            continue
        checks.append(
            {
                "checkId": "evidence",
                "label": f"준비할 증적 예시: {evidence_label}",
                "mapsToCheckKey": "evidence",
                "sourceDoc": "ISMS-P 인증기준 안내서(2023.11.23)",
            }
        )
        break
    return checks


def build_casebook_problems(control_id: str, *, limit: int = 12) -> list[dict[str, object]]:
    record = _load_problem_control(control_id)
    if not record:
        return []
    out: list[dict[str, object]] = []
    for item in record.get("checklistItems") or []:
        item_id = str(item.get("itemId") or "")
        check_key = str(item.get("checkKey") or "")
        block = item.get("ifUnchecked") or {}
        refs = list(block.get("sourceRefs") or [])
        for problem in block.get("problems") or []:
            text = str(problem).strip()
            if not text:
                continue
            ref = None
            if refs:
                ref = str(refs[0].get("ref") or refs[0].get("doc") or "")
            out.append(
                {
                    "problem": text,
                    "checklistItemId": item_id or None,
                    "checkKey": check_key or None,
                    "sourceRef": ref,
                    "sourceDoc": "사례집.md",
                }
            )
            if len(out) >= limit:
                return out
    return out


def dual_layer_for_control(control_id: str) -> dict[str, list[dict[str, object]]]:
    return {
        "officialChecks": build_official_checks(control_id),
        "casebookProblems": build_casebook_problems(control_id),
    }
