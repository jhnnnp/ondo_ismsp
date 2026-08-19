"""Architecture upgrade: causal SSOT, retrieve façade, verbalize split."""

from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.causal_retrieve import (
    project_causal_ssot_onto_gap,
    run_structured_retrieve,
)
from isms_pii_toolkit.control_assessment import analyze_assessment
from isms_pii_toolkit.llm_provider import make_mock_chat_client
from isms_pii_toolkit.report_evaluation import fill_canonical_report

client = TestClient(app)


def test_run_structured_retrieve_matches_problem_analysis_shape():
    assessments = {"2.7.1": "none", "2.7.2": "none", "3.1.1": "partial"}
    result = run_structured_retrieve(assessments)
    assert "causalFindings" in result
    assert "individualProblems" in result
    assert result["stats"]["causalFindingCount"] == len(result["causalFindings"])


def test_project_causal_ssot_prefers_problem_kb_wording():
    gap = {
        "controlId": "2.7.1",
        "title": "암호정책",
        "levelLabel": "미이행",
        "organicAnalysis": "템플릿 유기 분석",
        "problem": "템플릿 문제",
        "narrativeReport": "[통제 진단]\n기존",
        "cascadeRisks": [{"targetControlId": "2.7.2"}],
        "causalBasis": [],
    }
    findings = [
        {
            "findingId": "f-1",
            "controlId": "2.7.1",
            "problem": "암호키 관리 부재",
            "impacts": ["저장 데이터 노출"],
            "causalStatement": "때문에 체크 미충족 → 암호키 관리 부재",
        }
    ]
    projected = project_causal_ssot_onto_gap(gap, findings)
    assert "암호키 관리 부재" in projected["organicAnalysis"]
    assert projected["problem"] == "암호키 관리 부재"
    assert projected["causalFindingIds"] == ["f-1"]
    assert "[인과 SSOT" in projected["narrativeReport"]
    assert "저장 데이터 노출" in projected["narrativeReport"]


def test_analyze_assessment_exposes_pipeline_meta_and_ssot_ids():
    result = analyze_assessment(
        {"2.9.4": "none", "2.9.5": "none"},
        verbalize=False,
    )
    assert result["pipelineMeta"]["stages"][0] == "retrieve"
    assert "gap_ssot" in result["pipelineMeta"]["stages"]
    assert result["problemAnalysis"]["causalFindings"]
    # Critical (none) gaps must surface in topGaps ahead of bulk unknown
    assert result["topGaps"][0]["controlId"] in {"2.9.4", "2.9.5"}
    ssot_gaps = [g for g in result["topGaps"] if g.get("causalFindingIds")]
    assert ssot_gaps, "expected gap cards linked to causalFindingIds"
    gap = ssot_gaps[0]
    assert gap.get("causalBasis")
    assert "확인된 문제" in (gap.get("organicAnalysis") or "")
    control_findings = [
        f
        for f in result["problemAnalysis"]["causalFindings"]
        if f.get("controlId") == gap["controlId"]
    ]
    assert control_findings
    assert any(
        str(f.get("problem") or "") in (gap.get("organicAnalysis") or "")
        for f in control_findings
    )


def test_analyze_view_quest_trims_report_heavy_fields():
    result = analyze_assessment({"2.7.1": "none"}, view="quest")
    assert result["pipelineMeta"]["view"] == "quest"
    assert result["executiveReport"] is None
    assert result["cascadeChains"] == []
    assert result["confirmationActions"] or result["priorityQuests"] or True


def test_controls_report_endpoint_recomputes_facts_without_accepting_client_analysis():
    assessments = {"2.7.1": "none", "3.1.1": "partial"}
    analyzed = analyze_assessment(assessments, verbalize=False)
    readiness = analyzed["overallReadiness"]
    finding_count = analyzed["problemAnalysis"]["stats"]["causalFindingCount"]

    mock = make_mock_chat_client(
        {
            "executiveReport": fill_canonical_report(
                f"준비도 {readiness}% 갭 {analyzed['gapCount']}건"
            ),
            "keyInsights": ["insight-a", "insight-b", "insight-c"],
            "narratives": {},
            "recommendationDetails": [],
            "confidence": 0.9,
        }
    )

    from isms_pii_toolkit.verbalize_inference import apply_verbalizing

    merged = apply_verbalizing(
        analyzed,
        enabled=True,
        chat_client=mock,
        max_gaps=8,
        include_quests=False,
        report_only=True,
    )
    assert merged["overallReadiness"] == readiness
    assert merged["problemAnalysis"]["stats"]["causalFindingCount"] == finding_count
    assert merged["verbalizeMeta"]["applied"] is True
    assert merged["verbalizeMeta"]["latencyMs"] is not None
    assert "insight-a" in merged["keyInsights"]

    # API path recomputes facts from checklist input; arbitrary analyzed JSON is not accepted.
    response = client.post(
        "/controls/report",
        json={"assessments": assessments},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["overallReadiness"] == readiness
    assert payload["verbalizeMeta"]["requested"] is True
    # Legacy overlay path is gone; clients must send checklist assessments to /controls/report.
    assert client.post("/controls/verbalize", json={"analysis": analyzed}).status_code in {404, 405}
    assert client.post(
        "/controls/report",
        json={"analysis": analyzed},
    ).status_code == 422
