from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

TemporalStatus = Literal[
    "CURRENT",
    "POSSIBLY_CURRENT",
    "REVIEW_REQUIRED",
    "SUPERSEDED",
    "UNKNOWN",
]
ReviewStatus = Literal["AUTO_SUGGESTED", "HUMAN_CONFIRMED", "REJECTED"]


@dataclass(frozen=True)
class LawArticleRecord:
    article: str
    title: str | None = None
    text: str = ""
    effective_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article": self.article,
            "title": self.title,
            "text": self.text,
            "effectiveDate": self.effective_date,
        }


@dataclass
class LawDocumentRecord:
    document_id: str
    name: str
    document_type: str
    serial_number: str | None = None
    effective_date: str | None = None
    promulgation_date: str | None = None
    ministry: str | None = None
    revision_type: str | None = None
    current_status: str = "현행"
    original_url: str | None = None
    collected_at: str | None = None
    articles: list[LawArticleRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "documentId": self.document_id,
            "name": self.name,
            "documentType": self.document_type,
            "serialNumber": self.serial_number,
            "effectiveDate": self.effective_date,
            "promulgationDate": self.promulgation_date,
            "ministry": self.ministry,
            "revisionType": self.revision_type,
            "currentStatus": self.current_status,
            "source": {
                "provider": "국가법령정보센터",
                "originalUrl": self.original_url,
                "collectedAt": self.collected_at,
            },
            "articles": [article.to_dict() for article in self.articles],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LawDocumentRecord":
        source = payload.get("source") or {}
        return cls(
            document_id=str(payload.get("documentId") or ""),
            name=str(payload.get("name") or ""),
            document_type=str(payload.get("documentType") or ""),
            serial_number=_optional(payload.get("serialNumber")),
            effective_date=_optional(payload.get("effectiveDate")),
            promulgation_date=_optional(payload.get("promulgationDate")),
            ministry=_optional(payload.get("ministry")),
            revision_type=_optional(payload.get("revisionType")),
            current_status=str(payload.get("currentStatus") or "현행"),
            original_url=_optional(source.get("originalUrl")),
            collected_at=_optional(source.get("collectedAt")),
            articles=[
                LawArticleRecord(
                    article=str(article.get("article") or ""),
                    title=_optional(article.get("title")),
                    text=str(article.get("text") or ""),
                    effective_date=_optional(article.get("effectiveDate")),
                )
                for article in payload.get("articles") or []
                if article.get("article")
            ],
        )


@dataclass(frozen=True)
class LawReference:
    law_name: str
    article: str | None = None
    paragraph: str | None = None
    item: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lawName": self.law_name,
            "article": self.article,
            "paragraph": self.paragraph,
            "item": self.item,
        }


@dataclass
class InterpretationRecord:
    interpretation_id: str
    serial_number: str
    title: str
    case_number: str | None = None
    question_agency: str | None = None
    response_agency: str | None = None
    response_date: str | None = None
    question: str | None = None
    answer: str | None = None
    reasoning: str | None = None
    related_laws: list[LawReference] = field(default_factory=list)
    original_url: str | None = None
    collected_at: str | None = None
    temporal_status: TemporalStatus = "UNKNOWN"
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpretationId": self.interpretation_id,
            "serialNumber": self.serial_number,
            "caseNumber": self.case_number,
            "title": self.title,
            "questionAgency": self.question_agency,
            "responseAgency": self.response_agency,
            "responseDate": self.response_date,
            "question": self.question,
            "answer": self.answer,
            "reasoning": self.reasoning,
            "relatedLaws": [ref.to_dict() for ref in self.related_laws],
            "source": {
                "provider": "법제처",
                "originalUrl": self.original_url,
                "collectedAt": self.collected_at,
            },
            "temporalStatus": self.temporal_status,
            "warning": self.warning,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InterpretationRecord":
        source = payload.get("source") or {}
        return cls(
            interpretation_id=str(payload.get("interpretationId") or ""),
            serial_number=str(payload.get("serialNumber") or ""),
            case_number=_optional(payload.get("caseNumber")),
            title=str(payload.get("title") or ""),
            question_agency=_optional(payload.get("questionAgency")),
            response_agency=_optional(payload.get("responseAgency")),
            response_date=_optional(payload.get("responseDate")),
            question=_optional(payload.get("question")),
            answer=_optional(payload.get("answer")),
            reasoning=_optional(payload.get("reasoning")),
            related_laws=[
                LawReference(
                    law_name=str(ref.get("lawName") or ""),
                    article=_optional(ref.get("article")),
                    paragraph=_optional(ref.get("paragraph")),
                    item=_optional(ref.get("item")),
                )
                for ref in payload.get("relatedLaws") or []
                if ref.get("lawName")
            ],
            original_url=_optional(source.get("originalUrl")),
            collected_at=_optional(source.get("collectedAt")),
            temporal_status=str(payload.get("temporalStatus") or "UNKNOWN"),  # type: ignore[arg-type]
            warning=_optional(payload.get("warning")),
        )


def _optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
