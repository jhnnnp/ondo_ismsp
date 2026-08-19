"""Dual-layer official checks vs casebook problems."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "src/isms_pii_toolkit/data/problem_kb/casebook_crosswalk.json"


def _pilot_ids() -> list[str]:
    return [
        str(item["controlId"])
        for item in json.loads(CROSSWALK.read_text(encoding="utf-8"))["pilotControls"]
    ]


def test_dual_layer_fields_on_assess_gaps():
    from isms_pii_toolkit.control_assessment import analyze_assessment
    from isms_pii_toolkit.control_graph import list_controls

    assessments = {str(c["id"]): "done" for c in list_controls()}
    for cid in ("2.10.1", "2.5.6", "2.9.4"):
        assessments[cid] = "none"
    result = analyze_assessment(assessments, verbalize=False)
    gaps = {str(g["controlId"]): g for g in result["topGaps"]}
    gap = gaps["2.10.1"]
    assert gap.get("officialChecks"), "officialChecks required"
    assert gap.get("casebookProblems"), "casebookProblems required"
    assert all(row.get("sourceDoc") for row in gap["officialChecks"])
    assert gap["casebookProblems"]


def test_pilot_quest_checks_subset_of_official():
    from isms_pii_toolkit.control_graph import find_control
    from isms_pii_toolkit.dual_layer import build_official_checks
    from isms_pii_toolkit.quest_kb import resolve_quest

    for control_id in _pilot_ids()[:8]:
        control = find_control(control_id)
        if control is None:
            continue
        official = build_official_checks(control_id)
        if not official:
            continue
        resolved = resolve_quest(dict(control))
        official_labels = {str(row["label"]) for row in official}
        quest_labels = {str(row.get("label")) for row in (resolved.get("quest") or {}).get("checks") or []}
        assert quest_labels <= official_labels, f"{control_id}: {quest_labels - official_labels}"
        assert resolved.get("officialChecks")
        assert "casebookProblems" in resolved


def test_resolve_quest_exposes_dual_layer_for_thin():
    from isms_pii_toolkit.control_graph import find_control
    from isms_pii_toolkit.quest_kb import resolve_quest

    control = find_control("2.10.1")
    assert control
    resolved = resolve_quest(dict(control))
    assert resolved.get("officialChecks")
    assert resolved.get("casebookProblems") is not None
