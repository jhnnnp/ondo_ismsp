"""공식 안내서에서 추출한 official_kb 로더.

판정(assess)과 분리: 체크리스트/증적/제도/간편인증 확인 힌트만 제공한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data" / "official_kb"
CONTROLS_DIR = DATA_DIR / "controls"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    return _read_json(DATA_DIR / "index.json") or {"controls": [], "controlCount": 0}


@lru_cache(maxsize=1)
def load_institution() -> dict[str, Any]:
    return _read_json(DATA_DIR / "institution.json") or {}


@lru_cache(maxsize=1)
def load_officekeeper() -> dict[str, Any]:
    return _read_json(DATA_DIR / "officekeeper.json") or {}


@lru_cache(maxsize=128)
def load_control(control_id: str) -> dict[str, Any] | None:
    path = CONTROLS_DIR / f"{control_id.replace('.', '_')}.json"
    return _read_json(path)


def official_check_statements(control_id: str) -> list[str]:
    """주요 확인사항을 서술형 체크 문구로 반환."""
    from .control_assessment import checklist_as_statement
    from .official_text import merge_check_questions, sanitize_official_text

    rec = load_control(control_id)
    if not rec:
        return []
    questions = merge_check_questions(
        list(rec.get("checkQuestions") or []),
        list(rec.get("laws") or []),
    )
    out: list[str] = []
    for q in questions:
        s = checklist_as_statement(sanitize_official_text(str(q)).rstrip("?"))
        s = sanitize_official_text(s)
        if s and s not in out:
            out.append(s)
    return out


def official_evidence_examples(control_id: str) -> list[str]:
    from .official_text import is_usable_evidence, sanitize_official_text

    rec = load_control(control_id)
    if not rec:
        return []
    out: list[str] = []
    for raw in rec.get("evidenceExamples") or []:
        cleaned = sanitize_official_text(str(raw))
        if is_usable_evidence(cleaned) and cleaned not in out:
            out.append(cleaned)
    return out


def official_requirement(control_id: str) -> str | None:
    rec = load_control(control_id)
    if not rec:
        return None
    req = str(rec.get("requirement") or "").strip()
    return req or None


def official_chunks(
    control_id: str,
    *,
    max_checks: int = 6,
    max_evidence: int = 5,
    max_defects: int = 4,
    max_laws: int = 4,
) -> dict[str, Any]:
    """구조화 RAG 청크 — 임베딩 없이 official_kb에서 통제별 공식 근거를 발췌한다.

    판정에는 쓰지 않고, 상세 서술(LLM/템플릿) 입력으로만 사용한다.
    """
    rec = load_control(control_id)
    if not rec:
        return {
            "controlId": control_id,
            "found": False,
            "chunks": [],
            "sourceDoc": None,
            "pages": [],
        }

    source = rec.get("source") or {}
    source_doc = str(source.get("doc") or "").strip() or None
    pages = [int(p) for p in (source.get("pages") or []) if str(p).isdigit() or isinstance(p, int)]
    chunks: list[dict[str, str]] = []

    requirement = str(rec.get("requirement") or "").strip()
    if requirement:
        chunks.append({"kind": "requirement", "text": requirement})

    for question in list(rec.get("checkQuestions") or [])[: max(0, max_checks)]:
        text = str(question).strip()
        if text:
            chunks.append({"kind": "checkQuestion", "text": text})

    for law in list(rec.get("laws") or [])[: max(0, max_laws)]:
        text = str(law).strip()
        if text:
            chunks.append({"kind": "law", "text": text})

    for evidence in list(rec.get("evidenceExamples") or [])[: max(0, max_evidence)]:
        text = str(evidence).strip()
        if text:
            chunks.append({"kind": "evidenceExample", "text": text})

    for defect in list(rec.get("defectExamples") or [])[: max(0, max_defects)]:
        text = str(defect).strip()
        # OCR 잡음이 긴 꼬리는 잘라 낸다
        if len(text) > 420:
            text = text[:417].rstrip() + "…"
        if text:
            chunks.append({"kind": "defectExample", "text": text})

    return {
        "controlId": str(rec.get("controlId") or control_id),
        "title": str(rec.get("title") or ""),
        "found": bool(chunks),
        "chunks": chunks,
        "sourceDoc": source_doc,
        "pages": pages,
    }


def institution_confirmation_questions(*, as_statements: bool = True) -> list[str]:
    from .control_assessment import checklist_as_statement

    inst = load_institution()
    qs = [str(q) for q in (inst.get("confirmationQuestions") or []) if str(q).strip()]
    if not as_statements:
        return qs
    return [checklist_as_statement(q.rstrip("?")) for q in qs]


def _as_statement(text: str) -> str:
    from .control_assessment import checklist_as_statement

    return checklist_as_statement(str(text).rstrip("?"))


def simple_cert_hints(profile_tags: frozenset[str] | set[str] | None = None) -> dict[str, Any]:
    """간편인증 보조 힌트 — 통제 삭제/N-A 강제 없음."""
    ok = load_officekeeper()
    simple = ok.get("simpleCertification") or {}
    tags = set(profile_tags or ())
    relaxed: list[str] = []
    notes: list[str] = []
    mode: str | None = None

    # Heuristic: small org + cloud-only → surface both hint sets as lower priority candidates
    if "size:1-50" in tags:
        block = simple.get("smallEnterprise") or {}
        relaxed.extend(str(x) for x in (block.get("relaxedControlIds") or []))
        if block.get("note"):
            notes.append(str(block["note"]))
        mode = "smallEnterprise"
    if "cloud-only-no-dc" in tags or ("cloud" in tags and "on-prem-facility" not in tags):
        block = simple.get("noMajorFacility") or {}
        for cid in block.get("relaxedControlIds") or []:
            if str(cid) not in relaxed:
                relaxed.append(str(cid))
        if block.get("note"):
            notes.append(str(block["note"]))
        mode = mode or "noMajorFacility"

    return {
        "enabled": bool(relaxed),
        "mode": mode,
        "relaxedControlIds": relaxed,
        "tips": list(ok.get("tips") or [])[:8],
        "confirmationHints": [_as_statement(h) for h in (ok.get("confirmationHints") or [])],
        "notes": notes,
        "disclaimer": ok.get("disclaimer"),
        "sourceDoc": ok.get("sourceDoc"),
    }


def institution_public_payload() -> dict[str, Any]:
    inst = load_institution()
    if not inst:
        return {}
    return {
        "sourceDoc": inst.get("sourceDoc"),
        "disclaimer": inst.get("disclaimer"),
        "certTypes": inst.get("certTypes") or [],
        "obligationSummary": inst.get("obligationSummary") or [],
        "scopeRules": inst.get("scopeRules") or [],
        "processPhases": inst.get("processPhases") or [],
        "preparationChecks": list(inst.get("preparationChecks") or []),
        "confirmationQuestions": institution_confirmation_questions(as_statements=True),
    }


def clear_caches() -> None:
    load_index.cache_clear()
    load_institution.cache_clear()
    load_officekeeper.cache_clear()
    load_control.cache_clear()
