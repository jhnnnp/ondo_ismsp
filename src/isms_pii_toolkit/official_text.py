"""공식 KB 문구 정리 — OCR 잡음, 페이지 헤더, 증적 플레이스홀더."""

from __future__ import annotations

import re

_OCR_BULLET_RE = re.compile(r"\s*■\s*")
_PAGE_FOOTER_RE = re.compile(
    r"\s*\d{1,3}\s*정보보호\s*및\s*개인정보보호\s*관리체계\s*인증제도\s*안내서.*$"
)
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MID_START_RE = re.compile(r"^[,，]\s*")
_RELATED_LAW_TAIL_RE = re.compile(r"\s*관련\s*법규\s*$")
_PLACEHOLDER_RE = re.compile(r"^(?:1\s*예시|n\s*예시|예시)$", re.I)
_PAGE_ONLY_RE = re.compile(
    r"^\d{2,3}\s*정보보호\s*및\s*개인정보보호\s*관리체계\s*인증제도\s*안내서$"
)
_ASK_TAIL = ("있는가?", "있는가", "하나요?", "하나요", "습니까?", "습니까")


def sanitize_official_text(text: str) -> str:
    """OCR/페이지 푸터/공백을 정리한다."""
    t = str(text or "").strip()
    if not t:
        return ""
    t = _OCR_BULLET_RE.sub("·", t)
    t = t.replace("•", "·")
    t = _PAGE_FOOTER_RE.sub("", t).strip()
    t = _MID_START_RE.sub("", t)
    t = _RELATED_LAW_TAIL_RE.sub("", t).strip()
    t = _MULTI_SPACE_RE.sub(" ", t)
    t = re.sub(r"\s*,\s*", ", ", t)
    return t.strip(" ·")


def looks_like_check_question(text: str) -> bool:
    t = sanitize_official_text(text)
    if len(t) < 12:
        return False
    if t.startswith(("개인정보 보호법", "개인정보의 안전성", "정보통신망법", "전자금융")):
        return False
    if "제" in t[:12] and "조" in t[:20] and "인가" not in t[:20]:
        # 조문 인용
        if re.match(r"^개인정보|^정보통신|^전자", t):
            return False
    return t.endswith(_ASK_TAIL)


def is_usable_evidence(text: str) -> bool:
    t = sanitize_official_text(text)
    if not t or len(t) < 4:
        return False
    if _PLACEHOLDER_RE.match(t):
        return False
    if _PAGE_ONLY_RE.match(t):
        return False
    if t.startswith(("를 ", "을 ", "은 ", "는 ", "이 ", "가 ")):
        return False
    if t.endswith("(제") or t.endswith("(제)"):
        return False
    # 본문 문단이 섞인 긴 오염
    if len(t) > 80 and ("하여야 한다" in t or "폐기 일자" in t):
        return False
    return True


def clean_evidence_label(text: str, *, max_len: int = 56) -> str | None:
    t = sanitize_official_text(text)
    if not is_usable_evidence(t):
        return None
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip(" ,·(/") + "…"
    return t


def merge_check_questions(
    check_questions: list[str] | None,
    laws: list[str] | None = None,
) -> list[str]:
    """checkQuestions + laws에 섞인 확인문항을 합치고 정리한다."""
    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        cleaned = sanitize_official_text(raw)
        if not cleaned:
            return
        # 잘린 앞머리 보정 (2.2.4)
        if cleaned.startswith("및 규정의 중대한 변경"):
            cleaned = f"정보보호 및 개인정보보호 정책 {cleaned}"
        key = cleaned.rstrip("?")
        if key in seen:
            return
        if looks_like_check_question(cleaned) or cleaned.endswith(("있다", "한다", "받는다")):
            # 이미 서술형인 경우도 허용 (statement 변환 전)
            pass
        seen.add(key)
        # 질문형 유지
        if not cleaned.endswith("?"):
            if cleaned.endswith(("있는가", "하나요", "습니까")):
                cleaned = cleaned + "?"
        out.append(cleaned)

    for item in check_questions or []:
        add(str(item))
    for item in laws or []:
        if looks_like_check_question(str(item)):
            add(str(item))
    return out
