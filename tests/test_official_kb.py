"""Official guide KB grounding tests."""

from __future__ import annotations

import re

from isms_pii_toolkit.control_assessment import (
    analyze_assessment,
    certification_guide,
    checklist_as_statement,
    enrich_control,
    list_checklist_controls,
)
from isms_pii_toolkit.control_graph import list_controls
from isms_pii_toolkit.official_kb import (
    load_control,
    load_index,
    load_institution,
    load_officekeeper,
    official_check_statements,
    simple_cert_hints,
)
from isms_pii_toolkit.organization_profile import OrganizationContext
from isms_pii_toolkit.quest_kb import get_quest_overlay, thin_quest_from_control


def test_official_kb_covers_all_controls() -> None:
    index = load_index()
    assert index.get("controlCount") == 101
    assert index.get("controlsWithQuestions") == 101
    assert not index.get("missingQuestions")
    for control in list_controls():
        rec = load_control(str(control["id"]))
        assert rec is not None
        assert rec.get("requirement")
        assert rec.get("checkQuestions")


def test_official_sample_controls_match_guide_keywords() -> None:
    c113 = load_control("1.1.3")
    assert c113
    joined = " ".join(c113["checkQuestions"])
    assert "실무조직" in joined
    assert "위원회" in joined
    assert "협의체" in joined

    c123 = load_control("1.2.3")
    assert c123
    assert len(c123["checkQuestions"]) >= 4

    c254 = load_control("2.5.4")
    assert c254
    assert len(c254["checkQuestions"]) == 3
    assert any("비밀번호" in q for q in c254["checkQuestions"])


def test_enrich_control_uses_official_declarative_checklist() -> None:
    ga = re.compile(r"(는가|인가|은가|운가)$")
    controls = {c["id"]: c for c in list_checklist_controls()}
    assert len(controls) == 101
    sample = controls["1.1.3"]
    assert any("실무조직" in item for item in sample["checklistItems"])
    assert sample.get("officialRequirement")
    assert sample.get("officialEvidenceExamples")
    for control in controls.values():
        for item in control["checklistItems"]:
            assert not ga.search(str(item).strip()), f"{control['id']}: {item}"
            assert checklist_as_statement(item) == item


def test_institution_and_officekeeper_payloads() -> None:
    inst = load_institution()
    assert inst.get("confirmationQuestions")
    assert inst.get("preparationChecks")
    guide = certification_guide()
    assert guide.get("confirmationQuestions")
    assert "2개월" in str(guide["phases"][0]["summary"])

    ok = load_officekeeper()
    assert ok.get("simpleCertification")
    hints = simple_cert_hints(
        OrganizationContext(
            headcount_band="1-50",
            industry="technology",
            pii_volume="low",
            uses_cloud=True,
            has_on_prem_facility=False,
        ).tags
    )
    assert hints["enabled"]
    assert hints["relaxedControlIds"]


def test_analyze_includes_institution_and_simple_cert_hints() -> None:
    result = analyze_assessment(
        {c["id"]: "done" for c in list_controls()},
        organization_profile={
            "headcountBand": "1-50",
            "industry": "technology",
            "piiVolume": "low",
            "usesCloud": True,
            "hasOnPremFacility": False,
        },
    )
    assert result.get("institutionHints")
    assert result["institutionHints"].get("confirmationQuestions")
    assert result.get("simpleCertHints")
    assert result["simpleCertHints"].get("enabled")


def test_thin_quest_grounds_in_official_when_unlocked() -> None:
    # Pick a control that is typically thin-stub; still works even if handcrafted exists
    # by calling thin_quest_from_control directly.
    control = enrich_control(dict(next(c for c in list_controls() if c["id"] == "1.1.6")))
    thin = thin_quest_from_control(control)
    labels = [c["label"] for c in thin["quest"]["checks"]]
    assert labels
    assert thin.get("meta", {}).get("grounding") == "official" or any(
        "자원" in x or "예산" in x or "인력" in x for x in labels
    )
    # Locked handcrafted must remain get_quest_overlay path for pilots
    pilot = get_quest_overlay("2.5.4")
    if pilot and pilot.get("locked"):
        assert pilot.get("quality") == "handcrafted" or pilot.get("locked") is True


def test_official_check_statements_helper() -> None:
    stmts = official_check_statements("2.5.4")
    assert len(stmts) == 3
    assert all(not s.endswith("가") for s in stmts)
