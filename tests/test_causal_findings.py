"""CausalFinding / checkKey grounding tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_assessment import analyze_assessment
from isms_pii_toolkit.control_problem_engine import (
    analyze_problems,
    assemble_causal_findings,
    extract_individual_problems,
    preview_check_impact,
)
from isms_pii_toolkit.report_evaluation import fill_canonical_report
from isms_pii_toolkit.verbalize_inference import build_context_packet, validate_verbalize_payload

client = TestClient(app)


def test_checkkey_resolution_partial_only_implemented_evidence():
    assessments = {"2.9.4": "partial"}
    checks = {
        "2.9.4": {
            "reviewed": True,
            "policy": True,
            "implemented": False,
            "evidence": False,
        }
    }
    rows = extract_individual_problems(assessments, checks)
    assert rows
    assert all(row["controlId"] == "2.9.4" for row in rows)
    assert all(row["source"] == "checklist" for row in rows)
    assert len(rows) == 2

    matched_keys = set()
    for row in rows:
        assert row["because"]
        assert row["causalStatement"]
        assert row["mappingMode"] == "maturity_proxy"
        assert any(b["kind"] == "maturity_unchecked" for b in row["because"])
        assert any(b["kind"] == "checklist_item" for b in row["because"])
        for basis in row["because"]:
            if basis["kind"] == "maturity_unchecked":
                matched_keys.add(basis["checkKey"])
    assert matched_keys == {"implemented", "evidence"}


def test_reviewed_unchecked_does_not_select_policy_item_by_silent_index():
    """checkKey 매칭이므로 reviewed 미충족은 1번(item)만, policy 항목을 훔치지 않는다."""
    assessments = {"2.9.4": "partial"}
    checks = {
        "2.9.4": {
            "reviewed": False,
            "policy": True,
            "implemented": True,
            "evidence": True,
        }
    }
    rows = extract_individual_problems(assessments, checks)
    assert len(rows) == 1
    maturity = [b for b in rows[0]["because"] if b["kind"] == "maturity_unchecked"]
    assert len(maturity) == 1
    assert maturity[0]["checkKey"] == "reviewed"
    checklist = [b for b in rows[0]["because"] if b["kind"] == "checklist_item"][0]
    assert checklist["checklistItemId"] == "1"


def test_analyze_problems_exposes_causal_findings():
    assessments = {
        "2.9.4": "none",
        "2.9.5": "none",
        "2.7.1": "none",
        "2.7.2": "none",
    }
    analysis = analyze_problems(assessments)
    assert analysis["causalFindings"]
    assert analysis["stats"]["causalFindingCount"] == len(analysis["causalFindings"])
    finding = analysis["causalFindings"][0]
    assert finding["findingId"]
    assert finding["because"]
    assert finding["impacts"] or finding["operationalImpact"] or finding["problems"]
    assert (
        "때문에" in finding["causalStatement"]
        or "이므로" in finding["causalStatement"]
        or "미흡" in finding["causalStatement"]
    )

    compounds = analysis["compoundSyntheses"]
    if compounds:
        assert compounds[0]["because"]
        assert compounds[0]["causalStatement"]


def test_assemble_causal_findings_preserves_enriched_rows():
    rows = extract_individual_problems({"2.7.1": "none"})
    findings = assemble_causal_findings(rows)
    assert len(findings) == len(rows)
    assert findings[0]["findingId"] == rows[0]["findingId"]
    from isms_pii_toolkit.causal_contract import assert_causal_finding_contract

    for row in findings:
        assert assert_causal_finding_contract(row) == []


def test_causal_contract_rejects_empty_because():
    from isms_pii_toolkit.causal_contract import assert_causal_finding_contract

    bad = {
        "findingId": "2.9.4:1",
        "controlId": "2.9.4",
        "title": "로그",
        "because": [],
        "problem": "문제",
        "impacts": [],
        "causalStatement": "문장",
        "source": "checklist",
    }
    reasons = assert_causal_finding_contract(bad)
    assert any("because" in r for r in reasons)


def test_verbalize_rejects_causal_findings_mutation():
    structured = analyze_assessment({"2.9.4": "none", "2.7.1": "none"}, verbalize=False)
    packet = build_context_packet(structured)
    payload = {
        "executiveReport": f"준비도 {structured['overallReadiness']}% / 갭 {structured['gapCount']}건",
        "keyInsights": ["a", "b", "c"],
        "causalFindings": [{"findingId": "invented", "because": []}],
        "confidence": 0.9,
    }
    validation = validate_verbalize_payload(payload, packet)
    assert validation["ok"] is False
    assert any("causalFindings" in reason for reason in validation["reasons"])


def test_verbalize_keeps_causal_fingerprint():
    import json

    from isms_pii_toolkit.causal_contract import causal_chain_fingerprint
    from isms_pii_toolkit.verbalize_inference import apply_verbalizing

    structured = analyze_assessment({"2.9.4": "none", "2.7.1": "none"}, verbalize=False)
    before = causal_chain_fingerprint(
        list((structured.get("problemAnalysis") or {}).get("causalFindings") or [])
    )
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]
    top_id = structured["topGaps"][0]["controlId"]

    def fake_client(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "executiveReport": fill_canonical_report(
                    f"준비도 {overall}% / 갭 {gaps}건 {top_id}"
                ),
                "keyInsights": [f"준비도 {overall}%", f"갭 {gaps}건", f"{top_id}", "권고"],
                "confidence": 0.9,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is True
    after = causal_chain_fingerprint(
        list((result.get("problemAnalysis") or {}).get("causalFindings") or [])
    )
    assert before == after
    assert result["problemAnalysis"]["causalFindings"] == structured["problemAnalysis"]["causalFindings"]


def test_analyze_api_returns_causal_findings():
    response = client.post(
        "/controls/analyze",
        json={
            "assessments": {
                "2.9.4": "partial",
                "2.7.1": "none",
                "2.7.2": "none",
            },
            "controlChecks": {
                "2.9.4": {
                    "reviewed": True,
                    "policy": True,
                    "implemented": False,
                    "evidence": False,
                }
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    analysis = body["problemAnalysis"]
    assert analysis["causalFindings"]
    sample = next(row for row in analysis["individualProblems"] if row["controlId"] == "2.9.4")
    assert sample["because"]
    assert sample["causalStatement"]
    assert "impacts" in sample


def test_verbalize_packet_includes_causal_findings():
    structured = analyze_assessment(
        {
            "2.9.4": "none",
            "2.7.1": "none",
        },
        control_checks={
            "2.9.4": {
                "reviewed": False,
                "policy": False,
                "implemented": False,
                "evidence": False,
            }
        },
        verbalize=False,
    )
    packet = build_context_packet(structured, max_gaps=8)
    assert packet["causalFindings"]
    assert packet["causalFindings"][0]["because"]
    assert packet["causalFindings"][0]["causalStatement"]


def test_gap_path_includes_control_check_grounding():
    from isms_pii_toolkit.control_assessment import list_checklist_controls

    assessments = {str(control["id"]): "done" for control in list_checklist_controls()}
    assessments["2.9.4"] = "partial"
    structured = analyze_assessment(
        assessments,
        control_checks={
            "2.9.4": {
                "reviewed": True,
                "policy": True,
                "implemented": False,
                "evidence": False,
            }
        },
        verbalize=False,
    )
    gap = next(item for item in structured["topGaps"] if item["controlId"] == "2.9.4")
    assert gap["causalBasis"]
    unmet_rows = [row for row in gap["checklistBreakdown"] if row.get("unmet")]
    met_rows = [row for row in gap["checklistBreakdown"] if row.get("unmet") is False]
    assert len(unmet_rows) == 2
    assert {row["checkKey"] for row in unmet_rows} == {"implemented", "evidence"}
    assert met_rows
    assert "[체크 근거]" in (gap.get("narrativeReport") or "")


def test_preview_check_impact_resolves_finding():
    assessments = {"2.9.4": "partial"}
    checks = {
        "2.9.4": {
            "reviewed": True,
            "policy": True,
            "implemented": False,
            "evidence": False,
        }
    }
    preview = preview_check_impact(
        assessments,
        checks,
        control_id="2.9.4",
        check_key="implemented",
        checked=True,
    )
    assert preview["beforeCount"] == 2
    assert preview["afterCount"] == 1
    assert len(preview["resolvedFindings"]) == 1


def test_preview_check_impact_api():
    response = client.post(
        "/controls/preview-check-impact",
        json={
            "assessments": {"2.9.4": "partial"},
            "controlChecks": {
                "2.9.4": {
                    "reviewed": True,
                    "policy": True,
                    "implemented": False,
                    "evidence": False,
                }
            },
            "controlId": "2.9.4",
            "checkKey": "evidence",
            "checked": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["beforeCount"] == 2
    assert body["afterCount"] == 1
    assert body["resolvedFindings"]
    assert "해소" in body["summary"]


def test_direct_domain_checks_override_maturity_proxy():
    assessments = {"2.9.4": "partial"}
    checks = {
        "2.9.4": {
            "reviewed": True,
            "policy": True,
            "implemented": False,
            "evidence": False,
        }
    }
    domain = {"2.9.4": {"1": True, "2": True, "3": False, "4": True, "5": True}}
    rows = extract_individual_problems(assessments, checks, domain_checks=domain)
    assert len(rows) == 1
    assert rows[0]["mappingMode"] == "direct_checklist"
    assert rows[0]["checklistItemId"] == "3"
    assert not any(b.get("kind") == "maturity_unchecked" for b in rows[0]["because"])
    assert rows[0].get("riskAlternatives") is not None


def test_verbalize_consistency_mismatch_falls_back():
    import json

    from isms_pii_toolkit.verbalize_inference import apply_verbalizing

    structured = analyze_assessment(
        {"2.9.4": "none", "2.7.1": "none"},
        verbalize=False,
    )
    calls = {"n": 0}

    def fake_client(system_prompt: str, user_prompt: str) -> str:
        calls["n"] += 1
        overall = structured["overallReadiness"]
        gaps = structured["gapCount"]
        if calls["n"] == 1:
            narratives = {"2.9.4": "체크 1 문제"}
        else:
            narratives = {"2.7.1": "체크 1 문제"}
        return json.dumps(
            {
                "executiveReport": fill_canonical_report(
                    f"준비도 {overall} 갭 {gaps}건 요약"
                ),
                "keyInsights": ["a", "b", "c"],
                "narratives": narratives,
                "confidence": 0.9,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(
        structured,
        enabled=True,
        chat_client=fake_client,
        consistency_samples=2,
    )
    assert result["verbalizeMeta"]["applied"] is False
    assert any("Self-Consistency" in r for r in result["verbalizeMeta"]["reasons"])


def test_verbalize_rejects_invented_checklist_item():
    structured = analyze_assessment(
        {"2.9.4": "none"},
        control_checks={
            "2.9.4": {
                "reviewed": False,
                "policy": False,
                "implemented": False,
                "evidence": False,
            }
        },
        verbalize=False,
    )
    packet = build_context_packet(structured, max_gaps=4)
    payload = {
        "executiveReport": fill_canonical_report(
            f"준비도 {structured['overallReadiness']} 갭 {structured['gapCount']}건"
        ),
        "keyInsights": ["a", "b", "c"],
        "narratives": {
            "2.9.4": "체크 99번 항목이 치명적입니다.",
        },
        "confidence": 0.9,
    }
    validation = validate_verbalize_payload(payload, packet)
    assert validation["ok"] is False
    assert any("체크 항목" in reason for reason in validation["reasons"])
