"""공식 안내서 청크 + 상세 해설(LLM/템플릿) 테스트."""

from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_assessment import analyze_assessment, bootstrap_assessment
from isms_pii_toolkit.detail_narrative import (
    apply_detail_narratives,
    build_detail_packet,
    make_echo_detail_client,
    validate_detail_payload,
)
from isms_pii_toolkit.official_kb import official_chunks

client = TestClient(app)

CLOUD_PROFILE = {
    "headcountBand": "1-50",
    "industry": "technology",
    "piiVolume": "medium",
    "usesCloud": True,
    "usesOutsourcing": False,
    "usesRemoteAccess": False,
    "processesRrn": False,
    "hasOnPremFacility": False,
}


def test_official_chunks_for_known_control() -> None:
    chunks = official_chunks("2.7.1")
    assert chunks["found"] is True
    assert chunks["controlId"] == "2.7.1"
    kinds = {row["kind"] for row in chunks["chunks"]}
    assert "requirement" in kinds
    assert "checkQuestion" in kinds
    assert chunks["sourceDoc"]


def test_analyze_attaches_template_detail_narratives() -> None:
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "done"
    assessments["2.7.1"] = "none"
    result = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        verbalize=False,
    )
    assert result["detailNarrativeMeta"]["mode"] == "template"
    assert "2.7.1" in result["detailNarratives"]
    gap = next(g for g in result["topGaps"] if g["controlId"] == "2.7.1")
    assert gap.get("detailNarrative")
    assert "[공식 요구사항]" in gap["detailNarrative"]


def test_llm_detail_narratives_merge_with_mock_client() -> None:
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "done"
    assessments["2.7.1"] = "none"
    assessments["2.7.2"] = "partial"
    base = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        verbalize=False,
    )
    # analyze already applied template; re-run LLM upgrade on a clean structured copy
    base.pop("detailNarratives", None)
    for key in ("topGaps", "criticalGaps", "confirmedGaps"):
        for row in base.get(key) or []:
            row.pop("detailNarrative", None)
            row.pop("detailNarrativeTip", None)
            row.pop("detailNarrativeSources", None)

    merged = apply_detail_narratives(
        base,
        enabled=True,
        chat_client=make_echo_detail_client(),
        max_controls=4,
    )
    assert merged["detailNarrativeMeta"]["applied"] is True
    assert merged["detailNarrativeMeta"]["mode"] == "llm"
    assert "2.7.1" in merged["detailNarratives"]
    assert "공식 안내 기반" in merged["detailNarratives"]["2.7.1"]["summaryTip"]


def test_validate_detail_rejects_unknown_control() -> None:
    packet = build_detail_packet(
        {
            "topGaps": [
                {
                    "controlId": "2.7.1",
                    "title": "암호",
                    "level": "none",
                    "levelLabel": "미이행",
                    "severity": "critical",
                    "organicAnalysis": "미흡",
                    "riskIfMissing": "유출",
                    "immediateActions": [],
                    "causalBasis": [],
                }
            ],
            "confirmedGaps": [],
            "criticalGaps": [],
            "problemAnalysis": {"individualProblems": []},
            "overallReadiness": 10,
            "gapCount": 1,
        },
        max_controls=2,
    )
    bad = {
        "details": {
            "9.9.9": {"summaryTip": "x", "detail": "y"},
        },
        "confidence": 0.5,
    }
    validation = validate_detail_payload(bad, packet)
    assert validation["ok"] is False


def test_report_api_includes_detail_narrative_meta() -> None:
    assessments = bootstrap_assessment()
    response = client.post(
        "/controls/report",
        json={
            "assessments": assessments,
            "organizationProfile": CLOUD_PROFILE,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "detailNarrativeMeta" in data
    assert "detailNarratives" in data
    assert data["detailNarrativeMeta"]["requested"] is True
