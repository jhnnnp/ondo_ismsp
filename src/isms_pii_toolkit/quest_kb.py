"""1타 강사 퀘스트 오버레이 KB — 파일럿 풀 콘텐츠 + 기존 checklist thin 파생."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

QUEST_DIR = Path(__file__).resolve().parent / "data" / "quest_kb" / "controls"

CHECK_KEY_LABELS = {
    "reviewed": "정책/지침 반영",
    "policy": "담당/승인/점검 기록",
    "implemented": "시스템/운영 반영",
    "evidence": "증적 확보",
}

LEVEL_LABELS = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
    "done": "이행",
    "evidenced": "증적 확보",
    "na": "해당 없음",
}


@lru_cache(maxsize=1)
def _load_pilot_quests() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    if not QUEST_DIR.is_dir():
        return loaded
    for path in sorted(QUEST_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        control_id = str(data.get("controlId") or "")
        if control_id and isinstance(data.get("quest"), dict):
            loaded[control_id] = data
    return loaded


def get_quest_overlay(control_id: str) -> dict[str, Any] | None:
    return _load_pilot_quests().get(control_id)


def _has_batchim(text: str) -> bool | None:
    if not text:
        return None
    ch = text[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return ((code - 0xAC00) % 28) != 0
    return None


def _eul_reul(text: str) -> str:
    batchim = _has_batchim(text)
    if batchim is True:
        return "을"
    if batchim is False:
        return "를"
    return "을(를)"


def _i_ga(text: str) -> str:
    batchim = _has_batchim(text)
    if batchim is True:
        return "이"
    if batchim is False:
        return "가"
    return "이(가)"


def _strip_sentence_end(text: str) -> str:
    return str(text or "").strip().rstrip(".。")


def _to_imperative(text: str) -> str:
    """권장조치/상세문을 ‘~하세요’ 할 일 문장으로 맞춘다."""
    t = _strip_sentence_end(text)
    if not t:
        return "관련 화면/문서를 오늘 확인하세요."
    if t.endswith(("하세요", "하십시오")):
        return t + "."
    if t.endswith("합니다"):
        return t[:-3] + "하세요."
    if t.endswith("한다"):
        return t[:-2] + "하세요."
    if t.endswith("남깁니다"):
        return t[:-4] + "남기세요."
    if t.endswith("있습니다"):
        return t[:-4] + "두세요."
    return f"{t}부터 확인하세요."


def _to_state_check(text: str) -> str:
    """권장조치문을 체크용 상태 문장(~있다/한다)으로 맞춘다."""
    t = _strip_sentence_end(text)
    if not t:
        return "관련 조치가 반영되어 있다"
    if t.endswith(("있다", "한다", "된다", "남는다", "돌아간다")):
        return t
    if t.endswith(("하세요", "하십시오")):
        stem = t[:-3] if t.endswith("하세요") else t[:-4]
        return f"{stem.rstrip()}했다"
    if t.endswith("합니다"):
        return t[:-3] + "한다"
    if t.endswith("세요"):
        return t[:-2] + "했다"
    return t


def _as_ask_question(label: str) -> str:
    """체크 상태문을 확인 질문으로 바꾼다."""
    text = _strip_sentence_end(label)
    if text.startswith(("준비할 증적", "증적 예시")):
        return text
    if text.endswith(("나요?", "까요?", "습니까?", "나요", "까요", "습니까")):
        return text if text.endswith("?") else text + "?"
    swaps = (
        ("되어 있다", "되어 있나요?"),
        ("정해져 있다", "정해져 있나요?"),
        ("남아 있다", "남아 있나요?"),
        ("표시되어 있다", "표시되어 있나요?"),
        ("포함되어 있다", "포함되어 있나요?"),
        ("연결되어 있다", "연결되어 있나요?"),
        ("최소화되어 있다", "최소화되어 있나요?"),
        ("적혀 있다", "적혀 있나요?"),
        ("있다", "있나요?"),
        ("강제한다", "강제하나요?"),
        ("강제하고 있다", "강제하고 있나요?"),
        ("켠다", "켜 두었나요?"),
        ("점검한다", "점검하나요?"),
        ("발급한다", "발급하나요?"),
        ("갱신한다", "갱신하나요?"),
        ("마스킹한다", "마스킹하나요?"),
        ("분리 보관(또는 접근 제한)한다", "분리 보관하나요?"),
        ("한다", "하나요?"),
        ("된다", "되나요?"),
        ("남는다", "남나요?"),
        ("돌아간다", "돌아가나요?"),
        ("들어온다", "들어오나요?"),
        ("나눠 두었다", "나눠 두었나요?"),
        ("부여했다", "부여했나요?"),
        ("분리했다", "분리했나요?"),
        ("남겼다", "남겼나요?"),
        ("갱신했다", "갱신했나요?"),
    )
    for old, new in swaps:
        if text.endswith(old):
            return text[: -len(old)] + new
    return f"{text} — 확인했나요?"


def _thin_plain_question(title: str, area_id: str) -> str:
    obj = _eul_reul(title)
    if area_id == "1":
        return f"{title} 관련 문서와 승인/운영 기록을 지금 바로 꺼낼 수 있나요?"
    if area_id == "3":
        return f"개인정보 처리에서 {title}{obj} 지키고, 근거를 남기고 있나요?"
    return f"{title}{obj} 실제 설정/운영에 반영했고, 화면으로 보여줄 수 있나요?"


def _thin_when_missing(
    title: str,
    actions: list[str],
    detail: str | None,
    control_id: str = "",
) -> str:
    if detail:
        base = _to_imperative(detail)
    elif actions:
        base = _to_imperative(actions[0])
    else:
        base = f"{title} 담당자에게 관련 정책/설정/점검 기록이 있는지 물어보세요."
    try:
        from .applicability import PHYSICAL_DC_CONTROLS

        if control_id in PHYSICAL_DC_CONTROLS:
            return (
                f"클라우드만 사용하고 자체 전산실/IDC가 없으면 해당 없음으로 표시하세요. "
                f"물리 시설이 있으면 {base}"
            )
    except Exception:
        pass
    return base


def _sanitize_when_done(text: str) -> str:
    """업로드/파일명 슬롯 UI가 없으므로 관련 잔재를 치운다."""
    import re

    t = str(text or "").strip()
    if not t:
        return "확인한 화면/문서를 심사 때 바로 꺼낼 수 있게 모아 두세요."
    if re.search(r"(업로드|캡처해|파일명을\s*아래|아래에\s*남|슬롯)", t):
        t = re.sub(r"\s*파일명을\s*아래에\s*남겨\s*두세요\.?\s*$", "", t)
        t = re.sub(r"\s*캡처\s*파일명을\s*아래에\s*남겨\s*두세요\.?\s*$", "", t)
        t = re.sub(r"캡처해\s*업로드하세요\.?", "", t)
        t = re.sub(r"방금\s*확인하신\s*", "", t)
        t = re.sub(r"\s*캡처\s*$", "", t).strip(" .—-")
        if not t:
            return "확인한 화면/문서를 심사 때 바로 꺼낼 수 있게 모아 두세요."
        return f"{t} 관련 증적을 모아 두세요."
    if len(t) > 140 and ("안내서" in t or "제2장" in t):
        return "관련 증적(정책/설정 화면/점검 기록)을 모아 두세요."
    return t


def thin_quest_from_control(control: dict[str, Any]) -> dict[str, Any]:
    """파일럿이 없을 때 통제별 짧은 확인 퀘스트를 만든다.

    official_kb 주요 확인사항이 있으면 체크 라벨로 쓰고,
    없으면 recommendedActions / CONTROL_RECOMMENDATION_DETAILS로 가이드한다.
    locked handcrafted quest는 resolve_quest에서 이 함수보다 우선한다.
    """
    control_id = str(control.get("id") or control.get("controlId") or "")
    title = str(control.get("title") or control_id).strip() or control_id
    area_id = str(control.get("areaId") or "")
    audience = _thin_audience(area_id, str(control.get("categoryId") or ""))

    actions = [str(a).strip() for a in list(control.get("recommendedActions") or []) if str(a).strip()]
    detail: str | None = None
    try:
        from .control_assessment import CONTROL_RECOMMENDATION_DETAILS

        detail = CONTROL_RECOMMENDATION_DETAILS.get(control_id)
    except Exception:
        detail = None

    from .dual_layer import build_casebook_problems, build_official_checks

    official_rows = build_official_checks(control_id)
    casebook_problems = build_casebook_problems(control_id, limit=6)
    if official_rows:
        checks = [
            {
                "checkId": str(row["checkId"]),
                "label": str(row["label"]),
                "recommended": str(row["checkId"]) == "evidence",
                "mapsToCheckKey": row.get("mapsToCheckKey"),
            }
            for row in official_rows
        ]
        evidence_label = next(
            (str(row["label"]) for row in official_rows if str(row["checkId"]) == "evidence"),
            "",
        )
        when_done = (
            evidence_label.replace("증적 예시를 제시할 수 있다 (", "다음 증적 예시를 준비하세요: ").rstrip(")")
            if evidence_label.startswith("증적 예시를 제시할 수 있다")
            else f"확인한 {title} 화면/문서를 심사 때 바로 꺼낼 수 있게 모아 두세요."
        )
        return {
            "controlId": control_id,
            "source": "thin",
            "quality": "thin-stub",
            "meta": {"sourceDoc": "ISMS-P 인증기준 안내서(2023.11.23)", "grounding": "official"},
            "officialChecks": official_rows,
            "casebookProblems": casebook_problems,
            "quest": {
                "plainQuestion": _thin_plain_question(title, area_id),
                "audience": audience,
                "checks": checks,
                "actionGuide": {
                    "whenMissing": _thin_when_missing(title, actions, detail, control_id),
                    "guideRef": f"official-{control_id}",
                    "whenDone": when_done,
                },
                "evidenceSlots": [],
            },
        }

    if area_id == "1":
        implemented = "최근 1년 내 관련 운영/승인 기록이 있다"
    elif area_id == "3":
        implemented = f"{title} 기준이 실제 처리 업무/시스템에 반영되어 있다"
    else:
        implemented = f"{title} 관련 설정/운영이 실제로 적용되어 있다"
    if detail:
        implemented = _to_state_check(detail)
    elif actions:
        implemented = _to_state_check(actions[0])

    checks = [
        {
            "checkId": "reviewed",
            "label": f"{title} 기준이 정책/지침에 반영되어 있다",
            "recommended": False,
            "mapsToCheckKey": "reviewed",
        },
        {
            "checkId": "policy",
            "label": f"{title} 담당자와 점검/승인 방법이 정해져 있다",
            "recommended": False,
            "mapsToCheckKey": "policy",
        },
        {
            "checkId": "implemented",
            "label": implemented,
            "recommended": False,
            "mapsToCheckKey": "implemented",
        },
        {
            "checkId": "evidence",
            "label": f"{title} 관련 화면/문서를 바로 제시할 수 있다",
            "recommended": True,
            "mapsToCheckKey": "evidence",
        },
    ]

    return {
        "controlId": control_id,
        "source": "thin",
        "quality": "thin-stub",
        "officialChecks": [],
        "casebookProblems": casebook_problems,
        "quest": {
            "plainQuestion": _thin_plain_question(title, area_id),
            "audience": audience,
            "checks": checks,
            "actionGuide": {
                "whenMissing": _thin_when_missing(title, actions, detail, control_id),
                "guideRef": f"thin-{control_id}",
                "whenDone": f"확인한 {title} 화면/문서를 심사 때 바로 꺼낼 수 있게 모아 두세요.",
            },
            "evidenceSlots": [],
        },
    }


def _thin_audience(area_id: str, category_id: str) -> list[str]:
    if category_id.startswith(("2.5", "2.6", "2.7", "2.9", "2.10")):
        return ["인프라", "개발/운영", "보안(겸직)"]
    if category_id.startswith(("2.3", "3.3", "3.4")):
        return ["개인정보 담당", "계약/총무", "보안(겸직)"]
    if area_id == "1":
        return ["경영지원", "보안(겸직)", "개인정보 보호책임자"]
    if area_id == "3":
        return ["개인정보 담당", "서비스 운영", "보안(겸직)"]
    return ["담당자", "보안(겸직)"]



def resolve_quest(control: dict[str, Any]) -> dict[str, Any]:
    control_id = str(control.get("id") or "")
    from .dual_layer import build_casebook_problems, build_official_checks

    official_rows = build_official_checks(control_id)
    casebook_problems = build_casebook_problems(control_id, limit=6)
    overlay = get_quest_overlay(control_id)
    if overlay:
        result = dict(overlay)
        result["source"] = "pilot"
        # Dual-layer: confirmation labels from official guide; keep pilot guide copy.
        if official_rows:
            quest = dict(result.get("quest") or {})
            quest["checks"] = [
                {
                    "checkId": str(row["checkId"]),
                    "label": str(row["label"]),
                    "recommended": str(row["checkId"]) == "evidence",
                    "mapsToCheckKey": row.get("mapsToCheckKey"),
                }
                for row in official_rows
            ]
            result["quest"] = quest
            meta = dict(result.get("meta") or {})
            meta["grounding"] = "official+pilot"
            meta["sourceDoc"] = "ISMS-P 인증기준 안내서(2023.11.23)"
            result["meta"] = meta
        result["officialChecks"] = official_rows
        result["casebookProblems"] = casebook_problems
        return result
    thin = thin_quest_from_control(control)
    thin.setdefault("officialChecks", official_rows)
    thin.setdefault("casebookProblems", casebook_problems)
    return thin


def merge_quest_checks_into_control_checks(
    quest_checks: dict[str, dict[str, bool]] | None,
    control_checks: dict[str, dict[str, bool]] | None,
) -> dict[str, dict[str, bool]]:
    """questChecks의 mapsToCheckKey를 controlChecks에 병합.

    - assess UI의 명시 체크를 quest가 False/True로 덮어쓰지 않는다(True만 OR 반영).
    - `evidence` 성숙도는 캡처 없이 퀘스트 체크만으로 충족시키지 않는다.
    """
    merged: dict[str, dict[str, bool]] = {
        cid: dict(checks) for cid, checks in (control_checks or {}).items()
    }
    if not quest_checks:
        return merged
    for control_id, answers in quest_checks.items():
        quest = get_quest_overlay(control_id)
        check_defs: list[dict[str, Any]] = []
        if quest and isinstance(quest.get("quest"), dict):
            # Keep pilot overlay maps (legacy checkIds like mfa / pwd-complexity).
            check_defs.extend(
                row for row in (quest["quest"].get("checks") or []) if isinstance(row, dict)
            )
        from .control_graph import find_control

        control = find_control(control_id) or {"id": control_id}
        resolved = resolve_quest(dict(control))
        seen_ids = {str(row.get("checkId")) for row in check_defs}
        for row in (resolved.get("quest") or {}).get("checks") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("checkId"))
            if cid and cid not in seen_ids:
                check_defs.append(row)
                seen_ids.add(cid)
        if not check_defs:
            check_defs = [
                {"checkId": k, "mapsToCheckKey": k}
                for k in ("reviewed", "policy", "implemented", "evidence")
            ]
        id_to_key = {
            str(row.get("checkId")): str(row.get("mapsToCheckKey") or row.get("checkId"))
            for row in check_defs
            if isinstance(row, dict)
        }
        bucket = merged.setdefault(control_id, {})
        for check_id, checked in answers.items():
            if not checked:
                continue
            key = id_to_key.get(check_id, check_id)
            if key == "evidence":
                continue
            bucket[key] = True
    return merged


def _control_priority(control: dict[str, Any]) -> int:
    if "priority" in control:
        return int(control["priority"] or 0)
    category_id = str(control.get("categoryId") or "")
    area_id = str(control.get("areaId") or "")
    if area_id == "3":
        return 3
    if category_id.startswith(("2.5", "2.6", "2.7")):
        return 2
    if area_id == "1":
        return 2
    return 1


def build_priority_quests(
    *,
    assessments: dict[str, str],
    organization_context,
    quest_checks: dict[str, dict[str, bool]] | None,
    evidence_slots: dict[str, dict[str, Any]] | None,
    input_confidence: dict[str, str] | None,
    controls: list[dict[str, Any]],
    limit: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    from .applicability import resolve_applicability
    from .profile_prioritization import priority_delta

    weak = {"unknown", "none", "partial"}
    quests: list[dict[str, Any]] = []
    for control in controls:
        control_id = str(control["id"])
        level = assessments.get(control_id, "unknown")
        if level == "na" or not resolve_applicability(control_id, organization_context)["applicable"]:
            continue
        if level == "evidenced":
            continue
        resolved = resolve_quest(control)
        quest = resolved["quest"]
        answers = (quest_checks or {}).get(control_id) or {}
        slots_out = []
        for slot in list(quest.get("evidenceSlots") or []):
            slot_id = str(slot.get("slotId"))
            meta = (evidence_slots or {}).get(slot_id) or {}
            slots_out.append(
                {
                    "slotId": slot_id,
                    "title": slot.get("title"),
                    "accepts": list(slot.get("accepts") or []),
                    "requiredForLevel": slot.get("requiredForLevel"),
                    "uploaded": bool(meta.get("fileName") or meta.get("file_name")),
                    "fileName": meta.get("fileName") or meta.get("file_name"),
                }
            )
        checks_out = []
        for row in list(quest.get("checks") or []):
            check_id = str(row.get("checkId"))
            checks_out.append(
                {
                    "checkId": check_id,
                    "label": row.get("label"),
                    "recommended": bool(row.get("recommended")),
                    "mapsToCheckKey": row.get("mapsToCheckKey"),
                    "checked": answers.get(check_id),
                }
            )
        priority = _control_priority(control) + priority_delta(control_id, organization_context)
        if level in weak:
            priority += 5
        if resolved.get("source") == "pilot":
            # 손수 쓴 1타 콘텐츠를 thin 자동생성보다 앞에 둔다
            priority += 40
        guide = quest.get("actionGuide") or {}
        quests.append(
            {
                "controlId": control_id,
                "title": control.get("title"),
                "plainQuestion": quest.get("plainQuestion"),
                "audience": list(quest.get("audience") or []),
                "checks": checks_out,
                "actionGuide": {
                    "whenMissing": str(guide.get("whenMissing") or ""),
                    "guideRef": str(guide.get("guideRef") or ""),
                    "whenDone": _sanitize_when_done(str(guide.get("whenDone") or "")),
                },
                "evidenceSlots": slots_out,
                "level": level,
                "levelLabel": LEVEL_LABELS.get(level, level),
                "source": resolved.get("source", "thin"),
                "confidence": (input_confidence or {}).get(control_id, "unknown"),
                "_priority": priority,
                "_pilotFirst": 0 if resolved.get("source") == "pilot" else 1,
            }
        )
    quests.sort(
        key=lambda item: (int(item["_pilotFirst"]), -int(item["_priority"]), str(item["controlId"]))
    )
    for item in quests:
        item.pop("_priority", None)
        item.pop("_pilotFirst", None)
    total_candidates = len(quests)
    return quests[:limit], total_candidates


def build_confirmation_actions(
    *,
    gaps: list[dict[str, Any]],
    quest_checks: dict[str, dict[str, bool]] | None,
    evidence_slots: dict[str, dict[str, Any]] | None,
    input_confidence: dict[str, str] | None,
    controls: list[dict[str, Any]],
    limit: int = 10,
    session_bundle_mode: str | None = None,
    organization_context: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """오늘 확인할 질문 카드 — 통제당 1개(질문기 주인공).

    공식 확인사항은 detailChecks로만 내려 보내고, 기본 시야의 할 일로 펼치지 않는다.
    세션 묶음 모드(area|chain|theme)로 후보 순서를 재정렬한다.
    """
    from .session_bundle import order_gaps_for_session

    _ = evidence_slots  # 증적 파일명 슬롯은 주인공 목록에서 제외(기존 원칙)
    control_by_id = {str(c["id"]): c for c in controls}
    # 파일럿 퀘스트가 있는 통제에 소폭 가산한 뒤 묶음 모드로 재정렬
    boosted_gaps: list[dict[str, Any]] = []
    for gap in gaps:
        row = dict(gap)
        if get_quest_overlay(str(gap.get("controlId") or "")):
            row["priority"] = int(gap.get("priority") or 0) + 2
        boosted_gaps.append(row)
    ordered_gaps, bundle_meta = order_gaps_for_session(
        boosted_gaps,
        controls=controls,
        organization_context=organization_context,
        mode=session_bundle_mode,
        limit=max(limit * 3, 30),
    )
    actions: list[dict[str, Any]] = []
    for gap in ordered_gaps:
        control_id = str(gap["controlId"])
        confidence = (input_confidence or {}).get(control_id, "unknown")
        control = control_by_id.get(control_id)
        if not control:
            continue
        title = str(control.get("title") or control_id)
        resolved = resolve_quest(control)
        quest = resolved["quest"]
        answers = (quest_checks or {}).get(control_id) or {}
        ask_who = list(quest.get("audience") or ["담당자"])
        risk = str(
            gap.get("riskIfMissing")
            or f"{title}{_i_ga(title)} 미확인이면 심사/운영 가설이 남습니다."
        )
        guide_missing = str((quest.get("actionGuide") or {}).get("whenMissing") or "")
        plain = str(
            quest.get("plainQuestion") or f"{title} 현황을 담당자에게 확인했나요?"
        )

        detail_checks: list[dict[str, Any]] = []
        related_ids: list[str] = [control_id]
        unchecked_count = 0
        for row in list(quest.get("checks") or []):
            check_id = str(row.get("checkId") or "")
            if not check_id:
                continue
            if answers.get(check_id) is not True:
                unchecked_count += 1
            label = str(row.get("label") or plain or title)
            detail_checks.append(
                {
                    "checkId": check_id,
                    "question": _as_ask_question(label),
                    "label": label,
                    "recommended": bool(row.get("recommended")),
                }
            )
            related_ids.append(f"{control_id}:{check_id}")

        # 확인됨 + 세부 문항까지 다 체크면 주인공 목록에서 제외
        if confidence == "confirmed" and unchecked_count == 0:
            continue

        actions.append(
            {
                "actionId": f"ask-{control_id}",
                "priority": len(actions) + 1,
                "controlId": control_id,
                "title": title,
                "question": plain,
                "askWho": ask_who,
                "evidenceHint": None,
                "confidence": confidence,
                "whyItMatters": risk,
                "relatedFindingIds": related_ids,
                "checkId": None,
                "slotId": None,
                "actionGuide": guide_missing or None,
                "detailChecks": detail_checks,
            }
        )

    total_candidates = max(int(bundle_meta.get("candidates") or 0), len(actions))
    trimmed = actions[:limit]
    for idx, action in enumerate(trimmed, start=1):
        action["priority"] = idx
    meta = {
        **bundle_meta,
        "shown": len(trimmed),
        "candidates": total_candidates,
        "limit": limit,
    }
    return trimmed, meta


def build_control_session_details(
    controls: list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """세션 카드용 전 통제 카탈로그 — confirmationActions(우선 N개)와 무관하게 detailChecks를 채운다."""
    catalog: dict[str, dict[str, Any]] = {}
    for control in controls or []:
        control_id = str(control.get("id") or "")
        if not control_id:
            continue
        title = str(control.get("title") or control_id)
        resolved = resolve_quest(control)
        quest = resolved.get("quest") or {}
        plain = str(
            quest.get("plainQuestion") or f"{title} 이행 상태를 확인했나요?"
        )
        guide = str((quest.get("actionGuide") or {}).get("whenMissing") or "")
        detail_checks: list[dict[str, Any]] = []
        for row in list(quest.get("checks") or []):
            check_id = str(row.get("checkId") or "")
            if not check_id:
                continue
            label = str(row.get("label") or plain or title)
            detail_checks.append(
                {
                    "checkId": check_id,
                    "question": _as_ask_question(label),
                    "label": label,
                    "recommended": bool(row.get("recommended")),
                }
            )
        catalog[control_id] = {
            "title": title,
            "question": plain,
            "actionGuide": guide or None,
            "detailChecks": detail_checks,
        }
    return catalog


def summarize_input_confidence(
    assessments: dict[str, str],
    input_confidence: dict[str, str] | None,
) -> dict[str, Any]:
    applicable_ids = [cid for cid, level in assessments.items() if level != "na"]
    counts = {"confirmed": 0, "assumed": 0, "unknown": 0}
    for control_id in applicable_ids:
        conf = (input_confidence or {}).get(control_id, "unknown")
        if conf not in counts:
            conf = "unknown"
        counts[conf] += 1
    total = len(applicable_ids) or 1
    return {
        "confirmed": counts["confirmed"],
        "assumed": counts["assumed"],
        "unknown": counts["unknown"],
        "total": len(applicable_ids),
        "confirmedRatio": round(counts["confirmed"] / total, 3),
        "assumedRatio": round(counts["assumed"] / total, 3),
        "unknownRatio": round(counts["unknown"] / total, 3),
    }
