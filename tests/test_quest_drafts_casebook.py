"""Offline casebook quest draft script invariants."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_quest_drafts_from_casebook.py"
QUEST_DIR = ROOT / "src/isms_pii_toolkit/data/quest_kb/controls"
WEIGHTS = ROOT / "src/isms_pii_toolkit/data/problem_kb/defect_weights.json"
DRAFT_DIR = ROOT / "src/isms_pii_toolkit/data/quest_kb/drafts"


def test_locked_quests_remain_handcrafted():
    locked = {
        "2.5.4",
        "2.6.1",
        "2.6.2",
        "2.10.1",
        "1.4.1",
        "2.10.8",
        "2.5.6",
        "2.6.3",
        "1.2.1",
        "1.2.3",
        "1.2.4",
        "2.6.7",
        "2.9.5",
        "2.9.4",
        "2.8.5",
        "2.6.6",
        "2.6.4",
        "2.10.9",
        # mid-defect handcraft
        "1.1.5",
        "2.4.7",
        "2.5.5",
        "2.7.1",
        "1.1.3",
        "1.3.1",
        "2.3.1",
        "2.3.2",
        "2.5.3",
    }
    for cid in locked:
        path = QUEST_DIR / f"{cid.replace('.', '_')}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("locked") is True, cid
        assert data.get("quality") == "handcrafted", cid
        q = data["quest"]["plainQuestion"]
        assert "…" not in q, cid
        assert "?" in q or q.endswith("나요") or q.endswith("가요"), cid


def test_high_defect_quests_are_handcrafted():
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))["controls"]
    high = [
        cid
        for cid, meta in weights.items()
        if int(meta.get("defectCount") or 0) >= 4
    ]
    assert len(high) >= 10
    for cid in high:
        path = QUEST_DIR / f"{cid.replace('.', '_')}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("quality") == "handcrafted", cid
        assert data.get("locked") is True, cid
        quest = data["quest"]
        assert quest.get("plainQuestion")
        assert len(quest.get("checks") or []) >= 2
        assert "업로드하세요" not in (quest.get("actionGuide") or {}).get("whenDone", "")
        if data.get("meta"):
            assert data["meta"].get("sourceDoc") == "사례집.md"


def test_mid_defect_quests_are_handcrafted():
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))["controls"]
    mid = [
        cid
        for cid, meta in weights.items()
        if 2 <= int(meta.get("defectCount") or 0) <= 3
    ]
    assert mid
    for cid in mid:
        path = QUEST_DIR / f"{cid.replace('.', '_')}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("quality") == "handcrafted", cid
        assert data.get("locked") is True, cid
        assert "…" not in data["quest"]["plainQuestion"], cid
        assert (data.get("meta") or {}).get("sourceDoc") == "사례집.md", cid


def test_draft_script_skips_locked_on_apply():
    # Dry-run generation for a locked control should still write draft, not mutate locked file
    before = json.loads((QUEST_DIR / "2_5_4.json").read_text(encoding="utf-8"))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--control-id", "2.5.4", "--apply"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "locked" in proc.stdout
    after = json.loads((QUEST_DIR / "2_5_4.json").read_text(encoding="utf-8"))
    assert after == before
    draft = DRAFT_DIR / "2_5_4.json"
    assert draft.exists()
    draft_data = json.loads(draft.read_text(encoding="utf-8"))
    assert draft_data["quality"] == "casebook-draft"
    assert draft_data["controlId"] == "2.5.4"


def test_min_cases_zero_does_not_select_all_controls():
    """Regression: min_cases=0 must not treat every control as a target."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("quest_drafts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))["controls"]
    targets = []
    min_defect = 4
    min_cases = 0
    for cid, meta in weights.items():
        defect_ok = int(meta.get("defectCount") or 0) >= min_defect
        cases_ok = min_cases > 0 and int(meta.get("caseCount") or 0) >= min_cases
        if defect_ok or cases_ok:
            targets.append(cid)
    assert 10 <= len(targets) <= 40
    assert all(int(weights[c]["defectCount"]) >= 4 for c in targets)
