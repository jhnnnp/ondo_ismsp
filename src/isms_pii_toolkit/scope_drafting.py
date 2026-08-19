"""조직 프로파일로부터 인증 범위 검토용 초안을 만든다."""

from __future__ import annotations

from typing import Mapping

from .organization_profile import (
    HEADCOUNT_LABELS,
    INDUSTRY_LABELS,
    OrganizationContext,
    pii_volume_label,
)
from .profile_evidence import build_minimum_evidence_pack
from .profile_prioritization import FOUNDATION_CONTROLS, suggested_scenario_ids

DISCLAIMER = (
    "자체진단용 범위 검토 초안입니다. 최종 범위/제외 근거는 "
    "경영진/보안 책임자/개인정보 보호책임자가 "
    "자산목록/흐름도/위탁계약/클라우드 책임분담과 맞춰 확정하세요."
)


def build_scope_draft(
    context: OrganizationContext,
    review: Mapping[str, object] | None = None,
) -> dict[str, object]:
    candidate_items = _candidate_items(context)
    questions = _confirmation_questions(context)

    included_ids = _resolve_included_ids(candidate_items, review)
    answered_ids = _resolve_answered_ids(questions, review)

    for item in candidate_items:
        item["included"] = item["id"] in included_ids
    for question in questions:
        question["answered"] = question["id"] in answered_ids

    priority_ids = set(FOUNDATION_CONTROLS)
    for item in candidate_items:
        if item["included"]:
            priority_ids.update(item["relatedControlIds"])

    unanswered = [question["prompt"] for question in questions if not question["answered"]]
    excluded = [item for item in candidate_items if not item["included"]]
    review_notes: list[str] = []
    if unanswered:
        review_notes.append(
            f"아직 확인하지 않은 범위 질문 {len(unanswered)}건이 있습니다. "
            "공유 인프라/제외 영향/데이터 흐름부터 정리하세요."
        )
    if excluded:
        review_notes.append(
            "제외한 구간이 포함 범위와 계정/DB/로그/배치를 공유하면 제외 근거가 약해집니다. "
            "분리 운영 또는 ‘영향 없음’ 근거를 남기세요."
        )
        priority_ids.update({"1.1.4", "1.2.1"})

    evidence_pack = build_minimum_evidence_pack(context)

    return {
        "status": "draft",
        "disclaimer": DISCLAIMER,
        "boundaries": [
            {
                "type": item["type"],
                "title": item["title"],
                "draft": item["draft"],
            }
            for item in candidate_items
            if item["included"]
        ],
        "candidateItems": candidate_items,
        "confirmationQuestions": [question["prompt"] for question in questions],
        "confirmationItems": questions,
        "includedItemIds": sorted(included_ids),
        "answeredQuestionIds": sorted(answered_ids),
        "unansweredQuestions": unanswered,
        "reviewNotes": review_notes,
        "priorityControlIds": sorted(priority_ids, key=_control_sort),
        "suggestedScenarioIds": suggested_scenario_ids(context),
        "minimumEvidencePack": evidence_pack,
    }


def _candidate_items(context: OrganizationContext) -> list[dict[str, object]]:
    industry = INDUSTRY_LABELS.get(context.industry, context.industry)
    headcount = HEADCOUNT_LABELS.get(context.headcount_band, context.headcount_band)
    volume = pii_volume_label(context.pii_volume)
    items: list[dict[str, object]] = [
        {
            "id": "org-roles",
            "type": "organization",
            "title": "조직/역할 경계",
            "draft": (
                f"{headcount} 기준으로 개인정보 처리/접근승인/보안운영 역할과 "
                "겸직/대행 관계를 표로 정리합니다."
            ),
            "relatedControlIds": ["1.1.2", "1.1.3", "1.1.4"],
            "defaultIncluded": True,
        },
        {
            "id": "service-flow",
            "type": "service",
            "title": "서비스/개인정보 처리 경계",
            "draft": (
                f"{industry} 서비스의 수집→이용/제공→보관→파기 흐름과 "
                "동의/고지/목적 제한이 적용되는 채널/시스템을 포함합니다."
            ),
            "relatedControlIds": ["1.1.4", "1.2.2", "3.2.1"],
            "defaultIncluded": True,
        },
        {
            "id": "systems-data",
            "type": "system",
            "title": "정보시스템/데이터 경계",
            "draft": (
                f"{volume} 처리 규모를 전제로 DB/API/배치/로그/백업/관리자 단말과 "
                "개인정보 저장 위치를 자산목록에 맞춥니다."
            ),
            "relatedControlIds": ["1.2.1", "2.9.4", "3.2.1"],
            "defaultIncluded": True,
        },
    ]
    if context.uses_cloud:
        items.append(
            {
                "id": "cloud-boundary",
                "type": "cloud",
                "title": "클라우드 책임 경계",
                "draft": (
                    "클라우드 계정/리전/VPC/오브젝트 스토리지/관리 콘솔과 "
                    "CSP 책임분담(IaaS/PaaS/SaaS)을 범위서에 명시합니다."
                ),
                "relatedControlIds": ["2.5.1", "2.9.4", "2.10.2", "2.10.3"],
                "defaultIncluded": True,
            }
        )
    if context.uses_outsourcing:
        items.append(
            {
                "id": "vendor-boundary",
                "type": "vendor",
                "title": "위탁/외주 경계",
                "draft": (
                    "수탁사별 처리 업무/접근 시스템/접속경로/재위탁 여부와 "
                    "계약 종료 시 반환/파기 책임을 포함합니다."
                ),
                "relatedControlIds": ["2.3.1", "2.3.2", "2.3.3", "2.3.4", "3.4.1", "3.4.2"],
                "defaultIncluded": True,
            }
        )
    if context.uses_remote_access:
        items.append(
            {
                "id": "remote-boundary",
                "type": "remote",
                "title": "원격접속/재택 운영 경계",
                "draft": (
                    "원격/재택 운영 단말, VPN/ZTNA, MFA, 권한 승인, "
                    "접속/작업 기록이 인증 대상에 포함되는지 확인합니다."
                ),
                "relatedControlIds": ["2.5.1", "2.6.1", "2.6.2", "2.9.4"],
                "defaultIncluded": True,
            }
        )
    if context.processes_rrn:
        items.append(
            {
                "id": "rrn-boundary",
                "type": "sensitive",
                "title": "주민등록번호/고유식별정보 경계",
                "draft": (
                    "주민등록번호 처리의 법적 근거, 저장/전송 암호화, "
                    "별도 접근권한/현황관리 대상을 범위에 분리 표기합니다."
                ),
                "relatedControlIds": ["2.7.1", "2.7.2", "3.1.3", "3.2.1"],
                "defaultIncluded": True,
            }
        )
    if context.industry == "healthcare":
        items.append(
            {
                "id": "healthcare-emr",
                "type": "industry",
                "title": "의료 EMR/진료지원 시스템",
                "draft": (
                    "전자의무기록/처방/검사결과/영상 연계 시스템의 접근통제, "
                    "감사로그, 위탁 운영 구간을 포함합니다."
                ),
                "relatedControlIds": ["2.5.1", "2.9.4", "3.1.3", "3.2.1"],
                "defaultIncluded": True,
            }
        )
    if context.industry == "finance":
        items.append(
            {
                "id": "finance-core",
                "type": "industry",
                "title": "금융 고객/거래 시스템",
                "draft": (
                    "고객 식별정보/거래/조회/이체 관련 저장/전송 경로와 "
                    "권한분리/암호화 적용 구간을 포함합니다."
                ),
                "relatedControlIds": ["2.7.1", "2.9.4", "3.2.1", "3.2.2"],
                "defaultIncluded": True,
            }
        )
    return items


def _confirmation_questions(context: OrganizationContext) -> list[dict[str, object]]:
    questions: list[dict[str, object]] = [
        {
            "id": "shared-infra",
            "prompt": (
                "인증 대상과 제외 대상이 같은 IdP/AD, DB, 로그 저장소, "
                "배치 서버를 쓰지 않는지 확인했나요?"
            ),
        },
        {
            "id": "lifecycle-path",
            "prompt": (
                "개인정보 수집부터 파기까지 시스템/파일/담당자/보관기간을 "
                "흐름도 수준으로 설명할 수 있나요?"
            ),
        },
        {
            "id": "asset-diagram-match",
            "prompt": (
                "범위서의 자산/시스템 목록이 최신 네트워크도/클라우드 구성/CMDB와 "
                "맞는지 대조했나요?"
            ),
        },
        {
            "id": "exclusion-impact",
            "prompt": (
                "제외 구간이 포함 구간의 보안(기밀성/무결성/가용성)에 영향 없다는 "
                "근거(분리/접근차단/계약)가 있나요?"
            ),
        },
    ]
    if context.uses_cloud:
        questions.append(
            {
                "id": "cloud-ownership",
                "prompt": (
                    "클라우드 계정(빌링)/관리자 권한/리전, 로그/감사 보관 위치와 "
                    "CSP 책임분담표가 최신본으로 준비되어 있나요?"
                ),
            }
        )
    if context.uses_outsourcing:
        questions.append(
            {
                "id": "vendor-access",
                "prompt": (
                    "수탁사가 접근하는 개인정보 항목/시스템/접속경로와 재위탁 현황, "
                    "보안요구사항/점검 주기가 계약/대장에 반영되어 있나요?"
                ),
            }
        )
    if context.uses_remote_access:
        questions.append(
            {
                "id": "remote-controls",
                "prompt": (
                    "원격/재택 운영자의 단말 보안, VPN/ZTNA, MFA, 권한 승인, "
                    "접속/작업 기록이 인증 범위와 운영절차에 포함되나요?"
                ),
            }
        )
    if context.processes_rrn:
        questions.append(
            {
                "id": "rrn-legal-basis",
                "prompt": (
                    "주민등록번호 처리의 법적 근거, 저장/전송 암호화, "
                    "별도 접근권한/처리 현황을 증적으로 제시할 수 있나요?"
                ),
            }
        )
    return questions


def _resolve_included_ids(
    candidate_items: list[dict[str, object]],
    review: Mapping[str, object] | None,
) -> set[str]:
    defaults = {str(item["id"]) for item in candidate_items if item.get("defaultIncluded")}
    if not review:
        return defaults
    raw = review.get("includedItemIds", review.get("included_item_ids"))
    if raw is None:
        return defaults
    allowed = {str(item["id"]) for item in candidate_items}
    return {str(item_id) for item_id in raw if str(item_id) in allowed}


def _resolve_answered_ids(
    questions: list[dict[str, object]],
    review: Mapping[str, object] | None,
) -> set[str]:
    if not review:
        return set()
    raw = review.get("answeredQuestionIds", review.get("answered_question_ids"))
    if raw is None:
        return set()
    allowed = {str(question["id"]) for question in questions}
    return {str(question_id) for question_id in raw if str(question_id) in allowed}


def _control_sort(control_id: str) -> list[int]:
    return [int(part) for part in control_id.split(".")]
