from __future__ import annotations

import os
import ssl
import time
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen

import certifi

from .models import InterpretationRecord, LawDocumentRecord
from .parser import (
    normalize_law_go_kr_url,
    parse_document_search_list,
    parse_interpretation_detail,
    parse_interpretation_list,
    parse_law_document,
)

DEFAULT_BASE_URL = "https://apis.data.go.kr/1170000/law"


def secure_urlopen(request: Request, *, timeout: float) -> object:
    context = ssl.create_default_context(cafile=certifi.where())
    return urlopen(request, timeout=timeout, context=context)


class LegalApiError(RuntimeError):
    pass


@dataclass
class LegalApiClient:
    service_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 10.0
    max_retries: int = 3
    opener: Callable[..., object] = secure_urlopen

    @classmethod
    def from_env(cls) -> "LegalApiClient":
        key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
        if not key:
            raise LegalApiError("DATA_GO_KR_SERVICE_KEY가 설정되지 않았습니다.")
        return cls(
            service_key=key,
            base_url=os.getenv("LAW_OPEN_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=float(os.getenv("LAW_API_TIMEOUT_SECONDS", "10")),
            max_retries=max(1, min(5, int(os.getenv("LAW_API_MAX_RETRIES", "3")))),
        )

    def search_interpretations(
        self,
        query: str,
        *,
        page_no: int = 1,
        num_rows: int = 20,
    ) -> list[InterpretationRecord]:
        payload = self._get(
            "/expcSearchList.do",
            {
                "serviceKey": self.service_key,
                "target": "expc",
                "query": query or "*",
                "numOfRows": max(1, min(100, num_rows)),
                "pageNo": max(1, page_no),
            },
        )
        return parse_interpretation_list(payload)

    def fetch_interpretation_detail(self, record: InterpretationRecord) -> InterpretationRecord:
        if not record.original_url:
            raise LegalApiError("법령해석례 상세 링크가 없습니다.")
        url = normalize_law_go_kr_url(record.original_url)
        separator = "&" if "?" in url else "?"
        if "type=" not in url:
            url = f"{url}{separator}type=XML"
        else:
            url = url.replace("type=HTML", "type=XML")
        payload = self._request(url)
        return parse_interpretation_detail(payload, fallback=record)

    def fetch_law_document(self, query: str, *, target: str = "law") -> LawDocumentRecord | None:
        if target not in {"law", "admrul"}:
            raise LegalApiError("지원하지 않는 법령 문서 유형입니다.")
        endpoint = "/lawSearchList.do" if target == "law" else "/admrulSearchList.do"
        payload = self._get(endpoint, {
            "serviceKey": self.service_key,
            "target": target,
            "query": query,
            "numOfRows": 20,
            "pageNo": 1,
        })
        candidates = parse_document_search_list(payload, target=target)
        wanted = "".join(query.split()).casefold()
        metadata = next(
            (item for item in candidates if "".join(item["name"].split()).casefold() == wanted),
            candidates[0] if candidates else None,
        )
        if metadata is None:
            return None
        url = metadata["detailUrl"].replace("type=HTML", "type=XML")
        detail = self._request(url)
        return parse_law_document(detail, metadata={**metadata, "detailUrl": url}, target=target)

    def _get(self, path: str, params: dict[str, object]) -> bytes:
        base = self.base_url.rstrip("/")
        if urlparse(base).scheme != "https":
            raise LegalApiError("법령 Open API는 HTTPS 주소만 허용합니다.")
        return self._request(f"{base}/{path.lstrip('/')}?{urlencode(params)}")

    def _request(self, url: str) -> bytes:
        request = Request(url, headers={"Accept": "application/xml", "User-Agent": "isms-p-legal-sync/0.1"})
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.opener(request, timeout=self.timeout_seconds)
                payload = response.read(2_000_001)  # type: ignore[attr-defined]
                if len(payload) > 2_000_000:
                    raise LegalApiError("법령 API 응답이 허용 크기를 초과했습니다.")
                return payload
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt + 1 < self.max_retries:
                    time.sleep(2**attempt)
        raise LegalApiError("법령 API 요청에 실패했습니다. 인증키와 서비스 상태를 확인하세요.") from last_error
