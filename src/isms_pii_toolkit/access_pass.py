"""Random AI-report usage passes. Server stores hashes only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COOKIE_NAME = "ondo_ai_pass"
ADMIN_COOKIE_NAME = "ondo_admin"
TOKEN_PREFIX = "ondo_live_"
SESSION_PREFIX = "ondo_sess_"
ADMIN_SESSION_PREFIX = "ondo_adm_"
STORE_VERSION = 1
MIN_DURATION_DAYS = 1
MAX_DURATION_DAYS = 90
DEFAULT_DURATION_DAYS = 7
NOTE_MAX_LENGTH = 80
ADMIN_PASSWORD_MIN_LENGTH = 8
ADMIN_SESSION_HOURS = 12
ADMIN_LOGIN_PER_MINUTE = 8
ADMIN_PATH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{11,63}$")
RESERVED_ADMIN_PATHS = frozenset({
    "admin",
    "administrator",
    "api",
    "assets",
    "backend",
    "console",
    "controls",
    "dashboard",
    "docs",
    "favicon.ico",
    "health",
    "landing",
    "login",
    "logout",
    "manage",
    "openapi.json",
    "panel",
    "redoc",
    "secret",
    "staff",
    "static",
    "wp-admin",
})

_LOCK = threading.Lock()
_admin_login_counts: dict[tuple[str, int], int] = defaultdict(int)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def generate_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(24)}"


def generate_session_token() -> str:
    return f"{SESSION_PREFIX}{secrets.token_urlsafe(24)}"


def generate_admin_session_token() -> str:
    return f"{ADMIN_SESSION_PREFIX}{secrets.token_urlsafe(24)}"


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_note(note: str | None) -> str:
    return str(note or "").strip()[:NOTE_MAX_LENGTH]


def access_pass_required() -> bool:
    return os.getenv("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "1").lower() not in ("0", "false", "no")


def admin_password() -> str:
    return os.getenv("PII_TOOLKIT_ADMIN_PASSWORD", "").strip()


def admin_configured() -> bool:
    return len(admin_password()) >= ADMIN_PASSWORD_MIN_LENGTH


def admin_console_path() -> str | None:
    raw = os.getenv("PII_TOOLKIT_ADMIN_PATH", "").strip().strip("/")
    if not raw or "/" in raw or raw.lower() in RESERVED_ADMIN_PATHS:
        return None
    if not ADMIN_PATH_PATTERN.fullmatch(raw):
        return None
    return raw


def verify_admin_password(candidate: str) -> bool:
    expected = admin_password()
    if not admin_configured():
        return False
    return secrets.compare_digest(hash_secret(str(candidate or "")), hash_secret(expected))


def store_path() -> Path:
    configured = os.getenv("PII_TOOLKIT_ACCESS_PASS_STORE", "").strip()
    if configured:
        return Path(configured)
    return Path.home() / ".ondo" / "access-passes.json"


def empty_store() -> dict[str, Any]:
    return {"version": STORE_VERSION, "passes": [], "adminSessions": []}


def load_store() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_store()
    if not isinstance(payload, dict):
        return empty_store()
    passes = payload.get("passes")
    sessions = payload.get("adminSessions")
    if not isinstance(passes, list):
        passes = []
    if not isinstance(sessions, list):
        sessions = []
    return {
        "version": STORE_VERSION,
        "passes": [item for item in passes if isinstance(item, dict)],
        "adminSessions": [item for item in sessions if isinstance(item, dict)],
    }


def save_store(payload: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {
        "version": STORE_VERSION,
        "passes": payload.get("passes") if isinstance(payload.get("passes"), list) else [],
        "adminSessions": payload.get("adminSessions") if isinstance(payload.get("adminSessions"), list) else [],
    }
    serialized = json.dumps(normalized, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(serialized, encoding="utf-8")
    tmp.replace(path)


def bounded_duration_days(days: int) -> int:
    return max(MIN_DURATION_DAYS, min(MAX_DURATION_DAYS, int(days)))


def remaining_seconds(expires_at: str | None, now: datetime | None = None) -> int:
    expiry = parse_iso(expires_at)
    if expiry is None:
        return 0
    delta = expiry - (now or utc_now())
    return max(0, int(delta.total_seconds()))


def pass_lifecycle(record: dict[str, Any], now: datetime | None = None) -> str:
    if record.get("revokedAt"):
        return "revoked"
    current = now or utc_now()
    expires_at = parse_iso(record.get("expiresAt"))
    if expires_at is not None and expires_at <= current:
        return "expired"
    if record.get("activatedAt"):
        return "active"
    return "unused"


def pass_summary(record: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    status = pass_lifecycle(record, now)
    remaining = remaining_seconds(str(record.get("expiresAt") or ""), now) if status == "active" else 0
    return {
        "id": record.get("id"),
        "note": record.get("note") or "",
        "durationDays": record.get("durationDays"),
        "createdAt": record.get("createdAt"),
        "activatedAt": record.get("activatedAt"),
        "expiresAt": record.get("expiresAt"),
        "revokedAt": record.get("revokedAt"),
        "status": status,
        "remainingSeconds": remaining,
    }


def public_status(record: dict[str, Any] | None, *, required: bool | None = None, now: datetime | None = None) -> dict[str, Any]:
    is_required = access_pass_required() if required is None else required
    if not is_required:
        return {
            "required": False,
            "active": True,
            "remainingSeconds": None,
            "expiresAt": None,
            "durationDays": None,
        }
    if record is None or pass_lifecycle(record, now) != "active":
        return {
            "required": True,
            "active": False,
            "remainingSeconds": 0,
            "expiresAt": None if record is None else record.get("expiresAt"),
            "durationDays": None if record is None else record.get("durationDays"),
        }
    seconds = remaining_seconds(str(record.get("expiresAt") or ""), now)
    return {
        "required": True,
        "active": seconds > 0,
        "remainingSeconds": seconds,
        "expiresAt": record.get("expiresAt"),
        "durationDays": record.get("durationDays"),
    }


def issue_pass(
    *,
    duration_days: int = DEFAULT_DURATION_DAYS,
    note: str = "",
    now: datetime | None = None,
) -> str:
    token, _record = issue_pass_record(duration_days=duration_days, note=note, now=now)
    return token


def issue_pass_record(
    *,
    duration_days: int = DEFAULT_DURATION_DAYS,
    note: str = "",
    now: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    days = bounded_duration_days(duration_days)
    created = now or utc_now()
    token = generate_token()
    record = {
        "id": secrets.token_hex(8),
        "tokenHash": hash_secret(token),
        "note": normalize_note(note),
        "durationDays": days,
        "createdAt": to_iso(created),
        "activatedAt": None,
        "expiresAt": None,
        "revokedAt": None,
        "sessionHash": None,
    }
    with _LOCK:
        payload = load_store()
        payload["passes"].append(record)
        save_store(payload)
    return token, dict(record)


def list_passes(*, now: datetime | None = None) -> list[dict[str, Any]]:
    payload = load_store()
    rows = [pass_summary(item, now) for item in payload["passes"]]
    rows.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
    return rows


def _find_by_id(payload: dict[str, Any], pass_id: str) -> dict[str, Any] | None:
    for item in payload["passes"]:
        if item.get("id") == pass_id:
            return item
    return None


def _find_by_hash(payload: dict[str, Any], field: str, digest: str) -> dict[str, Any] | None:
    for item in payload["passes"]:
        if item.get(field) == digest:
            return item
    return None


class AccessPassError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def update_pass_note(pass_id: str, note: str) -> dict[str, Any]:
    cleaned_id = str(pass_id or "").strip()
    with _LOCK:
        payload = load_store()
        record = _find_by_id(payload, cleaned_id)
        if record is None:
            raise AccessPassError("사용권을 찾을 수 없습니다.", status_code=404)
        record["note"] = normalize_note(note)
        save_store(payload)
        snapshot = dict(record)
    return snapshot


def revoke_pass(pass_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    cleaned_id = str(pass_id or "").strip()
    current = now or utc_now()
    with _LOCK:
        payload = load_store()
        record = _find_by_id(payload, cleaned_id)
        if record is None:
            raise AccessPassError("사용권을 찾을 수 없습니다.", status_code=404)
        if not record.get("revokedAt"):
            record["revokedAt"] = to_iso(current)
            record["sessionHash"] = None
            save_store(payload)
        snapshot = dict(record)
    return snapshot


def register_pass(token: str, *, now: datetime | None = None) -> tuple[str, dict[str, Any]]:
    cleaned = str(token or "").strip()
    if len(cleaned) < 16:
        raise AccessPassError("사용권 형식이 올바르지 않습니다.")
    current = now or utc_now()
    token_digest = hash_secret(cleaned)
    session_token = generate_session_token()
    session_digest = hash_secret(session_token)
    with _LOCK:
        payload = load_store()
        record = _find_by_hash(payload, "tokenHash", token_digest)
        if record is None:
            raise AccessPassError("유효하지 않은 사용권입니다.")
        if record.get("revokedAt"):
            raise AccessPassError("회수된 사용권입니다.", status_code=403)
        expires_at = parse_iso(record.get("expiresAt"))
        if expires_at is not None and expires_at <= current:
            raise AccessPassError("만료된 사용권입니다.", status_code=403)
        if record.get("activatedAt") is None:
            days = bounded_duration_days(int(record.get("durationDays") or DEFAULT_DURATION_DAYS))
            record["activatedAt"] = to_iso(current)
            record["expiresAt"] = to_iso(current + timedelta(days=days))
            record["durationDays"] = days
        record["sessionHash"] = session_digest
        save_store(payload)
        snapshot = dict(record)
    return session_token, snapshot


def resolve_session(session_token: str | None, *, now: datetime | None = None) -> dict[str, Any] | None:
    cleaned = str(session_token or "").strip()
    if not cleaned:
        return None
    current = now or utc_now()
    digest = hash_secret(cleaned)
    payload = load_store()
    record = _find_by_hash(payload, "sessionHash", digest)
    if record is None:
        return None
    if pass_lifecycle(record, current) != "active":
        return None
    if remaining_seconds(str(record.get("expiresAt") or ""), current) <= 0:
        return None
    return dict(record)


def reserve_admin_login(client_id: str) -> None:
    bucket = int(time.time()) // 60
    stale = [key for key in _admin_login_counts if key[1] < bucket - 1]
    for key in stale:
        del _admin_login_counts[key]
    key = (client_id or "unknown", bucket)
    if _admin_login_counts[key] >= ADMIN_LOGIN_PER_MINUTE:
        raise AccessPassError("로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요.", status_code=429)
    _admin_login_counts[key] += 1


def create_admin_session(*, now: datetime | None = None) -> str:
    current = now or utc_now()
    token = generate_admin_session_token()
    expires = current + timedelta(hours=ADMIN_SESSION_HOURS)
    with _LOCK:
        payload = load_store()
        payload["adminSessions"] = [
            item
            for item in payload.get("adminSessions", [])
            if remaining_seconds(str(item.get("expiresAt") or ""), current) > 0
        ]
        payload["adminSessions"].append({
            "sessionHash": hash_secret(token),
            "expiresAt": to_iso(expires),
        })
        save_store(payload)
    return token


def resolve_admin_session(session_token: str | None, *, now: datetime | None = None) -> dict[str, Any] | None:
    cleaned = str(session_token or "").strip()
    if not cleaned or not admin_configured():
        return None
    current = now or utc_now()
    digest = hash_secret(cleaned)
    payload = load_store()
    for item in payload.get("adminSessions", []):
        if item.get("sessionHash") != digest:
            continue
        if remaining_seconds(str(item.get("expiresAt") or ""), current) <= 0:
            return None
        return dict(item)
    return None


def clear_admin_session(session_token: str | None) -> None:
    cleaned = str(session_token or "").strip()
    if not cleaned:
        return
    digest = hash_secret(cleaned)
    with _LOCK:
        payload = load_store()
        payload["adminSessions"] = [
            item for item in payload.get("adminSessions", []) if item.get("sessionHash") != digest
        ]
        save_store(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="isms-p-pass", description="AI 보고서 사용권을 발급합니다.")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue", help="난수 사용권을 하나 발급합니다.")
    issue.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DURATION_DAYS,
        help=f"첫 등록 후 유효 일수 ({MIN_DURATION_DAYS}-{MAX_DURATION_DAYS})",
    )
    issue.add_argument("--note", default="", help="관리용 메모")
    args = parser.parse_args(argv)
    if args.command == "issue":
        days = bounded_duration_days(args.days)
        token = issue_pass(duration_days=days, note=args.note)
        print(token)
        print(f"첫 등록 후 {days}일 동안 AI 보고서에 사용할 수 있습니다.", file=sys.stderr)
        print("이 문자열은 다시 보여주지 않습니다. 사용자에게만 전달하세요.", file=sys.stderr)
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
