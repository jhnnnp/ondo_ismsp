"""조직 프로파일 기반 최소 증적 세트 (업로드 GRC가 아닌 점검 목록)."""

from __future__ import annotations

from .organization_profile import (
    HEADCOUNT_LABELS,
    INDUSTRY_LABELS,
    OrganizationContext,
    pii_volume_label,
)
from .profile_prioritization import FOUNDATION_CONTROLS


def build_minimum_evidence_pack(context: OrganizationContext | None) -> dict[str, object] | None:
    if context is None:
        return None

    items: list[dict[str, object]] = [
        {
            "id": "scope-statement",
            "title": "인증 범위서(초안/제외 근거 포함)",
            "why": "서비스/시스템/조직/물리/클라우드 경계와 제외 사유를 심사원에게 설명하는 기준 문서",
            "relatedControlIds": sorted(FOUNDATION_CONTROLS, key=_control_sort),
            "required": True,
        },
        {
            "id": "policy-approval",
            "title": "정보보호/개인정보보호 정책 승인본",
            "why": "정책 수립/개정/경영진 승인 이력을 보여주는 기본 증적",
            "relatedControlIds": ["1.1.1", "1.1.5", "2.1.1"],
            "required": True,
        },
        {
            "id": "asset-inventory",
            "title": "정보자산/개인정보 현황표",
            "why": "보유 항목/보관위치/책임자/보관기간이 자산식별/현황관리의 입력값이 됨",
            "relatedControlIds": ["1.2.1", "3.2.1"],
            "required": True,
        },
        {
            "id": "risk-assessment",
            "title": "위험평가 결과 및 보호대책 선정표",
            "why": "위험 식별/평가와 보호대책 선정/잔여위험 수용의 근거",
            "relatedControlIds": ["1.2.3", "1.2.4"],
            "required": context.headcount_band != "1-50",
        },
    ]

    if context.uses_cloud:
        items.append(
            {
                "id": "cloud-shared-responsibility",
                "title": "클라우드 책임분담표/계정/리전 목록",
                "why": "계정 소유/관리자 권한/리전/로그 보관 위치와 CSP/자사 책임 경계를 증명",
                "relatedControlIds": ["2.5.1", "2.9.4", "2.10.2", "2.10.3"],
                "required": True,
            }
        )
    if context.uses_outsourcing:
        items.append(
            {
                "id": "vendor-contracts",
                "title": "수탁사 계약서/보안조항/재위탁 현황",
                "why": "위탁 범위/보안요구/재위탁/점검/파기 책임이 문서화되어 있어야 함",
                "relatedControlIds": ["2.3.1", "2.3.2", "3.4.1"],
                "required": True,
            }
        )
    if context.uses_remote_access:
        items.append(
            {
                "id": "remote-access-logs",
                "title": "원격접속 VPN/MFA 설정과 접속기록 샘플",
                "why": "원격 운영자 인증/권한/접속/작업 기록의 운영 실재를 확인",
                "relatedControlIds": ["2.5.3", "2.6.1", "2.9.4"],
                "required": True,
            }
        )
    if context.processes_rrn or context.pii_volume == "high":
        items.append(
            {
                "id": "crypto-and-rrn",
                "title": "암호화 적용 현황/주민등록번호 처리 근거",
                "why": "고유식별/민감정보 보호와 처리 현황관리를 연결하는 핵심 증적",
                "relatedControlIds": ["2.7.1", "2.7.2", "3.1.3", "3.2.1"],
                "required": True,
            }
        )
    if context.industry in {"healthcare", "finance", "public"}:
        industry = INDUSTRY_LABELS.get(context.industry, context.industry)
        items.append(
            {
                "id": "industry-ops-log",
                "title": f"{industry} 핵심 시스템 접근/처리 로그 샘플",
                "why": "업종 핵심 처리 구간의 추적 가능성/권한오남용 탐지 가능성을 보여줌",
                "relatedControlIds": ["2.9.4", "2.9.5", "3.2.1"],
                "required": True,
            }
        )

    required_count = sum(1 for item in items if item["required"])
    headcount = HEADCOUNT_LABELS.get(context.headcount_band, context.headcount_band)
    industry = INDUSTRY_LABELS.get(context.industry, context.industry)
    volume = pii_volume_label(context.pii_volume, with_short=False)
    return {
        "summary": (
            f"{headcount} / {industry} / 개인정보 {volume} 기준 "
            f"최소 증적 후보 {len(items)}건(필수 {required_count}건). "
            "업로드/합격 판정이 아니라 심사 전 준비 체크리스트입니다."
        ),
        "items": items,
        "requiredCount": required_count,
        "totalCount": len(items),
    }


def _control_sort(control_id: str) -> list[int]:
    return [int(part) for part in control_id.split(".")]
