from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_assessment import list_checklist_controls
from isms_pii_toolkit.control_search import (
    USER_SEARCH_ALIASES,
    build_search_entries,
    build_search_hints,
    build_search_intents,
)

client = TestClient(app)


def test_account_control_has_user_wording_hints() -> None:
    hints = " ".join(build_search_hints("2.5.1"))
    compact = hints.replace(" ", "")
    assert "불필요한계정제거" in compact
    assert "미사용계정" in compact


def test_account_lifecycle_intents_are_kept_on_their_own_controls() -> None:
    account = " ".join(build_search_hints("2.5.1")).replace(" ", "")
    employment = " ".join(build_search_hints("2.2.5")).replace(" ", "")
    contractor = " ".join(build_search_hints("2.3.4")).replace(" ", "")

    assert "계정필요성확인" in account
    assert "재직여부확인" in employment
    assert "계약만료계정삭제" in contractor
    assert "불필요한계정제거" not in employment


def test_patch_control_has_operational_wording_hints() -> None:
    hints = " ".join(build_search_hints("2.10.8"))
    compact = hints.replace(" ", "")
    assert "보안패치" in compact
    assert "패치" in compact


def test_checklist_payload_includes_search_hints() -> None:
    controls = {str(item["id"]): item for item in list_checklist_controls()}
    account = controls["2.5.1"]
    assert account["searchHints"]
    assert any("불필요" in hint and "계정" in hint for hint in account["searchHints"])


def test_checklist_api_exposes_search_hints() -> None:
    payload = client.get("/controls/checklist").json()
    account = next(item for item in payload["controls"] if item["id"] == "2.5.1")
    compact = " ".join(account["searchHints"]).replace(" ", "")
    assert "불필요한계정제거" in compact


def test_every_control_has_multiple_user_wording_aliases() -> None:
    controls = list_checklist_controls()
    control_ids = {str(item["id"]) for item in controls}

    assert set(USER_SEARCH_ALIASES) == control_ids
    assert all(len(USER_SEARCH_ALIASES[control_id]) >= 2 for control_id in control_ids)
    assert sum(len(items) for items in USER_SEARCH_ALIASES.values()) >= 300


def test_every_user_wording_alias_is_exposed_as_a_search_hint() -> None:
    for control_id, aliases in USER_SEARCH_ALIASES.items():
        hints = {"".join(item.lower().split()) for item in build_search_hints(control_id)}
        for alias in aliases:
            assert "".join(alias.lower().split()) in hints, (control_id, alias)


def test_weighted_search_index_has_more_than_one_thousand_expressions() -> None:
    entries = [
        entry
        for control_id in USER_SEARCH_ALIASES
        for entry in build_search_entries(control_id)
    ]

    assert len(entries) >= 1_000
    assert {entry["kind"] for entry in entries} >= {"alias", "problem", "audit", "official"}
    assert all(0 < int(entry["weight"]) <= 100 for entry in entries)


def test_checklist_api_exposes_weighted_search_entries() -> None:
    payload = client.get("/controls/checklist").json()
    account = next(item for item in payload["controls"] if item["id"] == "2.5.1")
    exact = next(item for item in account["searchEntries"] if item["text"] == "불필요한 계정 제거")

    assert exact == {"text": "불필요한 계정 제거", "weight": 100, "kind": "alias"}


def test_all_101_controls_have_structured_field_intents() -> None:
    assert len(USER_SEARCH_ALIASES) == 101
    for control_id, aliases in USER_SEARCH_ALIASES.items():
        intents = build_search_intents(control_id)
        assert len(intents) == len(aliases), control_id
        assert all(intent["concepts"] for intent in intents), control_id
        assert all(intent["reason"] for intent in intents), control_id


def test_checklist_api_exposes_intent_signatures_for_every_control() -> None:
    payload = client.get("/controls/checklist").json()
    assert len(payload["controls"]) == 101
    assert all(control["searchIntents"] for control in payload["controls"])

    account = next(control for control in payload["controls"] if control["id"] == "2.5.1")
    intent = next(row for row in account["searchIntents"] if row["phrase"] == "계정 필요성 확인")
    assert "계정" in intent["concepts"]
    assert "필요성" in intent["concepts"]
