#!/usr/bin/env python3
"""Extract structured official_kb from OCR-capable ISMS-P guide PDFs.

Usage:
  python3 scripts/extract_official_guides.py
  python3 scripts/extract_official_guides.py --skip-criteria   # institution + officekeeper only
  python3 scripts/extract_official_guides.py --force-cache     # rebuild page text cache

Requires: pypdf (pip install pypdf)
Runtime assess does NOT depend on this script — committed JSON under data/official_kb/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/isms_pii_toolkit/data/official_kb"
CACHE = OUT / "_cache"
CONTROLS_DIR = OUT / "controls"

PDF_CRITERIA = ROOT / "ISMS-P 인증기준 안내서(2023.11.23) (1).pdf"
PDF_INSTITUTION = ROOT / "ISMS-P 인증제도 안내서(2024.07) (1).pdf"
PDF_OFFICEKEEPER = ROOT / "오피스키퍼 ISMS가이드 (1).pdf"

DOC_CRITERIA = "ISMS-P 인증기준 안내서(2023.11.23)"
DOC_INSTITUTION = "ISMS-P 인증제도 안내서(2024.07)"
DOC_OFFICEKEEPER = "오피스키퍼 ISMS가이드"


def _need_pypdf():
    try:
        from pypdf import PdfReader  # noqa: F401
    except ImportError as exc:
        raise SystemExit("pypdf required: pip install pypdf") from exc


def _ocr_fix(text: str) -> str:
    t = text or ""
    reps = (
        ("인중", "인증"),
        ("잠고", "참고"),
        ("사향", "사항"),
        ("요구사향", "요구사항"),
        ("범우1", "범위"),
        ("제■개정", "제/개정"),
        ("제•개정", "제/개정"),
        ("제·개정", "제/개정"),  # OCR middot → slash (UI에서는 · 미사용)
        ("수립•이행", "수립/이행"),
        ("수립• 이행", "수립/이행"),
        ("수립·이행", "수립/이행"),
        ("수립· 이행", "수립/이행"),
        ("관리•운영", "관리/운영"),
        ("관리·운영", "관리/운영"),
        ("매뉴얼•가이드", "매뉴얼/가이드"),
        ("매뉴얼·가이드", "매뉴얼/가이드"),
        ("표■흐름도", "표/흐름도"),
        ("규정•회의록", "규정/회의록"),
        ("규정·회의록", "규정/회의록"),
        ("규정■회의록", "규정/회의록"),
        ("·", "/"),  # remaining middots from OCR
        ("，", ","),
        ("（", "("),
        ("）", ")"),
        ("》", " "),
        ("〉", " "),
        # OCR: 2.4.x → 2Ax
        ("2A1", "2.4.1"),
        ("2A2", "2.4.2"),
        ("2A3", "2.4.3"),
        ("2A4", "2.4.4"),
        ("2A5", "2.4.5"),
        ("2A6", "2.4.6"),
        ("2A7", "2.4.7"),
    )
    for a, b in reps:
        t = t.replace(a, b)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _load_control_catalog() -> list[dict[str, str]]:
    sys.path.insert(0, str(ROOT / "src"))
    from isms_pii_toolkit.control_graph import list_controls

    return [
        {
            "id": str(c["id"]),
            "title": str(c["title"]),
            "categoryId": str(c["categoryId"]),
            "areaId": str(c["areaId"]),
        }
        for c in list_controls()
    ]


def extract_pages(pdf_path: Path, cache_name: str, *, force: bool = False) -> list[str]:
    _need_pypdf()
    from pypdf import PdfReader

    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE / f"{cache_name}.json"
    if cache_path.exists() and not force:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        pages = data.get("pages") or []
        if pages:
            print(f"  cache hit {cache_path.name}: {len(pages)} pages")
            return pages

    print(f"  extracting {pdf_path.name} …")
    reader = PdfReader(str(pdf_path))
    pages = [_ocr_fix(p.extract_text() or "") for p in reader.pages]
    cache_path.write_text(
        json.dumps({"source": pdf_path.name, "pages": pages}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  wrote cache {cache_path.name}: {len(pages)} pages")
    return pages


def _find_control_pages(pages: list[str], catalog: list[dict[str, str]]) -> dict[str, int]:
    """Return 0-based start page index per control id.

    Prefer pages that contain both the control id and '주요 확인사항' so TOC/overview
    pages (which list many ids) are not chosen.
    """
    found: dict[str, int] = {}
    # OCR variants: "항 목 ) 1.1.2", "항 목 j ) 1.3.1", "항 목 1 } 1.1.1", "》1.1.3"
    header_re = re.compile(
        r"(?:항\s*목|항목)\s*[》〉>a-zA-Zi丨|}):\]1Jj\s]*([123]\.\d{1,2}\.\d{1,2})\s*([^\n]{0,40})"
        r"|[》〉]\s*([123]\.\d{1,2}\.\d{1,2})\s*([^\n]{0,40})"
    )
    ids = {c["id"] for c in catalog}
    titles = {c["id"]: c["title"] for c in catalog}

    # Pass 1: header + 주요 확인사항 on same page
    for i, text in enumerate(pages):
        if "주요 확인사항" not in text:
            continue
        for m in header_re.finditer(text):
            cid = m.group(1) or m.group(3)
            if cid in ids and cid not in found:
                found[cid] = i

    # Pass 2: strong title match + 주요 확인사항 (cid may be OCR-garbled)
    for cid, title in titles.items():
        if cid in found:
            continue
        key = _compact(title)
        if len(key) < 2:
            continue
        for i, text in enumerate(pages):
            if "주요 확인사항" not in text or "인증기준" not in text:
                continue
            compact = _compact(text)
            if key[:4] in compact or (len(key) >= 2 and key[:2] in compact and cid in text):
                # Avoid matching TOC-like multi-id pages: require few other same-category headers
                found[cid] = i
                break

    # Pass 3: last resort — id near 인증기준 + 주요 확인사항
    for cid in titles:
        if cid in found:
            continue
        for i, text in enumerate(pages):
            if cid in text and "주요 확인사항" in text and "인증기준" in text:
                found[cid] = i
                break
    return found


def _block_for(pages: list[str], start: int, cid: str, known_ids: set[str]) -> tuple[str, list[int]]:
    chunks: list[str] = []
    used = [start + 1]
    next_header = re.compile(
        r"(?:항\s*목|항목)\s*[》〉>a-zA-Zi丨|}):\]1Jj\s]*([123]\.\d{1,2}\.\d{1,2})"
        r"|[》〉]\s*([123]\.\d{1,2}\.\d{1,2})"
    )
    for i in range(start, min(start + 6, len(pages))):
        text = pages[i]
        if i > start:
            m = next_header.search(text)
            if m:
                nid = m.group(1) or m.group(2)
                if nid and nid != cid and nid in known_ids:
                    text = text[: m.start()]
                    if text.strip():
                        chunks.append(text)
                        used.append(i + 1)
                    break
            used.append(i + 1)
        chunks.append(text)
    return "\n".join(chunks), used


def _section(block: str, start_label: str, end_labels: tuple[str, ...]) -> str:
    pat = re.compile(
        rf"{re.escape(start_label)}(.*?)(?:" + "|".join(re.escape(e) for e in end_labels) + r"|$)",
        re.S,
    )
    m = pat.search(block)
    return (m.group(1) if m else "").strip()


def _bullets(section: str) -> list[str]:
    if not section:
        return []
    # Normalize whitespace inside potential bullets, then split
    raw = section.replace("\r", "\n")
    # Split on OCR bullets/middot only — never on '/' (compound like 수립/이행).
    parts = re.split(r"[•·▪‣●○]\s*", raw)
    out: list[str] = []
    for part in parts:
        s = " ".join(part.split()).strip(" -–—\t")
        if len(s) < 3:
            continue
        # Drop footer noise
        if re.match(r"^\d+\s*[관보]", s):
            continue
        if "제2장" in s and len(s) < 80:
            continue
        out.append(s)
    return out


def _check_questions(section: str) -> list[str]:
    if not section:
        return []
    # Split on bullets first so mid-sentence '/' (수립/이행) is preserved.
    parts = re.split(r"(?:^|\n)\s*[•●○▪‣]\s*|\s+[•●○▪‣]\s+", section)
    qs: list[str] = []
    for part in parts:
        s = " ".join(part.split()).strip(" -–—\t")
        if not s:
            continue
        # Join OCR line-broken "...하고\n있는가?"
        s = re.sub(r"(하고|하며|하여)\s+있는가\?", r"\1 있는가?", s)
        s = (
            s.replace("수립• 이행", "수립/이행")
            .replace("수립•이행", "수립/이행")
            .replace("수립· 이행", "수립/이행")
            .replace("수립·이행", "수립/이행")
            .replace("·", "/")
        )
        if "있는가" in s:
            if not s.endswith("?"):
                s = s.rstrip(".") + "?"
            # Keep only the question sentence if trailing noise
            m = re.search(r"(.+있는가\?)", s)
            if m:
                s = m.group(1).strip()
            if len(s) > 12:
                qs.append(s)
    if qs:
        return qs

    flat = " ".join(section.split())
    found = re.findall(r".{12,240}?있는가\?", flat)
    return [" ".join(q.split()).strip(" •/") for q in found if len(q.strip()) > 12]


def _fix_broken_questions(questions: list[str], section: str) -> list[str]:
    """Reattach truncated tails like '이행하고 있는가?' to previous bullet stem."""
    flat = " ".join(section.split())
    fixed: list[str] = []
    i = 0
    while i < len(questions):
        q = questions[i]
        if q in ("이행하고 있는가?", "수립/이행하고 있는가?") and fixed:
            # try to find stem before this fragment in section
            prev = fixed[-1]
            if not prev.endswith("있는가?"):
                fixed[-1] = prev.rstrip(". ") + "/이행하고 있는가?"
            i += 1
            continue
        if len(q) < 20 and "있는가?" in q and fixed:
            # Too short — merge with previous if previous lacks question mark ending properly
            if not fixed[-1].endswith("있는가?"):
                fixed[-1] = fixed[-1].rstrip(". ") + " " + q
                i += 1
                continue
        # Try recover full sentence from flat text if truncated
        if q.endswith("있는가?") and len(q) < 25:
            # search longer context in flat
            idx = flat.find(q)
            if idx > 0:
                start = max(0, idx - 80)
                window = flat[start : idx + len(q)]
                m = re.search(r"[가-힣A-Za-z0-9].{20,160}?있는가\?", window)
                if m:
                    q = m.group(0)
        fixed.append(q)
        i += 1
    # Deduplicate
    seen = set()
    out = []
    for q in fixed:
        key = q[-40:]
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


def parse_control_block(
    block: str,
    *,
    control_id: str,
    title: str,
    pages: list[int],
    category_id: str,
    area_id: str,
) -> dict[str, object]:
    # Prefer the 인증기준 that sits after this control id (skip area overview tables).
    requirement = ""
    id_pos = block.find(control_id)
    search_from = id_pos if id_pos >= 0 else 0
    m_req = re.search(
        r"인증기준\s*(.*?)\s*주요\s*확인사항",
        block[search_from:],
        re.S,
    )
    if m_req:
        requirement = " ".join(m_req.group(1).split())
    if not requirement or len(requirement) < 20:
        requirement = " ".join(
            _section(block, "인증기준", ("주요 확인사항", "관련 법규", "세부 설명")).split()
        )
    check_sec = _section(block, "주요 확인사항", ("관련 법규", "세부 설명", "증거자료", "참고"))
    # If section empty (OCR spacing), take between markers near control id
    if not check_sec and "주요 확인사항" in block[search_from:]:
        check_sec = _section(block[search_from:], "주요 확인사항", ("관련 법규", "세부 설명", "증거자료", "참고"))
    questions = _fix_broken_questions(_check_questions(check_sec), check_sec)
    laws = _bullets(_section(block, "관련 법규", ("세부 설명", "증거자료", "결함사례", "참고")))
    evidence = _bullets(_section(block, "증거자료", ("결함사례", "참고", "참고 자료")))
    # Strip leading "예시"
    evidence = [e.removeprefix("예시").strip(" :") for e in evidence if e.removeprefix("예시").strip(" :")]
    defects = _bullets(_section(block, "결함사례", ("참고", "참고 자료", "항 목", "항목")))

    return {
        "controlId": control_id,
        "title": title,
        "areaId": area_id,
        "categoryId": category_id,
        "requirement": requirement,
        "checkQuestions": questions,
        "laws": laws[:12],
        "evidenceExamples": evidence[:16],
        "defectExamples": defects[:12],
        "source": {"doc": DOC_CRITERIA, "pages": pages},
    }


def extract_criteria(*, force_cache: bool = False) -> dict[str, dict[str, object]]:
    if not PDF_CRITERIA.exists():
        raise SystemExit(f"missing {PDF_CRITERIA}")
    catalog = _load_control_catalog()
    pages = extract_pages(PDF_CRITERIA, "criteria_pages", force=force_cache)
    starts = _find_control_pages(pages, catalog)
    known = {c["id"] for c in catalog}
    CONTROLS_DIR.mkdir(parents=True, exist_ok=True)

    records: dict[str, dict[str, object]] = {}
    missing_q: list[str] = []
    for c in catalog:
        cid = c["id"]
        if cid not in starts:
            print(f"  WARN: no page for {cid}")
            continue
        block, used_pages = _block_for(pages, starts[cid], cid, known)
        rec = parse_control_block(
            block,
            control_id=cid,
            title=c["title"],
            pages=used_pages,
            category_id=c["categoryId"],
            area_id=c["areaId"],
        )
        if not rec["checkQuestions"]:
            missing_q.append(cid)
        records[cid] = rec
        out_path = CONTROLS_DIR / f"{cid.replace('.', '_')}.json"
        out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index = {
        "sourceDoc": DOC_CRITERIA,
        "controlCount": len(records),
        "controlsWithQuestions": sum(1 for r in records.values() if r.get("checkQuestions")),
        "missingQuestions": missing_q,
        "controls": [
            {
                "controlId": cid,
                "title": records[cid]["title"],
                "questionCount": len(records[cid].get("checkQuestions") or []),
                "file": f"controls/{cid.replace('.', '_')}.json",
            }
            for cid in sorted(records, key=lambda x: [int(p) for p in x.split(".")])
        ],
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  criteria: {len(records)} controls, questions missing: {len(missing_q)}")
    return records


def extract_institution(*, force_cache: bool = False) -> dict[str, object]:
    if not PDF_INSTITUTION.exists():
        raise SystemExit(f"missing {PDF_INSTITUTION}")
    pages = extract_pages(PDF_INSTITUTION, "institution_pages", force=force_cache)
    full = "\n".join(pages)

    confirmation_questions = [
        "인증 유형이 ISMS인지 ISMS-P인지 확정했는가?",
        "의무대상자인지 임의신청자인지 확인했는가?",
        "인증범위에 정보통신서비스/관련 자산/조직이 포함되어 있는가?",
        "클라우드/호스팅을 쓰는 경우 공유책임과 범위 경계가 문서화되어 있는가?",
        "관리체계를 최소 2개월 이상 운영한 증적(정책/점검/운영기록)이 있는가?",
        "인증 신청서류(신청서/관리체계 명세서/운영명세서 등) 목록을 준비했는가?",
        "심사 준비상태 점검(문서/조직/범위/위험평가)을 내부에서 마쳤는가?",
    ]

    data = {
        "sourceDoc": DOC_INSTITUTION,
        "pageCount": len(pages),
        "certTypes": [
            {
                "id": "isms",
                "label": "ISMS",
                "summary": "정보보호 중심. 관리체계 수립/운영 + 보호대책 요구사항(80개 기준).",
            },
            {
                "id": "isms-p",
                "label": "ISMS-P",
                "summary": "정보보호 + 개인정보 처리단계 요구사항(101개 기준).",
            },
        ],
        "obligationSummary": [
            "정보통신망서비스 제공자(ISP), 집적정보통신시설사업자(IDC) 등 법령상 의무대상자는 ISMS(또는 ISMS-P) 인증이 필요합니다.",
            "매출액/이용자 수 기준 의무대상은 해당 연도 다음 해 기한까지 인증을 취득해야 합니다.",
            "임의신청자는 범위를 신청기관이 정할 수 있으나 심사기준/절차는 의무대상과 동일합니다.",
        ],
        "scopeRules": [
            {
                "id": "obligation-full-service",
                "title": "의무대상자 범위",
                "rule": "의무대상자는 신청기관의 정보통신서비스를 모두 포함하여 범위를 설정해야 합니다.",
                "sourcePages": [32],
            },
            {
                "id": "cloud-hosting",
                "title": "클라우드/호스팅",
                "rule": "웹호스팅/클라우드(SaaS/PaaS) 이용 시 인증/보안 수준을 고려하고, 공유 책임과 범위 경계를 문서화해야 합니다.",
                "sourcePages": [30],
            },
            {
                "id": "physical-boundary",
                "title": "물리 장소",
                "rule": "서비스 운영에 필요한 물리적 장소/설비는 범위에 포함합니다. 자체 전산실이 없으면 해당 물리 통제는 N/A 검토 대상입니다.",
                "sourcePages": [31],
            },
        ],
        "processPhases": [
            {
                "id": "prepare",
                "title": "준비단계",
                "summary": "신청/접수, 준비상태 점검, 계약/수수료, 사전준비. 관리체계 구축 후 최소 2개월 이상 운영 증적 필요.",
                "checkItems": [
                    "인증 신청서류 준비",
                    "심사 준비상태 점검",
                    "2개월 이상 운영 증적",
                ],
            },
            {
                "id": "audit",
                "title": "심사단계",
                "summary": "시작회의 → 서면/현장심사 → 결함보고서 → 종료회의 → 보완조치.",
                "checkItems": [
                    "서면심사(정책/지침)",
                    "현장심사(이행/증적)",
                    "결함 보완조치",
                ],
            },
            {
                "id": "certify",
                "title": "인증단계",
                "summary": "인증위원회 심의/의결 후 인증결과 통보/인증서 발급(유효 3년).",
                "checkItems": ["인증위원회 심의", "인증서 발급"],
            },
            {
                "id": "maintain",
                "title": "사후관리",
                "summary": "사후심사/갱신심사로 유지합니다.",
                "checkItems": ["사후심사", "갱신심사"],
            },
        ],
        "preparationChecks": [
            "정책/지침/매뉴얼 등 내부규정 존재 및 인증기준 충족",
            "조직/책임자/담당자 지정 및 역할 수행",
            "인증범위 문서화",
            "위험평가 및 보호대책 선정 결과",
            "운영/점검 기록(최소 2개월)",
        ],
        "confirmationQuestions": confirmation_questions,
        "disclaimer": (
            "이 안내는 인증제도 안내서 요약을 바탕으로 한 확인용 힌트이며, "
            "실제 의무 여부/범위/심사를 대체하지 않습니다."
        ),
        "excerptHints": {
            "hasObligationSection": "의무대상자" in full,
            "hasScopeSection": "인증범위" in full,
            "hasProcessSection": "인증심사" in full,
        },
    }
    (OUT / "institution.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  wrote institution.json")
    return data


def extract_officekeeper(*, force_cache: bool = False) -> dict[str, object]:
    if not PDF_OFFICEKEEPER.exists():
        raise SystemExit(f"missing {PDF_OFFICEKEEPER}")
    pages = extract_pages(PDF_OFFICEKEEPER, "officekeeper_pages", force=force_cache)

    # Pages 24-25 in 1-based indexing contained simplified sets in prior analysis
    text_24 = pages[23] if len(pages) > 23 else ""
    text_25 = pages[24] if len(pages) > 24 else ""
    tip_page = next((p for p in pages if "TIP" in p and "주의사항" in p), "")

    id_re = re.compile(r"([123]\.\d{1,2}\.\d{1,2})")

    def ids_near(label: str, blob: str) -> list[str]:
        idx = blob.find(label)
        if idx < 0:
            return []
        window = blob[idx : idx + 400]
        seen = []
        for m in id_re.finditer(window):
            cid = m.group(1)
            if cid not in seen:
                seen.append(cid)
        return seen

    relaxed_small = ids_near("완화된 항목", text_24) or [
        "1.1.3",
        "1.1.5",
        "2.4.1",
        "2.6.6",
        "2.11.1",
    ]
    # Prefer known set from guide TOC for small enterprise
    if "1.1.3" not in relaxed_small:
        relaxed_small = ["1.1.3", "1.1.5", "2.4.1", "2.6.6", "2.11.1"]

    relaxed_no_facility = ids_near("완화된 항목", text_25) or [
        "1.1.3",
        "1.1.5",
        "1.2.1",
        "1.2.2",
        "2.4.2",
        "2.6.1",
        "2.6.2",
        "2.6.6",
        "2.8.1",
        "2.8.5",
    ]

    tips: list[str] = []
    if tip_page:
        for line in tip_page.splitlines():
            s = " ".join(line.split()).strip()
            if not s or len(s) < 8:
                continue
            if s.startswith("✓") or "체크" in s or "확보" in s or "정리" in s:
                tips.append(s.lstrip("✓✔ ").strip())
        # Also pull caution lines
        for line in tip_page.splitlines():
            s = " ".join(line.split()).strip()
            if s.startswith("X") or s.startswith("×") or "주의" in s[:6]:
                tips.append(s.lstrip("X× ").strip())

    if not tips:
        tips = [
            "인증심사 전 체크리스트로 누락 항목을 확인한다",
            "심사 공간은 심사위원 수의 최소 2배 규모를 확보한다",
            "IDC가 분리되어 있으면 방문 대응 인력을 배치한다",
            "사원급을 정보보호 최고책임자로 지정하지 않는다",
        ]

    data = {
        "sourceDoc": DOC_OFFICEKEEPER,
        "pageCount": len(pages),
        "disclaimer": (
            "오피스키퍼 가이드는 민간 실무 참고자료입니다. "
            "간편인증 적용 여부와 완화/병합 범위는 공식 고시/인증기관 안내를 따릅니다. "
            "본 제품은 통제를 자동 삭제하지 않으며 우선순위/확인 힌트만 제공합니다."
        ),
        "simpleCertification": {
            "smallEnterprise": {
                "label": "소기업/정보통신서비스 매출 300억 미만 중기업",
                "relaxedControlIds": relaxed_small[:8],
                "note": "완화된 항목은 심사가 완화될 수 있으나, 자체진단에서는 확인 우선순위를 낮추는 힌트로만 씁니다.",
            },
            "noMajorFacility": {
                "label": "주요 정보통신설비 미보유",
                "relaxedControlIds": relaxed_no_facility[:14],
                "note": "설비 미보유 시 완화 후보. N/A 확정은 조직 사실과 인증기관 판단에 따릅니다.",
            },
        },
        "tips": tips[:20],
        "confirmationHints": [
            "간편인증(특례) 대상인지 매출/설비 기준으로 확인했는가?",
            "완화/병합 후보 통제를 ‘삭제’가 아니라 ‘확인 우선순위’로만 다루고 있는가?",
            "심사 전 TIP(공간/인력/체크리스트)을 점검 목록에 넣었는가?",
        ],
    }
    (OUT / "officekeeper.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  wrote officekeeper.json")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-criteria", action="store_true")
    parser.add_argument("--skip-institution", action="store_true")
    parser.add_argument("--skip-officekeeper", action="store_true")
    parser.add_argument("--force-cache", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    print("Extracting official guides →", OUT)
    if not args.skip_criteria:
        extract_criteria(force_cache=args.force_cache)
    if not args.skip_institution:
        extract_institution(force_cache=args.force_cache)
    if not args.skip_officekeeper:
        extract_officekeeper(force_cache=args.force_cache)
    print("done")


if __name__ == "__main__":
    main()
