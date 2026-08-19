#!/usr/bin/env python3
"""Import the PIPC/KISA 2023 privacy interpretation casebook into the local KB."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


CASES = [
    ("I-1", "공동 개인정보처리자 인정 여부", 3, ["3.3.1"]),
    ("I-2", "공동주택의 개인정보처리자", 6, ["1.1.4", "2.3.1", "3.2.1"]),
    ("II-1", "예약 서비스 제공을 위한 개인정보 수집·이용", 13, ["3.1.1", "3.1.2"]),
    ("II-2", "홍보·마케팅을 위한 개인정보의 수집·이용", 15, ["3.1.7"]),
    ("II-3", "근로자 채용 단계의 개인정보 수집·이용", 19, ["3.1.1", "3.1.2", "2.2.1"]),
    ("II-4", "근로자 위치정보의 수집·이용", 22, ["3.1.1", "3.1.2", "3.1.4"]),
    ("II-5", "보험회사의 개인(신용)정보의 수집", 31, ["3.1.1", "3.1.4", "3.3.2"]),
    ("III-1", "경매물건 또는 공실의 관리비 연체내역 제공", 37, ["3.2.4", "3.3.1"]),
    ("III-2", "중고거래 플랫폼 사업자의 개인정보 목적 외 제3자 제공", 41, ["3.2.4", "3.3.1"]),
    ("III-3", "개인정보의 국외 이전", 44, ["3.3.4"]),
    ("IV-1", "개인정보 처리방침을 링크한 개인정보 수집·이용 동의", 49, ["3.1.1", "3.5.1"]),
    ("IV-2", "약관 관련 개인정보의 수집·이용 동의", 52, ["3.1.1"]),
    ("IV-3", "만 14세 미만 아동의 법정대리인 동의 절차", 59, ["3.1.1", "3.5.3"]),
    ("V-1", "회원 탈퇴 시 개인정보 보관 기준", 63, ["3.4.1", "3.4.2", "3.5.1"]),
    ("V-2", "개인정보가 포함된 공공기록물의 파기 및 분리 보관", 66, ["3.4.1", "3.4.2"]),
    ("V-3", "퇴직근로자 개인정보의 파기 및 분리 보관", 69, ["2.2.5", "3.4.1", "3.4.2"]),
    ("VI-1", "사망자 주민등록번호의 활용", 73, ["3.1.3"]),
    ("VI-2", "이벤트 등에서의 주민등록번호의 처리 제한", 79, ["3.1.3"]),
    ("VII-1", "행정상 위임·위탁에 따른 개인정보의 제공", 85, ["3.3.1", "3.3.2"]),
    ("VII-2", "행정기관의 민간에 대한 개인정보 위·수탁", 87, ["2.3.2", "2.3.3", "3.3.2"]),
    ("VIII-1", "가명처리 목적의 개인정보 목적 외 제3자 제공", 93, ["3.2.4", "3.2.5", "3.3.1"]),
    ("VIII-2", "가명처리 목적의 개인정보 수탁자 전달", 98, ["3.2.5", "3.3.2"]),
    ("VIII-3", "가명처리를 위한 개인정보의 위·수탁", 103, ["3.2.5", "3.3.2"]),
    ("VIII-4", "가명정보의 파기", 105, ["3.2.5", "3.4.1"]),
    ("IX-1", "단체메일 발송 시 개인정보 안전성 확보조치", 111, ["2.10.5", "2.11.1", "3.1.4", "3.5.3"]),
    ("IX-2", "해킹 등 유출 사고 대비 개인정보 안전성 확보조치", 114, ["2.5.3", "2.6.1", "2.9.4", "2.11.1", "2.11.3"]),
    ("X-1", "학원 등의 개인정보 제공과 개인정보 처리방침", 123, ["3.3.1", "3.5.1"]),
    ("X-2", "보험회사의 개인정보 제공과 개인정보 처리방침", 129, ["3.3.1", "3.5.1"]),
    ("XI-1", "수술실 개인영상정보의 수집 및 열람", 135, ["3.1.6", "3.4.1", "3.5.2"]),
    ("XI-2", "제3자의 부당 이익 침해와 개인정보 열람 제한 사유", 145, ["3.1.6", "3.5.2"]),
]

ROMAN_SECTION = {
    "I": "Ⅰ", "II": "Ⅱ", "III": "Ⅲ", "IV": "Ⅳ", "V": "Ⅴ", "VI": "Ⅵ",
    "VII": "Ⅶ", "VIII": "Ⅷ", "IX": "Ⅸ", "X": "Ⅹ", "XI": "Ⅺ",
}


def _clean(text: str, *, limit: int) -> str:
    text = re.sub(r"=== PAGE \d+ ===", " ", text)
    text = re.sub(r"2023\s*개인정보\s*법령해석\s*사례\s*30선", " ", text)
    text = re.sub(r"\n\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪ]+\.\s*[^\n]+\n\s*[•·]\s*\d+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def _field(section: str, start: str, end: str | None, *, limit: int) -> str:
    tail = section.split(start, 1)[1] if start in section else ""
    if end and end in tail:
        tail = tail.split(end, 1)[0]
    return _clean(tail, limit=limit)


def build(source: Path) -> dict[str, object]:
    pages = [page.extract_text() or "" for page in PdfReader(source).pages]
    text = "\n".join(f"=== PAGE {index + 1} ===\n{body}" for index, body in enumerate(pages))
    starts: list[tuple[int, tuple[str, str, int, list[str]]]] = []
    for item in CASES:
        section, number = item[0].split("-", 1)
        marker = f"주제{ROMAN_SECTION[section]}-{number}"
        position = text.find(marker)
        if position < 0:
            raise RuntimeError(f"사례 시작점을 찾을 수 없습니다: {marker}")
        starts.append((position, item))
    records = []
    for index, (position, (case_id, title, page, control_ids)) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        section = text[position:end]
        records.append({
            "caseId": f"pipc-kisa-2023-{case_id.lower()}",
            "section": case_id,
            "title": title,
            "question": _field(section, "1. 질의 요지", "2. 답변", limit=3000),
            "answer": _field(section, "2. 답변", "3. 이유", limit=5000),
            "reasoning": _field(section, "3. 이유", None, limit=9000),
            "controlIds": control_ids,
            "sourcePage": page,
            "source": {
                "provider": "개인정보보호위원회·한국인터넷진흥원",
                "document": "2023 개인정보 법령해석 사례 30선",
                "publishedAt": "2023-12",
                "sourceType": "PIPC_KISA_CASEBOOK",
            },
            "warning": "2023년 공개 사례이므로 현재 적용 전 현행 법령과 조직의 사실관계를 함께 확인해야 합니다.",
        })
    return {"schemaVersion": 1, "recordCount": len(records), "records": records}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {payload['recordCount']} cases -> {args.output}")


if __name__ == "__main__":
    main()
