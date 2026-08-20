from __future__ import annotations

import re
from dataclasses import dataclass

from .models import InterpretationRecord, LawReference
from .parser import extract_law_references, law_key


_GENERIC_KEYWORDS = {
    "관리", "이용", "수집", "현황", "보안", "보호", "조치", "처리",
    "제공", "제한", "관련", "기준", "사항", "목적", "동의", "정보",
    "시스템", "운영", "개발", "외부", "내부", "해당", "경우",
    "개인정보", "보호조치", "목적의", "법령에", "하여야",
}
_SHORT_KEYWORDS_KEEP = {"위탁", "수탁", "외주", "열람", "파기", "접속", "로그"}


@dataclass(frozen=True)
class InterpretationMatch:
    interpretation_id: str
    score: int
    reasons: tuple[str, ...]
    review_status: str = "AUTO_SUGGESTED"
    label: str = "조문 일치"

    def to_dict(self) -> dict[str, object]:
        return {
            "interpretationId": self.interpretation_id,
            "matchScore": self.score,
            "matchLabel": self.label,
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
    interp_refs = interpretation_law_references(interpretation)
    score = 0
    reasons: list[str] = []
    has_strong_article_match = False

    for control_ref in control_refs:
        for interpretation_ref in interp_refs:
            if law_key(control_ref.law_name) != law_key(interpretation_ref.law_name):
                continue
            if control_ref.article and articles_match(control_ref.article, interpretation_ref.article):
                has_strong_article_match = True
                score += 50
                reasons.append(f"{control_ref.law_name} {control_ref.article} 일치")
            else:
                score += 20
                reasons.append(f"관련 법령 {control_ref.law_name} 일치")
            break

    matched_keywords = _matched_keywords(control_record, interpretation)
    if matched_keywords:
        score += min(20, len(matched_keywords) * 5)
        reasons.append(f"통제 핵심어 일치: {', '.join(matched_keywords[:3])}")

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
        label=_match_label(score, bool(matched_keywords)),
    )


def interpretation_law_references(interpretation: InterpretationRecord) -> list[LawReference]:
    refs: list[LawReference] = []
    for text in (interpretation.title, interpretation.question, interpretation.answer):
        for ref in extract_law_references(text or ""):
            if ref not in refs:
                refs.append(ref)
    for ref in interpretation.related_laws:
        if ref not in refs:
            refs.append(ref)
    return _drop_parent_articles(refs)


def articles_match(left: str | None, right: str | None) -> bool:
    return _article_key(left) == _article_key(right) and bool(_article_key(left))


def _drop_parent_articles(refs: list[LawReference]) -> list[LawReference]:
    branched = {
        (law_key(ref.law_name), _base_article(ref.article))
        for ref in refs
        if _article_branch(ref.article)
    }
    out: list[LawReference] = []
    for ref in refs:
        base = _base_article(ref.article)
        if ref.article and not _article_branch(ref.article) and (law_key(ref.law_name), base) in branched:
            continue
        out.append(ref)
    return out


def _article_key(article: str | None) -> str:
    return re.sub(r"\s+", "", article or "")


def _base_article(article: str | None) -> str:
    return re.sub(r"의\d+$", "", _article_key(article))


def _article_branch(article: str | None) -> str | None:
    match = re.search(r"의(\d+)$", _article_key(article))
    return match.group(1) if match else None


def _matched_keywords(control_record: dict[str, object], interpretation: InterpretationRecord) -> list[str]:
    source = " ".join(filter(None, [
        str(control_record.get("title") or ""),
        str(control_record.get("requirement") or ""),
    ]))
    keywords = []
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", source):
        if token in _GENERIC_KEYWORDS or token in keywords:
            continue
        if len(token) < 3 and token not in _SHORT_KEYWORDS_KEEP:
            continue
        keywords.append(token)
    haystack = " ".join(filter(None, [interpretation.title, interpretation.question, interpretation.answer]))
    return [keyword for keyword in keywords if keyword in haystack]


def _match_label(score: int, has_keywords: bool) -> str:
    if score >= 70:
        return "강한 연결"
    if has_keywords:
        return "조문·핵심어 일치"
    return "조문 일치"
