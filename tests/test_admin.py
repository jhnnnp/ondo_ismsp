from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from isms_pii_toolkit.access_pass import AccessPassError, admin_console_path, register_pass, resolve_session
from isms_pii_toolkit.api import create_app

ADMIN_PATH = "n7k2Qm18xW4pLd9c"


def _prefix(path: str = "") -> str:
    return f"/{ADMIN_PATH}{path}"


def _admin_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, password: str = "admin-secret") -> TestClient:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "1")
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PASSWORD", password)
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", ADMIN_PATH)
    return TestClient(create_app())


def test_admin_console_path_rejects_guessable_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PII_TOOLKIT_ADMIN_PATH", raising=False)
    assert admin_console_path() is None
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", "admin")
    assert admin_console_path() is None
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", "controls")
    assert admin_console_path() is None
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", "short")
    assert admin_console_path() is None
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", "hidden/nested")
    assert admin_console_path() is None
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", ADMIN_PATH)
    assert admin_console_path() == ADMIN_PATH


def test_admin_routes_are_absent_without_secret_path() -> None:
    client = TestClient(create_app())
    assert client.get("/admin").status_code == 404
    assert client.get("/admin/session").status_code == 404
    assert client.post("/admin/login", json={"password": "admin-secret"}).status_code == 404
    assert client.get(_prefix()).status_code == 404
    assert client.get("/docs").status_code == 200
    assert ADMIN_PATH not in client.get("/openapi.json").text
    assert "/admin" not in client.get("/openapi.json").text


def test_reserved_admin_path_does_not_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", "admin")
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PASSWORD", "admin-secret")
    client = TestClient(create_app())
    assert client.get("/admin").status_code == 404
    assert client.get("/admin/session").status_code == 404


def test_admin_page_is_served_only_on_secret_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = _admin_client(monkeypatch, tmp_path)
    assert client.get("/admin").status_code == 404
    response = client.get(_prefix())
    assert response.status_code == 200
    assert "사용권 관리" in response.text
    assert 'id="issueForm"' in response.text
    assert 'rel="icon" href="/favicon.svg"' in response.text
    assert f"{_prefix()}/assets/admin.css" in response.text
    assert 'window.ADMIN_BASE = "' + _prefix() + '"' in response.text
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"
    css = client.get(_prefix("/assets/admin.css"))
    js = client.get(_prefix("/assets/admin.js"))
    assert css.status_code == 200
    assert ".issued-banner" in css.text
    assert js.status_code == 200
    assert "ADMIN_BASE" in js.text
    assert "/admin/passes" not in js.text
    assert "/admin/" not in client.get("/openapi.json").text
    assert ADMIN_PATH not in client.get("/openapi.json").text


def test_admin_requires_configured_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ADMIN_PATH", ADMIN_PATH)
    client = TestClient(create_app())
    session = client.get(_prefix("/session"))
    assert session.status_code == 200
    assert session.json() == {"configured": False, "authenticated": False}
    login = client.post(_prefix("/login"), json={"password": "admin-secret"})
    assert login.status_code == 503
    listed = client.get(_prefix("/passes"))
    assert listed.status_code == 503


def test_admin_can_issue_list_note_and_revoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _admin_client(monkeypatch, tmp_path)
    assert client.get(_prefix("/passes")).status_code == 401
    wrong = client.post(_prefix("/login"), json={"password": "not-the-password"})
    assert wrong.status_code == 401
    login = client.post(_prefix("/login"), json={"password": "admin-secret"})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert f"Path=/{ADMIN_PATH}" in login.headers.get("set-cookie", "")

    issued = client.post(_prefix("/passes"), json={"durationDays": 3, "note": "파일럿"})
    assert issued.status_code == 200
    token = issued.json()["token"]
    pass_id = issued.json()["record"]["id"]
    assert token.startswith("ondo_live_")
    assert issued.json()["record"]["note"] == "파일럿"
    assert issued.json()["record"]["status"] == "unused"

    listed = client.get(_prefix("/passes"))
    assert listed.status_code == 200
    rows = listed.json()["passes"]
    assert len(rows) == 1
    assert rows[0]["id"] == pass_id
    assert "token" not in rows[0]
    assert "tokenHash" not in str(listed.json())

    renamed = client.patch(_prefix(f"/passes/{pass_id}"), json={"note": "김민수"})
    assert renamed.status_code == 200
    assert renamed.json()["note"] == "김민수"

    register_pass(token)
    active = client.get(_prefix("/passes")).json()["passes"][0]
    assert active["status"] == "active"

    revoked = client.post(_prefix(f"/passes/{pass_id}/revoke"))
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    with pytest.raises(AccessPassError, match="회수"):
        register_pass(token)


def test_revoked_pass_cannot_keep_ai_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _admin_client(monkeypatch, tmp_path)
    client.post(_prefix("/login"), json={"password": "admin-secret"})
    issued = client.post(_prefix("/passes"), json={"durationDays": 7, "note": "세션"})
    token = issued.json()["token"]
    pass_id = issued.json()["record"]["id"]
    session, _record = register_pass(token)
    assert resolve_session(session) is not None
    client.post(_prefix(f"/passes/{pass_id}/revoke"))
    assert resolve_session(session) is None


def test_admin_logout_clears_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _admin_client(monkeypatch, tmp_path)
    client.post(_prefix("/login"), json={"password": "admin-secret"})
    assert client.get(_prefix("/passes")).status_code == 200
    logout = client.post(_prefix("/logout"))
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get(_prefix("/passes")).status_code == 401
    assert client.patch(_prefix("/passes/missing"), json={"note": "x"}).status_code == 401
    client = _admin_client(monkeypatch, tmp_path)
    client.post(_prefix("/login"), json={"password": "admin-secret"})
    assert client.post(_prefix("/passes/missing/revoke")).status_code == 404


def test_cli_issue_accepts_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    from io import StringIO

    from isms_pii_toolkit.access_pass import load_store, main

    monkeypatch.setattr("sys.stdout", StringIO())
    monkeypatch.setattr("sys.stderr", StringIO())
    assert main(["issue", "--days", "7", "--note", "내부"]) == 0
    assert load_store()["passes"][0]["note"] == "내부"
