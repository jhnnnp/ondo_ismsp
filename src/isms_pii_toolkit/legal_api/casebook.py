from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


CASEBOOK_PATH = Path(__file__).resolve().parent.parent / "data" / "legal_kb" / "casebooks" / "pipc-kisa-2023.json"


@lru_cache(maxsize=1)
def load_casebook_records() -> list[dict[str, object]]:
    if not CASEBOOK_PATH.exists():
        return []
    payload = json.loads(CASEBOOK_PATH.read_text(encoding="utf-8"))
    return [item for item in payload.get("records", []) if isinstance(item, dict)]


def cases_for_control(control_id: str) -> list[dict[str, object]]:
    return [
        item
        for item in load_casebook_records()
        if control_id in [str(value) for value in item.get("controlIds", [])]
    ]
