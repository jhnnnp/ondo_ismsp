#!/usr/bin/env python3
"""101개 통제 체크리스트/복합 문제 KB JSON 생성."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from isms_pii_toolkit.control_assessment import CATEGORY_META  # noqa: E402
from isms_pii_toolkit.control_graph import list_controls  # noqa: E402
from isms_pii_toolkit.control_insight_category_deep import CATEGORY_DEEP_INSIGHTS  # noqa: E402
from isms_pii_toolkit.control_insight_kb import (  # noqa: E402
    CONTROL_PROFILES,
    build_checklist_breakdown,
)

DATA_DIR = ROOT / "src" / "isms_pii_toolkit" / "data" / "problem_kb"
CONTROLS_DIR = DATA_DIR / "controls"
COMPOUNDS_FILE = DATA_DIR / "compounds.json"
INDEX_FILE = DATA_DIR / "index.json"

LEVEL_PROBLEM_PREFIX = {
    "unknown": "아직 점검/판단이 이뤄지지 않아",
    "none": "통제가 사실상 작동하지 않아",
    "partial": "일부만 이행되어",
}


def _level_problems(control_id: str, title: str, category_name: str, level: str, risk: str) -> dict:
    prefix = LEVEL_PROBLEM_PREFIX[level]
    return {
        "summary": f"{control_id} {title} — {prefix} {category_name} 영역 보호 공백이 발생합니다.",
        "problems": [
            f"{prefix} {title}({control_id}) 관련 정책/설정/운영기록을 심사에서 설명하기 어렵습니다.",
            f"{risk}",
            f"{title} 미흡 상태가 방치되면 인접 통제 심사에서 연쇄 질의로 확대될 수 있습니다.",
        ],
    }


def build_control_record(control: dict[str, object]) -> dict[str, object]:
    control_id = str(control["id"])
    title = str(control["title"])
    category_id = str(control["categoryId"])
    category_name = str(control["categoryName"])
    meta = CATEGORY_META.get(category_id, {})
    risk = str(meta.get("riskIfMissing", f"{title} 통제 미흡 시 보호 공백"))

    checklist_items: list[dict[str, object]] = []
    for index, row in enumerate(build_checklist_breakdown(control_id, title, category_id, "none"), start=1):
        op = str(row.get("operationalRisk", ""))
        audit = str(row.get("auditRisk", ""))
        checklist_items.append(
            {
                "itemId": str(index),
                "item": str(row.get("item", "")),
                "checkKey": ("reviewed", "policy", "implemented", "evidence")[index - 1]
                if index <= 4
                else "",
                "ifUnchecked": {
                    "problems": [
                        f"체크 미충족 시 {op}",
                        f"심사 관점: {audit}",
                        f"{title}({control_id}) 체크리스트 {index}번 항목 미이행으로 운영/증적 공백",
                    ],
                    "operationalImpact": op,
                    "auditImpact": audit,
                    "remediation": str(row.get("remediation", "")),
                    "relatedControls": list(row.get("relatedControls", [])),
                },
            }
        )

    profile = CONTROL_PROFILES.get(control_id, {})
    deep = CATEGORY_DEEP_INSIGHTS.get(category_id, {})
    scenarios = list(profile.get("scenarios", [])) or list(deep.get("scenarios", []))

    return {
        "controlId": control_id,
        "title": title,
        "areaId": str(control["areaId"]),
        "areaName": str(control["areaName"]),
        "categoryId": category_id,
        "categoryName": category_name,
        "riskIfMissing": risk,
        "focus": str(profile.get("focus", deep.get("focus", f"{title} 지속 이행"))),
        "checklistItems": checklist_items,
        "levelProblems": {
            level: _level_problems(control_id, title, category_name, level, risk)
            for level in ("unknown", "none", "partial")
        },
        "scenarios": scenarios[:5],
        "relatedControlIds": list(control.get("relatedControlIds", []))[:8],
        "scenarioIds": list(control.get("scenarioIds", [])),
    }


def _compound_key(control_ids: tuple[str, ...]) -> str:
    return "|".join(sorted(control_ids))


def build_compounds(controls_by_id: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    """Delegate to evidence-based builder (no generic templates)."""
    del controls_by_id  # controls already on disk / unused for compound text
    from rebuild_compounds_from_evidence import build_compounds as evidenced_build

    return evidenced_build()


def main() -> None:
    CONTROLS_DIR.mkdir(parents=True, exist_ok=True)
    controls = list_controls()
    controls_by_id: dict[str, dict[str, object]] = {}
    index: list[dict[str, str]] = []

    for control in controls:
        record = build_control_record(dict(control))
        cid = str(record["controlId"])
        controls_by_id[cid] = record
        path = CONTROLS_DIR / f"{cid.replace('.', '_')}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append({"controlId": cid, "file": path.name, "title": str(record["title"])})

    # Prefer dedicated evidence rebuild; fall back only if import fails.
    try:
        compounds = build_compounds(controls_by_id)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: evidenced compounds failed ({exc}); writing empty list")
        compounds = []
    COMPOUNDS_FILE.write_text(json.dumps(compounds, ensure_ascii=False, indent=2), encoding="utf-8")

    INDEX_FILE.write_text(
        json.dumps(
            {
                "version": 1,
                "totalControls": len(index),
                "totalCompounds": len(compounds),
                "controls": index,
                "compoundsFile": "compounds.json",
                "relationEvidenceFile": "relation_evidence.json",
                "compoundsEvidenceVersion": 2,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(index)} control JSON files to {CONTROLS_DIR}")
    print(f"Wrote {len(compounds)} compound rules to {COMPOUNDS_FILE}")


if __name__ == "__main__":
    main()
