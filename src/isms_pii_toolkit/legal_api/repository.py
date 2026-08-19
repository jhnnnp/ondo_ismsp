from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import InterpretationRecord, LawArticleRecord, LawDocumentRecord

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "legal_kb"
INTERPRETATIONS_DIR = DATA_DIR / "interpretations"


class LegalRepository:
    def __init__(self, root: Path = DATA_DIR):
        self.root = root
        self.interpretations_dir = root / "interpretations"
        self.laws_dir = root / "laws"

    def save_law(self, record: LawDocumentRecord) -> Path:
        self.laws_dir.mkdir(parents=True, exist_ok=True)
        safe_id = _safe_document_id(record.document_id)
        path = self.laws_dir / f"{safe_id}.json"
        path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def all_laws(self) -> list[LawDocumentRecord]:
        if not self.laws_dir.exists():
            return []
        return [
            LawDocumentRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.laws_dir.glob("*.json"))
        ]

    def find_law(self, law_name: str) -> LawDocumentRecord | None:
        wanted = _law_key(law_name)
        aliases = {
            "정보통신망법": "정보통신망이용촉진및정보보호등에관한법률",
            "개인정보보호법": "개인정보보호법",
        }
        wanted = aliases.get(wanted, wanted)
        for record in self.all_laws():
            candidate = aliases.get(_law_key(record.name), _law_key(record.name))
            if candidate == wanted:
                return record
        return None

    def find_article(self, law_name: str, article: str | None) -> tuple[LawDocumentRecord, LawArticleRecord | None] | None:
        document = self.find_law(law_name)
        if document is None:
            return None
        wanted = (article or "").replace(" ", "")
        found = next((item for item in document.articles if item.article.replace(" ", "") == wanted), None)
        return document, found

    def save(self, record: InterpretationRecord) -> Path:
        self.interpretations_dir.mkdir(parents=True, exist_ok=True)
        path = self.interpretations_dir / f"{record.interpretation_id}.json"
        path.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def get(self, interpretation_id: str) -> InterpretationRecord | None:
        safe_id = _safe_id(interpretation_id)
        path = self.interpretations_dir / f"{safe_id}.json"
        if not path.exists():
            return None
        return InterpretationRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def all(self) -> list[InterpretationRecord]:
        if not self.interpretations_dir.exists():
            return []
        records: list[InterpretationRecord] = []
        for path in sorted(self.interpretations_dir.glob("expc-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(InterpretationRecord.from_dict(payload))
        return records

    def search(
        self,
        *,
        query: str | None = None,
        law_name: str | None = None,
        article: str | None = None,
    ) -> list[InterpretationRecord]:
        query_norm = (query or "").casefold().strip()
        law_norm = (law_name or "").casefold().replace(" ", "")
        article_norm = (article or "").replace(" ", "")
        out: list[InterpretationRecord] = []
        for record in self.all():
            haystack = " ".join(
                filter(None, [record.title, record.question, record.answer, record.reasoning])
            ).casefold()
            if query_norm and query_norm not in haystack:
                continue
            if law_norm and not any(ref.law_name.casefold().replace(" ", "") == law_norm for ref in record.related_laws):
                continue
            if article_norm and not any((ref.article or "").replace(" ", "") == article_norm for ref in record.related_laws):
                continue
            out.append(record)
        return out


def _safe_id(value: str) -> str:
    if not value.startswith("expc-") or not value[5:].isdigit():
        raise ValueError("올바르지 않은 법령해석례 ID입니다.")
    return value


def _safe_document_id(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"})
    if not safe or safe != value:
        raise ValueError("올바르지 않은 법령 문서 ID입니다.")
    return safe


def _law_key(value: str) -> str:
    return "".join(str(value).split()).replace("ㆍ", "").casefold()
