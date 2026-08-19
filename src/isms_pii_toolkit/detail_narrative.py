"""상세 해설: 규칙 엔진 사실 + official_kb RAG 청크 → LLM 서술 (검증/폴백).

판정·점수·인과 finding은 바꾸지 않는다. 상세 문장만 작성한다.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .llm_provider import ChatClient, resolve_chat_client
from .official_kb import official_chunks

DETAIL_SYSTEM_PROMPT = """당신은 ISMS-P 자가진단 상세 해설 작성기입니다.
규칙 엔진이 확정한 사실과 공식 안내서 발췌(officialChunks)만 사용하세요.
새 통제 ID, 새 체크 ID, 합격/불합격 단정, 인증 가능 여부 단정을 금지합니다.
출력은 JSON만 허용합니다.
형식:
{
  "details": {
    "2.7.1": {
      "summaryTip": "한 줄 요약(80자 이내)",
      "detail": "상세 해설 문단. [공식 요구사항][현재 진단][확인 포인트][참고 결함 유형] 구조를 권장"
    }
  },
  "confidence": 0.0
}
details의 키는 입력 controls의 controlId와 정확히 일치해야 합니다.
"""

_FORBIDDEN = re.compile(
    r"(인증\s*가능|인증\s*불가|합격|불합격|반드시\s*결함|확정\s*결함)",
    re.IGNORECASE,
)
_CONTROL_ID_RE = re.compile(r"\b\d+(?:\.\d+){1,3}\b")


def _env_max_controls(default: int = 8) -> int:
    raw = os.getenv("PII_TOOLKIT_LLM_DETAIL_MAX_CONTROLS") or str(default)
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(1, min(20, value))


def _env_enabled(default: bool = True) -> bool:
    raw = (os.getenv("PII_TOOLKIT_LLM_DETAIL_NARRATIVES") or "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def select_detail_controls(structured: dict[str, Any], *, max_controls: int) -> list[dict[str, Any]]:
    """상세 해설 대상 통제 — 확정 미흡 우선, 그다음 미진단."""
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []

    def push(rows: list[dict[str, Any]]) -> None:
        for row in rows:
            cid = str(row.get("controlId") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            ordered.append(row)
            if len(ordered) >= max_controls:
                return

    confirmed = [
        g
        for g in list(structured.get("confirmedGaps") or structured.get("topGaps") or [])
        if str(g.get("level") or "") in {"none", "partial"}
    ]
    push(confirmed)
    if len(ordered) < max_controls:
        push(list(structured.get("topGaps") or []))
    if len(ordered) < max_controls:
        push(list(structured.get("criticalGaps") or []))
    return ordered[:max_controls]


def build_detail_packet(
    structured: dict[str, Any],
    *,
    max_controls: int | None = None,
) -> dict[str, Any]:
    limit = _env_max_controls() if max_controls is None else max(1, min(20, int(max_controls)))
    controls = select_detail_controls(structured, max_controls=limit)
    findings_by_control: dict[str, list[dict[str, Any]]] = {}
    problem = structured.get("problemAnalysis") or {}
    for row in list(problem.get("individualProblems") or [])[:80]:
        cid = str(row.get("controlId") or "")
        if not cid:
            continue
        findings_by_control.setdefault(cid, []).append(
            {
                "checklistItemId": row.get("checklistItemId"),
                "checklistItem": row.get("checklistItem"),
                "problems": list(row.get("problems") or [])[:2],
                "causalStatement": row.get("causalStatement"),
                "level": row.get("level"),
            }
        )

    items: list[dict[str, Any]] = []
    for gap in controls:
        cid = str(gap.get("controlId") or "")
        chunks = official_chunks(cid)
        items.append(
            {
                "controlId": cid,
                "title": gap.get("title"),
                "level": gap.get("level"),
                "levelLabel": gap.get("levelLabel"),
                "severity": gap.get("severity"),
                "organicAnalysis": gap.get("organicAnalysis") or gap.get("problem"),
                "riskIfMissing": gap.get("riskIfMissing"),
                "immediateActions": list(gap.get("immediateActions") or [])[:4],
                "causalBasis": list(gap.get("causalBasis") or [])[:4],
                "engineFindings": findings_by_control.get(cid, [])[:3],
                "officialChunks": chunks,
            }
        )
    return {
        "overallReadiness": structured.get("overallReadiness"),
        "gapCount": structured.get("gapCount"),
        "controls": items,
    }


def template_detail_for_control(item: dict[str, Any]) -> dict[str, str]:
    cid = str(item.get("controlId") or "")
    title = str(item.get("title") or cid)
    level_label = str(item.get("levelLabel") or item.get("level") or "")
    organic = str(item.get("organicAnalysis") or "").strip()
    chunks = (item.get("officialChunks") or {}).get("chunks") or []
    requirement = next((c["text"] for c in chunks if c.get("kind") == "requirement"), "")
    checks = [c["text"] for c in chunks if c.get("kind") == "checkQuestion"][:3]
    defects = [c["text"] for c in chunks if c.get("kind") == "defectExample"][:2]
    tip = organic[:80] if organic else f"{cid} {title} — {level_label}"
    detail_parts = [
        f"[공식 요구사항]\n{requirement or '공식 요구사항 발췌 없음.'}",
        f"[현재 진단]\n{organic or f'{cid} {title} 상태: {level_label}'}",
        "[확인 포인트]\n" + ("\n".join(f"- {q}" for q in checks) if checks else "- 공식 확인사항 발췌 없음."),
        "[참고 결함 유형]\n" + ("\n".join(f"- {d}" for d in defects) if defects else "- 안내서 결함 사례 발췌 없음."),
    ]
    return {"summaryTip": tip, "detail": "\n\n".join(detail_parts)}


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("detail narrative payload must be object")
    return data


def validate_detail_payload(
    payload: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    allowed = {str(item["controlId"]) for item in packet.get("controls") or []}
    details = payload.get("details")
    reasons: list[str] = []
    if not isinstance(details, dict) or not details:
        return {"ok": False, "reasons": ["details 객체 없음"], "inventedControlIds": []}

    invented: list[str] = []
    cleaned: dict[str, dict[str, str]] = {}
    for key, value in details.items():
        cid = str(key).strip()
        if cid not in allowed:
            invented.append(cid)
            continue
        if not isinstance(value, dict):
            reasons.append(f"{cid}: detail 항목 형식 오류")
            continue
        tip = str(value.get("summaryTip") or "").strip()
        detail = str(value.get("detail") or "").strip()
        if not detail:
            reasons.append(f"{cid}: detail 비어 있음")
            continue
        if len(detail) > 3500:
            reasons.append(f"{cid}: detail 길이 초과")
            continue
        if _FORBIDDEN.search(tip) or _FORBIDDEN.search(detail):
            reasons.append(f"{cid}: 금지 단정 문구")
            continue
        for found in _CONTROL_ID_RE.findall(f"{tip}\n{detail}"):
            if found not in allowed and found != cid:
                # 관련 통제 언급은 허용하되, 패킷 밖 ID가 과도하면 거부하지 않고 경고만
                # 단, 완전 무관한 새 주인공 통제 생성은 tip/detail 본문만으로는 막기 어려워
                # 키가 허용 집합인지만 강제한다.
                pass
        cleaned[cid] = {
            "summaryTip": tip[:120] if tip else detail[:80],
            "detail": detail,
        }

    if invented:
        reasons.append("패킷에 없는 controlId")
    if not cleaned:
        return {
            "ok": False,
            "reasons": reasons or ["유효한 detail 없음"],
            "inventedControlIds": invented,
        }
    return {
        "ok": True,
        "reasons": reasons,
        "inventedControlIds": invented,
        "details": cleaned,
        "confidence": float(payload.get("confidence") or 0.0),
    }


def _source_label(chunks_payload: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    doc = str(chunks_payload.get("sourceDoc") or "").strip()
    pages = chunks_payload.get("pages") or []
    if doc and pages:
        sources.append(f"{doc} p.{','.join(str(p) for p in pages[:4])}")
    elif doc:
        sources.append(doc)
    else:
        sources.append("official_kb")
    return sources


def _merge_details(
    structured: dict[str, Any],
    details: dict[str, dict[str, str]],
    *,
    mode: str,
    packet: dict[str, Any],
) -> dict[str, Any]:
    result = dict(structured)
    by_id = {
        str(item["controlId"]): item
        for item in packet.get("controls") or []
    }
    narrative_map: dict[str, dict[str, Any]] = {}
    for cid, body in details.items():
        item = by_id.get(cid) or {}
        chunks_payload = item.get("officialChunks") or official_chunks(cid)
        narrative_map[cid] = {
            "controlId": cid,
            "summaryTip": body["summaryTip"],
            "detail": body["detail"],
            "mode": mode,
            "sources": _source_label(chunks_payload),
        }

    def patch_gaps(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        patched: list[dict[str, Any]] = []
        for row in rows or []:
            copy = dict(row)
            cid = str(copy.get("controlId") or "")
            entry = narrative_map.get(cid)
            if entry:
                copy["detailNarrative"] = entry["detail"]
                copy["detailNarrativeTip"] = entry["summaryTip"]
                copy["detailNarrativeSources"] = list(entry["sources"])
                # 요약 탭 긴 서술이 비어 있으면 AI 상세로 보강 (엔진 organicAnalysis는 유지)
                if not str(copy.get("narrativeReport") or "").strip():
                    copy["narrativeReport"] = entry["detail"]
            patched.append(copy)
        return patched

    result["topGaps"] = patch_gaps(list(result.get("topGaps") or []))
    result["criticalGaps"] = patch_gaps(list(result.get("criticalGaps") or []))
    result["confirmedGaps"] = patch_gaps(list(result.get("confirmedGaps") or []))
    result["detailNarratives"] = narrative_map
    return result


def apply_detail_narratives(
    structured: dict[str, Any],
    *,
    enabled: bool | None = None,
    chat_client: ChatClient | None = None,
    max_controls: int | None = None,
) -> dict[str, Any]:
    """공식 문서 청크 + 엔진 사실로 상세 해설을 작성해 결과에 병합한다."""
    import time

    started = time.perf_counter()
    want = _env_enabled(True) if enabled is None else bool(enabled)
    meta: dict[str, Any] = {
        "requested": want,
        "applied": False,
        "provider": "none",
        "mode": "template",
        "controlCount": 0,
        "reasons": [],
        "inventedControlIds": [],
        "latencyMs": None,
    }
    result = dict(structured)
    packet = build_detail_packet(structured, max_controls=max_controls)
    controls = list(packet.get("controls") or [])
    meta["controlCount"] = len(controls)

    template_details = {
        str(item["controlId"]): template_detail_for_control(item)
        for item in controls
        if item.get("controlId")
    }

    if not want or not controls:
        if template_details:
            result = _merge_details(result, template_details, mode="template", packet=packet)
            meta["mode"] = "template"
            meta["reasons"] = ["상세 해설 비활성 또는 대상 없음 — 템플릿 유지"]
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        result["detailNarrativeMeta"] = meta
        return result

    client, provider_name, llm_cfg = resolve_chat_client(chat_client)
    if client is None:
        result = _merge_details(result, template_details, mode="template", packet=packet)
        meta["provider"] = "fallback"
        meta["mode"] = "template"
        meta["reasons"] = ["API 키 없음 — official_kb 템플릿 상세 유지"]
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        result["detailNarrativeMeta"] = meta
        return result

    user_prompt = (
        "다음 패킷의 규칙 엔진 사실과 officialChunks만으로 각 통제의 summaryTip/detail을 작성하세요.\n"
        "판정을 바꾸지 말고, 공식 요구사항·현재 진단·확인 포인트·참고 결함 유형을 읽기 쉽게 정리하세요.\n\n"
        + json.dumps(packet, ensure_ascii=False)
    )
    try:
        raw = client(DETAIL_SYSTEM_PROMPT, user_prompt)
        payload = _parse_llm_json(raw)
        validation = validate_detail_payload(payload, packet)
        if not validation["ok"]:
            result = _merge_details(result, template_details, mode="template", packet=packet)
            meta["provider"] = "fallback"
            meta["mode"] = "template"
            meta["reasons"] = list(validation["reasons"]) + ["검증 실패 — 템플릿 폴백"]
            meta["inventedControlIds"] = list(validation.get("inventedControlIds") or [])
        else:
            # 누락 통제는 템플릿으로 채움
            merged_details = dict(template_details)
            merged_details.update(validation["details"])
            result = _merge_details(result, merged_details, mode="llm", packet=packet)
            meta["applied"] = True
            meta["provider"] = provider_name
            meta["mode"] = "llm"
            meta["reasons"] = list(validation.get("reasons") or []) or ["공식 안내서 기반 상세 해설 적용"]
            meta["inventedControlIds"] = list(validation.get("inventedControlIds") or [])
            meta["model"] = llm_cfg.model
            meta["confidence"] = validation.get("confidence")
    except Exception as exc:  # noqa: BLE001
        result = _merge_details(result, template_details, mode="template", packet=packet)
        meta["provider"] = "fallback"
        meta["mode"] = "template"
        meta["reasons"] = [str(exc), "예외 — 템플릿 폴백"]

    meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
    result["detailNarrativeMeta"] = meta
    return result


def make_echo_detail_client(packet_factory_controls: list[str] | None = None) -> ChatClient:
    """테스트용: 허용 controlId에 대해 고정 JSON을 반환."""

    def _client(system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt
        try:
            packet = json.loads(user_prompt.split("\n\n", 1)[-1])
        except Exception:  # noqa: BLE001
            packet = {}
        details = {}
        for item in packet.get("controls") or []:
            cid = str(item.get("controlId") or "")
            if not cid:
                continue
            details[cid] = {
                "summaryTip": f"{cid} 공식 안내 기반 확인 필요",
                "detail": (
                    f"[공식 요구사항]\n테스트 요구사항\n\n"
                    f"[현재 진단]\n{item.get('organicAnalysis') or cid}\n\n"
                    f"[확인 포인트]\n- 공식 확인사항 점검\n\n"
                    f"[참고 결함 유형]\n- 안내서 사례 참고"
                ),
            }
        return json.dumps({"details": details, "confidence": 0.9}, ensure_ascii=False)

    return _client
