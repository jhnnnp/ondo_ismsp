from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from .models import InterpretationRecord, LawArticleRecord, LawDocumentRecord
from .models import LawReference

LAW_GO_KR_BASE = "https://www.law.go.kr"
_ARTICLE_RE = re.compile(r"제\s*(\d+)\s*조(?:의\s*(\d+))?")
_LAW_BLOCK_RE = re.compile(
    r"(?P<law>[가-힣A-Za-z0-9ㆍ·\s]+?(?:법|법률|시행령|시행규칙|규정|기준|고시))\s*"
    r"(?P<articles>제\s*\d+\s*조(?:의\s*\d+)?(?:\s*(?:,|및|부터|~|-|내지)\s*제?\s*\d+\s*조(?:의\s*\d+)?)*)"
)
_LAW_NAME_ALIASES = {
    "정보통신망법": "정보통신망이용촉진및정보보호등에관한법률",
    "정보통신망이용촉진및정보보호등에관한법률": "정보통신망이용촉진및정보보호등에관한법률",
}
_SKIP_LAW_NAME = re.compile(r"^(같은\s*[법조항호]|법|법률|시행령|시행규칙)$")
_NOISE_LAW_NAME = re.compile(r"(표준국어|사전 참조|판결례|해석례|결정례|이유서|심사보고서)")


class LegalXmlError(ValueError):
    pass


def parse_interpretation_list(xml_bytes: bytes) -> list[InterpretationRecord]:
    root = _safe_root(xml_bytes)
    result_code = _find_text(root, "resultCode", "결과코드")
    if result_code and result_code != "00":
        message = _find_text(root, "resultMsg", "결과메세지") or "법령 API 오류"
        raise LegalXmlError(f"법령 API 오류 {result_code}: {message}")

    records: list[InterpretationRecord] = []
    for node in root.iter():
        if _local_name(node.tag).lower() != "expc":
            continue
        serial = _child_text(node, "법령해석례일련번호")
        title = _child_text(node, "안건명")
        if not serial or not title:
            continue
        detail_path = _child_text(node, "법령해석례상세링크")
        records.append(
            InterpretationRecord(
                interpretation_id=f"expc-{serial}",
                serial_number=serial,
                case_number=_child_text(node, "안건번호") or None,
                title=title,
                question_agency=_child_text(node, "질의기관명") or None,
                response_agency=_child_text(node, "회신기관명") or None,
                response_date=_normalize_date(_child_text(node, "회신일자")),
                original_url=normalize_law_go_kr_url(detail_path) if detail_path else None,
            )
        )
    return records


def parse_document_search_list(xml_bytes: bytes, *, target: str) -> list[dict[str, str]]:
    root = _safe_root(xml_bytes)
    item_tag = "law" if target == "law" else "admrul"
    records: list[dict[str, str]] = []
    for node in root.iter():
        if _local_name(node.tag).casefold() != item_tag:
            continue
        values = {_local_name(child.tag): _node_text(child) for child in node}
        if target == "law":
            name = values.get("법령명한글", "")
            link = values.get("법령상세링크", "")
            document_id = values.get("법령ID", "")
            serial = values.get("법령일련번호", "")
        else:
            name = values.get("행정규칙명", "")
            link = values.get("행정규칙상세링크", "")
            document_id = values.get("행정규칙ID", "")
            serial = values.get("행정규칙일련번호", "")
        if name and link and document_id:
            records.append({
                "name": name,
                "detailUrl": normalize_law_go_kr_url(link),
                "documentId": document_id,
                "serialNumber": serial,
                "effectiveDate": _normalize_date(values.get("시행일자")) or "",
                "promulgationDate": _normalize_date(values.get("공포일자") or values.get("발령일자")) or "",
                "ministry": values.get("소관부처명", ""),
                "revisionType": values.get("제개정구분명", ""),
                "currentStatus": values.get("현행연혁구분", "현행") or "현행",
                "documentType": values.get("법령구분명") or values.get("행정규칙종류") or target,
            })
    return records


def parse_law_document(xml_bytes: bytes, *, metadata: dict[str, str], target: str) -> LawDocumentRecord:
    root = _safe_root(xml_bytes)
    articles: list[LawArticleRecord] = []
    if target == "law":
        for node in root.iter():
            if _local_name(node.tag) != "조문단위":
                continue
            number = _child_text(node, "조문번호")
            branch = _child_text(node, "조문가지번호")
            if not number:
                continue
            article = f"제{number}조" + (f"의{branch}" if branch and branch != "0" else "")
            texts = _texts_named(node, {"조문내용", "항내용", "호내용", "목내용"})
            title = _child_text(node, "조문제목") or None
            if not title and texts and re.match(r"제\d+(?:의\d+)?장\s", texts[0]):
                continue
            articles.append(LawArticleRecord(
                article=article,
                title=title,
                text="\n".join(texts),
                effective_date=_normalize_date(_child_text(node, "조문시행일자")),
            ))
    else:
        for node in root.iter():
            if _local_name(node.tag) != "조문내용":
                continue
            text = _node_text(node)
            match = re.match(r"제\s*(\d+)\s*조(?:의\s*(\d+))?(?:\(([^)]+)\))?", text)
            if not match:
                continue
            articles.append(LawArticleRecord(
                article=format_article(match.group(1), match.group(2)),
                title=(match.group(3) or "").strip() or None,
                text=text,
                effective_date=metadata.get("effectiveDate") or None,
            ))
    detail_url = metadata.get("detailUrl", "").replace("type=XML", "type=HTML")
    return LawDocumentRecord(
        document_id=f"{target}-{metadata['documentId']}",
        name=metadata["name"],
        document_type=metadata.get("documentType") or target,
        serial_number=metadata.get("serialNumber") or None,
        effective_date=metadata.get("effectiveDate") or None,
        promulgation_date=metadata.get("promulgationDate") or None,
        ministry=metadata.get("ministry") or None,
        revision_type=metadata.get("revisionType") or None,
        current_status=metadata.get("currentStatus") or "현행",
        original_url=detail_url,
        articles=articles,
    )


def parse_interpretation_detail(
    xml_bytes: bytes,
    *,
    fallback: InterpretationRecord | None = None,
) -> InterpretationRecord:
    root = _safe_root(xml_bytes)
    serial = _find_text(root, "법령해석례일련번호", "법령해석일련번호", "ID")
    if not serial and fallback:
        serial = fallback.serial_number
    title = _find_text(root, "안건명", "법령해석례명") or (fallback.title if fallback else "")
    if not serial or not title:
        raise LegalXmlError("법령해석례 상세 응답에 일련번호 또는 안건명이 없습니다.")

    related_texts = [
        text
        for text in (
            _find_text(root, "관련법령"),
            _find_text(root, "관련법령내용"),
            title,
            _find_text(root, "질의요지", "질의내용"),
            _find_text(root, "회답", "답변"),
        )
        if text
    ]
    refs: list[LawReference] = []
    for text in related_texts:
        for ref in extract_law_references(text):
            if ref not in refs:
                refs.append(ref)

    return InterpretationRecord(
        interpretation_id=f"expc-{serial}",
        serial_number=serial,
        case_number=_find_text(root, "안건번호") or (fallback.case_number if fallback else None),
        title=title,
        question_agency=_find_text(root, "질의기관명") or (fallback.question_agency if fallback else None),
        response_agency=_find_text(root, "회신기관명") or (fallback.response_agency if fallback else None),
        response_date=_normalize_date(_find_text(root, "회신일자")) or (fallback.response_date if fallback else None),
        question=_find_text(root, "질의요지", "질의내용"),
        answer=_find_text(root, "회답", "답변"),
        reasoning=_find_text(root, "이유"),
        related_laws=refs,
        original_url=fallback.original_url if fallback else None,
    )


def format_article(number: str, branch: str | None = None) -> str:
    article = f"제{number}조"
    if branch:
        return f"{article}의{branch}"
    return article


def law_key(value: str) -> str:
    compact = re.sub(r"[\s「」ㆍ·]", "", str(value or "")).casefold()
    return _LAW_NAME_ALIASES.get(compact, compact)


def extract_law_references(text: str) -> list[LawReference]:
    normalized = " ".join(str(text).split())
    refs: list[LawReference] = []
    matches = list(_LAW_BLOCK_RE.finditer(normalized))
    previous_law = ""
    for index, match in enumerate(matches):
        law_name = _canonical_law_name(match.group("law"), previous_law)
        if not law_name:
            continue
        previous_law = law_name
        # 안내서 표기는 `제16조(제목), 제19조(제목)`처럼 조문명 사이에
        # 괄호가 들어가므로, 다음 법령명이 시작되기 전까지 조문을 모두 수집한다.
        segment_end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        article_segment = normalized[match.start("articles"):segment_end]
        for number, branch in _ARTICLE_RE.findall(article_segment):
            ref = LawReference(law_name=law_name, article=format_article(number, branch or None))
            if ref not in refs:
                refs.append(ref)
    return refs


def _canonical_law_name(raw: str, previous: str) -> str | None:
    name = str(raw or "").strip(" ,·ㆍ「」")
    if not name or _NOISE_LAW_NAME.search(name):
        return None
    if re.fullmatch(r"같은\s*법", name):
        return previous or None
    compact = re.sub(r"\s+", "", name)
    if _SKIP_LAW_NAME.match(name) or len(compact) < 4:
        return None
    return name


def normalize_law_go_kr_url(path: str) -> str:
    url = urljoin(LAW_GO_KR_BASE, path.strip())
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"law.go.kr", "www.law.go.kr"}:
        raise LegalXmlError("허용되지 않은 법령 상세 링크입니다.")
    return url


def _safe_root(xml_bytes: bytes) -> ElementTree.Element:
    if len(xml_bytes) > 2_000_000:
        raise LegalXmlError("법령 API 응답이 허용 크기를 초과했습니다.")
    upper = xml_bytes[:4096].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise LegalXmlError("외부 엔티티가 포함된 XML은 허용되지 않습니다.")
    try:
        return ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as error:
        raise LegalXmlError("법령 API XML을 파싱할 수 없습니다.") from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ElementTree.Element, name: str) -> str:
    for child in node:
        if _local_name(child.tag) == name:
            return " ".join("".join(child.itertext()).split())
    return ""


def _node_text(node: ElementTree.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def _texts_named(node: ElementTree.Element, names: set[str]) -> list[str]:
    result: list[str] = []
    for child in node.iter():
        if _local_name(child.tag) not in names:
            continue
        text = _node_text(child)
        if text and text not in result:
            result.append(text)
    return result


def _find_text(root: ElementTree.Element, *names: str) -> str | None:
    wanted = set(names)
    for node in root.iter():
        if _local_name(node.tag) in wanted:
            text = " ".join("".join(node.itertext()).split())
            if text:
                return text
    return None


def _normalize_date(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 8:
        return value or None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
