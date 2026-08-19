"""Mandatory in-process cost guards for AI report generation."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator


class LlmReportLimitError(RuntimeError):
    """Raised when an AI report request exceeds a cost guard."""


class LlmReportGuard:
    """Per-client fixed-window limit plus global concurrency cap."""

    def __init__(self, *, requests_per_minute: int = 6, max_concurrent: int = 2) -> None:
        self.requests_per_minute = max(1, min(60, requests_per_minute))
        self._counts: dict[tuple[str, int], int] = defaultdict(int)
        self._semaphore = asyncio.Semaphore(max(1, min(8, max_concurrent)))

    def _reserve_request(self, client_id: str) -> None:
        bucket = int(time.time()) // 60
        stale = [key for key in self._counts if key[1] < bucket - 1]
        for key in stale:
            del self._counts[key]
        key = (client_id or "unknown", bucket)
        if self._counts[key] >= self.requests_per_minute:
            raise LlmReportLimitError("AI report request limit exceeded")
        self._counts[key] += 1

    @asynccontextmanager
    async def limit(self, client_id: str) -> AsyncIterator[None]:
        self._reserve_request(client_id)
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.1)
        except TimeoutError as error:
            raise LlmReportLimitError("AI report service is busy") from error
        try:
            yield
        finally:
            self._semaphore.release()
