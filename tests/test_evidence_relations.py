"""Evidence-grounded relations and compounds."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "src/isms_pii_toolkit/data/problem_kb/relation_evidence.json"
COMPOUNDS = ROOT / "src/isms_pii_toolkit/data/problem_kb/compounds.json"
CROSSWALK = ROOT / "src/isms_pii_toolkit/data/problem_kb/casebook_crosswalk.json"

FORBIDDEN = (
    "단일 결함이 아니라 연결된 업무 흐름 전체의 보호 공백",
    "탐지/차단/추적/통지/복구 중 2개 이상이 동시에 무력화",
)

PRIORITY_PAIRS = (
    ("2.10.1", "2.10.8"),
    ("2.10.8", "2.10.9"),
    ("2.5.5", "2.5.6"),
    ("2.6.1", "2.6.2"),
    ("2.6.2", "2.6.3"),
    ("2.9.4", "2.10.1"),
    ("1.4.1", "1.4.2"),
    ("1.2.1", "1.2.2"),
)


def test_relation_evidence_file_exists():
    assert EVIDENCE.is_file()
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert int(payload.get("edgeCount") or 0) >= 40
    assert payload.get("edges")


def test_priority_pairs_have_edges():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    edge_set = {(str(e["source"]), str(e["target"])) for e in payload["edges"]}
    for a, b in PRIORITY_PAIRS:
        assert (a, b) in edge_set or (b, a) in edge_set, f"missing priority edge {a}↔{b}"


def test_compounds_have_no_forbidden_templates():
    compounds = json.loads(COMPOUNDS.read_text(encoding="utf-8"))
    assert len(compounds) >= 20
    for compound in compounds:
        assert compound.get("evidenceRefs"), compound.get("compoundKey")
        assert compound.get("evidenceGrade") in {"strong", "medium", "weak"}
        for problem in compound.get("compoundProblems") or []:
            for tmpl in FORBIDDEN:
                assert tmpl not in str(problem), compound.get("compoundKey")


def test_load_manual_relations_includes_patch_edge():
    from isms_pii_toolkit.control_graph import load_manual_relations, load_relation_evidence

    load_manual_relations.cache_clear()
    load_relation_evidence.cache_clear()
    relations = load_manual_relations()
    targets = {t for t, _ in relations.get("2.10.1", ())}
    assert "2.10.8" in targets or "2.11.3" in targets


def test_synthesize_prefers_evidence_grade():
    from isms_pii_toolkit.control_problem_engine import analyze_problems

    result = analyze_problems(
        {
            "2.10.1": "none",
            "2.10.8": "none",
            "2.5.6": "partial",
        }
    )
    compounds = result["compoundSyntheses"]
    assert compounds
    top = compounds[0]
    assert top.get("evidenceGrade") in {"strong", "medium", "weak"}
    assert "evidenceLabels" in top or top.get("evidenceRefs") is not None


def test_cascade_includes_evidence_label():
    from isms_pii_toolkit.control_insight_kb import build_cascade_risks

    cascades = build_cascade_risks(
        "2.10.1",
        "보안시스템 운영",
        "none",
        {"2.10.1": "none", "2.10.8": "unknown", "2.11.3": "partial"},
    )
    assert cascades
    assert any(c.get("evidenceLabel") for c in cascades)
    assert any(c.get("groundingLevel") in {"casebook_cite", "category_adjacent", "interpret"} for c in cascades)
    assert all(len(c.get("logicSteps") or []) >= 4 for c in cascades)
    assert all(len(c.get("evidenceToCheck") or []) >= 3 for c in cascades)
    assert all(c.get("operationalImpact") for c in cascades)
    assert all(c.get("auditImpact") for c in cascades)


def test_grounding_levels_on_edges_and_compounds():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    compounds = json.loads(COMPOUNDS.read_text(encoding="utf-8"))
    allowed = {"casebook_cite", "category_adjacent", "interpret"}
    assert evidence.get("defectCsvRole")
    for edge in evidence["edges"]:
        assert edge.get("groundingLevel") in allowed
    for compound in compounds:
        assert compound.get("groundingLevel") in allowed
        assert compound.get("groundingNote")
        assert "재구성" in " ".join(str(p) for p in compound.get("compoundProblems") or []) or compound.get(
            "groundingNote"
        )


def test_synthesize_exposes_grounding_note():
    from isms_pii_toolkit.control_problem_engine import analyze_problems

    result = analyze_problems({"2.5.5": "none", "2.5.6": "none"})
    top = result["compoundSyntheses"][0]
    assert top.get("groundingLevel") in {"casebook_cite", "category_adjacent", "interpret"}
    assert top.get("groundingNote")
