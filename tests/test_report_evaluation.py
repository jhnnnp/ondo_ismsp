from __future__ import annotations

from isms_pii_toolkit.control_assessment import analyze_assessment, bootstrap_assessment
from isms_pii_toolkit.control_insight_verbalize import build_executive_report
from isms_pii_toolkit.report_evaluation import (
    CANONICAL_REPORT_HEADINGS,
    REPORT_DISCLAIMER,
    REPORT_SLOT_KEYS,
    assemble_canonical_report,
    classify_category_band,
    classify_evaluation_bands,
)
from isms_pii_toolkit.schemas import AssessResponse


def _coverage(
    category_id: str,
    *,
    reviewed: int,
    total: int,
    none: int = 0,
    partial: int = 0,
    done: int = 0,
    unknown: int = 0,
    category: str | None = None,
) -> dict:
    return {
        "category": category or category_id,
        "categoryId": category_id,
        "areaId": category_id.split(".")[0],
        "areaName": "영역",
        "reviewedCount": reviewed,
        "totalCount": total,
        "coveragePercent": round(reviewed / total * 100, 1) if total else 0.0,
        "statusCounts": {
            "none": none,
            "partial": partial,
            "done": done,
            "unknown": unknown,
        },
    }


def test_classify_strength_requires_reviewed_coverage_and_no_findings():
    assert classify_category_band(_coverage("2.5", reviewed=4, total=4, done=4)) == "strength"


def test_classify_weakness_when_any_finding_exists():
    assert classify_category_band(_coverage("2.7", reviewed=4, total=6, none=1, done=3, unknown=2)) == "weakness"


def test_classify_deferred_when_nothing_reviewed():
    assert classify_category_band(_coverage("1.1", reviewed=0, total=5, unknown=5)) == "deferred"


def test_classify_deferred_when_coverage_is_too_thin_even_if_done():
    assert classify_category_band(_coverage("3.1", reviewed=1, total=4, done=1, unknown=3)) == "deferred"


def test_classify_evaluation_bands_splits_all_categories():
    bands = classify_evaluation_bands(
        [
            _coverage("2.5", reviewed=4, total=4, done=4, category="인증"),
            _coverage("2.7", reviewed=3, total=3, none=2, done=1, category="암호"),
            _coverage("1.4", reviewed=0, total=6, unknown=6, category="외주"),
        ]
    )
    assert [item["categoryId"] for item in bands["strengths"]] == ["2.5"]
    assert [item["categoryId"] for item in bands["weaknesses"]] == ["2.7"]
    assert [item["categoryId"] for item in bands["deferred"]] == ["1.4"]
    assert bands["counts"] == {"strengths": 1, "weaknesses": 1, "deferred": 1}


def test_analyze_assessment_exposes_evaluation_bands_and_canonical_headings():
    assessments = bootstrap_assessment()
    done_id = next(control_id for control_id in assessments if control_id.startswith("2.5."))
    none_id = next(control_id for control_id in assessments if control_id.startswith("2.7."))
    assessments[done_id] = "done"
    assessments[none_id] = "none"
    result = analyze_assessment(assessments, verbalize=False)
    bands = result["evaluationBands"]
    assert bands["counts"]["weaknesses"] >= 1
    report = result["executiveReport"]
    for heading in CANONICAL_REPORT_HEADINGS:
        assert heading in report
    assert "양호하게 확인된 영역" in report
    assert "인증 심사를 대체하지 않" in report
    parsed = AssessResponse.model_validate(result)
    assert parsed.evaluation_bands is not None
    assert parsed.evaluation_bands.counts["weaknesses"] >= 1


def test_executive_report_uses_engine_bands_not_llm_titles():
    bands = classify_evaluation_bands(
        [
            _coverage("2.5", reviewed=3, total=3, done=3, category="인증"),
            _coverage("2.7", reviewed=2, total=2, none=2, category="암호"),
        ]
    )
    report = build_executive_report(
        40.0,
        "보완 필요",
        2,
        {"none": 2, "partial": 0, "done": 3, "unknown": 10},
        {},
        [],
        [],
        [],
        [],
        evaluation_bands=bands,
    )
    assert "3. 양호하게 확인된 영역" in report
    assert "인증" in report
    assert "암호" in report
    assert "[종합 평가]" not in report
    assert "1. 점검 진행" not in report


def test_assemble_canonical_report_uses_slots_and_owns_disclaimer():
    prose = {key: f"{key} 관찰" for key in REPORT_SLOT_KEYS}
    prose["actions"] = "인증 심사를 대체한다고 쓰면 안 되는 본문"
    assembled, missing = assemble_canonical_report(prose)
    assert missing == []
    assert assembled is not None
    for heading in CANONICAL_REPORT_HEADINGS:
        assert heading in assembled
    assert assembled.endswith(f"- {REPORT_DISCLAIMER}")
    assert assembled.count("8. 참고 한계") == 1
    assert "scope 관찰" in assembled


def test_assemble_canonical_report_rejects_missing_slot():
    prose = {key: "관찰" for key in REPORT_SLOT_KEYS}
    del prose["findings"]
    assembled, missing = assemble_canonical_report(prose)
    assert assembled is None
    assert missing == ["findings"]
