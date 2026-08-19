#!/usr/bin/env python3
"""Audit official_kb vs CONTROL_CHECKLIST / quest_kb.

Usage:
  PYTHONPATH=src python3 scripts/audit_official_vs_kb.py
  PYTHONPATH=src python3 scripts/audit_official_vs_kb.py --json docs/OFFICIAL_KB_GAP.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isms_pii_toolkit.control_assessment import CONTROL_CHECKLIST, checklist_as_statement, list_controls
from isms_pii_toolkit.official_kb import load_control, load_index
from isms_pii_toolkit.quest_kb import get_quest_overlay


def _tokens(text: str) -> set[str]:
    parts = re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")
    return {p.lower() for p in parts}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _best_overlap(official_qs: list[str], current: list[str]) -> float:
    if not official_qs or not current:
        return 0.0
    scores = []
    for o in official_qs:
        ot = _tokens(o)
        scores.append(max((_jaccard(ot, _tokens(c)) for c in current), default=0.0))
    return sum(scores) / len(scores)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", default=str(ROOT / "docs" / "OFFICIAL_KB_GAP.md"))
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    index = load_index()
    rows = []
    for control in list_controls():
        cid = str(control["id"])
        title = str(control["title"])
        official = load_control(cid) or {}
        oqs = [checklist_as_statement(str(q).rstrip("?")) for q in (official.get("checkQuestions") or [])]
        current = [checklist_as_statement(str(x)) for x in (CONTROL_CHECKLIST.get(cid) or [])]
        quest = get_quest_overlay(cid) or {}
        quality = str(
            quest.get("quality")
            or ("handcrafted" if quest.get("locked") else ("thin-stub" if quest else "missing"))
        )
        locked = bool(quest.get("locked"))
        q_checks = []
        for c in (quest.get("quest") or {}).get("checks") or []:
            if isinstance(c, dict) and c.get("label"):
                q_checks.append(str(c["label"]))

        overlap = _best_overlap(oqs, current)
        flag = "ok"
        if not oqs:
            flag = "missing_official"
        elif not current:
            flag = "missing_checklist"
        elif overlap < 0.15:
            flag = "low_overlap"
        elif abs(len(oqs) - len(current)) >= 2:
            flag = "count_mismatch"

        action = "review"
        if locked or quality == "handcrafted":
            action = "propose_only"
        elif quality == "thin-stub" or quest.get("source") == "thin":
            action = "auto_candidate"

        rows.append(
            {
                "controlId": cid,
                "title": title,
                "officialQuestionCount": len(oqs),
                "checklistCount": len(current),
                "questCheckCount": len(q_checks),
                "overlap": round(overlap, 3),
                "flag": flag,
                "questQuality": quality,
                "questLocked": locked,
                "action": action,
                "officialSample": oqs[:2],
                "checklistSample": current[:2],
            }
        )

    flagged = [r for r in rows if r["flag"] != "ok"]
    propose = [r for r in rows if r["action"] == "propose_only" and r["flag"] != "ok"]
    auto = [r for r in rows if r["action"] == "auto_candidate"]

    summary = {
        "sourceDoc": index.get("sourceDoc"),
        "controlCount": len(rows),
        "flaggedCount": len(flagged),
        "lowOverlap": sum(1 for r in rows if r["flag"] == "low_overlap"),
        "countMismatch": sum(1 for r in rows if r["flag"] == "count_mismatch"),
        "lockedProposeOnly": len(propose),
        "thinAutoCandidates": len(auto),
        "rows": rows,
    }

    md_lines = [
        "# Official KB Gap Report",
        "",
        f"> Source: `{summary['sourceDoc']}`, controls {summary['controlCount']}",
        "",
        "## Summary",
        "",
        f"- Flagged: **{summary['flaggedCount']}** (low_overlap {summary['lowOverlap']}, count_mismatch {summary['countMismatch']})",
        f"- Locked/handcrafted propose-only: **{summary['lockedProposeOnly']}**",
        f"- Thin-stub auto candidates: **{summary['thinAutoCandidates']}**",
        "",
        "## Priority mismatches (overlap < 0.15)",
        "",
        "| ID | Title | Official Q | Checklist | Overlap | Quest | Action |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for r in sorted((x for x in rows if x["flag"] == "low_overlap"), key=lambda x: x["overlap"]):
        md_lines.append(
            f"| {r['controlId']} | {r['title']} | {r['officialQuestionCount']} | {r['checklistCount']} | {r['overlap']} | {r['questQuality']} | {r['action']} |"
        )

    md_lines += [
        "",
        "## Sample: 1.1.3 / 1.2.3 / 2.5.4",
        "",
    ]
    for cid in ("1.1.3", "1.2.3", "2.5.4"):
        r = next(x for x in rows if x["controlId"] == cid)
        md_lines.append(f"### {cid} {r['title']} (overlap {r['overlap']}, {r['action']})")
        md_lines.append("")
        md_lines.append("Official:")
        for s in r["officialSample"]:
            md_lines.append(f"- {s}")
        md_lines.append("Current checklist:")
        for s in r["checklistSample"]:
            md_lines.append(f"- {s}")
        md_lines.append("")

    md_path = Path(args.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"wrote {md_path}")

    if args.json:
        jp = Path(args.json)
        jp.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {jp}")

    print(
        f"flagged={summary['flaggedCount']} low_overlap={summary['lowOverlap']} "
        f"thin_auto={summary['thinAutoCandidates']}"
    )


if __name__ == "__main__":
    main()
