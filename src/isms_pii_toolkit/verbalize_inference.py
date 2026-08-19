"""Facts-only Verbalizing Inference.

Deterministic analyze 결과를 Context Packet으로 만들고,
선택적으로 LLM이 서술만 담당한다. 새 통제/새 결함 창작은 거부하고
템플릿 서술로 폴백한다.

계약 (LLM 스왑 경계):
- 입력: CONTEXT_PACKET_TOP_KEYS 만
- 출력: VERBALIZE_OUTPUT_KEYS 만 (문장 필드)
- 불변: IMMUTABLE_STRUCTURED_KEYS (판정/집계 — merge가 덮어쓰지 않음)
"""

from __future__ import annotations

import json
import re
from typing import Any

from .llm_provider import ChatClient, resolve_chat_client

from .report_evaluation import CANONICAL_REPORT_HEADINGS, assemble_canonical_report, packet_evaluation_bands

CONTROL_ID_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")
CHECKLIST_MENTION_RE = re.compile(r"체크\s*(\d+)")
REQUIRED_REPORT_SECTIONS = CANONICAL_REPORT_HEADINGS
PROHIBITED_CONCLUSION_RE = re.compile(
    r"(?:인증|심사)\s*(?:가능|완료|통과|합격)|"
    r"ISMS-P\s*(?:준수\s*완료|적합\s*확정)|"
    r"(?:위험|문제)\s*(?:없음|없습니다)"
)
MAX_LLM_OUTPUT_CHARS = 50_000
MAX_EXECUTIVE_REPORT_CHARS = 20_000
MAX_INSIGHT_CHARS = 2_000
REPORT_ONLY_OUTPUT_KEYS = frozenset({"executiveReport", "sectionProse", "keyInsights", "confidence"})

# Product contract: LLM may only see these top-level packet keys.
CONTEXT_PACKET_TOP_KEYS: frozenset[str] = frozenset(
    {
        "summary",
        "cascadeChains",
        "multiGapOverlaps",
        "topGaps",
        "recommendations",
        "causalFindings",
        "profileContext",
        "suggestedScenarioIds",
        "scopePriorityControlIds",
        "confirmationActions",
        "priorityQuests",
        "inputConfidenceSummary",
        "applicabilityNotes",
        "disclaimer",
    }
)

# Product contract: LLM JSON may only contribute these fields.
VERBALIZE_OUTPUT_KEYS: frozenset[str] = frozenset(
    {
        "executiveReport",
        "sectionProse",
        "keyInsights",
        "narratives",
        "recommendationDetails",
        "actionQuestions",
        "questPhrasing",
        "confidence",
    }
)

# Never overwritten by verbalize merge (judgment / aggregates / causal facts).
IMMUTABLE_STRUCTURED_KEYS: frozenset[str] = frozenset(
    {
        "overallReadiness",
        "readinessLabel",
        "gapCount",
        "statusCounts",
        "areaReadiness",
        "weakCategories",
        "evaluationBands",
        "cascadeChains",
        "applicabilityNotes",
        "applicableControlCount",
        "naControlCount",
        "problemAnalysis",
    }
)

SYSTEM_PROMPT = """당신은 시니어 ISMS-P 인증심사원입니다. 지금 쓰는 글은 인증 결정서가 아니라 자체 점검 결과 보고서입니다.
Context Packet의 사실만 사용하세요. 통제 ID, 건수, 준비도 %, evaluationBands 등급을 바꾸거나 새 통제/새 결함을 만들지 마세요.
causalFindings가 있으면 because→problem→impacts 인과를 유지하고, because 항목을 삭제/교체/추가하지 마세요.
confirmationActions의 actionId 집합과 priorityQuests의 controlId 집합을 바꾸지 마세요.

문체:
- 개조식·명사형 종결. '~했다', '~이다' 서술체를 쓰지 않는다.
- 수식어와 마케팅 표현을 쓰지 않는다.
- 확인된 사실과 추가 확인이 필요한 점을 구분한다.
- 양호는 '이행이 확인된 범위'로만 쓴다. 칭찬하지 않는다.
- 미흡은 지적사항처럼 통제 ID와 상태를 적는다. 패킷에 없는 심각도를 올리지 않는다.
- 판단 보류 중분류는 양호 장에 넣지 말고, 범위 또는 종합 점검 결과에서 금회 확인하지 못했다고 쓴다.
- 인증 가능, 적합 확정, 위험 없음, 합격/불합격을 쓰지 않는다.
- 준비 온도, 이행률처럼 패킷에 없는 지표 이름을 만들지 않는다. overallReadiness는 보조 참고 구간으로만 쓴다.

출력은 반드시 JSON 한 개이며 스키마는 다음과 같습니다:
{
  "sectionProse": {
    "scope": "1장 본문",
    "observation": "2장 본문. 패킷의 overallReadiness와 gapCount 수치를 포함한다",
    "strengths": "3장 본문. evaluationBands.strengths만 사용",
    "weaknesses": "4장 본문. evaluationBands.weaknesses만 사용",
    "findings": "5장 본문. topGaps 통제 ID를 유지",
    "systemic": "6장 본문. 복합·연쇄만",
    "actions": "7장 본문. recommendations 순서"
  },
  "keyInsights": ["insight1", "..."],
  "narratives": {"2.7.1": "해당 통제 narrativeReport 문자열", "..."},
  "recommendationDetails": [{"title": "권고 제목", "detail": "관찰 문장"}],
  "actionQuestions": [{"actionId": "ask-2.5.4-mfa", "question": "일상어 질문", "whyItMatters": "왜 확인해야 하는지"}],
  "questPhrasing": [{"controlId": "2.5.4", "plainQuestion": "일상어 질문"}],
  "confidence": 0.0
}
장 제목과 8. 참고 한계는 출력하지 마세요. 서버가 붙입니다.
executiveReport를 직접 쓰지 말고 sectionProse만 채우세요.
각 narrative는 [통제 진단][종합 판단][체크리스트 교차 검토][시나리오][연쇄 영향][우선 보완] 섹션을 유지하세요.
actionQuestions/questPhrasing은 패킷에 있는 ID만 사용하고 문장만 다듬으세요.
모르거나 패킷에 없는 내용은 지어내지 말고 해당 필드를 생략하세요.
confidence는 0~1 사이이며, 확신이 낮으면 0.5 이하로 두세요.
"""


def build_context_packet(structured: dict[str, Any], max_gaps: int = 12) -> dict[str, Any]:
    top_gaps = list(structured.get("topGaps") or [])[:max_gaps]
    recommendations = list(structured.get("recommendations") or [])[:8]
    packet = {
        "summary": {
            "overallReadiness": structured.get("overallReadiness"),
            "readinessLabel": structured.get("readinessLabel"),
            "gapCount": structured.get("gapCount"),
            "statusCounts": structured.get("statusCounts"),
            "areaReadiness": structured.get("areaReadiness"),
            "weakCategories": list(structured.get("weakCategories") or [])[:5],
            "evaluationBands": packet_evaluation_bands(structured.get("evaluationBands")),
        },
        "cascadeChains": list(structured.get("cascadeChains") or [])[:8],
        "multiGapOverlaps": [
            {
                "bundleId": item.get("bundleId"),
                "title": item.get("title"),
                "matchedCount": item.get("matchedCount"),
                "summary": item.get("summary"),
                "controlIds": item.get("controlIds") or [
                    c.get("controlId") for c in (item.get("matchedControls") or [])
                ],
            }
            for item in list(structured.get("multiGapOverlaps") or [])[:5]
        ],
        "topGaps": [
            {
                "controlId": gap.get("controlId"),
                "title": gap.get("title"),
                "level": gap.get("level"),
                "levelLabel": gap.get("levelLabel"),
                "controlFocus": gap.get("controlFocus"),
                "riskIfMissing": gap.get("riskIfMissing"),
                "organicAnalysis": gap.get("organicAnalysis") or gap.get("problem"),
                "checklistBreakdown": list(gap.get("checklistBreakdown") or [])[:4],
                "cascadeRisks": list(gap.get("cascadeRisks") or [])[:3],
                "consequenceScenarios": list(gap.get("consequenceScenarios") or [])[:3],
                "immediateActions": list(gap.get("immediateActions") or [])[:3],
                "profileRelevance": list(gap.get("profileRelevance") or [])[:3],
            }
            for gap in top_gaps
        ],
        "recommendations": [
            {"priority": item.get("priority"), "title": item.get("title"), "detail": item.get("detail")}
            for item in recommendations
        ],
        "causalFindings": [
            {
                "findingId": item.get("findingId"),
                "controlId": item.get("controlId"),
                "title": item.get("title"),
                "level": item.get("level"),
                "source": item.get("source") or "checklist",
                "checklistItemId": item.get("checklistItemId"),
                "mappingMode": item.get("mappingMode"),
                "because": list(item.get("because") or [])[:4],
                "problem": item.get("problem") or ((item.get("problems") or [None])[0]),
                "impacts": list(item.get("impacts") or [])[:2],
                "mayCause": [
                    {
                        "targetControlId": edge.get("targetControlId"),
                        "reason": edge.get("reason"),
                    }
                    for edge in list(item.get("mayCause") or [])[:3]
                ],
                "causalStatement": item.get("causalStatement"),
                "remediation": item.get("remediation"),
            }
            for item in _packet_causal_findings(structured, max_gaps)
        ],
        "profileContext": structured.get("profileContext"),
        "suggestedScenarioIds": list(structured.get("suggestedScenarioIds") or [])[:6],
        "scopePriorityControlIds": list(
            (structured.get("scopeDraft") or {}).get("priorityControlIds") or []
        )[:20],
        "confirmationActions": [
            {
                "actionId": item.get("actionId"),
                "controlId": item.get("controlId"),
                "question": item.get("question"),
                "whyItMatters": item.get("whyItMatters"),
                "askWho": list(item.get("askWho") or [])[:3],
                "confidence": item.get("confidence"),
            }
            for item in list(structured.get("confirmationActions") or [])[:12]
        ],
        "priorityQuests": [
            {
                "controlId": item.get("controlId"),
                "plainQuestion": item.get("plainQuestion"),
                "title": item.get("title"),
            }
            for item in list(structured.get("priorityQuests") or [])[:8]
        ],
        "inputConfidenceSummary": structured.get("inputConfidenceSummary"),
        "applicabilityNotes": list(structured.get("applicabilityNotes") or [])[:12],
        "disclaimer": "실제 인증 심사 판단을 대체하지 않습니다.",
    }
    return packet


def _packet_causal_findings(structured: dict[str, Any], max_gaps: int) -> list[dict[str, Any]]:
    from .causal_contract import filter_valid_causal_findings

    raw = list((structured.get("problemAnalysis") or {}).get("causalFindings") or [])
    valid, _ = filter_valid_causal_findings(raw)
    return valid[:max_gaps]


def assert_context_packet_contract(packet: dict[str, Any]) -> list[str]:
    """Return contract violations (empty list = ok). Used by tests and gates."""
    reasons: list[str] = []
    keys = set(packet.keys())
    missing = sorted(CONTEXT_PACKET_TOP_KEYS - keys)
    extra = sorted(keys - CONTEXT_PACKET_TOP_KEYS)
    if missing:
        reasons.append(f"Context Packet 누락 키: {', '.join(missing)}")
    if extra:
        reasons.append(f"Context Packet 비계약 키: {', '.join(extra)}")
    summary = packet.get("summary")
    if not isinstance(summary, dict):
        reasons.append("summary 는 object 여야 함")
    else:
        for field in ("overallReadiness", "gapCount", "statusCounts"):
            if field not in summary:
                reasons.append(f"summary.{field} 누락")
    if not isinstance(packet.get("topGaps"), list):
        reasons.append("topGaps 는 list 여야 함")
    if not isinstance(packet.get("disclaimer"), str) or not packet.get("disclaimer"):
        reasons.append("disclaimer 필수")
    findings = packet.get("causalFindings")
    if findings is None or not isinstance(findings, list):
        reasons.append("causalFindings 는 list 여야 함")
    else:
        from .causal_contract import assert_causal_finding_contract

        for index, finding in enumerate(findings):
            for reason in assert_causal_finding_contract(finding):
                reasons.append(f"causalFindings[{index}]: {reason}")
    return reasons


def assert_verbalize_output_contract(payload: dict[str, Any]) -> list[str]:
    """Reject unknown top-level LLM keys (soft: only report extras)."""
    extra = sorted(set(payload.keys()) - VERBALIZE_OUTPUT_KEYS)
    if extra:
        return [f"Verbalize 출력 비계약 키: {', '.join(extra)}"]
    return []


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        blobs: list[str] = []
        for item in value.values():
            blobs.extend(_walk_strings(item))
        return blobs
    if isinstance(value, list):
        blobs = []
        for item in value:
            blobs.extend(_walk_strings(item))
        return blobs
    return []


def allowed_control_ids(packet: dict[str, Any]) -> set[str]:
    """Packet에 명시되거나 본문에 이미 등장한 통제 ID만 허용."""
    allowed: set[str] = set()
    for blob in _walk_strings(packet):
        allowed.update(extract_control_ids(blob))
    return {item for item in allowed if CONTROL_ID_RE.fullmatch(item)}


def allowed_checklist_refs(packet: dict[str, Any]) -> dict[str, set[str]]:
    """controlId → 허용 checklistItemId 집합."""
    allowed: dict[str, set[str]] = {}
    for finding in packet.get("causalFindings") or []:
        if not isinstance(finding, dict):
            continue
        control_id = str(finding.get("controlId") or "")
        if not control_id:
            continue
        bucket = allowed.setdefault(control_id, set())
        for basis in finding.get("because") or []:
            if not isinstance(basis, dict):
                continue
            item_id = str(basis.get("checklistItemId") or "").strip()
            if item_id:
                bucket.add(item_id)
        item_id = str(finding.get("checklistItemId") or "").strip()
        if item_id:
            bucket.add(item_id)
    for gap in packet.get("topGaps") or []:
        if not isinstance(gap, dict):
            continue
        control_id = str(gap.get("controlId") or "")
        if not control_id:
            continue
        bucket = allowed.setdefault(control_id, set())
        for row in gap.get("checklistBreakdown") or []:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("checklistItemId") or "").strip()
            if item_id:
                bucket.add(item_id)
    return allowed


def extract_control_ids(text: str) -> set[str]:
    return set(CONTROL_ID_RE.findall(text or ""))


def _collect_text_blobs(payload: dict[str, Any]) -> list[str]:
    blobs = [str(payload.get("executiveReport") or "")]
    blobs.extend(str(item) for item in payload.get("keyInsights") or [])
    prose = payload.get("sectionProse")
    if isinstance(prose, dict):
        blobs.extend(str(value) for value in prose.values())
    narratives = payload.get("narratives") or {}
    if isinstance(narratives, dict):
        blobs.extend(str(value) for value in narratives.values())
    for item in payload.get("recommendationDetails") or []:
        if isinstance(item, dict):
            blobs.append(str(item.get("detail") or ""))
            blobs.append(str(item.get("title") or ""))
    return blobs


def validate_verbalize_payload(
    payload: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    allowed = allowed_control_ids(packet)
    summary = packet.get("summary") or {}
    overall = summary.get("overallReadiness")
    gap_count = summary.get("gapCount")

    # Hard refuse if model tries to emit judgment aggregates or mutate causal facts.
    judgment_leak = sorted(set(payload.keys()) & IMMUTABLE_STRUCTURED_KEYS)
    if judgment_leak:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": [f"판정 필드 출력 금지: {', '.join(judgment_leak)}"],
            "inventedControlIds": [],
        }
    if "causalFindings" in payload:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": ["causalFindings 출력 금지 — 인과 체인은 규칙 엔진 전용"],
            "inventedControlIds": [],
        }
    contract_extras = assert_verbalize_output_contract(payload)
    if contract_extras:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": contract_extras,
            "inventedControlIds": [],
        }

    executive = str(payload.get("executiveReport") or "").strip()
    insights = payload.get("keyInsights")
    if not executive:
        return {"ok": False, "confidence": 0.0, "reasons": ["executiveReport 비어 있음"], "inventedControlIds": []}
    if not isinstance(insights, list) or not insights:
        return {"ok": False, "confidence": 0.0, "reasons": ["keyInsights 형식 오류"], "inventedControlIds": []}
    if len(executive) > MAX_EXECUTIVE_REPORT_CHARS:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": ["executiveReport 출력 길이 초과"],
            "inventedControlIds": [],
        }
    if len(insights) > 8 or any(len(str(item)) > MAX_INSIGHT_CHARS for item in insights):
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": ["keyInsights 출력 개수 또는 길이 초과"],
            "inventedControlIds": [],
        }

    blobs = _collect_text_blobs(payload)
    if sum(len(blob) for blob in blobs) > MAX_LLM_OUTPUT_CHARS:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": ["LLM 전체 출력 길이 초과"],
            "inventedControlIds": [],
        }
    mentioned = set()
    for blob in blobs:
        mentioned.update(extract_control_ids(blob))
    invented = sorted(mentioned - allowed) if allowed else []
    if invented:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": [f"패킷에 없는 통제 ID 생성: {', '.join(invented[:8])}"],
            "inventedControlIds": invented,
        }
    missing_sections = [section for section in REQUIRED_REPORT_SECTIONS if section not in executive]
    if missing_sections:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": [f"리포트 필수 섹션 누락: {', '.join(missing_sections)}"],
            "inventedControlIds": [],
        }
    prohibited = [blob for blob in blobs if PROHIBITED_CONCLUSION_RE.search(blob)]
    if prohibited:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": ["근거 없는 인증·안전 결론 감지"],
            "inventedControlIds": [],
        }

    checklist_allowed = allowed_checklist_refs(packet)
    invented_items: list[str] = []
    narratives = payload.get("narratives") or {}
    if isinstance(narratives, dict):
        for control_id, text in narratives.items():
            allowed_items = checklist_allowed.get(str(control_id), set())
            if not allowed_items:
                continue
            for match in CHECKLIST_MENTION_RE.finditer(str(text or "")):
                item_id = match.group(1)
                if item_id not in allowed_items:
                    invented_items.append(f"{control_id}:{item_id}")
    for blob in blobs:
        # executive/insights에서 "2.9.4 ... 체크 9" 형태를 느슨히 검사
        for control_id in extract_control_ids(blob):
            allowed_items = checklist_allowed.get(control_id, set())
            if not allowed_items:
                continue
            for match in CHECKLIST_MENTION_RE.finditer(blob):
                item_id = match.group(1)
                # 같은 문장 창에서 해당 통제와 가까운 언급만 엄격히 보려면 비용↑ → 전역은 soft
                if item_id not in allowed_items and control_id in blob[max(0, match.start() - 40) : match.end() + 40]:
                    invented_items.append(f"{control_id}:{item_id}")
    invented_items = sorted(set(invented_items))
    if invented_items:
        return {
            "ok": False,
            "confidence": 0.0,
            "reasons": [f"패킷에 없는 체크 항목 생성: {', '.join(invented_items[:8])}"],
            "inventedControlIds": invented_items,
        }

    confidence = payload.get("confidence")
    try:
        confidence_value = float(confidence) if confidence is not None else 0.8
    except (TypeError, ValueError):
        confidence_value = 0.5
    confidence_value = max(0.0, min(1.0, confidence_value))

    if overall is not None and not re.search(rf"(?<![\d.]){re.escape(str(overall))}(?![\d.])", executive):
        reasons.append("executiveReport에 overallReadiness 수치가 없음")
        confidence_value = min(confidence_value, 0.45)
    if gap_count is not None and not re.search(rf"(?<!\d){re.escape(str(gap_count))}(?!\d)", executive):
        reasons.append("executiveReport에 gapCount 수치가 없음")
        confidence_value = min(confidence_value, 0.45)
    if len(insights) < 3:
        reasons.append("keyInsights가 너무 적음")
        confidence_value = min(confidence_value, 0.4)

    # Hard refuse when model itself reports low confidence.
    if confidence_value < 0.3:
        return {
            "ok": False,
            "confidence": confidence_value,
            "reasons": reasons + ["모델 confidence 낮음 — 서술 거부"],
            "inventedControlIds": [],
        }

    ok = confidence_value >= 0.5
    if not ok:
        reasons.append("검증 confidence 부족 — 템플릿 폴백")

    quest_validation = validate_quest_verbalize_fields(payload, packet)
    if not quest_validation["ok"]:
        # quest 필드만 실패하면 report는 살리고 quest는 무시하도록 reasons만 남김
        reasons.extend(quest_validation["reasons"])
        payload.pop("actionQuestions", None)
        payload.pop("questPhrasing", None)
        confidence_value = min(confidence_value, 0.7)

    return {
        "ok": ok,
        "confidence": confidence_value,
        "reasons": reasons,
        "inventedControlIds": [],
        "questOk": quest_validation["ok"],
    }


def validate_quest_verbalize_fields(
    payload: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    """actionId/controlId 집합 불변 검증. 판정 필드는 허용하지 않음."""
    reasons: list[str] = []
    allowed_actions = {
        str(item.get("actionId"))
        for item in (packet.get("confirmationActions") or [])
        if isinstance(item, dict) and item.get("actionId")
    }
    allowed_quest_controls = {
        str(item.get("controlId"))
        for item in (packet.get("priorityQuests") or [])
        if isinstance(item, dict) and item.get("controlId")
    }

    action_questions = payload.get("actionQuestions")
    if action_questions is not None:
        if not isinstance(action_questions, list):
            return {"ok": False, "reasons": ["actionQuestions 형식 오류"]}
        seen: set[str] = set()
        for row in action_questions:
            if not isinstance(row, dict):
                return {"ok": False, "reasons": ["actionQuestions 항목 형식 오류"]}
            action_id = str(row.get("actionId") or "")
            if not action_id or action_id not in allowed_actions:
                return {
                    "ok": False,
                    "reasons": [f"패킷에 없는 actionId: {action_id or '(empty)'}"],
                }
            if action_id in seen:
                return {"ok": False, "reasons": [f"중복 actionId: {action_id}"]}
            seen.add(action_id)
            if not str(row.get("question") or "").strip():
                reasons.append(f"{action_id} question 비어 있음")

    quest_phrasing = payload.get("questPhrasing")
    if quest_phrasing is not None:
        if not isinstance(quest_phrasing, list):
            return {"ok": False, "reasons": ["questPhrasing 형식 오류"]}
        for row in quest_phrasing:
            if not isinstance(row, dict):
                return {"ok": False, "reasons": ["questPhrasing 항목 형식 오류"]}
            control_id = str(row.get("controlId") or "")
            if control_id not in allowed_quest_controls:
                return {
                    "ok": False,
                    "reasons": [f"패킷에 없는 quest controlId: {control_id or '(empty)'}"],
                }

    # 판정성 키워드 하드 거부
    blobs = []
    for row in action_questions or []:
        if isinstance(row, dict):
            blobs.extend([str(row.get("question") or ""), str(row.get("whyItMatters") or "")])
    for row in quest_phrasing or []:
        if isinstance(row, dict):
            blobs.append(str(row.get("plainQuestion") or ""))
    banned = ("합격", "불합격", "인증 완료", "심사 통과")
    for blob in blobs:
        if any(token in blob for token in banned):
            return {"ok": False, "reasons": ["퀘스트 서술에 합격/불합격 단정 포함"]}

    return {"ok": True, "reasons": reasons}


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("LLM JSON must be an object")
    return data


def hydrate_report_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Prefer sectionProse slots; headings and disclaimer are assembled in process."""
    result = dict(payload)
    prose = result.get("sectionProse")
    if not isinstance(prose, dict):
        return result, []
    assembled, missing = assemble_canonical_report(prose)
    if missing:
        return result, missing
    if assembled:
        result["executiveReport"] = assembled
    return result, []


def _report_fact_fingerprint(payload: dict[str, Any]) -> tuple[object, ...]:
    """Compare facts across samples while allowing prose variation."""
    text = "\n".join(_collect_text_blobs(payload))
    control_ids = tuple(sorted(extract_control_ids(text)))
    numbers = tuple(sorted(set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.])", text))))
    sections = tuple(section for section in REQUIRED_REPORT_SECTIONS if section in text)
    narratives = tuple(sorted(str(key) for key in (payload.get("narratives") or {}).keys()))
    action_ids = tuple(
        sorted(
            str(item.get("actionId"))
            for item in (payload.get("actionQuestions") or [])
            if isinstance(item, dict) and item.get("actionId")
        )
    )
    quest_ids = tuple(
        sorted(
            str(item.get("controlId"))
            for item in (payload.get("questPhrasing") or [])
            if isinstance(item, dict) and item.get("controlId")
        )
    )
    return control_ids, numbers, sections, narratives, action_ids, quest_ids


def default_openai_chat_client(system_prompt: str, user_prompt: str) -> str:
    """Backward-compatible alias — prefer llm_provider.openai_chat_client."""
    from .llm_provider import openai_chat_client

    return openai_chat_client(system_prompt, user_prompt)


def _merge_verbalized(structured: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(structured)
    # Defense in depth: never let judgment aggregates ride in via payload.
    safe_payload = {k: v for k, v in payload.items() if k not in IMMUTABLE_STRUCTURED_KEYS}
    result["executiveReport"] = str(
        safe_payload.get("executiveReport") or structured.get("executiveReport") or ""
    )
    insights = safe_payload.get("keyInsights")
    if isinstance(insights, list) and insights:
        result["keyInsights"] = [str(item) for item in insights][:8]

    narratives = safe_payload.get("narratives") or {}
    if isinstance(narratives, dict):
        top_gaps = []
        for gap in list(structured.get("topGaps") or []):
            gap_copy = dict(gap)
            control_id = str(gap_copy.get("controlId") or "")
            if control_id in narratives and str(narratives[control_id]).strip():
                gap_copy["narrativeReport"] = str(narratives[control_id]).strip()
            top_gaps.append(gap_copy)
        result["topGaps"] = top_gaps
        # keep criticalGaps in sync for overlapping IDs
        critical = []
        narrative_by_id = {
            str(gap.get("controlId")): gap.get("narrativeReport")
            for gap in top_gaps
        }
        for gap in list(structured.get("criticalGaps") or []):
            gap_copy = dict(gap)
            control_id = str(gap_copy.get("controlId") or "")
            if control_id in narrative_by_id and narrative_by_id[control_id]:
                gap_copy["narrativeReport"] = narrative_by_id[control_id]
            critical.append(gap_copy)
        result["criticalGaps"] = critical

    details = safe_payload.get("recommendationDetails") or []
    if isinstance(details, list) and details:
        detail_by_title = {
            str(item.get("title")): str(item.get("detail") or "")
            for item in details
            if isinstance(item, dict) and item.get("title")
        }
        recommendations = []
        for item in list(structured.get("recommendations") or []):
            item_copy = dict(item)
            title = str(item_copy.get("title") or "")
            if title in detail_by_title and detail_by_title[title].strip():
                item_copy["detail"] = detail_by_title[title].strip()
            recommendations.append(item_copy)
        result["recommendations"] = recommendations

    from .control_insight_verbalize import build_report_sections

    result["reportSections"] = build_report_sections(
        list(result.get("keyInsights") or []),
        str(result.get("executiveReport") or ""),
    )

    # Quest mode: string-field surgery only
    action_questions = safe_payload.get("actionQuestions")
    if isinstance(action_questions, list) and action_questions:
        by_id = {
            str(item.get("actionId")): item
            for item in action_questions
            if isinstance(item, dict) and item.get("actionId")
        }
        actions = []
        for action in list(structured.get("confirmationActions") or []):
            action_copy = dict(action)
            patch = by_id.get(str(action_copy.get("actionId") or ""))
            if patch:
                if str(patch.get("question") or "").strip():
                    action_copy["question"] = str(patch["question"]).strip()
                if str(patch.get("whyItMatters") or "").strip():
                    action_copy["whyItMatters"] = str(patch["whyItMatters"]).strip()
            actions.append(action_copy)
        result["confirmationActions"] = actions

    quest_phrasing = safe_payload.get("questPhrasing")
    if isinstance(quest_phrasing, list) and quest_phrasing:
        by_control = {
            str(item.get("controlId")): item
            for item in quest_phrasing
            if isinstance(item, dict) and item.get("controlId")
        }
        quests = []
        for quest in list(structured.get("priorityQuests") or []):
            quest_copy = dict(quest)
            patch = by_control.get(str(quest_copy.get("controlId") or ""))
            if patch and str(patch.get("plainQuestion") or "").strip():
                quest_copy["plainQuestion"] = str(patch["plainQuestion"]).strip()
            quests.append(quest_copy)
        result["priorityQuests"] = quests

    return result

def apply_verbalizing(
    structured: dict[str, Any],
    *,
    enabled: bool = False,
    chat_client: ChatClient | None = None,
    max_gaps: int = 12,
    consistency_samples: int = 1,
    include_quests: bool = True,
    report_only: bool = False,
) -> dict[str, Any]:
    import time

    started = time.perf_counter()
    meta = {
        "requested": bool(enabled),
        "applied": False,
        "provider": "none",
        "confidence": 1.0,
        "reasons": [],
        "inventedControlIds": [],
        "mode": "template",
        "model": None,
        "latencyMs": None,
        "maxGaps": max(1, min(50, int(max_gaps or 12))),
        "sampleCount": 0,
        "includeQuests": bool(include_quests),
    }
    result = dict(structured)
    if not enabled:
        result["verbalizeMeta"] = meta
        return result

    packet = build_context_packet(structured, max_gaps=max_gaps)
    if not include_quests:
        packet["confirmationActions"] = []
        packet["priorityQuests"] = []
    packet_violations = assert_context_packet_contract(packet)
    if packet_violations:
        meta["reasons"] = packet_violations + ["Context Packet 계약 위반 — 템플릿 유지"]
        meta["provider"] = "fallback"
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        result["verbalizeMeta"] = meta
        return result

    client, provider_name, llm_cfg = resolve_chat_client(chat_client)
    if client is None:
        meta["reasons"] = ["API 키 없음 — 템플릿 서술 유지"]
        meta["provider"] = "fallback"
        meta["model"] = llm_cfg.model
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        result["verbalizeMeta"] = meta
        return result

    if report_only:
        user_prompt = (
            "사용자가 체크한 통제항목의 규칙 엔진 분석 결과입니다. 이 Context Packet의 사실만 사용해 "
            "전체 진단 보고서를 작성하세요.\n"
            "출력 JSON에는 sectionProse, keyInsights, confidence만 포함하세요.\n"
            "sectionProse는 scope, observation, strengths, weaknesses, findings, systemic, actions를 모두 채우세요. "
            "장 제목과 참고 한계는 쓰지 마세요.\n"
            "observation에는 overallReadiness와 gapCount 수치를 포함하고, "
            "evaluationBands의 양호·미흡·판단 보류를 바꾸지 마세요.\n"
            "판정·점수·통제 ID를 새로 만들지 말고 인증 가능 여부를 단정하지 마세요.\n\n"
            + json.dumps(packet, ensure_ascii=False)
        )
    else:
        user_prompt = (
            "다음 Context Packet만 사용해 sectionProse, keyInsights, narratives, "
            "recommendationDetails"
            + (", actionQuestions, questPhrasing" if include_quests else "")
            + "을 JSON으로 작성하세요.\n"
            "sectionProse의 일곱 슬롯을 모두 채우고 장 제목은 쓰지 마세요.\n"
            "causalFindings의 because→problem 인과를 유지하세요.\n"
            + (
                "actionId/controlId 집합은 패킷과 동일해야 하며 문장만 다듬으세요.\n\n"
                if include_quests
                else "퀘스트 필드는 생략하세요.\n\n"
            )
            + json.dumps(packet, ensure_ascii=False)
        )
    samples = max(1, min(3, int(consistency_samples or 1)))
    meta["sampleCount"] = samples
    accepted: list[tuple[dict[str, Any], dict[str, Any]]] = []
    last_error = ""
    try:
        for _ in range(samples):
            try:
                raw = client(SYSTEM_PROMPT, user_prompt)
                payload = parse_llm_json(raw)
                if report_only:
                    payload = {
                        key: value
                        for key, value in payload.items()
                        if key in REPORT_ONLY_OUTPUT_KEYS
                    }
                if not include_quests:
                    payload.pop("actionQuestions", None)
                    payload.pop("questPhrasing", None)
                payload, missing_slots = hydrate_report_payload(payload)
                if missing_slots:
                    last_error = f"관찰 슬롯 누락: {', '.join(missing_slots)}"
                    continue
                validation = validate_verbalize_payload(payload, packet)
                if validation["ok"]:
                    accepted.append((payload, validation))
                else:
                    last_error = "; ".join(validation["reasons"]) or "validation failed"
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)

        if not accepted:
            meta["provider"] = "fallback"
            meta["mode"] = "template"
            meta["reasons"] = [last_error or "Verbalize 샘플 없음", "Self-Correction: 서술 거부 후 템플릿 폴백"]
            meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
            result["verbalizeMeta"] = meta
            return result

        if samples > 1:
            if len(accepted) < 2:
                meta["provider"] = "fallback"
                meta["mode"] = "template"
                meta["reasons"] = [
                    f"Self-Consistency: 유효 샘플 {len(accepted)}/{samples}",
                    "불일치/부족으로 템플릿 폴백",
                ]
                meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
                result["verbalizeMeta"] = meta
                return result
            fingerprint_a = _report_fact_fingerprint(accepted[0][0])
            fingerprint_b = _report_fact_fingerprint(accepted[1][0])
            if fingerprint_a != fingerprint_b:
                meta["provider"] = "fallback"
                meta["mode"] = "template"
                meta["reasons"] = ["Self-Consistency: 핵심 사실 집합 불일치", "템플릿 폴백"]
                meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
                result["verbalizeMeta"] = meta
                return result

        payload, validation = accepted[0]
        meta["confidence"] = validation["confidence"]
        meta["reasons"] = list(validation["reasons"])
        if samples > 1:
            meta["reasons"] = list(meta["reasons"]) + [f"Self-Consistency: {len(accepted)}/{samples} 샘플 일치"]
        meta["inventedControlIds"] = list(validation["inventedControlIds"])
        if validation.get("questOk") is False:
            meta["reasons"] = list(meta["reasons"]) + ["quest 필드 검증 실패 — 템플릿 퀘스트 유지"]
        merged = _merge_verbalized(structured, payload)
        for key in IMMUTABLE_STRUCTURED_KEYS:
            if key in structured:
                merged[key] = structured[key]
        # Defense: causal fingerprint must stay identical after verbalize.
        from .causal_contract import causal_chain_fingerprint

        before_fp = causal_chain_fingerprint(
            list((structured.get("problemAnalysis") or {}).get("causalFindings") or [])
        )
        after_fp = causal_chain_fingerprint(
            list((merged.get("problemAnalysis") or {}).get("causalFindings") or [])
        )
        if before_fp != after_fp:
            meta["provider"] = "fallback"
            meta["mode"] = "template"
            meta["reasons"] = ["인과 체인 fingerprint 변경 감지 — 템플릿 폴백"]
            meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
            result = dict(structured)
            result["verbalizeMeta"] = meta
            return result
        meta["applied"] = True
        meta["provider"] = provider_name
        meta["model"] = llm_cfg.model
        meta["mode"] = "llm-consistency" if samples > 1 else "llm"
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        merged["verbalizeMeta"] = meta
        return merged
    except Exception as exc:  # noqa: BLE001 - verbalize must never break analyze
        meta["provider"] = "fallback"
        meta["mode"] = "template"
        meta["confidence"] = 0.0
        meta["reasons"] = [f"Verbalize 실패: {exc}"]
        meta["latencyMs"] = int((time.perf_counter() - started) * 1000)
        result["verbalizeMeta"] = meta
        return result
