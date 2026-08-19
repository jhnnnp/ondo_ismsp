"""조직 특성에 따른 통제 관련성/우선순위 오버레이.

정렬·추천용 내부 힌트다. 사용자에게 인증 맞춤처럼 약속하지 말 것.
현재 UI는 클라우드/전산실만 노출하므로 uses_cloud 관련 delta가 체감의 대부분이다.
"""

from __future__ import annotations

from .defect_priority import defect_priority_delta, defect_relevance_reasons
from .organization_profile import OrganizationContext, pii_volume_label

FOUNDATION_CONTROLS = frozenset({"1.1.4", "1.1.5", "1.2.1", "1.2.2", "1.2.3", "1.2.4"})
CLOUD_CONTROLS = frozenset({"2.5.1", "2.5.2", "2.6.1", "2.6.2", "2.9.4", "2.9.5", "2.10.2", "2.10.3"})
OUTSOURCING_CONTROLS = frozenset({"2.3.1", "2.3.2", "2.3.3", "2.3.4", "3.4.1", "3.4.2"})
REMOTE_ACCESS_CONTROLS = frozenset({"2.5.1", "2.5.3", "2.6.1", "2.6.2", "2.6.5", "2.9.4"})
HIGH_PII_CONTROLS = frozenset({"2.7.1", "2.7.2", "2.9.4", "2.9.5", "3.2.1", "3.2.2", "3.2.3", "3.5.2"})
RRN_CONTROLS = frozenset({"2.7.1", "2.7.2", "3.1.3", "3.2.1", "3.2.2"})

# Live scenario IDs from control_graph.SCENARIOS
INDUSTRY_SCENARIOS: dict[str, tuple[str, ...]] = {
    "retail": ("retail-cs-log-pii", "membership-data-lifecycle"),
    "healthcare": ("healthcare-emr-access", "retail-cs-log-pii"),
    "public": ("public-citizen-service", "external-developer-access"),
    "finance": ("finance-customer-data", "membership-data-lifecycle"),
    "technology": ("tech-saas-tenant", "cloud-campaign-page", "external-developer-access"),
    "general": ("security-review-certification",),
}


def priority_delta(control_id: str, context: OrganizationContext | None) -> int:
    delta = defect_priority_delta(control_id)
    if context is None:
        return delta
    if context.headcount_band == "1-50" and control_id in FOUNDATION_CONTROLS:
        delta += 3
    if context.uses_cloud and control_id in CLOUD_CONTROLS:
        delta += 3
    if context.uses_outsourcing and control_id in OUTSOURCING_CONTROLS:
        delta += 3
    if context.uses_remote_access and control_id in REMOTE_ACCESS_CONTROLS:
        delta += 2
    if context.pii_volume == "high" and control_id in HIGH_PII_CONTROLS:
        delta += 3
    elif context.pii_volume == "medium" and control_id in HIGH_PII_CONTROLS:
        delta += 1
    if context.processes_rrn and control_id in RRN_CONTROLS:
        delta += 4
    # 간편인증 완화 후보: 삭제가 아니라 우선순위만 약간 낮춤 (힌트)
    try:
        from .official_kb import simple_cert_hints

        hints = simple_cert_hints(context.tags)
        if control_id in set(hints.get("relaxedControlIds") or []):
            delta -= 1
    except Exception:
        pass
    return delta


def relevance_reasons(control_id: str, context: OrganizationContext | None) -> list[str]:
    reasons = defect_relevance_reasons(control_id)
    if context is None:
        return reasons
    if context.headcount_band == "1-50" and control_id in FOUNDATION_CONTROLS:
        reasons.append("소규모 조직의 최소 관리체계/범위/자산 기반 우선 통제")
    if context.uses_cloud and control_id in CLOUD_CONTROLS:
        reasons.append("클라우드 사용에 따른 계정/로그/공개서버 경계 관련")
    if context.uses_outsourcing and control_id in OUTSOURCING_CONTROLS:
        reasons.append("외주/위탁 처리의 계약/감독/재위탁 경계 관련")
    if context.uses_remote_access and control_id in REMOTE_ACCESS_CONTROLS:
        reasons.append("원격접속 환경의 인증/권한/접속기록 관련")
    if context.pii_volume in {"medium", "high"} and control_id in HIGH_PII_CONTROLS:
        reasons.append(
            f"{pii_volume_label(context.pii_volume, with_short=False)} 개인정보 처리 조직의 보호/추적 통제"
        )
    if context.processes_rrn and control_id in RRN_CONTROLS:
        reasons.append("주민등록번호 처리에 따른 제한/암호화/현황관리 통제")
    try:
        from .official_kb import simple_cert_hints

        hints = simple_cert_hints(context.tags)
        if control_id in set(hints.get("relaxedControlIds") or []):
            reasons.append("간편인증 완화 후보(참고) — 삭제가 아니라 확인 우선순위 힌트")
    except Exception:
        pass
    return reasons


def suggested_scenario_ids(context: OrganizationContext | None) -> list[str]:
    if context is None:
        return []
    scenarios = list(INDUSTRY_SCENARIOS.get(context.industry, ()))
    if context.uses_cloud:
        scenarios.append("cloud-campaign-page")
        if context.industry == "technology":
            scenarios.append("tech-saas-tenant")
    if context.uses_outsourcing or context.uses_remote_access:
        scenarios.append("external-developer-access")
    if context.pii_volume == "high" or context.processes_rrn:
        if context.industry == "healthcare":
            scenarios.append("healthcare-emr-access")
        elif context.industry == "finance":
            scenarios.append("finance-customer-data")
        else:
            scenarios.append("membership-data-lifecycle")
    scenarios.append("security-review-certification")
    return list(dict.fromkeys(scenarios))


def bundle_priority_delta(control_ids: list[str] | tuple[str, ...], context: OrganizationContext | None) -> int:
    if not control_ids:
        return 0
    return min(12, sum(priority_delta(control_id, context) for control_id in control_ids) // 2)
