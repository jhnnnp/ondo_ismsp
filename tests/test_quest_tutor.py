"""1타 강사 퀘스트 / N/A / confirmationActions 테스트."""

from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.applicability import PHYSICAL_DC_CONTROLS, apply_na_to_assessments
from isms_pii_toolkit.control_assessment import analyze_assessment, bootstrap_assessment
from isms_pii_toolkit.organization_profile import normalize_organization_profile
from isms_pii_toolkit.quest_kb import get_quest_overlay, resolve_quest
from isms_pii_toolkit.report_evaluation import CANONICAL_REPORT_HEADINGS
from isms_pii_toolkit.verbalize_inference import (
    build_context_packet,
    validate_quest_verbalize_fields,
    validate_verbalize_payload,
)

client = TestClient(app)

CLOUD_PROFILE = {
    "headcountBand": "1-50",
    "industry": "technology",
    "piiVolume": "low",
    "usesCloud": True,
    "hasOnPremFacility": False,
}


def test_cloud_only_marks_physical_controls_na() -> None:
    context = normalize_organization_profile(CLOUD_PROFILE)
    assert context is not None
    assert "cloud-only-no-dc" in context.tags
    assessments = {cid: "unknown" for cid in list(PHYSICAL_DC_CONTROLS) + ["2.4.7", "2.5.4"]}
    merged, notes = apply_na_to_assessments(assessments, context)
    for cid in PHYSICAL_DC_CONTROLS:
        assert merged[cid] == "na"
    assert merged["2.4.7"] == "unknown"
    assert merged["2.5.4"] == "unknown"
    assert len(notes) == len(PHYSICAL_DC_CONTROLS)


def test_analyze_excludes_na_from_readiness_denominator() -> None:
    assessments = bootstrap_assessment()
    for cid in PHYSICAL_DC_CONTROLS:
        assessments[cid] = "none"
    result = analyze_assessment(assessments, organization_profile=CLOUD_PROFILE, verbalize=False)
    assert result["naControlCount"] == len(PHYSICAL_DC_CONTROLS)
    assert result["applicableControlCount"] == 101 - len(PHYSICAL_DC_CONTROLS)
    assert result["statusCounts"].get("na") == len(PHYSICAL_DC_CONTROLS)
    gap_ids = {g["controlId"] for g in result["topGaps"]}
    assert not (PHYSICAL_DC_CONTROLS & gap_ids)


def test_on_prem_keeps_physical_controls() -> None:
    profile = {**CLOUD_PROFILE, "hasOnPremFacility": True}
    assessments = bootstrap_assessment()
    result = analyze_assessment(assessments, organization_profile=profile, verbalize=False)
    assert result["naControlCount"] == 0


def test_pilot_quest_and_confirmation_actions() -> None:
    assert get_quest_overlay("2.5.4") is not None
    assert get_quest_overlay("2.6.1") is not None
    assert get_quest_overlay("2.6.2") is not None
    assessments = bootstrap_assessment()
    # 다른 갭을 줄여 2.5.4 confirmation이 limit 안에 들어오게 한다
    for cid in assessments:
        assessments[cid] = "done"
    assessments["2.5.4"] = "none"
    result = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        quest_checks={"2.5.4": {"pwd-complexity": False, "mfa": False}},
        input_confidence={"2.5.4": "unknown"},
        verbalize=False,
    )
    assert result["confirmationActions"]
    assert any(a["controlId"] == "2.5.4" for a in result["confirmationActions"])
    assert result["inputConfidenceSummary"]["unknown"] >= 1
    assert any(q["controlId"] == "2.5.4" and q["source"] == "pilot" for q in result["priorityQuests"])


def test_sticky_na_clears_when_on_prem_enabled() -> None:
    assessments = bootstrap_assessment()
    for cid in PHYSICAL_DC_CONTROLS:
        assessments[cid] = "na"
    onprem = {**CLOUD_PROFILE, "hasOnPremFacility": True}
    result = analyze_assessment(assessments, organization_profile=onprem, verbalize=False)
    assert result["naControlCount"] == 0
    assert result["statusCounts"].get("na", 0) == 0
    assert not any(n["controlId"] == "2.4.1" for n in result["applicabilityNotes"])
    assert result["applicableControlCount"] == 101


def test_quest_merge_does_not_force_evidence_or_overwrite_false() -> None:
    from isms_pii_toolkit.quest_kb import merge_quest_checks_into_control_checks

    merged = merge_quest_checks_into_control_checks(
        {"2.5.4": {"mfa": True, "pwd-complexity": True}},
        {"2.5.4": {"evidence": False, "implemented": False}},
    )
    assert merged["2.5.4"].get("evidence") is False
    assert merged["2.5.4"].get("implemented") is True


def test_quest_verbalize_rejects_invented_action_id() -> None:
    assessments = bootstrap_assessment()
    assessments["2.5.4"] = "none"
    structured = analyze_assessment(assessments, organization_profile=CLOUD_PROFILE, verbalize=False)
    packet = build_context_packet(structured)
    report_body = "\n".join(
        [
            f"준비도 {structured['overallReadiness']}% / 갭 {structured['gapCount']}건",
            *CANONICAL_REPORT_HEADINGS,
        ]
    )
    bad = {
        "executiveReport": report_body,
        "keyInsights": ["a", "b", "c"],
        "narratives": {},
        "recommendationDetails": [],
        "actionQuestions": [{"actionId": "invented-action", "question": "x", "whyItMatters": "y"}],
        "confidence": 0.9,
    }
    quest = validate_quest_verbalize_fields(bad, packet)
    assert quest["ok"] is False
    validation = validate_verbalize_payload(bad, packet)
    assert validation.get("questOk") is False
    assert "actionQuestions" not in bad


def test_analyze_api_returns_quest_fields() -> None:
    assessments = bootstrap_assessment()
    response = client.post(
        "/controls/analyze",
        json={
            "assessments": assessments,
            "organizationProfile": CLOUD_PROFILE,
            "questChecks": {"2.5.4": {"mfa": True}},
            "inputConfidence": {"2.5.4": "confirmed"},
            "evidenceSlots": {
                "aws-pwd-policy-screenshot": {
                    "fileName": "pwd.png",
                    "controlId": "2.5.4",
                    "uploadedAt": "2026-07-27T00:00:00Z",
                }
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "confirmationActions" in data
    assert "priorityQuests" in data
    assert "inputConfidenceSummary" in data
    assert data["naControlCount"] >= 1


def test_thin_quest_derives_for_non_pilot() -> None:
    """파일럿이 전 통제에 있어도 thin 폴백 엔진은 유지한다."""
    from isms_pii_toolkit.control_assessment import list_checklist_controls
    from isms_pii_toolkit.quest_kb import thin_quest_from_control

    control = next(c for c in list_checklist_controls() if c["id"] == "2.9.2")
    other = next(c for c in list_checklist_controls() if c["id"] == "2.10.8")
    quest_a = thin_quest_from_control(control)
    quest_b = thin_quest_from_control(other)
    assert quest_a["source"] == "thin"
    assert "화면으로 보여줄 수 있나요" in quest_a["quest"]["plainQuestion"]
    assert "서버로" not in quest_a["quest"]["actionGuide"]["whenDone"]
    assert quest_a["quest"]["actionGuide"]["whenMissing"].endswith(("세요.", "세요"))
    labels_a = [row["label"] for row in quest_a["quest"]["checks"]]
    labels_b = [row["label"] for row in quest_b["quest"]["checks"]]
    # Official grounding: checks come from 인증기준 주요 확인사항 (may not embed title).
    if quest_a.get("meta", {}).get("grounding") == "official":
        assert labels_a and labels_b
        assert labels_a != labels_b
    else:
        assert any(control["title"] in label for label in labels_a)
        assert any(other["title"] in label for label in labels_b)
        assert labels_a != labels_b
    assert not any(label.endswith(("합니다", "하세요")) for label in labels_a)


def test_all_controls_have_pilot_overlays() -> None:
    from isms_pii_toolkit.control_assessment import CONTROL_CHECKLIST, list_checklist_controls
    from isms_pii_toolkit.quest_kb import _load_pilot_quests

    _load_pilot_quests.cache_clear()
    control_ids = {c["id"] for c in list_checklist_controls()}
    pilots = set(_load_pilot_quests())
    assert pilots == control_ids
    assert set(CONTROL_CHECKLIST) == control_ids
    for cid in ("2.4.1", "2.4.6"):
        done = _load_pilot_quests()[cid]["quest"]["actionGuide"]["whenMissing"]
        assert "해당 없음" in done


def test_confirmation_actions_use_ask_form() -> None:
    from isms_pii_toolkit.quest_kb import _load_pilot_quests

    _load_pilot_quests.cache_clear()
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "done"
    assessments["2.5.4"] = "none"
    result = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        input_confidence={"2.5.4": "unknown"},
        verbalize=False,
    )
    questions = [a["question"] for a in result["confirmationActions"] if a["controlId"] == "2.5.4"]
    assert questions
    assert all("?" in q or q.endswith("나요") for q in questions)
    assert not any(q.startswith("증적 확보:") for q in questions)


def test_confirmation_actions_one_card_per_control_limit_ten() -> None:
    """A realign: 주인공 목록은 통제당 1질문, 최대 10개. 공식 문항은 detailChecks."""
    from isms_pii_toolkit.quest_kb import _load_pilot_quests

    _load_pilot_quests.cache_clear()
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "done"
    for cid in ("2.5.4", "2.6.1", "2.10.1", "1.4.1", "3.2.1", "2.9.4"):
        assessments[cid] = "none"
    result = analyze_assessment(assessments, organization_profile=CLOUD_PROFILE, verbalize=False)
    actions = result["confirmationActions"]
    assert 1 <= len(actions) <= 10
    assert result["confirmationActionMeta"]["limit"] == 10
    control_ids = [a["controlId"] for a in actions]
    assert len(control_ids) == len(set(control_ids))
    target = next(a for a in actions if a["controlId"] == "2.10.1")
    assert target.get("title")
    assert isinstance(target.get("detailChecks"), list)
    assert len(target["detailChecks"]) >= 1


def test_control_session_details_cover_all_controls() -> None:
    """우선 confirmationActions 밖 통제도 세션 카드용 detailChecks를 갖는다."""
    assessments = bootstrap_assessment()
    result = analyze_assessment(assessments, organization_profile=CLOUD_PROFILE, verbalize=False)
    catalog = result.get("controlSessionDetails") or {}
    assert len(catalog) == len(assessments)
    assert "2.11.1" in catalog
    assert len(catalog["2.11.1"].get("detailChecks") or []) >= 1
    action_ids = {a["controlId"] for a in (result.get("confirmationActions") or [])}
    outside = next(cid for cid in catalog if cid not in action_ids)
    assert len(catalog[outside].get("detailChecks") or []) >= 1


def test_priority_quests_list_pilots_first() -> None:
    from isms_pii_toolkit.quest_kb import _load_pilot_quests

    _load_pilot_quests.cache_clear()
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "evidenced"
    for cid in ("2.5.4", "2.6.1", "3.2.2", "1.2.3"):
        assessments[cid] = "none"
    result = analyze_assessment(assessments, organization_profile=CLOUD_PROFILE, verbalize=False)
    tops = result["priorityQuests"][:4]
    assert len(tops) == 4
    assert all(q["source"] == "pilot" for q in tops)
    assert {q["controlId"] for q in tops} == {"2.5.4", "2.6.1", "3.2.2", "1.2.3"}


def test_expanded_pilots_cover_startup_core() -> None:
    from isms_pii_toolkit.quest_kb import _load_pilot_quests

    _load_pilot_quests.cache_clear()
    core = {
        "1.1.4",
        "1.2.2",
        "1.2.3",
        "1.2.4",
        "2.3.1",
        "2.5.4",
        "2.6.1",
        "2.7.1",
        "2.7.2",
        "2.9.4",
        "2.10.2",
        "2.11.1",
        "3.1.3",
        "3.2.2",
        "3.3.1",
        "3.3.4",
        "3.4.1",
        "3.4.2",
        "3.5.2",
    }
    loaded = _load_pilot_quests()
    missing = core - set(loaded)
    assert not missing, missing
    assert len(loaded) == 101
    for cid in core:
        q = loaded[cid]["quest"]["plainQuestion"]
        assert "요구사항을 실제로 적용" not in q
        done = loaded[cid]["quest"]["actionGuide"]["whenDone"]
        assert "업로드하세요" not in done
        assert "캡처해 업로드" not in done


def test_control_checklist_is_control_specific_for_siblings() -> None:
    from isms_pii_toolkit.control_assessment import list_checklist_controls

    controls = {c["id"]: c for c in list_checklist_controls()}
    a = controls["1.1.1"]["checklistItems"]
    b = controls["1.1.2"]["checklistItems"]
    c = controls["2.7.1"]["checklistItems"]
    d = controls["2.7.2"]["checklistItems"]
    assert a != b
    assert c != d
    assert any("경영진" in item for item in a)
    assert any("CISO" in item or "보호책임자" in item for item in b)
    assert any("암호화 대상" in item for item in c)
    assert any("암호키" in item or "키" in item for item in d)


def test_checklist_items_use_declarative_endings() -> None:
    import re

    from isms_pii_toolkit.control_assessment import checklist_as_statement, list_checklist_controls

    assert checklist_as_statement("기록이 있는가") == "기록이 있다"
    assert checklist_as_statement("최신 상태인가") == "최신 상태이다"
    assert checklist_as_statement("이미 반영되어 있다") == "이미 반영되어 있다"

    ga = re.compile(r"(는가|인가|은가|운가)$")
    for control in list_checklist_controls():
        for item in control.get("checklistItems") or []:
            assert not ga.search(str(item).strip()), f"{control['id']}: {item}"
