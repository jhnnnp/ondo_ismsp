from __future__ import annotations

from isms_pii_toolkit.organization_profile import normalize_organization_profile
from isms_pii_toolkit.profile_prioritization import (
    priority_delta,
    relevance_reasons,
    suggested_scenario_ids,
)


def test_small_cloud_profile_prioritizes_foundation_and_cloud_controls() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "1-50",
            "industry": "technology",
            "piiVolume": "low",
            "usesCloud": True,
        }
    )
    assert context is not None
    assert priority_delta("1.1.4", context) > priority_delta("2.4.1", context)
    assert priority_delta("2.10.2", context) > priority_delta("2.4.1", context)
    assert relevance_reasons("2.10.2", context)
    assert "cloud-campaign-page" in suggested_scenario_ids(context)
    assert "tech-saas-tenant" in suggested_scenario_ids(context)


def test_outsourcing_and_rrn_flags_raise_distinct_control_families() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "51-300",
            "industry": "general",
            "piiVolume": "medium",
            "usesOutsourcing": True,
            "processesRrn": True,
        }
    )
    assert context is not None
    assert priority_delta("2.3.1", context) > 0
    assert priority_delta("3.1.3", context) > 0
    assert priority_delta("2.4.1", context) == 0


def test_absent_context_keeps_only_empirical_defect_overlay() -> None:
    from isms_pii_toolkit.defect_priority import defect_priority_delta

    # No org profile → profile overlay 0; empirical defect/casebook weight may remain.
    assert priority_delta("2.4.1", None) == 0
    assert priority_delta("1.1.4", None) == defect_priority_delta("1.1.4")
    assert suggested_scenario_ids(None) == []
    # 2.4.1 has no defect/case weight → no relevance reasons without profile
    assert relevance_reasons("2.4.1", None) == []


def test_outsourcing_relevance_reason_is_emitted() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "51-300",
            "industry": "public",
            "piiVolume": "low",
            "usesOutsourcing": True,
        }
    )
    assert context is not None
    assert any("외주/위탁" in reason for reason in relevance_reasons("2.3.1", context))
    assert "external-developer-access" in suggested_scenario_ids(context)
    assert "public-citizen-service" in suggested_scenario_ids(context)


def test_high_pii_and_remote_access_raise_related_families() -> None:
    context = normalize_organization_profile(
        {
            "headcountBand": "301+",
            "industry": "healthcare",
            "piiVolume": "high",
            "usesRemoteAccess": True,
            "processesRrn": True,
        }
    )
    assert context is not None
    assert priority_delta("2.9.4", context) > priority_delta("2.4.1", context)
    assert priority_delta("2.6.1", context) > 0
    assert any("대규모 개인정보 처리" in reason for reason in relevance_reasons("2.9.4", context))
    assert any("원격접속" in reason for reason in relevance_reasons("2.6.1", context))
    assert any("주민등록번호" in reason for reason in relevance_reasons("3.1.3", context))
    assert "healthcare-emr-access" in suggested_scenario_ids(context)


def test_medium_pii_applies_smaller_boost_than_high() -> None:
    medium = normalize_organization_profile(
        {"headcountBand": "51-300", "industry": "general", "piiVolume": "medium"}
    )
    high = normalize_organization_profile(
        {"headcountBand": "51-300", "industry": "general", "piiVolume": "high"}
    )
    assert medium is not None and high is not None
    assert priority_delta("2.7.1", high) > priority_delta("2.7.1", medium) > 0


def test_finance_and_technology_get_domain_scenarios() -> None:
    finance = normalize_organization_profile(
        {"headcountBand": "51-300", "industry": "finance", "piiVolume": "high", "processesRrn": True}
    )
    tech = normalize_organization_profile(
        {"headcountBand": "1-50", "industry": "technology", "piiVolume": "medium", "usesCloud": True}
    )
    assert finance is not None and tech is not None
    assert "finance-customer-data" in suggested_scenario_ids(finance)
    assert "tech-saas-tenant" in suggested_scenario_ids(tech)
