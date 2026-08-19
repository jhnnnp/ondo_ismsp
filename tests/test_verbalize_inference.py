"""Facts-only Verbalizing Inference tests."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_assessment import analyze_assessment, bootstrap_assessment
from isms_pii_toolkit.llm_provider import (
    load_verbalize_llm_config,
    make_mock_chat_client,
    resolve_chat_client,
)
from isms_pii_toolkit.report_evaluation import REPORT_DISCLAIMER, REPORT_SLOT_KEYS, fill_canonical_report
from isms_pii_toolkit.verbalize_inference import (
    CONTEXT_PACKET_TOP_KEYS,
    IMMUTABLE_STRUCTURED_KEYS,
    VERBALIZE_OUTPUT_KEYS,
    apply_verbalizing,
    assert_context_packet_contract,
    build_context_packet,
    parse_llm_json,
    validate_quest_verbalize_fields,
    validate_verbalize_payload,
)

client = TestClient(app)


PROFILE = {
    "headcountBand": "1-50",
    "industry": "retail",
    "piiVolume": "medium",
    "usesCloud": True,
    "usesOutsourcing": False,
    "remoteWork": False,
    "handlesRrn": False,
}


def _base_structured() -> dict:
    assessments = bootstrap_assessment()
    for control_id in list(assessments)[:8]:
        assessments[control_id] = "none"
    return analyze_assessment(assessments, organization_profile=PROFILE, verbalize=False)


def test_verbalize_disabled_keeps_template_mode():
    structured = _base_structured()
    assert structured["verbalizeMeta"]["requested"] is False
    assert structured["verbalizeMeta"]["applied"] is False
    assert structured["verbalizeMeta"]["mode"] == "template"
    assert structured["executiveReport"]


def test_verbalize_without_api_key_falls_back(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    structured = _base_structured()
    original = structured["executiveReport"]
    result = apply_verbalizing(structured, enabled=True)
    assert result["verbalizeMeta"]["requested"] is True
    assert result["verbalizeMeta"]["applied"] is False
    assert result["verbalizeMeta"]["provider"] == "fallback"
    assert result["executiveReport"] == original


def test_context_packet_matches_product_contract():
    structured = _base_structured()
    packet = build_context_packet(structured)
    assert set(packet.keys()) == CONTEXT_PACKET_TOP_KEYS
    assert assert_context_packet_contract(packet) == []
    # Snapshot of nested summary fields required by verbalize prompts/validators
    summary = packet["summary"]
    assert "overallReadiness" in summary
    assert "gapCount" in summary
    assert "evaluationBands" in summary
    assert set(summary["evaluationBands"]) >= {"strengths", "weaknesses", "deferred", "counts"}
    assert isinstance(packet["topGaps"], list)
    assert isinstance(packet["causalFindings"], list)
    assert packet["disclaimer"]


def test_validate_rejects_invented_control_ids():
    structured = _base_structured()
    packet = build_context_packet(structured)
    payload = {
        "executiveReport": f"준비도 {structured['overallReadiness']}% / 갭 {structured['gapCount']}건 / 통제 9.9.9 검토",
        "keyInsights": ["a", "b", "c"],
        "narratives": {},
        "recommendationDetails": [],
        "confidence": 0.9,
    }
    validation = validate_verbalize_payload(payload, packet)
    assert validation["ok"] is False
    assert "9.9.9" in validation["inventedControlIds"]


def test_validate_rejects_judgment_field_leak():
    structured = _base_structured()
    packet = build_context_packet(structured)
    payload = {
        "executiveReport": f"준비도 {structured['overallReadiness']}% / 갭 {structured['gapCount']}건",
        "keyInsights": ["a", "b", "c"],
        "overallReadiness": 99.0,
        "gapCount": 1,
        "confidence": 0.9,
    }
    validation = validate_verbalize_payload(payload, packet)
    assert validation["ok"] is False
    assert any("판정 필드" in reason for reason in validation["reasons"])


def test_validate_rejects_invented_action_id():
    structured = _base_structured()
    packet = build_context_packet(structured)
    # Ensure packet has a known action set (may be empty — invent still fails)
    payload = {
        "executiveReport": f"준비도 {structured['overallReadiness']}% / 갭 {structured['gapCount']}건",
        "keyInsights": ["a", "b", "c"],
        "actionQuestions": [
            {
                "actionId": "ask-invented-never-exist",
                "question": "임의 질문",
                "whyItMatters": "확인",
            }
        ],
        "confidence": 0.9,
    }
    quest = validate_quest_verbalize_fields(payload, packet)
    assert quest["ok"] is False
    assert any("actionId" in reason for reason in quest["reasons"])


def test_apply_verbalizing_merges_valid_llm_payload():
    structured = _base_structured()
    top_id = structured["topGaps"][0]["controlId"]
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]

    def fake_client(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "executiveReport": fill_canonical_report(
                    f"준비도 {overall}% / 갭 {gaps}건 {top_id} 우선"
                ),
                "keyInsights": [
                    f"준비도 {overall}%",
                    f"갭 {gaps}건",
                    f"우선 통제 {top_id}",
                    "권고 유지",
                ],
                "narratives": {
                    top_id: (
                        f"[통제 진단]\n{top_id} 맞춤 서술\n"
                        "[종합 판단]\n미이행\n[체크리스트 교차 검토]\n항목 확인\n"
                        "[시나리오]\n사고 가능\n[연쇄 영향]\n연쇄\n[우선 보완]\n조치"
                    )
                },
                "recommendationDetails": [
                    {
                        "title": structured["recommendations"][0]["title"],
                        "detail": "LLM이 다듬은 권고 상세",
                    }
                ],
                "confidence": 0.86,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is True
    assert result["verbalizeMeta"]["mode"] == "llm"
    assert result["verbalizeMeta"]["provider"] == "custom"
    assert str(overall) in result["executiveReport"]
    assert result["topGaps"][0]["narrativeReport"].startswith("[통제 진단]")
    assert result["recommendations"][0]["detail"] == "LLM이 다듬은 권고 상세"
    # numeric facts must remain unchanged
    assert result["overallReadiness"] == overall
    assert result["gapCount"] == gaps
    for key in IMMUTABLE_STRUCTURED_KEYS:
        if key in structured:
            assert result[key] == structured[key]


def test_mock_provider_swaps_cleanly():
    structured = _base_structured()
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]
    top_id = structured["topGaps"][0]["controlId"]
    mock = make_mock_chat_client(
        {
            "executiveReport": fill_canonical_report(f"준비도 {overall}% / 갭 {gaps}건 {top_id}"),
            "keyInsights": [f"준비도 {overall}%", f"갭 {gaps}건", f"{top_id}", "권고"],
            "narratives": {top_id: f"[통제 진단]\n{top_id}\n[종합 판단]\nx\n[체크리스트 교차 검토]\nx\n[시나리오]\nx\n[연쇄 영향]\nx\n[우선 보완]\nx"},
            "confidence": 0.9,
        }
    )
    result = apply_verbalizing(structured, enabled=True, chat_client=mock)
    assert result["verbalizeMeta"]["applied"] is True
    assert result["verbalizeMeta"]["provider"] == "custom"
    assert result["overallReadiness"] == overall


def test_apply_verbalizing_falls_back_on_low_confidence():
    structured = _base_structured()
    original = structured["executiveReport"]

    def fake_client(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "executiveReport": f"준비도 {structured['overallReadiness']}% 갭 {structured['gapCount']}",
                "keyInsights": ["a", "b", "c"],
                "confidence": 0.1,
            }
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is False
    assert result["executiveReport"] == original
    assert any("거부" in reason or "폴백" in reason for reason in result["verbalizeMeta"]["reasons"])


def test_apply_verbalizing_falls_back_on_invented_control():
    structured = _base_structured()
    original = structured["executiveReport"]

    def fake_client(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "executiveReport": (
                    f"준비도 {structured['overallReadiness']}% 갭 {structured['gapCount']} 통제 8.8.8"
                ),
                "keyInsights": ["a", "b", "c"],
                "confidence": 0.9,
            }
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is False
    assert result["executiveReport"] == original
    assert result["verbalizeMeta"]["provider"] == "fallback"


def test_report_only_changes_report_fields_not_control_content():
    structured = _base_structured()
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]
    original_gap = structured["topGaps"][0]
    top_id = original_gap["controlId"]

    def fake_client(_system: str, user: str) -> str:
        assert "전체 진단 보고서" in user
        assert "sectionProse" in user
        prose = {key: f"준비도 {overall}% 갭 {gaps}건 {top_id} 확인" for key in REPORT_SLOT_KEYS}
        return json.dumps(
            {
                "sectionProse": prose,
                "keyInsights": [f"준비도 {overall}%", f"갭 {gaps}건", top_id],
                "narratives": {top_id: "변경되면 안 되는 통제 본문"},
                "recommendationDetails": [],
                "confidence": 0.91,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(
        structured,
        enabled=True,
        chat_client=fake_client,
        include_quests=False,
        report_only=True,
    )

    assert result["verbalizeMeta"]["applied"] is True
    assert result["executiveReport"] != structured["executiveReport"]
    assert result["topGaps"][0] == original_gap
    assert result["confirmationActions"] == structured["confirmationActions"]


def test_validate_rejects_unfounded_certification_conclusion():
    structured = _base_structured()
    packet = build_context_packet(structured)
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]
    payload = {
        "executiveReport": fill_canonical_report(
            f"준비도 {overall}% / 갭 {gaps}건으로 인증 가능"
        ),
        "keyInsights": ["인증 가능", "영역 확인", "보완 계획"],
        "confidence": 0.9,
    }

    validation = validate_verbalize_payload(payload, packet)

    assert validation["ok"] is False
    assert any("인증" in reason for reason in validation["reasons"])


def test_parse_llm_json_strips_fences():
    payload = parse_llm_json('```json\n{"executiveReport":"ok","keyInsights":["a"]}\n```')
    assert payload["executiveReport"] == "ok"


def test_resolve_chat_client_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    resolved, name, cfg = resolve_chat_client(None)
    assert resolved is None
    assert name == "fallback"
    assert cfg.configured is False


def test_resolve_chat_client_with_key(monkeypatch):
    monkeypatch.setenv("PII_TOOLKIT_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PII_TOOLKIT_OPENAI_MODEL", "gpt-test")
    resolved, name, cfg = resolve_chat_client(None)
    assert resolved is not None
    assert name == "openai"
    assert cfg.model == "gpt-test"
    assert load_verbalize_llm_config().configured is True


def test_verbalize_output_contract_keys_are_stable():
    assert "executiveReport" in VERBALIZE_OUTPUT_KEYS
    assert "sectionProse" in VERBALIZE_OUTPUT_KEYS
    assert "overallReadiness" not in VERBALIZE_OUTPUT_KEYS
    assert "gapCount" in IMMUTABLE_STRUCTURED_KEYS


def test_analyze_is_deterministic_and_report_requests_ai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    assessments = bootstrap_assessment()
    response = client.post(
        "/controls/analyze",
        json={
            "assessments": assessments,
            "organizationProfile": PROFILE,
            "verbalize": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verbalizeMeta"]["requested"] is False
    assert body["verbalizeMeta"]["applied"] is False
    assert body["overallReadiness"] is not None

    report_response = client.post(
        "/controls/report",
        json={
            "assessments": assessments,
            "organizationProfile": PROFILE,
        },
    )
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["verbalizeMeta"]["requested"] is True
    assert report["verbalizeMeta"]["applied"] is False
    assert report["overallReadiness"] == body["overallReadiness"]


def _slot_prose(overall: object, gaps: object, extra: str = "") -> dict[str, str]:
    body = f"준비도 {overall}% 갭 {gaps}건 {extra}".strip()
    return {key: body for key in REPORT_SLOT_KEYS}


def test_apply_verbalizing_assembles_section_prose_and_keeps_disclaimer():
    structured = _base_structured()
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]
    top_id = structured["topGaps"][0]["controlId"]

    def fake_client(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "sectionProse": _slot_prose(overall, gaps, top_id),
                "keyInsights": [f"준비도 {overall}%", f"갭 {gaps}건", top_id, "관찰"],
                "confidence": 0.88,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is True
    report = result["executiveReport"]
    assert "1. 점검 개요 및 범위" in report
    assert "3. 양호하게 확인된 영역" in report
    assert report.endswith(f"- {REPORT_DISCLAIMER}")
    assert str(overall) in report
    assert result["overallReadiness"] == overall


def test_incomplete_section_prose_falls_back_to_template():
    structured = _base_structured()
    original = structured["executiveReport"]
    overall = structured["overallReadiness"]
    gaps = structured["gapCount"]

    def fake_client(_system: str, _user: str) -> str:
        prose = _slot_prose(overall, gaps)
        del prose["strengths"]
        return json.dumps(
            {
                "sectionProse": prose,
                "keyInsights": ["a", "b", "c"],
                "confidence": 0.9,
            },
            ensure_ascii=False,
        )

    result = apply_verbalizing(structured, enabled=True, chat_client=fake_client)
    assert result["verbalizeMeta"]["applied"] is False
    assert result["executiveReport"] == original
    assert any("슬롯" in reason for reason in result["verbalizeMeta"]["reasons"])
