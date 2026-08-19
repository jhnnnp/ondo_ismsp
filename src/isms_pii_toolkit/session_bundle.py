"""이번 세션 우선 통제 묶음 — 영역 / 연결 줄기 / 업무 테마."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from .control_graph import load_manual_relations
from .organization_profile import OrganizationContext
from .profile_prioritization import (
    CLOUD_CONTROLS,
    FOUNDATION_CONTROLS,
    HIGH_PII_CONTROLS,
    OUTSOURCING_CONTROLS,
    REMOTE_ACCESS_CONTROLS,
    RRN_CONTROLS,
)

SessionBundleMode = Literal["area", "chain", "theme"]
VALID_SESSION_BUNDLE_MODES = frozenset({"area", "chain", "theme"})
DEFAULT_SESSION_BUNDLE_MODE: SessionBundleMode = "chain"

_DATA_ROOT = Path(__file__).resolve().parent / "data" / "problem_kb"


def normalize_session_bundle_mode(value: str | None) -> SessionBundleMode:
    mode = str(value or DEFAULT_SESSION_BUNDLE_MODE).strip().lower()
    if mode not in VALID_SESSION_BUNDLE_MODES:
        return DEFAULT_SESSION_BUNDLE_MODE
    return mode  # type: ignore[return-value]


@lru_cache(maxsize=1)
def _compound_neighbors() -> dict[str, tuple[str, ...]]:
    path = _DATA_ROOT / "compounds.json"
    if not path.is_file():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in rows or []:
        ids = [str(cid) for cid in (row.get("controlIds") or []) if str(cid).strip()]
        if len(ids) < 2:
            continue
        for source in ids:
            for target in ids:
                if source != target:
                    adjacency[source].add(target)
    return {key: tuple(sorted(values)) for key, values in adjacency.items()}


def _gap_priority(gap: dict[str, Any]) -> int:
    return int(gap.get("priority") or 0)


def _gap_rank_key(gap: dict[str, Any]) -> tuple:
    severity = {"critical": 0, "high": 1, "medium": 2}.get(str(gap.get("severity") or ""), 3)
    return (
        0 if gap.get("scenarioRelevant") else 1,
        severity,
        -int(gap.get("profilePriority") or 0),
        -_gap_priority(gap),
        str(gap.get("controlId") or ""),
    )


def _relation_neighbors(control_id: str, control_by_id: dict[str, dict[str, Any]]) -> list[str]:
    forward = load_manual_relations()
    neighbors: list[str] = []
    seen: set[str] = set()

    def add(cid: str) -> None:
        if not cid or cid == control_id or cid in seen:
            return
        seen.add(cid)
        neighbors.append(cid)

    for target, _reason in forward.get(control_id, ()):
        add(str(target))
    for source, edges in forward.items():
        for target, _reason in edges:
            if str(target) == control_id:
                add(str(source))
    control = control_by_id.get(control_id) or {}
    for related in list(control.get("relatedControlIds") or [])[:8]:
        add(str(related))
    for related in _compound_neighbors().get(control_id, ()):
        add(str(related))
    return neighbors


def _theme_catalog(context: OrganizationContext | None) -> list[dict[str, Any]]:
    themes: list[dict[str, Any]] = [
        {
            "themeId": "foundation",
            "title": "관리체계 기반",
            "summary": "정책·범위·자산 등 관리체계 기본 통제를 한 세션으로 묶습니다.",
            "controlIds": FOUNDATION_CONTROLS,
            "active": True,
        }
    ]
    if context is None:
        return themes
    if context.uses_cloud:
        themes.append(
            {
                "themeId": "cloud",
                "title": "클라우드 운영",
                "summary": "클라우드 계정·로그·공개서버·책임 경계 관련 통제입니다.",
                "controlIds": CLOUD_CONTROLS,
                "active": True,
            }
        )
    if context.uses_outsourcing:
        themes.append(
            {
                "themeId": "outsourcing",
                "title": "외주·위탁",
                "summary": "외주/위탁 계약·감독·재위탁 경계를 한 줄기로 확인합니다.",
                "controlIds": OUTSOURCING_CONTROLS,
                "active": True,
            }
        )
    if context.uses_remote_access:
        themes.append(
            {
                "themeId": "remote",
                "title": "원격접속",
                "summary": "원격/재택 인증·권한·접속기록 통제를 묶습니다.",
                "controlIds": REMOTE_ACCESS_CONTROLS,
                "active": True,
            }
        )
    if context.pii_volume in {"medium", "high"} or context.processes_rrn:
        themes.append(
            {
                "themeId": "pii-lifecycle",
                "title": "개인정보 보호·생명주기",
                "summary": "암호화·접근·현황·고유식별 등 개인정보 핵심 통제입니다.",
                "controlIds": HIGH_PII_CONTROLS | RRN_CONTROLS,
                "active": True,
            }
        )
    return themes


def _pick_theme(
    gaps: list[dict[str, Any]],
    context: OrganizationContext | None,
) -> dict[str, Any] | None:
    gap_ids = {str(g["controlId"]) for g in gaps}
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for theme in _theme_catalog(context):
        ids = set(theme["controlIds"]) & gap_ids
        if not ids:
            continue
        score = sum(_gap_priority(g) for g in gaps if str(g["controlId"]) in ids)
        scored.append((score, len(ids), theme))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], -item[1], str(item[2]["themeId"])))
    return scored[0][2]


def _order_area(
    gaps: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for gap in gaps:
        by_category[str(gap.get("categoryName") or "기타")].append(gap)

    def category_score(items: list[dict[str, Any]]) -> tuple:
        return (
            -sum(_gap_priority(g) for g in items),
            -len(items),
            str(items[0].get("categoryName") or ""),
        )

    ranked_categories = sorted(by_category.values(), key=category_score)
    if not ranked_categories:
        return [], {
            "mode": "area",
            "bundleTitle": "영역 묶음",
            "bundleSummary": "묶을 영역 후보가 없습니다.",
            "areaLabel": None,
            "themeId": None,
            "chainPath": [],
        }

    primary = sorted(ranked_categories[0], key=_gap_rank_key)
    area_name = str(primary[0].get("areaName") or "")
    category = str(primary[0].get("categoryName") or "영역")
    selected = list(primary[:limit])

    if len(selected) < min(6, limit):
        primary_ids = {str(g["controlId"]) for g in selected}
        same_area = [
            g
            for group in ranked_categories[1:]
            for g in sorted(group, key=_gap_rank_key)
            if str(g.get("areaName") or "") == area_name
            and str(g["controlId"]) not in primary_ids
        ]
        for gap in same_area:
            if len(selected) >= limit:
                break
            selected.append(gap)

    return selected, {
        "mode": "area",
        "bundleTitle": f"{category} 중심",
        "bundleSummary": (
            f"같은 영역({category}) 통제를 한 세션으로 묶었습니다. "
            "담당·증적 흐름이 비슷한 항목부터 진단하세요."
        ),
        "areaLabel": category,
        "themeId": None,
        "chainPath": [str(g["controlId"]) for g in selected],
    }


def _order_chain(
    gaps: list[dict[str, Any]],
    controls: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not gaps:
        return [], {
            "mode": "chain",
            "bundleTitle": "연결 줄기",
            "bundleSummary": "묶을 후보가 없습니다.",
            "areaLabel": None,
            "themeId": None,
            "chainPath": [],
        }

    control_by_id = {str(c["id"]): c for c in controls}
    gap_by_id = {str(g["controlId"]): g for g in gaps}
    ranked = sorted(gaps, key=_gap_rank_key)
    seed = ranked[0]
    seed_id = str(seed["controlId"])

    ordered_ids: list[str] = []
    queue: deque[str] = deque([seed_id])
    seen: set[str] = set()
    while queue and len(ordered_ids) < limit:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        if current not in gap_by_id:
            for neighbor in _relation_neighbors(current, control_by_id):
                if neighbor not in seen:
                    queue.append(neighbor)
            continue
        ordered_ids.append(current)
        for neighbor in _relation_neighbors(current, control_by_id):
            if neighbor not in seen:
                queue.append(neighbor)

    if len(ordered_ids) < limit:
        for gap in ranked:
            cid = str(gap["controlId"])
            if cid in ordered_ids:
                continue
            ordered_ids.append(cid)
            if len(ordered_ids) >= limit:
                break

    selected = [gap_by_id[cid] for cid in ordered_ids if cid in gap_by_id]
    seed_title = str(seed.get("title") or seed_id)
    area_label = str(seed.get("categoryName") or "") or None
    path_labels = []
    for gap in selected[:5]:
        path_labels.append(str(gap.get("title") or gap["controlId"]))
    chain_text = " → ".join(path_labels)
    if len(selected) > 5:
        chain_text = f"{chain_text} …"

    return selected, {
        "mode": "chain",
        "bundleTitle": f"{seed_id} {seed_title} 줄기",
        "bundleSummary": (
            f"우선 통제 {seed_id}를 시드로 관련·복합 연결 통제를 한 줄기로 묶었습니다. "
            f"{chain_text}"
        ),
        "areaLabel": area_label,
        "themeId": None,
        "chainPath": [str(g["controlId"]) for g in selected],
    }


def _order_theme(
    gaps: list[dict[str, Any]],
    context: OrganizationContext | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    theme = _pick_theme(gaps, context)
    if theme is None:
        # 테마 교집합이 없으면 영역 묶음으로 안전하게 폴백
        selected, meta = _order_area(gaps, limit)
        meta["mode"] = "theme"
        meta["bundleTitle"] = "업무 테마 (영역 폴백)"
        meta["bundleSummary"] = (
            "프로파일 테마와 겹치는 미진단 통제가 적어 영역 묶음으로 대체했습니다."
        )
        return selected, meta

    theme_ids = set(theme["controlIds"])
    in_theme = sorted(
        [g for g in gaps if str(g["controlId"]) in theme_ids],
        key=_gap_rank_key,
    )
    selected = list(in_theme[:limit])
    if len(selected) < min(6, limit):
        selected_ids = {str(g["controlId"]) for g in selected}
        for gap in sorted(gaps, key=_gap_rank_key):
            cid = str(gap["controlId"])
            if cid in selected_ids:
                continue
            selected.append(gap)
            selected_ids.add(cid)
            if len(selected) >= limit:
                break

    return selected, {
        "mode": "theme",
        "bundleTitle": str(theme["title"]),
        "bundleSummary": str(theme["summary"]),
        "areaLabel": str(selected[0].get("categoryName") or "") if selected else None,
        "themeId": str(theme["themeId"]),
        "chainPath": [str(g["controlId"]) for g in selected],
    }


def order_gaps_for_session(
    gaps: list[dict[str, Any]],
    *,
    controls: list[dict[str, Any]],
    organization_context: OrganizationContext | None = None,
    mode: str | None = None,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """후보 gap을 세션 묶음 모드에 맞게 재정렬하고 상한을 적용한다."""
    normalized = normalize_session_bundle_mode(mode)
    eligible = [g for g in gaps if str(g.get("controlId") or "").strip()]
    capped = max(1, min(20, int(limit or 10)))

    if normalized == "area":
        selected, meta = _order_area(eligible, capped)
    elif normalized == "theme":
        selected, meta = _order_theme(eligible, organization_context, capped)
    else:
        selected, meta = _order_chain(eligible, controls, capped)

    meta = {
        **meta,
        "mode": normalized,
        "limit": capped,
        "candidates": len(eligible),
        "shown": len(selected),
    }
    return selected, meta
