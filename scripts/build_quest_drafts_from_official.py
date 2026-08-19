#!/usr/bin/env python3
"""Build quest drafts from official_kb for thin-stub controls only.

Locked/handcrafted quests are never overwritten — they appear as proposals in the gap report.

Usage:
  PYTHONPATH=src python3 scripts/build_quest_drafts_from_official.py
  PYTHONPATH=src python3 scripts/build_quest_drafts_from_official.py --apply
  PYTHONPATH=src python3 scripts/build_quest_drafts_from_official.py --control-id 1.1.6 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isms_pii_toolkit.control_assessment import enrich_control, list_controls
from isms_pii_toolkit.official_kb import load_control, official_check_statements, official_evidence_examples
from isms_pii_toolkit.quest_kb import QUEST_DIR, _load_pilot_quests, get_quest_overlay, thin_quest_from_control

DRAFT_DIR = ROOT / "src/isms_pii_toolkit/data/quest_kb/drafts/official"


def main() -> None:
    _load_pilot_quests.cache_clear()

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write into quest_kb/controls for unlocked thin stubs")
    parser.add_argument("--control-id", default="")
    args = parser.parse_args()

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    wrote_draft = 0
    applied = 0
    skipped_locked = 0

    for control in list_controls():
        cid = str(control["id"])
        if args.control_id and cid != args.control_id:
            continue
        if not load_control(cid):
            continue
        existing = get_quest_overlay(cid)
        locked = bool(existing and (existing.get("locked") or existing.get("quality") == "handcrafted"))
        if locked:
            # Proposal only
            proposal = {
                "controlId": cid,
                "action": "propose_only",
                "reason": "locked_or_handcrafted",
                "officialCheckCount": len(official_check_statements(cid)),
                "evidenceExamples": official_evidence_examples(cid)[:5],
                "existingPlainQuestion": (existing or {}).get("quest", {}).get("plainQuestion"),
            }
            path = DRAFT_DIR / f"{cid.replace('.', '_')}.propose.json"
            path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            skipped_locked += 1
            wrote_draft += 1
            continue

        enriched = enrich_control(dict(control))
        draft = thin_quest_from_control(enriched)
        draft["quality"] = "thin-stub"
        draft["locked"] = False
        draft["meta"] = {
            **(draft.get("meta") or {}),
            "builtFrom": "official_kb",
            "sourceDoc": "ISMS-P 인증기준 안내서(2023.11.23)",
        }
        draft_path = DRAFT_DIR / f"{cid.replace('.', '_')}.json"
        draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        wrote_draft += 1

        if args.apply:
            out = QUEST_DIR / f"{cid.replace('.', '_')}.json"
            # Preserve locked if race; only write unlocked
            if out.exists():
                cur = json.loads(out.read_text(encoding="utf-8"))
                if cur.get("locked") or cur.get("quality") == "handcrafted":
                    skipped_locked += 1
                    continue
            out.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            applied += 1

    print(f"drafts={wrote_draft} applied={applied} locked_proposals={skipped_locked} dir={DRAFT_DIR}")


if __name__ == "__main__":
    main()
