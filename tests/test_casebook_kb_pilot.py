"""Casebook-grounded problem_kb pilot coverage."""

from __future__ import annotations

import json
from pathlib import Path

from isms_pii_toolkit.control_problem_engine import _load_control, extract_individual_problems

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "src/isms_pii_toolkit/data/problem_kb/casebook_crosswalk.json"
CONTROLS = ROOT / "src/isms_pii_toolkit/data/problem_kb/controls"


def test_pilot_controls_have_casebook_source_refs():
    pilots = [
        str(item["controlId"])
        for item in json.loads(CROSSWALK.read_text(encoding="utf-8"))["pilotControls"]
    ]
    _load_control.cache_clear()
    for control_id in pilots:
        path = CONTROLS / f"{control_id.replace('.', '_')}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record.get("casebookMeta", {}).get("pilot") is True
        assert record.get("casebookMeta", {}).get("caseCount", 0) > 0
        refs = []
        for item in record["checklistItems"]:
            refs.extend(item["ifUnchecked"].get("sourceRefs") or [])
            assert any("[사례집" in p for p in item["ifUnchecked"]["problems"])
        assert refs, f"{control_id} missing sourceRefs"
        assert all(r.get("doc") == "사례집.md" for r in refs)


def test_extract_problems_surfaces_source_refs_for_pilot():
    _load_control.cache_clear()
    rows = extract_individual_problems({"1.4.1": "none", "2.10.1": "none"})
    assert rows
    with_refs = [row for row in rows if row.get("sourceRefs")]
    assert with_refs
    assert any("사례집" in str(row.get("problem") or "") for row in with_refs)
    assert all(ref.get("ref", "").startswith("사례집.md#") for row in with_refs for ref in row["sourceRefs"])
