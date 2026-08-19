from __future__ import annotations

import re
from urllib.parse import quote

from .casebook import cases_for_control, load_casebook_records
from .matcher import control_law_references, match_interpretation
from .repository import LegalRepository
from ..official_kb import load_control
from ..official_text import is_usable_evidence, sanitize_official_text
from ..official_guidance import guidance_for_control

DISCLAIMER = (
    "법령해석례는 구체적 사안에 대한 행정해석이며 현재 ISMS-P 인증 적합성을 직접 확정하지 않습니다. "
    "현행 법령과 조직의 사실관계를 함께 검토해야 합니다."
)


def search_interpretations(
    *,
    query: str | None = None,
    law_name: str | None = None,
    article: str | None = None,
    repository: LegalRepository | None = None,
) -> dict[str, object]:
    repo = repository or LegalRepository()
    records = repo.search(query=query, law_name=law_name, article=article)
    return {
        "total": len(records),
        "items": [record.to_dict() for record in records],
        "disclaimer": DISCLAIMER,
    }


def interpretation_detail(
    interpretation_id: str,
    *,
    repository: LegalRepository | None = None,
) -> dict[str, object] | None:
    record = (repository or LegalRepository()).get(interpretation_id)
    if record is None:
        return None
    payload = record.to_dict()
    payload["disclaimer"] = DISCLAIMER
    return payload


def control_legal_basis(
    control_id: str,
    *,
    repository: LegalRepository | None = None,
) -> dict[str, object] | None:
    control = load_control(control_id)
    if control is None:
        return None
    repo = repository or LegalRepository()
    refs = control_law_references(control)
    explicit_refs = control_law_references({**control, "areaId": ""})
    matches: list[tuple[object, object]] = []
    for record in repo.all():
        match = match_interpretation(control, record)
        if match is not None:
            matches.append((match, record))
    matches.sort(key=lambda pair: pair[0].score, reverse=True)  # type: ignore[union-attr]
    interpretations: list[dict[str, object]] = []
    for match, record in matches:
        item = record.to_dict()  # type: ignore[union-attr]
        item.update(match.to_dict())  # type: ignore[union-attr]
        interpretations.append(item)
    source = control.get("source") or {}
    return {
        "controlId": control_id,
        "controlTitle": str(control.get("title") or ""),
        "requirementSummary": _clean(control.get("requirement")),
        "auditQuestions": _clean_list(control.get("checkQuestions"), limit=8),
        "evidenceExamples": _evidence_list(control.get("evidenceExamples"), limit=8),
        "defectExamples": _defect_list(control.get("defectExamples"), limit=5),
        "guideSource": {
            "document": str(source.get("doc") or "") or None,
            "pages": [int(page) for page in source.get("pages") or [] if str(page).isdigit()],
        },
        "laws": [
            _enrich_law_reference(
                ref.to_dict(),
                control.get("laws") or [],
                repo,
                basis_type="DIRECT" if ref in explicit_refs else "COMMON_CERTIFICATION_BASIS",
            )
            for ref in refs
        ],
        "interpretations": interpretations,
        "casebookExamples": cases_for_control(control_id),
        "officialGuidance": guidance_for_control(control_id),
        "casebookCorpusSize": len(load_casebook_records()),
        "interpretationCorpusSize": len(repo.all()),
        "interpretationDataStatus": _sync_status(repo),
        "lastUpdatedAt": _sync_timestamp(repo),
        "disclaimer": DISCLAIMER,
    }


def _clean(value: object, *, max_length: int = 1200) -> str | None:
    text = sanitize_official_text(str(value or "")).strip()
    if not text:
        return None
    return text if len(text) <= max_length else f"{text[: max_length - 1].rstrip()}…"


def _clean_list(values: object, *, limit: int, max_length: int = 500) -> list[str]:
    result: list[str] = []
    for raw in list(values or [])[:limit]:  # type: ignore[arg-type]
        text = _clean(raw, max_length=max_length)
        if text and text not in result:
            result.append(text)
    return result


def _evidence_list(values: object, *, limit: int) -> list[str]:
    return [
        text
        for text in _clean_list(values, limit=limit)
        if is_usable_evidence(text)
    ]


def _defect_list(values: object, *, limit: int) -> list[str]:
    results: list[str] = []
    for text in _clean_list(values, limit=limit, max_length=360):
        # 안내서 PDF의 다음 페이지로 잘린 OCR 조각은 공식 사례처럼 노출하지 않는다.
        if len(text) < 45 or not re.search(r"(?:경우|않음|미흡|누락|위반)[.)]?$", text):
            continue
        results.append(text)
    return results


def _enrich_law_reference(
    reference: dict[str, object],
    raw_laws: object,
    repository: LegalRepository,
    *,
    basis_type: str,
) -> dict[str, object]:
    law_name = str(reference.get("lawName") or "")
    article = str(reference.get("article") or "")
    article_title = None
    if article:
        pattern = rf"{re.escape(article)}\s*\(([^)]+)\)"
        for raw in raw_laws:  # type: ignore[union-attr]
            match = re.search(pattern, str(raw))
            if match:
                article_title = sanitize_official_text(match.group(1)).strip() or None
                break
    stored = repository.find_article(law_name, article or None)
    document, stored_article = stored if stored else (None, None)
    return {
        **reference,
        "basisType": basis_type,
        "articleTitle": stored_article.title if stored_article and stored_article.title else article_title,
        "articleText": stored_article.text if stored_article else None,
        "effectiveDate": (stored_article.effective_date if stored_article else None) or (document.effective_date if document else None),
        "promulgationDate": document.promulgation_date if document else None,
        "ministry": document.ministry if document else None,
        "documentType": document.document_type if document else None,
        "currentStatus": document.current_status if document else None,
        "collectedAt": document.collected_at if document else None,
        "sourceUrl": document.original_url if document and document.original_url else (
            f"https://www.law.go.kr/법령/{quote(law_name)}" if law_name else None
        ),
    }


def _sync_timestamp(repository: LegalRepository) -> str | None:
    path = repository.root / "sync_state.json"
    if not path.exists():
        return None
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("lastSuccessfulSync")


def _sync_status(repository: LegalRepository) -> str:
    path = repository.root / "sync_state.json"
    if not path.exists():
        return "NOT_CONFIGURED"
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("status") or "UNKNOWN")
