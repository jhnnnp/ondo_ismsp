"""Random AI-report usage passes. Server stores hashes only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
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
BLOB_STORE_PATHNAME = "ondo/access-passes.json"
BLOB_API_VERSION = "12"
BLOB_HTTP_TIMEOUT = 12
MIN_DURATION_DAYS = 1
MAX_DURATION_DAYS = 90
DEFAULT_DURATION_DAYS = 7
PASS_KIND_TIMED = "timed"
PASS_KIND_INVITE = "invite"
PASS_KINDS = frozenset({PASS_KIND_TIMED, PASS_KIND_INVITE})
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
    "workspace",
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


def _env_flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).lower() not in ("0", "false", "no")


def access_pass_required() -> bool:
    """AI report endpoints require a registered pass."""
    return _env_flag("PII_TOOLKIT_ACCESS_PASS_REQUIRED", "1")


def workspace_pass_required() -> bool:
    """Workspace UI requires a registered pass before the product renders."""
    return _env_flag("PII_TOOLKIT_WORKSPACE_PASS_REQUIRED", "1")


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


def blob_read_write_token() -> str:
    return os.getenv("BLOB_READ_WRITE_TOKEN", "").strip().strip('"')


def use_blob_store() -> bool:
    if os.getenv("PII_TOOLKIT_ACCESS_PASS_STORE", "").strip():
        return False
    return bool(blob_read_write_token())


def blob_store_id() -> str | None:
    token = blob_read_write_token()
    parts = token.split("_")
    if len(parts) >= 4 and parts[:3] == ["vercel", "blob", "rw"]:
        return parts[3]
    return None


def _normalize_store(payload: dict[str, Any] | None) -> dict[str, Any]:
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


def empty_store() -> dict[str, Any]:
    return {"version": STORE_VERSION, "passes": [], "adminSessions": []}


def _blob_url(pathname: str, *, cache: bool = True) -> str:
    store_id = blob_store_id()
    if not store_id:
        raise AccessPassError("사용권 저장소 토큰이 올바르지 않습니다.", status_code=503)
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in pathname.split("/") if part)
    url = f"https://{store_id}.private.blob.vercel-storage.com/{encoded}"
    if not cache:
        url = f"{url}?cache=0"
    return url


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _blob_request(url: str, *, method: str, data: bytes | None = None, extra_headers: dict[str, str] | None = None) -> bytes:
    headers = {
        "Authorization": f"Bearer {blob_read_write_token()}",
        "x-api-version": BLOB_API_VERSION,
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=BLOB_HTTP_TIMEOUT, context=_ssl_context()) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise FileNotFoundError(url) from error
        raise AccessPassError("사용권 저장소에 연결하지 못했습니다.", status_code=503) from error
    except urllib.error.URLError as error:
        raise AccessPassError("사용권 저장소에 연결하지 못했습니다.", status_code=503) from error


def _load_blob_store() -> dict[str, Any]:
    try:
        raw = _blob_request(_blob_url(BLOB_STORE_PATHNAME, cache=False), method="GET")
    except FileNotFoundError:
        return empty_store()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return empty_store()
    return _normalize_store(payload)


def _save_blob_store(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    params = urllib.parse.urlencode({"pathname": BLOB_STORE_PATHNAME})
    _blob_request(
        f"https://vercel.com/api/blob/?{params}",
        method="PUT",
        data=body,
        extra_headers={
            "x-vercel-blob-access": "private",
            "x-allow-overwrite": "1",
            "x-add-random-suffix": "0",
            "x-content-type": "application/json",
        },
    )


def load_store() -> dict[str, Any]:
    if use_blob_store():
        return _load_blob_store()
    path = store_path()
    if not path.is_file():
        return empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_store()
    return _normalize_store(payload)


def save_store(payload: dict[str, Any]) -> None:
    normalized = _normalize_store(payload)
    if use_blob_store():
        _save_blob_store(normalized)
        return
    if os.getenv("VERCEL"):
        raise AccessPassError("사용권 저장소가 설정되지 않았습니다.", status_code=503)
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(normalized, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(serialized, encoding="utf-8")
    tmp.replace(path)


def bounded_duration_days(days: int) -> int:
    return max(MIN_DURATION_DAYS, min(MAX_DURATION_DAYS, int(days)))


def normalize_pass_kind(kind: str | None) -> str:
    value = str(kind or PASS_KIND_TIMED).strip().lower()
    if value in {PASS_KIND_INVITE, "invitation"}:
        return PASS_KIND_INVITE
    return PASS_KIND_TIMED


def pass_kind(record: dict[str, Any] | None) -> str:
    if not record:
        return PASS_KIND_TIMED
    return normalize_pass_kind(str(record.get("kind") or PASS_KIND_TIMED))


def is_invite_pass(record: dict[str, Any] | None) -> bool:
    return pass_kind(record) == PASS_KIND_INVITE


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
    kind = pass_kind(record)
    remaining = 0
    if status == "active" and not is_invite_pass(record):
        remaining = remaining_seconds(str(record.get("expiresAt") or ""), now)
    return {
        "id": record.get("id"),
        "token": str(record.get("token") or ""),
        "note": record.get("note") or "",
        "kind": kind,
        "durationDays": None if kind == PASS_KIND_INVITE else record.get("durationDays"),
        "createdAt": record.get("createdAt"),
        "activatedAt": record.get("activatedAt"),
        "expiresAt": record.get("expiresAt"),
        "revokedAt": record.get("revokedAt"),
        "status": status,
        "remainingSeconds": remaining,
    }


def public_status(
    record: dict[str, Any] | None,
    *,
    required: bool | None = None,
    workspace_required: bool | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    ai_required = access_pass_required() if required is None else required
    ui_required = workspace_pass_required() if workspace_required is None else workspace_required
    if not ai_required and not ui_required:
        return {
            "required": False,
            "workspaceRequired": False,
            "active": True,
            "remainingSeconds": None,
            "expiresAt": None,
            "durationDays": None,
            "kind": None,
        }
    if record is None or pass_lifecycle(record, now) != "active":
        return {
            "required": ai_required,
            "workspaceRequired": ui_required,
            "active": False,
            "remainingSeconds": 0,
            "expiresAt": None if record is None else record.get("expiresAt"),
            "durationDays": None if record is None else record.get("durationDays"),
            "kind": None if record is None else pass_kind(record),
        }
    if is_invite_pass(record):
        return {
            "required": ai_required,
            "workspaceRequired": ui_required,
            "active": True,
            "remainingSeconds": None,
            "expiresAt": None,
            "durationDays": None,
            "kind": PASS_KIND_INVITE,
        }
    seconds = remaining_seconds(str(record.get("expiresAt") or ""), now)
    return {
        "required": ai_required,
        "workspaceRequired": ui_required,
        "active": seconds > 0,
        "remainingSeconds": seconds,
        "expiresAt": record.get("expiresAt"),
        "durationDays": record.get("durationDays"),
        "kind": PASS_KIND_TIMED,
    }


def issue_pass(
    *,
    duration_days: int | None = DEFAULT_DURATION_DAYS,
    note: str = "",
    kind: str | None = None,
    now: datetime | None = None,
) -> str:
    token, _record = issue_pass_record(duration_days=duration_days, note=note, kind=kind, now=now)
    return token


def issue_pass_record(
    *,
    duration_days: int | None = DEFAULT_DURATION_DAYS,
    note: str = "",
    kind: str | None = None,
    now: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    pass_type = normalize_pass_kind(kind)
    created = now or utc_now()
    token = generate_token()
    days = None if pass_type == PASS_KIND_INVITE else bounded_duration_days(
        DEFAULT_DURATION_DAYS if duration_days is None else duration_days
    )
    record = {
        "id": secrets.token_hex(8),
        "tokenHash": hash_secret(token),
        "token": token,
        "note": normalize_note(note),
        "kind": pass_type,
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


def delete_pass(pass_id: str) -> dict[str, Any]:
    cleaned_id = str(pass_id or "").strip()
    with _LOCK:
        payload = load_store()
        record = _find_by_id(payload, cleaned_id)
        if record is None:
            raise AccessPassError("사용권을 찾을 수 없습니다.", status_code=404)
        payload["passes"] = [item for item in payload["passes"] if item.get("id") != cleaned_id]
        save_store(payload)
        snapshot = dict(record)
    return snapshot


def delete_passes(*, pass_ids: list[str] | None = None, delete_all: bool = False) -> int:
    wanted = {str(item or "").strip() for item in (pass_ids or []) if str(item or "").strip()}
    if not delete_all and not wanted:
        raise AccessPassError("삭제할 사용권을 선택하세요.")
    with _LOCK:
        payload = load_store()
        current = list(payload.get("passes") or [])
        if delete_all:
            deleted_count = len(current)
            payload["passes"] = []
        else:
            remaining = [item for item in current if item.get("id") not in wanted]
            deleted_count = len(current) - len(remaining)
            payload["passes"] = remaining
        if deleted_count:
            save_store(payload)
    return deleted_count


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
        if is_invite_pass(record) and record.get("sessionHash"):
            raise AccessPassError("이미 다른 브라우저에 등록된 초대권입니다.", status_code=403)
        if record.get("activatedAt") is None:
            record["activatedAt"] = to_iso(current)
            if is_invite_pass(record):
                record["kind"] = PASS_KIND_INVITE
                record["durationDays"] = None
                record["expiresAt"] = None
            else:
                days = bounded_duration_days(int(record.get("durationDays") or DEFAULT_DURATION_DAYS))
                record["kind"] = PASS_KIND_TIMED
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
    if is_invite_pass(record):
        return dict(record)
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
        help=f"첫 등록 후 유효 일수 ({MIN_DURATION_DAYS}-{MAX_DURATION_DAYS}). 초대권에는 쓰지 않습니다.",
    )
    issue.add_argument(
        "--kind",
        choices=sorted(PASS_KINDS),
        default=PASS_KIND_TIMED,
        help="timed: 기간권, invite: 회수 전까지 유효한 초대권",
    )
    issue.add_argument("--note", default="", help="관리용 메모")
    args = parser.parse_args(argv)
    if args.command == "issue":
        kind = normalize_pass_kind(args.kind)
        token = issue_pass(duration_days=args.days, note=args.note, kind=kind)
        print(token)
        if kind == PASS_KIND_INVITE:
            print("초대권입니다. 회수하기 전까지 작업대에 사용할 수 있습니다.", file=sys.stderr)
        else:
            days = bounded_duration_days(args.days)
            print(f"첫 등록 후 {days}일 동안 AI 보고서에 사용할 수 있습니다.", file=sys.stderr)
        print("이 문자열은 다시 보여주지 않습니다. 사용자에게만 전달하세요.", file=sys.stderr)
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
