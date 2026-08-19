"""AI-assisted rewriting for a user-selected report passage."""

from __future__ import annotations

import json
from typing import Literal

from .llm_provider import ChatClient, resolve_chat_client

RewriteMode = Literal["diagnostic_intro", "result_interpretation", "improvement_plan", "executive_brief"]

MODE_INSTRUCTIONS: dict[RewriteMode, str] = {
    "diagnostic_intro": (
        "자체 점검 결과 보고서의 도입부로 재구성하세요. 진단 배경, 현재 관리체계를 확인할 필요성, "
        "강점과 보완 과제를 파악하려는 목적 순서로 쓰되 입력에 없는 위협·사고·법적 의무는 만들지 마세요."
    ),
    "result_interpretation": (
        "자체 점검 결과 설명으로 재구성하세요. 점검 개요와 확인 결과를 먼저 제시하고, "
        "판단이 보류된 범위와 결과의 의미를 구분하세요."
    ),
    "improvement_plan": (
        "자체 점검 개선계획으로 재구성하세요. 확인된 미흡, 예상 영향, 필요한 개선 조치, "
        "우선순위 순서로 쓰세요. 입력에 없는 담당자·기한·증적은 만들지 마세요."
    ),
    "executive_brief": (
        "경영진 의사결정용 요약으로 재구성하세요. 현재 상태, 주요 위험, 필요한 결정이나 지원, "
        "다음 조치 순서로 짧고 명확하게 쓰세요."
    ),
}


def rewrite_report_passage(
    text: str,
    mode: RewriteMode,
    *,
    chat_client: ChatClient | None = None,
) -> dict[str, object]:
    """Rewrite text without allowing the model to change assessment facts."""
    client, provider, _config = resolve_chat_client(chat_client)
    if client is None:
        return {
            "original": text,
            "suggestion": text,
            "applied": False,
            "provider": "fallback",
            "reason": "OpenAI API 키가 설정되지 않아 개선안을 만들지 않았습니다.",
        }

    system_prompt = """당신은 ISMS-P 자체 점검 결과 보고서 문장 편집자입니다.
입력에 없는 통제, 수치, 판정, 증적, 법적 결론을 추가하거나 변경하지 마세요.
사실관계와 의미를 보존하고 문장 표현만 개선하세요.
개조식·명사형 종결을 유지하고 '~했다', '~이다' 서술체를 쓰지 마세요.
반드시 {\"suggestion\": \"개선한 문장\"} JSON 객체만 반환하세요."""
    user_prompt = f"개선 방식: {MODE_INSTRUCTIONS[mode]}\n\n선택 문장:\n{text}"
    try:
        payload = json.loads(client(system_prompt, user_prompt))
        suggestion = str(payload.get("suggestion") or "").strip()
        if not suggestion:
            raise ValueError("AI 응답에 개선 문장이 없습니다.")
        return {
            "original": text,
            "suggestion": suggestion,
            "applied": suggestion != text,
            "provider": provider,
            "reason": "개선안을 만들었습니다." if suggestion != text else "원문과 동일한 개선안입니다.",
        }
    except (json.JSONDecodeError, TypeError, ValueError, RuntimeError) as error:
        return {
            "original": text,
            "suggestion": text,
            "applied": False,
            "provider": "fallback",
            "reason": f"개선안을 만들지 못했습니다: {error}",
        }
