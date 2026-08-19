"""Deterministic evaluation bands for the executive self-assessment report.

LLM may narrate these bands. It must not reclassify them.
"""

from __future__ import annotations

from typing import Any, Literal

EvaluationBand = Literal["strength", "weakness", "deferred"]

STRENGTH_MIN_COVERAGE_PERCENT = 50.0

CANONICAL_REPORT_HEADINGS: tuple[str, ...] = (
    "1. 점검 개요 및 범위",
    "2. 종합 점검 결과",
    "3. 양호하게 확인된 영역",
    "4. 미흡이 집중된 영역",
    "5. 핵심 지적사항",
    "6. 반복·연계 미흡",
    "7. 우선 보완 순서",
    "8. 참고 한계",
)

REPORT_DISCLAIMER = (
    "본 문서는 자체 점검 입력과 규칙 엔진 결과입니다. "
    "실제 인증 심사를 대체하지 않으며, 내부 점검·학습용 참고 자료로만 쓰세요."
)

REPORT_TITLE = "ISMS-P 자체 점검 결과 보고서 (참고용)"

REPORT_INTRODUCTION = (
    "진단 배경과 목적\n"
    "- 목적: 입력된 ISMS-P 통제 이행 상태를 기준으로 강점과 보완 필요 영역을 사전 파악\n"
    "- 산출: 우선 개선과제 및 후속 확인 대상 정리"
)

REPORT_SECTION_SLOTS: tuple[tuple[str, str], ...] = (
    ("scope", "1. 점검 개요 및 범위"),
    ("observation", "2. 종합 점검 결과"),
    ("strengths", "3. 양호하게 확인된 영역"),
    ("weaknesses", "4. 미흡이 집중된 영역"),
    ("findings", "5. 핵심 지적사항"),
    ("systemic", "6. 반복·연계 미흡"),
    ("actions", "7. 우선 보완 순서"),
)

REPORT_SLOT_KEYS: tuple[str, ...] = tuple(key for key, _heading in REPORT_SECTION_SLOTS)


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def category_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    statuses = dict(item.get("statusCounts") or {})
    reviewed = _int(item.get("reviewedCount"), 0)
    total = _int(item.get("totalCount", item.get("count")), 0)
    coverage = item.get("coveragePercent")
    if coverage is None and total > 0:
        coverage = round(reviewed / total * 100, 1)
    return {
        "category": str(item.get("category") or ""),
        "categoryId": str(item.get("categoryId") or ""),
        "areaId": str(item.get("areaId") or ""),
        "areaName": str(item.get("areaName") or ""),
        "reviewedCount": reviewed,
        "totalCount": total,
        "coveragePercent": round(_float(coverage, 0.0), 1),
        "statusCounts": {
            "none": _int(statuses.get("none"), 0),
            "partial": _int(statuses.get("partial"), 0),
            "done": _int(statuses.get("done"), 0) + _int(statuses.get("evidenced"), 0),
            "unknown": _int(statuses.get("unknown"), 0),
        },
    }


def classify_category_band(item: dict[str, Any]) -> EvaluationBand:
    snapshot = category_snapshot(item)
    statuses = snapshot["statusCounts"]
    finding_count = statuses["none"] + statuses["partial"]
    if finding_count > 0:
        return "weakness"
    if snapshot["reviewedCount"] <= 0:
        return "deferred"
    if snapshot["coveragePercent"] < STRENGTH_MIN_COVERAGE_PERCENT:
        return "deferred"
    return "strength"


def classify_evaluation_bands(category_coverage: list[dict[str, Any]] | None) -> dict[str, Any]:
    strengths: list[dict[str, Any]] = []
    weaknesses: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for raw in category_coverage or []:
        snapshot = category_snapshot(raw)
        if not snapshot["categoryId"] and not snapshot["category"]:
            continue
        band = classify_category_band(snapshot)
        snapshot["band"] = band
        if band == "strength":
            strengths.append(snapshot)
        elif band == "weakness":
            weaknesses.append(snapshot)
        else:
            deferred.append(snapshot)

    def finding_count(item: dict[str, Any]) -> int:
        statuses = item["statusCounts"]
        return statuses["none"] + statuses["partial"]

    strengths.sort(key=lambda item: (-item["coveragePercent"], item["category"]))
    weaknesses.sort(key=lambda item: (-finding_count(item), item["coveragePercent"], item["category"]))
    deferred.sort(key=lambda item: (item["coveragePercent"], item["category"]))
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "deferred": deferred,
        "counts": {
            "strengths": len(strengths),
            "weaknesses": len(weaknesses),
            "deferred": len(deferred),
        },
    }


def packet_evaluation_bands(bands: dict[str, Any] | None, *, limit: int = 6) -> dict[str, Any]:
    source = bands or {}
    counts = dict(source.get("counts") or {})

    def compact(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "category": item.get("category"),
                "categoryId": item.get("categoryId"),
                "areaName": item.get("areaName"),
                "band": item.get("band"),
                "reviewedCount": item.get("reviewedCount"),
                "totalCount": item.get("totalCount"),
                "coveragePercent": item.get("coveragePercent"),
                "statusCounts": item.get("statusCounts"),
            }
            for item in list(items)[:limit]
        ]

    return {
        "strengths": compact(list(source.get("strengths") or [])),
        "weaknesses": compact(list(source.get("weaknesses") or [])),
        "deferred": compact(list(source.get("deferred") or [])),
        "counts": {
            "strengths": _int(counts.get("strengths"), 0),
            "weaknesses": _int(counts.get("weaknesses"), 0),
            "deferred": _int(counts.get("deferred"), 0),
        },
    }


def fill_canonical_report(shared_body: str) -> str:
    body = str(shared_body or "").strip() or "해당 내용 없음"
    return "\n\n".join(f"{heading}\n{body}" for heading in CANONICAL_REPORT_HEADINGS)


def assemble_canonical_report(section_prose: object) -> tuple[str | None, list[str]]:
    """Build the canonical report from LLM slot prose. Section 8 is code-owned."""
    if not isinstance(section_prose, dict):
        return None, []
    missing: list[str] = []
    blocks: list[str] = [REPORT_TITLE, "", REPORT_INTRODUCTION, ""]
    for key, heading in REPORT_SECTION_SLOTS:
        text = str(section_prose.get(key) or "").strip()
        if not text:
            missing.append(key)
        blocks.append(heading)
        blocks.append(text)
        blocks.append("")
    if missing:
        return None, missing
    blocks.append("8. 참고 한계")
    blocks.append(f"- {REPORT_DISCLAIMER}")
    return "\n".join(blocks).strip(), []
