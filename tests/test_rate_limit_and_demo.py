from fastapi.testclient import TestClient

from isms_pii_toolkit.api import create_app


def test_ui_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ENABLE_DEMO", "0")
    client = TestClient(create_app())
    assert client.get("/").status_code == 404
    assert client.get("/controls/map").status_code == 404
    assert client.get("/controls/map/dashboard").status_code == 404
    assert client.get("/controls/map/assets/app.js").status_code == 404
    assert client.get("/landing/assets/landing.css").status_code == 404
