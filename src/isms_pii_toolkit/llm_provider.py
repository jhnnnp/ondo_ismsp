"""Pluggable LLM chat providers for facts-only verbalization.

Deterministic analyze never depends on this module. Verbalize may swap
OpenAI / mock / custom clients behind the same ChatClient signature.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

ChatClient = Callable[[str, str], str]


@dataclass(frozen=True)
class VerbalizeLlmConfig:
    """Env-backed settings for optional verbalize LLM calls."""

    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    temperature: float

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def load_verbalize_llm_config() -> VerbalizeLlmConfig:
    api_key = os.getenv("PII_TOOLKIT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or None
    if api_key is not None:
        api_key = api_key.strip() or None
    timeout_raw = os.getenv("PII_TOOLKIT_OPENAI_TIMEOUT") or "45"
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 45.0
    return VerbalizeLlmConfig(
        api_key=api_key,
        base_url=(os.getenv("PII_TOOLKIT_OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip(
            "/"
        ),
        model=os.getenv("PII_TOOLKIT_OPENAI_MODEL") or "gpt-4o-mini",
        timeout_seconds=max(5.0, min(180.0, timeout_seconds)),
        temperature=0.2,
    )


def openai_chat_client(
    system_prompt: str,
    user_prompt: str,
    *,
    config: VerbalizeLlmConfig | None = None,
) -> str:
    cfg = config or load_verbalize_llm_config()
    if not cfg.api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    body = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        f"{cfg.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=cfg.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail[:300]}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("OpenAI response missing choices")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("OpenAI response missing content")
    return str(content)


def make_openai_chat_client(config: VerbalizeLlmConfig | None = None) -> ChatClient:
    cfg = config or load_verbalize_llm_config()

    def _client(system_prompt: str, user_prompt: str) -> str:
        return openai_chat_client(system_prompt, user_prompt, config=cfg)

    return _client


def make_mock_chat_client(payload: dict[str, Any] | Callable[[str, str], dict[str, Any]]) -> ChatClient:
    """Test/local provider: always returns JSON for the given payload or factory."""

    def _client(system_prompt: str, user_prompt: str) -> str:
        data = payload if isinstance(payload, dict) else payload(system_prompt, user_prompt)
        if not isinstance(data, dict):
            raise TypeError("mock chat payload must be a dict")
        return json.dumps(data, ensure_ascii=False)

    return _client


def resolve_chat_client(
    chat_client: ChatClient | None = None,
    *,
    config: VerbalizeLlmConfig | None = None,
) -> tuple[ChatClient | None, str, VerbalizeLlmConfig]:
    """Resolve which client to use.

    Returns (client_or_none, provider_name, config).
    client is None when verbalize should keep template narratives.
    """
    cfg = config or load_verbalize_llm_config()
    if chat_client is not None:
        return chat_client, "custom", cfg
    if not cfg.configured:
        return None, "fallback", cfg
    return make_openai_chat_client(cfg), "openai", cfg
