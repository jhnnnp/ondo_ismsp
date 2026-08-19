#!/usr/bin/env python3
"""official_kb JSON 문구 정리: OCR, 페이지 푸터, laws→checkQuestions, 깨진 증적."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isms_pii_toolkit.official_text import (  # noqa: E402
    is_usable_evidence,
    looks_like_check_question,
    merge_check_questions,
    sanitize_official_text,
)

CONTROLS = ROOT / "src" / "isms_pii_toolkit" / "data" / "official_kb" / "controls"

# 완전히 오염된 증적을 대체할 최소 안전 라벨
EVIDENCE_FALLBACKS: dict[str, list[str]] = {
    "2.2.3": ["정보보호·개인정보보호 서약서", "서약서 보관·관리 대장"],
    "2.2.4": ["정보보호·개인정보보호 교육 계획서", "교육결과보고서", "교육참석자목록"],
    "2.5.3": ["사용자 인증 설정 화면", "인증 정책/절차"],
    "2.5.5": ["특수계정·권한 목록", "권한부여·회수 이력"],
    "2.6.4": ["DB 계정·권한 목록", "DB 접근통제 설정"],
    "2.6.5": ["무선네트워크 사용 신청·승인 이력", "무선 AP 보안설정"],
    "2.7.2": ["암호키 관리 대장", "암호키 생성·배포·폐기 절차"],
    "2.8.5": ["소스 반출·이관 승인 이력", "형상관리 저장소 접근권한"],
    "2.8.6": ["운영이관 승인 이력", "이관 체크리스트"],
    "2.1.1": ["정책 제·개정 이력", "문서관리 대장"],
    "2.10.7": ["보조저장매체 관리대장", "보유 현황·사용이력"],
    "1.1.5": ["정보보호·개인정보보호 정책/지침/절차서"],
    "2.9.6": ["시간동기화 설정 화면", "NTP/시각동기화 정책"],
    "2.10.4": ["전자거래·핀테크 보안점검 결과", "결제/거래 구간 암호화 설정"],
    "2.11.3": ["이상행위 모니터링 화면", "탐지·대응 이력"],
    "3.2.3": ["앱 접근권한 고지·동의 화면", "접근권한 최소화 설정"],
    "3.3.3": ["영업양도 개인정보 이전 통지 내역", "이전 관련 계약/안내문"],
}


def _clean_list(values: list[object] | None, *, as_evidence: bool = False) -> list[str]:
    out: list[str] = []
    for raw in values or []:
        cleaned = sanitize_official_text(str(raw))
        if not cleaned:
            continue
        if as_evidence and not is_usable_evidence(cleaned):
            continue
        if cleaned not in out:
            out.append(cleaned)
    return out


def _clean_laws(values: list[object] | None) -> list[str]:
    """확인문항으로 승격된 항목은 laws에서 제거."""
    out: list[str] = []
    for raw in values or []:
        text = str(raw)
        if looks_like_check_question(text):
            continue
        cleaned = sanitize_official_text(text)
        if not cleaned or len(cleaned) < 8:
            continue
        if cleaned.startswith("주요 확인사항"):
            continue
        if cleaned not in out:
            out.append(cleaned)
    return out


def process_file(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    cid = str(data.get("controlId") or "")
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)

    if data.get("requirement"):
        data["requirement"] = sanitize_official_text(str(data["requirement"]))

    merged = merge_check_questions(
        list(data.get("checkQuestions") or []),
        list(data.get("laws") or []),
    )
    data["checkQuestions"] = merged
    data["laws"] = _clean_laws(list(data.get("laws") or []))

    evidence = _clean_list(list(data.get("evidenceExamples") or []), as_evidence=True)
    if not evidence and cid in EVIDENCE_FALLBACKS:
        evidence = list(EVIDENCE_FALLBACKS[cid])
    data["evidenceExamples"] = evidence

    data["defectExamples"] = _clean_list(list(data.get("defectExamples") or []))

    after = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if after == before:
        return False
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def main() -> None:
    changed = 0
    for path in sorted(CONTROLS.glob("*.json")):
        if process_file(path):
            changed += 1
            print("updated", path.name)
    print(f"done: {changed} files")


if __name__ == "__main__":
    main()
