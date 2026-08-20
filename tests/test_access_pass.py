from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from isms_pii_toolkit.access_pass import (
    COOKIE_NAME,
    AccessPassError,
    issue_pass,
    load_store,
    main,
    public_status,
    register_pass,
    remaining_seconds,
    resolve_session,
    save_store,
)
from isms_pii_toolkit.api import create_app
from isms_pii_toolkit.control_assessment import bootstrap_assessment


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "1")
    monkeypatch.setenv("PII_TOOLKIT_WORKSPACE_PASS_REQUIRED", "1")
    return TestClient(create_app())


def test_issue_and_register_starts_clock_from_first_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    now = datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc)
    token = issue_pass(duration_days=3, now=now)
    assert token.startswith("ondo_live_")
    store = load_store()
    assert store["passes"][0]["activatedAt"] is None
    assert store["passes"][0]["tokenHash"] != token

    session, record = register_pass(token, now=now)
    assert session.startswith("ondo_sess_")
    assert record["activatedAt"] == "2026-08-19T08:00:00+00:00"
    assert record["expiresAt"] == "2026-08-22T08:00:00+00:00"
    assert remaining_seconds(record["expiresAt"], now + timedelta(days=2, hours=1)) == 23 * 3600
    assert resolve_session(session, now=now) is not None
    assert resolve_session("ondo_sess_unknown", now=now) is None


def test_expired_pass_cannot_register_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    token = issue_pass(duration_days=3, now=now)
    register_pass(token, now=now)
    with pytest.raises(AccessPassError, match="만료"):
        register_pass(token, now=now + timedelta(days=4))


def test_unknown_token_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    with pytest.raises(AccessPassError, match="유효하지 않은"):
        register_pass("ondo_live_this-is-not-a-real-token")


def test_report_endpoints_require_registered_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    client = _client(monkeypatch, tmp_path)
    assessments = bootstrap_assessment()
    payload = {"assessments": assessments}

    blocked = client.post("/controls/report", json=payload)
    assert blocked.status_code == 403
    rewrite = client.post("/controls/report/rewrite", json={"text": "선택 문장", "mode": "executive_brief"})
    assert rewrite.status_code == 403
    analyze = client.post("/controls/analyze", json=payload)
    assert analyze.status_code == 200

    token = issue_pass(duration_days=7)
    registered = client.post("/access/register", json={"token": token})
    assert registered.status_code == 200
    body = registered.json()
    assert body["required"] is True
    assert body["workspaceRequired"] is True
    assert body["active"] is True
    assert body["remainingSeconds"] > 6 * 24 * 3600
    assert COOKIE_NAME in client.cookies

    allowed = client.post("/controls/report", json=payload)
    assert allowed.status_code == 200
    allowed_rewrite = client.post(
        "/controls/report/rewrite",
        json={"text": "선택 문장", "mode": "executive_brief"},
    )
    assert allowed_rewrite.status_code == 200
    status = client.get("/access/status")
    assert status.status_code == 200
    assert status.json()["active"] is True
    workspace = client.get("/workspace")
    assert 'class="is-workspace-locked"' not in workspace.text
    assert workspace.headers.get("x-robots-tag") == "noindex, nofollow"


def test_status_without_cookie_is_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.get("/access/status")
    assert response.status_code == 200
    assert response.json() == {
        "required": True,
        "workspaceRequired": True,
        "active": False,
        "remainingSeconds": 0,
        "expiresAt": None,
        "durationDays": None,
        "kind": None,
    }
    workspace = client.get("/workspace")
    assert workspace.status_code == 200
    assert 'class="is-workspace-locked"' in workspace.text
    assert 'id="workspaceAccessGate"' in workspace.text


def test_optional_pass_keeps_ai_report_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "0")
    monkeypatch.setenv("PII_TOOLKIT_WORKSPACE_PASS_REQUIRED", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    response = client.post("/controls/report", json={"assessments": bootstrap_assessment()})
    assert response.status_code == 200
    status = client.get("/access/status").json()
    assert status["required"] is False
    assert status["workspaceRequired"] is True
    assert status["active"] is False
    workspace = client.get("/workspace")
    assert 'class="is-workspace-locked"' in workspace.text


def test_open_workspace_still_requires_ai_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "1")
    monkeypatch.setenv("PII_TOOLKIT_WORKSPACE_PASS_REQUIRED", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    workspace = client.get("/workspace")
    assert workspace.status_code == 200
    assert 'class="is-workspace-locked"' not in workspace.text
    blocked = client.post("/controls/report", json={"assessments": bootstrap_assessment()})
    assert blocked.status_code == 403
    status = client.get("/access/status").json()
    assert status["required"] is True
    assert status["workspaceRequired"] is False
    assert status["active"] is False


def test_cli_issue_prints_token_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    stdout = StringIO()
    stderr = StringIO()
    monkeypatch.setattr("sys.stdout", stdout)
    monkeypatch.setattr("sys.stderr", stderr)
    assert main(["issue", "--days", "3"]) == 0
    token = stdout.getvalue().strip()
    assert token.startswith("ondo_live_")
    assert "3일" in stderr.getvalue()
    saved = load_store()
    assert saved["passes"][0]["durationDays"] == 3
    assert saved["passes"][0]["tokenHash"] != token


def test_short_token_and_naive_expiry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    with pytest.raises(AccessPassError, match="형식"):
        register_pass("too-short")
    naive = datetime(2026, 8, 22, 8, 0, tzinfo=timezone.utc)
    assert remaining_seconds("2026-08-22T08:00:00", naive) == 0
    assert remaining_seconds(None) == 0
    token = issue_pass(duration_days=1, now=datetime(2026, 8, 19, tzinfo=timezone.utc))
    session, _record = register_pass(token, now=datetime(2026, 8, 19, tzinfo=timezone.utc))
    assert resolve_session(session, now=datetime(2026, 8, 21, tzinfo=timezone.utc)) is None


def test_default_store_path_uses_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PII_TOOLKIT_ACCESS_PASS_STORE", raising=False)
    monkeypatch.setattr("isms_pii_toolkit.access_pass.Path.home", lambda: tmp_path)
    from isms_pii_toolkit.access_pass import store_path

    assert store_path() == tmp_path / ".ondo" / "access-passes.json"
    status = public_status(None, required=True)
    assert status["active"] is False
    assert status["remainingSeconds"] == 0


def test_corrupted_store_starts_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "access-passes.json"
    store.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(store))
    token = issue_pass(duration_days=7)
    assert token.startswith("ondo_live_")
    save_store({"version": 1, "passes": "bad"})
    assert load_store()["passes"] == []


def test_blob_store_roundtrip_without_local_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PII_TOOLKIT_ACCESS_PASS_STORE", raising=False)
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "vercel_blob_rw_testhostid1_secret")
    remote: dict[str, object] = {}

    def fake_load() -> dict:
        return remote.get("payload") or {"version": 1, "passes": [], "adminSessions": []}

    def fake_save(payload: dict) -> None:
        remote["payload"] = payload

    monkeypatch.setattr("isms_pii_toolkit.access_pass._load_blob_store", fake_load)
    monkeypatch.setattr("isms_pii_toolkit.access_pass._save_blob_store", fake_save)
    token = issue_pass(duration_days=3, note="배포")
    payload = remote["payload"]
    assert isinstance(payload, dict)
    assert payload["passes"][0]["note"] == "배포"
    session, _record = register_pass(token)
    assert session.startswith("ondo_sess_")
    assert resolve_session(session) is not None
