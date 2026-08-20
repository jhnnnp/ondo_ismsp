from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app, run
from isms_pii_toolkit.control_assessment import _cached_checklist_controls, list_checklist_controls

client = TestClient(app)


def test_health_endpoint_returns_service_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_page_returns_isms_ui() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ISMS-P" in response.text
    assert "ONDO°" in response.text


def test_workspace_assets_are_cacheable_and_large_api_responses_are_compressed() -> None:
    asset = client.get("/controls/map/assets/app.js")
    checklist = client.get("/controls/checklist", headers={"Accept-Encoding": "gzip"})

    assert asset.headers["cache-control"] == "public, max-age=3600, must-revalidate"
    assert checklist.headers["cache-control"] == "public, max-age=3600, must-revalidate"
    assert checklist.headers["content-encoding"] == "gzip"


def test_reference_checklist_is_built_once_per_process() -> None:
    _cached_checklist_controls.cache_clear()

    first = list_checklist_controls()
    second = list_checklist_controls()

    assert first == second
    assert _cached_checklist_controls.cache_info().misses == 1
    assert _cached_checklist_controls.cache_info().hits == 1


def test_legal_basis_endpoints_work_without_external_api_key() -> None:
    basis = client.get("/controls/3.1.5/legal-basis")
    assert basis.status_code == 200
    payload = basis.json()
    assert payload["controlId"] == "3.1.5"
    assert any(item["article"] == "제20조" for item in payload["laws"])
    assert isinstance(payload["interpretations"], list)
    assert "직접 확정하지 않습니다" in payload["disclaimer"]

    search = client.get("/legal/interpretations?q=개인정보")
    assert search.status_code == 200
    assert search.json()["total"] >= 0


def test_pii_demo_endpoints_are_not_exposed() -> None:
    assert client.post("/scan/text", json={"text": "test@example.com"}).status_code == 404
    assert client.post("/redact/text", json={"text": "test@example.com"}).status_code == 404
    assert client.post("/decrypt/text", json={"text": "token", "encryptionKey": "x"}).status_code == 404
    assert client.get("/controls/pii-bridge/scan").status_code == 404


def test_run_binds_to_localhost_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PII_TOOLKIT_API_HOST", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_API_PORT", raising=False)
    with patch("uvicorn.run") as mock_run:
        run()
    mock_run.assert_called_once_with("isms_pii_toolkit.api:app", host="127.0.0.1", port=8000)
