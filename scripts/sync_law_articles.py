#!/usr/bin/env python3
"""101개 ISMS-P 통제에서 참조하는 현행 법령·고시 조문을 동기화한다."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from isms_pii_toolkit.legal_api.client import LegalApiClient, LegalApiError
from isms_pii_toolkit.legal_api.matcher import control_law_references
from isms_pii_toolkit.legal_api.repository import LegalRepository
from isms_pii_toolkit.official_kb import load_control, load_index


def _load_project_env() -> None:
    sync_path = Path(__file__).with_name("sync_legal_interpretations.py")
    spec = importlib.util.spec_from_file_location("legal_sync_env", sync_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module._load_project_env()


def referenced_documents() -> list[tuple[str, str]]:
    names: set[str] = set()
    for item in load_index().get("controls") or []:
        control_id = str(item.get("controlId") or item.get("id") or "")
        record = load_control(control_id) if control_id else None
        if not record:
            continue
        names.update(ref.law_name for ref in control_law_references(record))

    documents: set[tuple[str, str]] = set()
    for name in names:
        normalized = "".join(name.split())
        if "안전성확보조치기준" in normalized:
            documents.add(("개인정보의 안전성 확보조치 기준", "admrul"))
        elif normalized in {"개인정보보호법"}:
            documents.add(("개인정보 보호법", "law"))
        elif normalized in {"정보통신망법", "정보통신망이용촉진및정보보호등에관한법률"}:
            documents.add(("정보통신망 이용촉진 및 정보보호 등에 관한 법률", "law"))
    return sorted(documents)


def main() -> int:
    _load_project_env()
    client = LegalApiClient.from_env()
    repository = LegalRepository()
    saved = 0
    for name, target in referenced_documents():
        try:
            record = client.fetch_law_document(name, target=target)
        except LegalApiError as error:
            print(f"WARN\t{name}\t{error}")
            continue
        if record is None:
            print(f"WARN\t{name}\t검색 결과 없음")
            continue
        record.collected_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
        repository.save_law(record)
        saved += 1
        print(f"{record.document_id}\t{record.name}\t조문 {len(record.articles)}개")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
