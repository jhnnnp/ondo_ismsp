"""세션 묶음 모드(area/chain/theme) 테스트."""

from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_assessment import analyze_assessment, bootstrap_assessment
from isms_pii_toolkit.session_bundle import normalize_session_bundle_mode, order_gaps_for_session

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


def test_normalize_session_bundle_mode() -> None:
    assert normalize_session_bundle_mode(None) == "chain"
    assert normalize_session_bundle_mode("area") == "area"
    assert normalize_session_bundle_mode("THEME") == "theme"
    assert normalize_session_bundle_mode("nope") == "chain"


def test_area_mode_keeps_same_category_first() -> None:
    gaps = [
        {
            "controlId": "2.6.1",
            "title": "A",
            "categoryName": "접근통제",
            "areaName": "보호대책",
            "severity": "high",
            "priority": 40,
            "profilePriority": 2,
        },
        {
            "controlId": "2.6.2",
            "title": "B",
            "categoryName": "접근통제",
            "areaName": "보호대책",
            "severity": "medium",
            "priority": 30,
            "profilePriority": 1,
        },
        {
            "controlId": "3.1.1",
            "title": "C",
            "categoryName": "개인정보 수집",
            "areaName": "개인정보",
            "severity": "critical",
            "priority": 90,
            "profilePriority": 5,
        },
    ]
    selected, meta = order_gaps_for_session(
        gaps,
        controls=[{"id": "2.6.1", "relatedControlIds": []}, {"id": "2.6.2", "relatedControlIds": []}],
        mode="area",
        limit=2,
    )
    assert meta["mode"] == "area"
    assert meta["areaLabel"] == "개인정보 수집"
    assert [g["controlId"] for g in selected] == ["3.1.1"]
    categories = {g["categoryName"] for g in selected}
    assert categories == {"개인정보 수집"}


def test_chain_mode_expands_from_seed_relation() -> None:
    gaps = [
        {
            "controlId": "2.7.1",
            "title": "암호정책",
            "categoryName": "암호통제",
            "areaName": "보호대책",
            "severity": "critical",
            "priority": 100,
            "profilePriority": 4,
        },
        {
            "controlId": "2.7.2",
            "title": "키관리",
            "categoryName": "암호통제",
            "areaName": "보호대책",
            "severity": "high",
            "priority": 20,
            "profilePriority": 1,
        },
        {
            "controlId": "1.1.1",
            "title": "무관",
            "categoryName": "관리체계",
            "areaName": "관리체계",
            "severity": "medium",
            "priority": 10,
            "profilePriority": 0,
        },
    ]
    controls = [
        {"id": "2.7.1", "relatedControlIds": ["2.7.2"]},
        {"id": "2.7.2", "relatedControlIds": ["2.7.1"]},
        {"id": "1.1.1", "relatedControlIds": []},
    ]
    selected, meta = order_gaps_for_session(
        gaps,
        controls=controls,
        mode="chain",
        limit=2,
    )
    ids = [g["controlId"] for g in selected]
    assert meta["mode"] == "chain"
    assert ids[0] == "2.7.1"
    assert "2.7.2" in ids


def test_analyze_respects_session_bundle_mode() -> None:
    assessments = bootstrap_assessment()
    for cid in assessments:
        assessments[cid] = "done"
    assessments["2.7.1"] = "unknown"
    assessments["2.7.2"] = "unknown"
    assessments["2.6.1"] = "unknown"
    assessments["3.1.1"] = "unknown"

    chain = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        session_bundle_mode="chain",
        verbalize=False,
    )
    area = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        session_bundle_mode="area",
        verbalize=False,
    )
    theme = analyze_assessment(
        assessments,
        organization_profile=CLOUD_PROFILE,
        session_bundle_mode="theme",
        verbalize=False,
    )

    assert chain["confirmationActionMeta"]["mode"] == "chain"
    assert area["confirmationActionMeta"]["mode"] == "area"
    assert theme["confirmationActionMeta"]["mode"] == "theme"
    assert chain["confirmationActionMeta"]["bundleTitle"]
    assert area["confirmationActionMeta"]["areaLabel"]
    assert theme["confirmationActions"]


def test_analyze_api_accepts_session_bundle_mode() -> None:
    assessments = bootstrap_assessment()
    response = client.post(
        "/controls/analyze",
        json={
            "assessments": assessments,
            "organizationProfile": CLOUD_PROFILE,
            "sessionBundleMode": "theme",
        },
    )
    assert response.status_code == 200
    data = response.json()
    meta = data["confirmationActionMeta"]
    assert meta["mode"] == "theme"
    assert "bundleTitle" in meta
    assert "bundleSummary" in meta
