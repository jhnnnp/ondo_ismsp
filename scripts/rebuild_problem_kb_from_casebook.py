#!/usr/bin/env python3
"""Rebuild problem_kb controls from 사례집.md and emit defect_weights.json.

Usage:
  .venv/bin/python scripts/rebuild_problem_kb_from_casebook.py --all
  .venv/bin/python scripts/rebuild_problem_kb_from_casebook.py --pilot
  .venv/bin/python scripts/rebuild_problem_kb_from_casebook.py --weights-only
  .venv/bin/python scripts/rebuild_problem_kb_from_casebook.py --dry-run --all
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASEBOOK = ROOT / "사례집.md"
CONTROLS_DIR = ROOT / "src/isms_pii_toolkit/data/problem_kb/controls"
CROSSWALK = ROOT / "src/isms_pii_toolkit/data/problem_kb/casebook_crosswalk.json"
INDEX = ROOT / "src/isms_pii_toolkit/data/problem_kb/index.json"
WEIGHTS_OUT = ROOT / "src/isms_pii_toolkit/data/problem_kb/defect_weights.json"
DEFECT_CSV = ROOT / "한국인터넷진흥원_ISMS_PIMS 연도별 결함현황_20211231.csv"

CHECK_KEYS = ("reviewed", "policy", "implemented", "evidence")

BUCKET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "reviewed": ("정책", "지침", "명시", "수립", "정의", "문서", "기준", "계획"),
    "policy": ("승인", "보고", "담당", "지정", "절차", "권한 부여", "책임", "위원회"),
    "implemented": (
        "적용",
        "설정",
        "미설치",
        "미이행",
        "누락",
        "차단",
        "허용",
        "사용",
        "접근",
        "패치",
        "암호화",
        "로그",
        "클라우드",
    ),
    "evidence": ("증적", "기록", "점검", "검토", "확인되지", "미실시", "주기", "이력", "대장"),
}


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


def score_bucket(text: str, key: str) -> int:
    return sum(1 for kw in BUCKET_KEYWORDS[key] if kw in text)


def assign_cases(cases: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    buckets: dict[str, list[dict[str, object]]] = {k: [] for k in CHECK_KEYS}
    leftover: list[dict[str, object]] = []
    for case in cases:
        text = str(case["text"])
        scores = {k: score_bucket(text, k) for k in CHECK_KEYS}
        best = max(CHECK_KEYS, key=lambda k: (scores[k], -CHECK_KEYS.index(k)))
        if scores[best] == 0:
            leftover.append(case)
        else:
            buckets[best].append(case)
    for index, case in enumerate(leftover):
        buckets[CHECK_KEYS[index % len(CHECK_KEYS)]].append(case)
    if cases:
        for key in CHECK_KEYS:
            if buckets[key]:
                continue
            donor = max(CHECK_KEYS, key=lambda k: len(buckets[k]))
            if buckets[donor]:
                buckets[key].append(buckets[donor].pop(0))
    return buckets


def control_file(control_id: str) -> Path:
    return CONTROLS_DIR / f"{control_id.replace('.', '_')}.json"


def rebuild_one(
    record: dict[str, object],
    case_block: dict[str, object],
    *,
    defect_hint: int | None = None,
    pilot: bool = False,
) -> dict[str, object]:
    cases = list(case_block.get("cases") or [])
    buckets = assign_cases(cases)
    related = [str(x) for x in record.get("relatedControlIds") or []]
    control_id = str(record["controlId"])
    title = str(record.get("title") or case_block.get("title") or control_id)

    items_out = []
    existing_items = list(record.get("checklistItems") or [])
    for index, key in enumerate(CHECK_KEYS):
        base = dict(existing_items[index]) if index < len(existing_items) else {}
        bucket = buckets[key]
        if bucket:
            item_text = (
                f"사례집 {control_id} 유형 결함(예: {str(bucket[0]['text'])[:48]}…)에 해당하는 "
                f"정책/이행/증적이 갖춰져 있는가"
            )
        else:
            item_text = str(base.get("item") or f"'{title}' 통제 요구사항 이행 여부")

        problems = []
        source_refs = []
        for case in bucket[:4]:
            n = int(case["n"])
            text = str(case["text"]).rstrip(".")
            problems.append(f"[사례집 {control_id}.{n}] {text}")
            source_refs.append(
                {
                    "doc": "사례집.md",
                    "controlId": control_id,
                    "caseNo": n,
                    "ref": f"사례집.md#{control_id}.{n}",
                }
            )
        if not problems:
            prior = dict(base.get("ifUnchecked") or {})
            problems = [str(p) for p in prior.get("problems") or []][:3]
            source_refs = list(prior.get("sourceRefs") or [])

        primary = problems[0] if problems else f"{title} 관련 사례집 유형 결함 가능"
        audit = f"인증 심사에서 {control_id} {title} 항목의 사례집형 결함으로 지적될 수 있습니다."
        remediation = (
            f"{control_id} {title}: 사례집 해당 사례 유형을 점검표에 반영하고 "
            f"정책/설정/운영기록 증적을 맞춥니다."
        )
        item_related = list(
            dict.fromkeys(
                [str(x) for x in (dict(base.get("ifUnchecked") or {}).get("relatedControls") or [])]
                + related[:3]
            )
        )[:4]

        items_out.append(
            {
                "itemId": str(base.get("itemId") or str(index + 1)),
                "item": item_text,
                "checkKey": key,
                "ifUnchecked": {
                    "problems": problems
                    or [
                        f"{title}({control_id}) 체크 미충족 시 사례집형 운영/심사 결함으로 이어질 수 있습니다."
                    ],
                    "operationalImpact": (
                        primary.replace(f"[사례집 {control_id}.{bucket[0]['n']}] ", "")
                        if bucket
                        else primary
                    ),
                    "auditImpact": audit,
                    "remediation": remediation,
                    "relatedControls": item_related,
                    "sourceRefs": source_refs,
                },
            }
        )

    top_texts = [str(c["text"]) for c in cases[:5]]
    level_problems = {}
    for level, prefix in (
        ("unknown", "아직 점검되지 않아"),
        ("none", "통제가 사실상 미이행되어"),
        ("partial", "일부만 이행되어"),
    ):
        problems = []
        if top_texts:
            problems.append(f"{prefix} 다음 사례집 유형 결함이 남을 수 있습니다: {top_texts[0]}")
            for text in top_texts[1:3]:
                problems.append(text)
        else:
            problems.append(f"{prefix} {control_id} {title} 보호 공백이 발생합니다.")
        level_problems[level] = {
            "summary": f"{control_id} {title} — {prefix} 사례집 기준 결함 위험이 있습니다.",
            "problems": problems,
            "sourceRefs": [
                {
                    "doc": "사례집.md",
                    "controlId": control_id,
                    "caseNo": int(c["n"]),
                    "ref": f"사례집.md#{control_id}.{int(c['n'])}",
                }
                for c in cases[:3]
            ],
        }

    scenarios = [str(c["text"]) for c in cases[:3]] or list(record.get("scenarios") or [])[:3]

    out = dict(record)
    out["title"] = title
    out["checklistItems"] = items_out
    out["levelProblems"] = level_problems
    out["scenarios"] = scenarios
    out["casebookMeta"] = {
        "sourceDoc": "사례집.md",
        "caseCount": len(cases),
        "pilot": bool(pilot),
        "defectHint": defect_hint,
        "rebuiltAt": "2026-07-28",
    }
    if cases:
        out["riskIfMissing"] = str(cases[0]["text"])[:180]
        out["focus"] = f"사례집 {control_id} 결함 유형을 기준으로 {title} 정책/이행/증적 정합 유지"
    return out


def build_defect_map(
    crosswalk: dict[str, object], casebook: dict[str, dict[str, object]]
) -> dict[str, dict[str, object]]:
    legacy_to_current = {
        str(row["legacyItem"]).strip(): str(row["controlId"])
        for row in crosswalk.get("crosswalk") or []
    }
    defects: dict[str, int] = defaultdict(int)
    sources: dict[str, list[str]] = defaultdict(list)
    if DEFECT_CSV.is_file():
        rows = list(csv.reader(DEFECT_CSV.read_text(encoding="cp949").splitlines()))
        for row in rows[1:]:
            if len(row) < 4:
                continue
            try:
                n = int(str(row[3]).strip() or 0)
            except ValueError:
                n = 0
            item = str(row[2]).strip()
            current = legacy_to_current.get(item)
            if not current or n <= 0:
                continue
            defects[current] += n
            sources[current].append(f"{item}({n})")

    controls: dict[str, dict[str, object]] = {}
    kb_ids = {
        str(c["controlId"]) for c in json.loads(INDEX.read_text(encoding="utf-8"))["controls"]
    }
    for control_id in sorted(kb_ids, key=lambda x: [int(p) for p in x.split(".")]):
        controls[control_id] = {
            "defectCount": int(defects.get(control_id, 0)),
            "caseCount": len((casebook.get(control_id) or {}).get("cases") or []),
            "sources": sources.get(control_id, []),
        }
    return controls


def write_weights(controls: dict[str, dict[str, object]]) -> None:
    payload = {
        "version": 1,
        "sourceCsv": DEFECT_CSV.name,
        "sourceCasebook": CASEBOOK.name,
        "crosswalk": CROSSWALK.name,
        "controls": controls,
    }
    WEIGHTS_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true", help="Rebuild every KB control present in 사례집")
    parser.add_argument("--pilot", action="store_true", help="Rebuild pilotControls only")
    parser.add_argument("--weights-only", action="store_true")
    args = parser.parse_args()
    if not args.all and not args.pilot and not args.weights_only:
        args.all = True

    cross = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    pilots = {str(p["controlId"]) for p in cross.get("pilotControls") or []}
    casebook = parse_casebook(CASEBOOK.read_text(encoding="utf-8"))
    defect_map = build_defect_map(cross, casebook)

    if not args.dry_run:
        write_weights(defect_map)
        print(f"wrote {WEIGHTS_OUT.relative_to(ROOT)}")

    if args.weights_only:
        return 0

    targets = (
        sorted(pilots)
        if args.pilot
        else sorted(
            {
                str(c["controlId"])
                for c in json.loads(INDEX.read_text(encoding="utf-8"))["controls"]
            },
            key=lambda x: [int(p) for p in x.split(".")],
        )
    )

    rewritten = []
    skipped = []
    for control_id in targets:
        path = control_file(control_id)
        if not path.exists():
            skipped.append(f"{control_id}:missing-file")
            continue
        if control_id not in casebook or not casebook[control_id].get("cases"):
            skipped.append(f"{control_id}:no-cases")
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        defect_hint = int((defect_map.get(control_id) or {}).get("defectCount") or 0) or None
        updated = rebuild_one(
            record,
            casebook[control_id],
            defect_hint=defect_hint,
            pilot=control_id in pilots,
        )
        rewritten.append((control_id, len(casebook[control_id]["cases"]), path))
        if not args.dry_run:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mode = "pilot" if args.pilot else "all"
    print(f"rewrote {len(rewritten)} controls ({mode})" + (" dry-run" if args.dry_run else ""))
    for control_id, n, path in rewritten[:20]:
        print(f"  {control_id}: {n} cases -> {path.name}")
    if len(rewritten) > 20:
        print(f"  ... +{len(rewritten) - 20} more")
    if skipped:
        print(
            f"skipped {len(skipped)}: {', '.join(skipped[:12])}"
            + (" ..." if len(skipped) > 12 else "")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
