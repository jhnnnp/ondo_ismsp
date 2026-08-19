"""Defect-frequency priority + full casebook KB coverage."""

from __future__ import annotations

import json
from pathlib import Path

from isms_pii_toolkit.control_assessment import analyze_assessment
from isms_pii_toolkit.control_problem_engine import _load_control
from isms_pii_toolkit.defect_priority import (
    _load_weights,
    defect_count,
    defect_priority_delta,
)
from isms_pii_toolkit.profile_prioritization import priority_delta, relevance_reasons
from isms_pii_toolkit.quest_kb import build_priority_quests

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "src/isms_pii_toolkit/data/problem_kb/controls"
INDEX = ROOT / "src/isms_pii_toolkit/data/problem_kb/index.json"


def test_defect_weights_boost_high_frequency_controls():
    _load_weights.cache_clear()
    assert defect_count("2.10.1") >= 14
    assert defect_priority_delta("2.10.1") >= defect_priority_delta("1.1.1")
    assert priority_delta("2.10.1", None) == defect_priority_delta("2.10.1")
    reasons = relevance_reasons("1.4.1", None)
    assert any("결함현황" in r for r in reasons)


def test_most_controls_rebuilt_from_casebook():
    _load_control.cache_clear()
    kb_ids = [str(c["controlId"]) for c in json.loads(INDEX.read_text(encoding="utf-8"))["controls"]]
    rebuilt = 0
    for control_id in kb_ids:
        path = CONTROLS / f"{control_id.replace('.', '_')}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        meta = record.get("casebookMeta") or {}
        if meta.get("caseCount"):
            rebuilt += 1
            assert any(
                (item.get("ifUnchecked") or {}).get("sourceRefs")
                for item in record.get("checklistItems") or []
            )
    assert rebuilt >= 100


def test_analyze_and_quests_prefer_high_defect_controls():
    _load_control.cache_clear()
    _load_weights.cache_clear()
    assessments = {
        "2.10.1": "none",
        "1.1.1": "none",
        "2.5.6": "none",
        "1.4.1": "none",
    }
    result = analyze_assessment(assessments, verbalize=False)
    top_ids = [g["controlId"] for g in result["topGaps"][:4]]
    assert top_ids[0] in {"2.10.1", "1.4.1", "2.5.6"}
    assert any("결함현황" in r for g in result["topGaps"] for r in (g.get("profileRelevance") or []))

    from isms_pii_toolkit.control_assessment import list_checklist_controls

    quests = build_priority_quests(
        assessments=assessments,
        organization_context=None,
        quest_checks=None,
        evidence_slots=None,
        input_confidence=None,
        controls=list_checklist_controls(),
        limit=5,
    )[0]
    quest_ids = [q["controlId"] for q in quests]
    assert "2.10.1" in quest_ids or "1.4.1" in quest_ids
