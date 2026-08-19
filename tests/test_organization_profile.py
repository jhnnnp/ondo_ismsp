from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.organization_profile import normalize_organization_profile
from isms_pii_toolkit.profile_evidence import build_minimum_evidence_pack
from isms_pii_toolkit.scope_drafting import build_scope_draft

client = TestClient(app)


def test_profile_normalization_derives_stable_tags() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "1-50",
            "industry": "technology",
            "piiVolume": "high",
            "usesCloud": True,
            "usesOutsourcing": True,
        }
    )
    assert context is not None
    assert {"size:1-50", "cloud", "outsourcing", "pii:high"} <= set(context.tags)


def test_profile_normalization_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        normalize_organization_profile(
            {"headcountBand": "0", "industry": "general", "piiVolume": "low"}
        )
    with pytest.raises(ValueError):
        normalize_organization_profile(
            {"headcountBand": "1-50", "industry": "unknown", "piiVolume": "low"}
        )
    with pytest.raises(ValueError):
        normalize_organization_profile(
            {"headcountBand": "1-50", "industry": "general", "piiVolume": "huge"}
        )


def test_profile_tags_include_remote_and_rrn() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "51-300",
            "industry": "finance",
            "piiVolume": "medium",
            "usesRemoteAccess": True,
            "processesRrn": True,
        }
    )
    assert context is not None
    assert {"remote-access", "rrn", "size:51-300", "industry:finance"} <= set(context.tags)


def test_scope_draft_covers_cloud_vendor_and_human_confirmation() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "1-50",
            "industry": "technology",
            "piiVolume": "medium",
            "usesCloud": True,
            "usesOutsourcing": True,
            "usesRemoteAccess": True,
            "processesRrn": True,
        }
    )
    assert context is not None
    draft = build_scope_draft(context)
    boundary_types = {row["type"] for row in draft["boundaries"]}
    assert {"organization", "service", "system", "cloud", "vendor"} <= boundary_types
    assert "초안" in draft["disclaimer"]
    assert "1.1.4" in draft["priorityControlIds"]
    assert "3.1.3" in draft["priorityControlIds"]
    assert draft["candidateItems"]
    assert draft["confirmationItems"]
    assert draft["minimumEvidencePack"]["requiredCount"] >= 4
    assert any("주민등록번호" in question for question in draft["confirmationQuestions"])


def test_scope_review_exclusions_and_answers_update_priority() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "1-50",
            "industry": "technology",
            "piiVolume": "low",
            "usesCloud": True,
        }
    )
    assert context is not None
    draft = build_scope_draft(
        context,
        {
            "includedItemIds": ["org-roles", "service-flow"],
            "answeredQuestionIds": ["shared-infra", "lifecycle-path"],
        },
    )
    assert "cloud-boundary" not in draft["includedItemIds"]
    assert "cloud" not in {item["type"] for item in draft["boundaries"]}
    assert draft["unansweredQuestions"]
    assert any("제외한 구간" in note or "제외한 경계" in note for note in draft["reviewNotes"])
    assert "1.1.4" in draft["priorityControlIds"]


def test_minimum_evidence_pack_for_healthcare() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "51-300",
            "industry": "healthcare",
            "piiVolume": "high",
            "processesRrn": True,
        }
    )
    pack = build_minimum_evidence_pack(context)
    assert pack is not None
    ids = {item["id"] for item in pack["items"]}
    assert "crypto-and-rrn" in ids
    assert "industry-ops-log" in ids


def test_profile_and_scope_api_contracts() -> None:
    profile = {
        "headcountBand": "1-50",
        "industry": "technology",
        "piiVolume": "high",
        "usesCloud": True,
        "usesOutsourcing": False,
        "usesRemoteAccess": True,
        "processesRrn": False,
    }
    validated = client.post("/controls/organization-profile/validate", json=profile)
    assert validated.status_code == 200
    assert "cloud" in validated.json()["tags"]

    drafted = client.post(
        "/controls/scope/draft",
        json={
            "organizationProfile": profile,
            "scopeReview": {
                "includedItemIds": ["org-roles", "service-flow", "systems-data", "cloud-boundary"],
                "answeredQuestionIds": ["shared-infra"],
            },
        },
    )
    assert drafted.status_code == 200
    payload = drafted.json()
    assert payload["status"] == "draft"
    assert "tech-saas-tenant" in payload["suggestedScenarioIds"]
    assert "cloud-campaign-page" in payload["suggestedScenarioIds"]
    assert payload["minimumEvidencePack"]["totalCount"] >= 4
    assert payload["candidateItems"]
