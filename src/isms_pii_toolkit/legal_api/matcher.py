from __future__ import annotations

import re
from dataclasses import dataclass

from .models import InterpretationRecord, LawReference
from .parser import extract_law_references


@dataclass(frozen=True)
class InterpretationMatch:
    interpretation_id: str
    score: int
    reasons: tuple[str, ...]
    review_status: str = "AUTO_SUGGESTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "interpretationId": self.interpretation_id,
            "matchScore": self.score,
            "matchReasons": list(self.reasons),
            "reviewStatus": self.review_status,
        }


def control_law_references(control_record: dict[str, object]) -> list[LawReference]:
    refs: list[LawReference] = []
    for law_text in control_record.get("laws") or []:  # type: ignore[union-attr]
        for ref in extract_law_references(str(law_text)):
            if ref not in refs:
                refs.append(ref)
    area_id = str(control_record.get("areaId") or "")
    if not refs and area_id in {"1", "2"}:
        refs.append(LawReference(
            "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
            "제47조",
        ))
    return refs


def match_interpretation(
    control_record: dict[str, object],
    interpretation: InterpretationRecord,
) -> InterpretationMatch | None:
    control_refs = control_law_references(control_record)
    score = 0
    reasons: list[str] = []
    has_strong_article_match = False

    for control_ref in control_refs:
        for interpretation_ref in interpretation.related_laws:
            if _law_key(control_ref.law_name) != _law_key(interpretation_ref.law_name):
                continue
            strong_article_match = (
                control_ref.article
                and control_ref.article == interpretation_ref.article
                and (
                    control_ref.article in interpretation.title
                    or len(interpretation.related_laws) <= 3
                )
            )
            if strong_article_match:
                has_strong_article_match = True
                score += 50
                reasons.append(f"{control_ref.law_name} {control_ref.article} 일치")
            else:
                score += 20
                reasons.append(f"관련 법령 {control_ref.law_name} 일치")
            break

    title = str(control_record.get("title") or "")
    keywords = [token for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", title) if token not in {"개인정보", "보호조치"}]
    haystack = " ".join(filter(None, [interpretation.title, interpretation.question, interpretation.answer]))
    matched = [keyword for keyword in keywords if keyword in haystack]
    if matched:
        score += min(20, len(matched) * 5)
        reasons.append(f"통제 핵심어 일치: {', '.join(matched[:3])}")

    if interpretation.temporal_status == "REVIEW_REQUIRED":
        score -= 25
        reasons.append("해석 이후 법령 개정 가능성")
    elif interpretation.temporal_status == "SUPERSEDED":
        score -= 50
        reasons.append("후속 법령·해석으로 대체됨")

    # 법령명만 같은 해석례는 범위가 지나치게 넓다. 최소 한 개 조문이 정확히
    # 일치하거나 그에 준하는 강한 근거가 있을 때만 통제 후보로 노출한다.
    if any(ref.article for ref in control_refs) and not has_strong_article_match:
        return None
    if score < 50:
        return None
    return InterpretationMatch(
        interpretation_id=interpretation.interpretation_id,
        score=max(0, min(100, score)),
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _law_key(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()
