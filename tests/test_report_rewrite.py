from __future__ import annotations

from isms_pii_toolkit.llm_provider import make_mock_chat_client
from isms_pii_toolkit.report_rewrite import rewrite_report_passage
from fastapi.testclient import TestClient
from isms_pii_toolkit.api import app


def test_report_rewrite_returns_suggestion_without_applying_it() -> None:
    client = make_mock_chat_client({"suggestion": "위험평가 결과를 경영진에게 보고하였다."})
    result = rewrite_report_passage(
        "위험평가 결과 보고함.",
        "diagnostic_intro",
        chat_client=client,
    )

    assert result["original"] == "위험평가 결과 보고함."
    assert result["suggestion"] == "위험평가 결과를 경영진에게 보고하였다."
    assert result["applied"] is True
    assert result["provider"] == "custom"


def test_report_rewrite_keeps_original_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    result = rewrite_report_passage("원문", "result_interpretation")

    assert result["suggestion"] == "원문"
    assert result["applied"] is False
    assert result["provider"] == "fallback"
    assert "API 키" in str(result["reason"])


def test_report_rewrite_endpoint_reports_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_OPENAI_API_KEY", raising=False)
    response = TestClient(app).post(
        "/controls/report/rewrite",
        json={"text": "선택 문장", "mode": "executive_brief"},
    )

    assert response.status_code == 200
    assert response.json()["applied"] is False
    assert response.json()["suggestion"] == "선택 문장"
