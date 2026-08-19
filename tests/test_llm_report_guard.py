from __future__ import annotations

import asyncio

import pytest

from isms_pii_toolkit.llm_report_guard import LlmReportGuard, LlmReportLimitError


def test_report_guard_limits_each_client_per_minute() -> None:
    guard = LlmReportGuard(requests_per_minute=2, max_concurrent=1)

    async def exercise() -> None:
        async with guard.limit("client-a"):
            pass
        async with guard.limit("client-a"):
            pass
        with pytest.raises(LlmReportLimitError, match="request limit"):
            async with guard.limit("client-a"):
                pass
        async with guard.limit("client-b"):
            pass

    asyncio.run(exercise())


def test_report_guard_rejects_excess_concurrency() -> None:
    guard = LlmReportGuard(requests_per_minute=6, max_concurrent=1)

    async def exercise() -> None:
        async with guard.limit("client-a"):
            with pytest.raises(LlmReportLimitError, match="busy"):
                async with guard.limit("client-b"):
                    pass

    asyncio.run(exercise())
