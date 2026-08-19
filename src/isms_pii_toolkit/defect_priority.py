"""KISA 연도별 결함현황 → 현행 ISMS-P controlId 가중치."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

WEIGHTS_PATH = Path(__file__).resolve().parent / "data" / "problem_kb" / "defect_weights.json"


@lru_cache(maxsize=1)
def _load_weights() -> dict[str, dict[str, object]]:
    if not WEIGHTS_PATH.is_file():
        return {}
    data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    controls = data.get("controls") or {}
    return {str(cid): dict(meta) for cid, meta in controls.items()}


def defect_count(control_id: str) -> int:
    meta = _load_weights().get(control_id) or {}
    try:
        return int(meta.get("defectCount") or 0)
    except (TypeError, ValueError):
        return 0


def casebook_case_count(control_id: str) -> int:
    meta = _load_weights().get(control_id) or {}
    try:
        return int(meta.get("caseCount") or 0)
    except (TypeError, ValueError):
        return 0


def defect_mapping_meta(control_id: str) -> dict[str, object]:
    """과거 결함현황을 현행 통제에 연결한 매핑 메타데이터를 반환한다."""
    meta = _load_weights().get(control_id) or {}
    return {
        "defectCount": defect_count(control_id),
        "caseCount": casebook_case_count(control_id),
        "mappedSources": [str(item) for item in (meta.get("sources") or []) if item],
    }


def defect_priority_delta(control_id: str) -> int:
    """Empirical boost from historical defect frequency + casebook density.

    Scale is kept modest so org-profile and pilot quest boosts still dominate.
    """
    defects = defect_count(control_id)
    cases = casebook_case_count(control_id)
    delta = 0
    if defects >= 14:
        delta += 8
    elif defects >= 9:
        delta += 6
    elif defects >= 5:
        delta += 4
    elif defects >= 2:
        delta += 2
    elif defects >= 1:
        delta += 1
    if cases >= 20:
        delta += 3
    elif cases >= 10:
        delta += 2
    elif cases >= 5:
        delta += 1
    return min(12, delta)


def defect_relevance_reasons(control_id: str) -> list[str]:
    defects = defect_count(control_id)
    cases = casebook_case_count(control_id)
    reasons: list[str] = []
    if defects >= 5:
        reasons.append(f"KISA 결함현황 고빈도 통제(매핑 결함 {defects}건)")
    elif defects >= 1:
        reasons.append(f"KISA 결함현황 관련 통제(매핑 결함 {defects}건)")
    if cases >= 10:
        reasons.append(f"사례집 결함 유형 {cases}건 — 점검 우선")
    return reasons
