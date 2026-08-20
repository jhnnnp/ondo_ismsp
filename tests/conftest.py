from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_access_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_STORE", str(tmp_path / "access-passes.json"))
    monkeypatch.setenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "0")
    monkeypatch.setenv("PII_TOOLKIT_WORKSPACE_PASS_REQUIRED", "0")
    monkeypatch.delenv("PII_TOOLKIT_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("PII_TOOLKIT_ADMIN_PATH", raising=False)
