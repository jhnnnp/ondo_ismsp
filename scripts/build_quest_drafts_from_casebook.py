#!/usr/bin/env python3
"""Offline quest drafts from 사례집 + defect weights (runtime judgment stays separate).

Usage:
  .venv/bin/python scripts/build_quest_drafts_from_casebook.py --min-defect 4
  .venv/bin/python scripts/build_quest_drafts_from_casebook.py --min-defect 4 --apply
  .venv/bin/python scripts/build_quest_drafts_from_casebook.py --control-id 2.10.1 --apply
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASEBOOK = ROOT / "사례집.md"
WEIGHTS = ROOT / "src/isms_pii_toolkit/data/problem_kb/defect_weights.json"
INDEX = ROOT / "src/isms_pii_toolkit/data/problem_kb/index.json"
QUEST_DIR = ROOT / "src/isms_pii_toolkit/data/quest_kb/controls"
DRAFT_DIR = ROOT / "src/isms_pii_toolkit/data/quest_kb/drafts"

CHECK_KEYS = ("reviewed", "policy", "implemented")


def parse_casebook(text: str) -> dict[str, dict[str, object]]:
    parts = re.split(r"(?m)^(?=\d+\.\d+\.\d+\.\s)", text)
    out: dict[str, dict[str, object]] = {}
    for part in parts:
        head = re.match(r"^(\d+\.\d+\.\d+)\.\s*(.+?)(?:\s*▶.*)?\s*$", part, re.M)
        if not head:
            continue
        control_id = head.group(1)
        title = head.group(2).strip()
        cases: list[dict[str, object]] = []
        for line in part.splitlines()[1:]:
            m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
            if not m:
                continue
            body = m.group(2).strip()
            if re.match(r"^\d+\.\d+", body):
                continue
            cases.append({"n": int(m.group(1)), "text": body})
        out[control_id] = {"title": title, "cases": cases}
    return out


def _clip(text: str, limit: int = 72) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("，", ",", "/", " 및 ", " 또는 ", "/", " "):
        idx = cut.rfind(sep)
        if idx >= max(24, limit // 3):
            cut = cut[:idx]
            break
    else:
        cut = cut.rstrip(" ,/")
        if len(cut) > 8:
            cut = cut[:-1]
    return cut.rstrip(" ,/") + "…"


def _clean_case(case_text: str) -> str:
    t = re.sub(r"\s*\(개정.*?\)\s*$", "", case_text)
    t = re.sub(r"\s*\(CELA\).*", "", t)
    return t.strip().rstrip(".")


def case_to_question(title: str, case_text: str) -> str:
    t = _clean_case(case_text)
    for sep in ("그러나 ", "하지만 ", "다만 ", "있으나 ", "고 있으나 "):
        if sep in t and ("하지 않" in t or "않은" in t or "없거나" in t or "미흡" in t):
            # Prefer the gap clause after contrast connector for a shorter ask
            gap = t.split(sep, 1)[-1].strip().rstrip(",")
            if "하지 않은 경우" in gap or gap.endswith("하지 않은"):
                gap = gap.replace("하지 않은 경우", "").replace("하지 않은", "").strip()
                return f"{_clip(gap, 48)} — 지금 하고 있나요?"
            if "않은 경우" in gap:
                gap = gap.replace("않은 경우", "").strip()
                return f"{_clip(gap, 48)} 상태를 피하고 있나요?"
            return f"{title}: {_clip(gap, 44)} — 해당 없음을 확인했나요?"
    if "하지 않은 경우" in t:
        stem = t.replace("하지 않은 경우", "").strip().rstrip(",")
        return f"{_clip(stem, 48)} — 지금 하고 있나요?"
    if "않은 경우" in t:
        stem = t.replace("않은 경우", "").strip().rstrip(",")
        return f"{_clip(stem, 48)} 상태를 피하고 있나요?"
    if "경우" in t:
        stem = t.rsplit("경우", 1)[0].strip().rstrip(",")
        return f"{title}: {_clip(stem, 44)} — 해당 없음을 확인했나요?"
    return f"{title}에서 {_clip(t, 44)} 같은 공백이 없는지 확인했나요?"


def case_to_check_label(case_text: str, case_no: int) -> str:
    t = _clean_case(case_text)
    t = re.sub(r"\s*경우$", "", t).strip()
    # Prefer the actionable tail after common connectors
    for sep in ("그러나 ", "하지만 ", "다만 ", "있으나 ", "고 있으나 "):
        if sep in t:
            t = t.split(sep, 1)[-1].strip()
            break
    short = _clip(t, 56)
    if "하지 않" in short or "미흡" in short or "누락" in short or "없거나" in short:
        return f"사례 {case_no}형 공백 없음: {_clip(short, 48)}"
    return f"사례 {case_no} 대비 조치됨: {short}"


def audience_for(control_id: str, area_id: str) -> list[str]:
    if control_id.startswith(("2.5", "2.6", "2.7", "2.9", "2.10")):
        return ["인프라", "개발/운영", "보안(겸직)"]
    if control_id.startswith(("1.2", "1.4")):
        return ["보안(겸직)", "경영지원", "개인정보 보호책임자"]
    if area_id == "3":
        return ["개인정보 담당", "서비스 운영", "보안(겸직)"]
    if area_id == "1":
        return ["경영지원", "보안(겸직)", "개인정보 보호책임자"]
    return ["담당자", "보안(겸직)"]


def build_draft(
    control_id: str,
    title: str,
    area_id: str,
    cases: list[dict[str, object]],
    *,
    defect_count: int,
    case_count: int,
) -> dict[str, object]:
    top = cases[:5] or [{"n": 1, "text": f"{title} 관련 증적/운영 공백"}]
    plain = case_to_question(title, str(top[0]["text"]))
    checks = []
    for index, case in enumerate(top[:3]):
        checks.append(
            {
                "checkId": f"case-{case['n']}",
                "label": case_to_check_label(str(case["text"]), int(case["n"])),
                "recommended": index == 0,
                "mapsToCheckKey": CHECK_KEYS[index % len(CHECK_KEYS)],
            }
        )
    first = _clip(str(top[0]["text"]), 90)
    return {
        "controlId": control_id,
        "locked": False,
        "quality": "casebook-draft",
        "meta": {
            "sourceDoc": "사례집.md",
            "defectCount": defect_count,
            "caseCount": case_count,
            "sourceRefs": [f"사례집.md#{control_id}.{int(c['n'])}" for c in top[:3]],
            "generatedBy": "scripts/build_quest_drafts_from_casebook.py",
        },
        "quest": {
            "plainQuestion": plain,
            "audience": audience_for(control_id, area_id),
            "checks": checks,
            "actionGuide": {
                "whenMissing": (
                    f"사례집 {control_id} 유형을 점검표에 넣고, "
                    f"대표 공백({first})부터 정책/설정/기록을 맞추세요."
                ),
                "guideRef": f"casebook-{control_id}",
                "whenDone": f"{control_id} 관련 사례집 유형 점검 증적 파일명을 아래에 남겨 두세요.",
            },
            "evidenceSlots": [
                {
                    "slotId": f"casebook-{control_id.replace('.', '-')}-memo",
                    "title": f"{title} 사례집형 점검 파일명 메모",
                    "accepts": ["image", "pdf"],
                    "requiredForLevel": "evidenced",
                }
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-defect", type=int, default=4)
    parser.add_argument("--min-cases", type=int, default=0)
    parser.add_argument("--control-id", action="append", default=[])
    parser.add_argument("--apply", action="store_true", help="Write into quest_kb/controls (skip locked)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    casebook = parse_casebook(CASEBOOK.read_text(encoding="utf-8"))
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8")).get("controls") or {}
    index = {
        str(c["controlId"]): c for c in json.loads(INDEX.read_text(encoding="utf-8"))["controls"]
    }

    if args.control_id:
        targets = list(dict.fromkeys(args.control_id))
    else:
        targets = []
        for cid, meta in weights.items():
            defect_ok = int(meta.get("defectCount") or 0) >= args.min_defect
            cases_ok = args.min_cases > 0 and int(meta.get("caseCount") or 0) >= args.min_cases
            if defect_ok or cases_ok:
                targets.append(cid)
        targets.sort(key=lambda c: (-int((weights.get(c) or {}).get("defectCount") or 0), c))

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    skipped = []
    for control_id in targets:
        if control_id not in casebook or not casebook[control_id].get("cases"):
            skipped.append(f"{control_id}:no-cases")
            continue
        title = str((index.get(control_id) or {}).get("title") or casebook[control_id]["title"])
        area_id = str((index.get(control_id) or {}).get("areaId") or control_id.split(".")[0])
        meta_w = weights.get(control_id) or {}
        draft = build_draft(
            control_id,
            title,
            area_id,
            list(casebook[control_id]["cases"]),
            defect_count=int(meta_w.get("defectCount") or 0),
            case_count=int(meta_w.get("caseCount") or 0),
        )
        draft_path = DRAFT_DIR / f"{control_id.replace('.', '_')}.json"
        live_path = QUEST_DIR / f"{control_id.replace('.', '_')}.json"
        if not args.dry_run:
            draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        applied = False
        if args.apply and not args.dry_run:
            if live_path.is_file():
                existing = json.loads(live_path.read_text(encoding="utf-8"))
                if existing.get("locked") is True:
                    skipped.append(f"{control_id}:locked")
                    written.append((control_id, str(draft_path.relative_to(ROOT)), False))
                    continue
            live_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            applied = True
        written.append((control_id, str(draft_path.relative_to(ROOT)), applied))

    print(f"drafts {len(written)} (apply={args.apply})")
    for control_id, path, applied in written[:25]:
        print(f"  {control_id}: {path}" + (" [applied]" if applied else ""))
    if len(written) > 25:
        print(f"  ... +{len(written) - 25} more")
    if skipped:
        print("skipped:", ", ".join(skipped[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
