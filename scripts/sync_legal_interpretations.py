#!/usr/bin/env python3
"""법제처 법령해석례를 검색해 로컬 legal_kb로 동기화한다.

사용자 요청 처리 중 실행하지 않고 운영 배치/개발 명령으로만 사용한다.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from isms_pii_toolkit.legal_api.client import LegalApiClient, LegalApiError
from isms_pii_toolkit.legal_api.repository import LegalRepository

DEFAULT_QUERIES = [
    "개인정보 보호법",
    "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
    "개인정보",
    "정보보호",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="법제처 법령해석례 로컬 동기화")
    parser.add_argument("--query", action="append", dest="queries", help="검색어(반복 가능)")
    parser.add_argument("--pages", type=int, default=1, help="검색어별 최대 페이지")
    parser.add_argument("--rows", type=int, default=20, help="페이지당 목록 수(최대 100)")
    parser.add_argument("--list-only", action="store_true", help="상세 본문을 조회하지 않음")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 대상만 출력")
    parser.add_argument(
        "--all-control-laws",
        action="store_true",
        help="101개 공식 통제에서 관련 법령·조문 검색어를 자동 생성",
    )
    return parser.parse_args()


def main() -> int:
    _load_project_env()
    args = parse_args()
    client = LegalApiClient.from_env()
    repository = LegalRepository()
    seen: set[str] = set()
    saved = 0
    errors: list[str] = []

    queries = args.queries or (_control_law_queries() if args.all_control_laws else DEFAULT_QUERIES)
    for query in queries:
        for page in range(1, max(1, args.pages) + 1):
            try:
                records = client.search_interpretations(query, page_no=page, num_rows=args.rows)
            except LegalApiError as error:
                errors.append(f"{query}/{page}: {error}")
                continue
            for list_record in records:
                if list_record.interpretation_id in seen:
                    continue
                seen.add(list_record.interpretation_id)
                if repository.get(list_record.interpretation_id) is not None:
                    continue
                record = list_record
                if not args.list_only:
                    try:
                        record = client.fetch_interpretation_detail(list_record)
                    except LegalApiError as error:
                        errors.append(f"{list_record.interpretation_id}: {error}")
                record.collected_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
                print(f"{record.interpretation_id}\t{record.title}")
                if not args.dry_run:
                    repository.save(record)
                    saved += 1

    if not args.dry_run:
        _write_sync_state(repository, saved=saved, errors=errors)
    if errors:
        for error in errors:
            print(f"WARN\t{error}")
    return 0 if saved or args.dry_run else 1


def _control_law_queries() -> list[str]:
    from isms_pii_toolkit.legal_api.matcher import control_law_references
    from isms_pii_toolkit.official_kb import load_index, load_control

    queries: set[str] = set()
    for item in load_index().get("controls") or []:
        control_id = str(item.get("controlId") or item.get("id") or "")
        control = load_control(control_id) if control_id else None
        if not control:
            continue
        for ref in control_law_references(control):
            law_name = ref.law_name.replace("개인정보보호법", "개인정보 보호법")
            queries.add(" ".join(filter(None, [law_name, ref.article])))
    return sorted(queries)


def _load_project_env() -> None:
    """프로젝트 .env를 읽되 이미 주입된 운영 환경변수를 덮어쓰지 않는다."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _write_sync_state(repository: LegalRepository, *, saved: int, errors: list[str]) -> None:
    repository.root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    previous: dict[str, object] = {}
    state_path = repository.root / "sync_state.json"
    if state_path.exists():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = {}
    payload = {
        "status": "PARTIAL" if errors else "SUCCESS",
        "lastSuccessfulSync": now if saved else previous.get("lastSuccessfulSync"),
        "saved": saved,
        "totalRecords": len(repository.all()),
        "errorCount": len(errors),
        "sources": {"data_go_kr_expc": {"syncedAt": now}},
    }
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
