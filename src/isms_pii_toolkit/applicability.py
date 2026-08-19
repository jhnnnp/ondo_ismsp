"""프로파일 기반 통제 적용성(N/A) 규칙 — 결정론, LLM 비개입.

UI에서 의미 있는 규칙은 사실상 하나다:
클라우드만 사용하고 자체 전산실이 없으면 물리/전산실 6개(2.4.1~2.4.6)를 N/A.
"""

from __future__ import annotations

from .organization_profile import OrganizationContext

# 클라우드만 쓰고 자체 전산실/IDC가 없을 때 물리/전산실 계열을 N/A 처리.
# 2.4.7(업무환경 보안)은 사무실이 있으면 여전히 적용.
PHYSICAL_DC_CONTROLS = frozenset(
    {"2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.5", "2.4.6"}
)

CLOUD_ONLY_NO_DC = "cloud-only-no-dc"


def profile_tags_for_applicability(context: OrganizationContext | None) -> frozenset[str]:
    if context is None:
        return frozenset()
    tags = set(context.tags)
    if context.uses_cloud and not context.has_on_prem_facility:
        tags.add(CLOUD_ONLY_NO_DC)
    return frozenset(tags)


def resolve_applicability(
    control_id: str,
    context: OrganizationContext | None,
) -> dict[str, object]:
    """통제가 적용되는지 판정. applicable=False면 N/A."""
    tags = profile_tags_for_applicability(context)
    if CLOUD_ONLY_NO_DC in tags and control_id in PHYSICAL_DC_CONTROLS:
        return {
            "applicable": False,
            "level": "na",
            "reason": "클라우드만 사용하고 자체 전산실/IDC가 없어 물리/전산실 통제는 해당 없음",
            "ruleId": CLOUD_ONLY_NO_DC,
        }
    return {
        "applicable": True,
        "level": None,
        "reason": None,
        "ruleId": None,
    }


def apply_na_to_assessments(
    assessments: dict[str, str],
    context: OrganizationContext | None,
    control_ids: list[str] | None = None,
) -> tuple[dict[str, str], list[dict[str, object]]]:
    """프로파일 규칙으로 N/A를 강제 적용하고, 더 이상 해당 없으면 sticky na를 해제한다."""
    ids = control_ids or list(assessments.keys())
    merged = dict(assessments)
    notes: list[dict[str, object]] = []
    for control_id in ids:
        decision = resolve_applicability(control_id, context)
        if not decision["applicable"]:
            merged[control_id] = "na"
            notes.append(
                {
                    "controlId": control_id,
                    "reason": decision["reason"],
                    "ruleId": decision["ruleId"],
                }
            )
        elif merged.get(control_id) == "na":
            # 프로파일이 바뀌어 다시 적용 대상이면 미점검으로 되돌린다.
            merged[control_id] = "unknown"
    return merged, notes
