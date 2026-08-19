from __future__ import annotations

from .control_graph import find_control, load_manual_relations
from .score_metrics import (
    ASSESSED_SCORE_LABEL,
    ASSESSED_SCORE_TOOLTIP,
    OVERALL_SCORE_LABEL,
    OVERALL_SCORE_TOOLTIP,
    qualitative_label,
)

LEVEL_LABEL: dict[str, str] = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
}


def _relation_narrative(control_id: str, related_ids: list[str]) -> str:
    if not related_ids:
        return "직접 연결된 후속 통제 정보가 제한적이므로, 동일 카테고리 인접 통제를 함께 점검하는 것이 좋습니다."
    parts: list[str] = []
    relations = load_manual_relations()
    for target_id in related_ids[:4]:
        reason = None
        for tid, r in relations.get(control_id, ()):
            if tid == target_id:
                reason = r
                break
        if reason is None:
            for src, targets in relations.items():
                for tid, r in targets:
                    if tid == control_id and src == target_id:
                        reason = r
                        break
        target = find_control(target_id)
        title = str(target["title"]) if target else ""
        if reason:
            parts.append(f"{target_id}({title}): {reason}")
        else:
            parts.append(f"{target_id} {title}과(와) 동일 시나리오/흐름에서 함께 검토됩니다.")
    return " ".join(parts)


def _verification_method(item: str, title: str) -> str:
    return (
        f"최근 3개월 분기 점검 기준으로 정책/지침 문서, 시스템 설정 캡처, 운영 로그 샘플을 대조해 "
        f"'{item}' 이행 여부를 확인합니다. 담당자 인터뷰 시 {title} 운영 절차를 단계별로 설명할 수 있어야 합니다."
    )


def _evidence_hint(item: str, category_id: str) -> str:
    hints = {
        "2.9": "변경관리 이력, 백업 성공 로그, 로그 수집/점검표, NTP 동기화 점검 기록",
        "2.7": "암호정책서, 암호화 적용 설정 화면, 키관리 접근권한 기록",
        "2.5": "계정 발급/변경 신청서, 권한 매트릭스, 분기 권한검토 결과",
        "2.6": "방화벽/ACL, DB 접근통제 설정, 원격접근 승인 기록",
        "3.2": "개인정보 보유 현황표, 목적 외 이용 승인 로그, 마스킹 적용 증적",
        "3.1": "수집 동의 화면, 수집 항목 매핑표, 주민번호 처리 근거",
        "1.2": "정보자산 목록, 개인정보 흐름도, 위험평가/보호대책 선정표",
    }
    base = hints.get(category_id, "정책/지침, 담당자 지정 문서, 정기 점검 기록")
    return f"'{item}' 확인 시 우선 제시할 증적: {base}."


def enrich_checklist_row(
    detail: dict[str, object],
    control_id: str,
    title: str,
    category_id: str,
    level: str,
) -> dict[str, object]:
    related = list(detail.get("relatedControls", []))
    op_risk = str(detail.get("operationalRisk", ""))
    return {
        **detail,
        "consequenceIfFailed": (
            f"{LEVEL_LABEL.get(level, '미흡')} 상태에서 이 항목이 충족되지 않으면 {op_risk}"
        ),
        "verificationMethod": _verification_method(str(detail.get("item", "")), title),
        "evidenceHint": _evidence_hint(str(detail.get("item", "")), category_id),
        "relationshipNote": _relation_narrative(control_id, related),
    }


def build_gap_narrative(
    control_id: str,
    title: str,
    category_name: str,
    area_name: str,
    level: str,
    level_label: str,
    focus: str,
    risk_if_missing: str,
    organic_analysis: str,
    checklist_breakdown: list[dict[str, object]],
    consequence_scenarios: list[str],
    cascade_risks: list[dict[str, object]],
    immediate_actions: list[str],
) -> str:
    checklist_lines = []
    for index, row in enumerate(checklist_breakdown, start=1):
        checklist_lines.append(
            f"{index}) {row['item']} — 운영 관점에서는 {row['operationalRisk']} "
            f"심사 관점에서는 {row['auditRisk']}"
        )

    cascade_lines = []
    for cascade in cascade_risks[:5]:
        cascade_lines.append(
            f"- {control_id} → {cascade['targetControlId']} {cascade.get('targetTitle', '')}: "
            f"{cascade.get('impact', cascade.get('connectionReason', ''))}"
        )

    scenario_block = "\n".join(f"- {s}" for s in consequence_scenarios[:4])
    action_block = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(immediate_actions[:4]))

    cascade_section = "\n".join(cascade_lines) if cascade_lines else "- 직접 매핑된 연쇄 경로는 제한적이나, 동일 영역 통제와 함께 결함으로 확대될 수 있습니다."

    return "\n".join(
        [
            f"[통제 진단] {control_id} {title} — {level_label}",
            "",
            f"{area_name} / {category_name} 영역에서 본 통제는 '{focus}'를 요구합니다. "
            f"현재 자가진단 결과는 **{level_label}**이며, 핵심 리스크는 다음과 같습니다: {risk_if_missing}",
            "",
            "[종합 판단]",
            organic_analysis,
            "",
            "[체크리스트 교차 검토]",
            *checklist_lines,
            "",
            "[사고/결함 시나리오]",
            scenario_block,
            "",
            "[연쇄 영향 분석]",
            cascade_section,
            "",
            "[우선 보완 조치]",
            action_block or "1. 정책/지침 반영 후 운영 증적을 통제별로 연결합니다.",
        ]
    )


def build_review_items(
    *,
    applicable_count: int,
    reviewed_count: int,
    overall_percent: float,
    assessed_percent: float | None,
    status_counts: dict[str, int],
    weak_categories: list[dict[str, object]],
    cascade_chains: list[dict[str, object]],
    confirmed_gaps: list[dict[str, object]],
    unreviewed_gaps: list[dict[str, object]],
    multigap_overlaps: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    completion = round(reviewed_count / applicable_count * 100, 1) if applicable_count else 0.0
    none_count = int(status_counts.get("none", 0))
    partial_count = int(status_counts.get("partial", 0))
    unknown_count = int(status_counts.get("unknown", 0))
    done_count = int(status_counts.get("done", 0)) + int(status_counts.get("evidenced", 0))
    # 진행률과 미점검 수는 보고서 요약에 이미 노출된다. 확인 카드에는 사용자가
    # 판정한 미흡과 그로부터 파생된 참고 분석만 담아 중복 클릭을 만들지 않는다.
    items: list[dict[str, object]] = []

    if confirmed_gaps:
        top_gaps = confirmed_gaps[:4]
        top_ids = [str(gap["controlId"]) for gap in top_gaps]
        items.append(
            {
                "id": "confirmed-findings",
                "kind": "finding",
                "classification": "verified_finding",
                "title": "확인된 미흡",
                "headline": f"입력으로 확인된 미흡 통제는 {len(confirmed_gaps)}개입니다.",
                "metric": len(confirmed_gaps),
                "metricUnit": "건",
                "metricLabel": "확인된 미흡",
                "stats": [
                    {"label": "미이행", "value": none_count, "tone": "danger"},
                    {"label": "부분 이행", "value": partial_count, "tone": "mid"},
                ],
                "chips": top_ids,
                "controlNodes": [
                    {
                        "controlId": str(gap.get("controlId") or ""),
                        "title": str(gap.get("title") or gap.get("controlId") or ""),
                        "level": str(gap.get("level") or "unknown"),
                        "levelLabel": str(gap.get("levelLabel") or "미점검"),
                        "role": str(gap.get("categoryName") or gap.get("areaName") or ""),
                    }
                    for gap in top_gaps
                ],
                "question": "실제 입력된 미흡 상태와 우선 보완 대상을 확인했나요?",
                "explanation": "미점검 통제는 제외하고 미이행 또는 부분 이행으로 판정한 통제만 집계했습니다.",
                "basis": [f"자가진단 판정: 미이행 {none_count}개", f"자가진단 판정: 부분 이행 {partial_count}개"],
                "confidenceLevel": "high",
                "confidenceLabel": "확인된 판정",
                "action": {"type": "control", "label": "최우선 통제 열기", "controlId": top_ids[0]},
            }
        )

    weak_with_confirmed_gaps = [
        category
        for category in weak_categories
        if int((category.get("statusCounts") or {}).get("none", 0))
        + int((category.get("statusCounts") or {}).get("partial", 0))
        > 0
    ]
    if confirmed_gaps and weak_with_confirmed_gaps:
        weakest = weak_with_confirmed_gaps[0]
        reviewed = int(weakest.get("reviewedCount", 0))
        total = int(weakest.get("count", 0))
        coverage = float(weakest.get("coveragePercent", 0))
        category_statuses = dict(weakest.get("statusCounts") or {})
        items.append(
            {
                "id": f"weak-category-{weakest.get('categoryId', weakest['category'])}",
                "kind": "weak",
                "classification": "verified_finding",
                "title": "보완 집중 분야",
                "headline": str(weakest["category"]),
                "metric": coverage,
                "metricUnit": "%",
                "metricLabel": "분야 점검 완료율",
                "coveragePercent": coverage,
                "stats": [
                    {"label": "미이행", "value": int(category_statuses.get("none", 0)), "tone": "danger"},
                    {"label": "부분 이행", "value": int(category_statuses.get("partial", 0)), "tone": "mid"},
                    {
                        "label": "이행",
                        "value": int(category_statuses.get("done", 0))
                        + int(category_statuses.get("evidenced", 0)),
                        "tone": "ok",
                    },
                    {
                        "label": ASSESSED_SCORE_LABEL,
                        "value": str(
                            weakest.get("qualitativeLabel")
                            or qualitative_label(weakest.get("score"))
                        ),
                        "tone": "muted",
                        "secondary": True,
                        "tooltip": ASSESSED_SCORE_TOOLTIP,
                    },
                ],
                "question": "이 분야의 확인된 미흡 통제를 우선 보완할까요?",
                "explanation": (
                    "미점검은 제외하고, 미이행·부분 이행이 실제로 존재하는 분야만 비교했습니다. "
                    "큰 숫자는 취약도 점수가 아니라 분야 점검 완료율입니다."
                ),
                "basis": [
                    f"분야 내 점검 완료 {reviewed}/{total}",
                    f"확인된 미흡 {int(category_statuses.get('none', 0)) + int(category_statuses.get('partial', 0))}개",
                ],
                "confidenceLevel": "medium" if reviewed < total else "high",
                "confidenceLabel": "부분 표본" if reviewed < total else "평가 완료",
                "action": {"type": "control", "label": "관련 통제 열기", "controlId": str(weakest.get("firstControlId", ""))},
            }
        )

    if cascade_chains:
        chain = cascade_chains[0]
        origin_title = str(chain.get("originTitle") or chain["originControlId"])
        target_title = str(chain.get("targetTitle") or chain["targetControlId"])
        origin_level_label = str(chain.get("originLevelLabel") or "미점검")
        target_level = str(chain.get("targetLevel") or "unknown")
        target_role = "아직 점검 안 함" if target_level == "unknown" else "영향받을 통제"
        items.append(
            {
                "id": f"cascade-{chain['originControlId']}-{chain['targetControlId']}",
                "kind": "cascade",
                "classification": "hypothesis",
                "title": "연결 위험 확인",
                "headline": (
                    f"'{origin_title}'의 {origin_level_label} 상태가 "
                    f"'{target_title}'에 영향을 줄 수 있습니다."
                ),
                "routeLabel": "통제 간 영향 경로",
                "path": [str(chain["originControlId"]), str(chain["targetControlId"])],
                "pathNodes": [
                    {
                        "controlId": str(chain["originControlId"]),
                        "title": origin_title,
                        "role": "확인된 약점",
                        "level": str(chain.get("originLevel") or "unknown"),
                        "levelLabel": origin_level_label,
                    },
                    {
                        "controlId": str(chain["targetControlId"]),
                        "title": target_title,
                        "role": target_role,
                        "level": target_level,
                        "levelLabel": str(chain.get("targetLevelLabel") or "미점검"),
                    },
                ],
                "relationLabel": "영향 가능성",
                "question": f"'{target_title}'에 필요한 조치와 증적이 실제로 반영됐는지 확인하세요.",
                "explanation": str(chain.get("connectionReason") or chain.get("impact") or ""),
                "nextAction": f"먼저 '{target_title}'의 정책·설정·운영 증적을 점검하세요.",
                "basis": ["확인된 미흡 통제에서 시작", "통제 관계 그래프 기반 추론"],
                "confidenceLevel": "medium",
                "confidenceLabel": "연결 가능성",
                "action": {
                    "type": "control",
                    "label": "영향 통제 점검",
                    "controlId": str(chain["targetControlId"]),
                },
            }
        )

    if multigap_overlaps:
        overlap = multigap_overlaps[0]
        matched = list(overlap.get("matchedControls") or [])
        control_ids = [str(item.get("controlId")) for item in matched[:4]]
        severity_label = {
            "critical": "심각",
            "high": "높음",
            "medium": "중간",
        }.get(str(overlap.get("severity")), "확인 필요")
        items.append(
            {
                "id": f"overlap-{overlap.get('bundleId', 'top')}",
                "kind": "overlap",
                "classification": "hypothesis",
                "title": "복합 위험 후보",
                "headline": str(overlap.get("title") or "다중 통제 겹침"),
                "chips": control_ids,
                "controlNodes": [
                    {
                        "controlId": str(item.get("controlId") or ""),
                        "title": str(item.get("title") or item.get("controlId") or ""),
                        "level": str(item.get("level") or "unknown"),
                        "levelLabel": str(item.get("levelLabel") or "미점검"),
                    }
                    for item in matched[:4]
                ],
                "stats": [
                    {
                        "label": "일치 통제",
                        "value": f"{overlap.get('matchedCount', 0)}/{overlap.get('requiredCount', 0)}",
                        "tone": "mid",
                    },
                    {"label": "위험 수준", "value": severity_label, "tone": "danger"},
                    {
                        "label": "환경",
                        "value": "전체 일치" if overlap.get("matchType") == "full" else "부분 일치",
                        "tone": "ok",
                    },
                ],
                "question": "공통 원인과 증적을 하나의 보완 과제로 묶을 수 있나요?",
                "explanation": str(overlap.get("summary") or ""),
                "basis": [
                    f"미이행·부분 이행 통제 {overlap.get('matchedCount', 0)}개 일치",
                    str(overlap.get("sourceLabel") or "다중 갭 규칙"),
                ],
                "confidenceLevel": "medium",
                "confidenceLabel": "규칙 기반 후보",
                "action": {
                    "type": "control",
                    "label": "관련 통제 검토",
                    "controlId": control_ids[0] if control_ids else "",
                },
            }
        )

    return items[:7]


def build_key_insights(
    overall_percent: float,
    readiness_label: str,
    gap_count: int,
    status_counts: dict[str, int],
    weak_categories: list[dict[str, object]],
    cascade_chains: list[dict[str, object]],
    top_gaps: list[dict[str, object]],
    multigap_overlaps: list[dict[str, object]] | None = None,
) -> list[str]:
    insights: list[str] = []
    none_count = int(status_counts.get("none", 0))
    unknown_count = int(status_counts.get("unknown", 0))
    partial_count = int(status_counts.get("partial", 0))

    reviewed = none_count + partial_count + int(status_counts.get("done", 0)) + int(
        status_counts.get("evidenced", 0)
    )
    insights.append(
        f"점검 완료 {reviewed}건, 확인된 미흡 {gap_count}건, 미점검 {unknown_count}건"
        f"(미이행 {none_count} · 부분 이행 {partial_count}). "
        f"보조 참고: {OVERALL_SCORE_LABEL} '{readiness_label}'."
    )

    if weak_categories:
        weakest = weak_categories[0]
        weak_level = str(
            weakest.get("qualitativeLabel") or qualitative_label(weakest.get("score"))
        )
        insights.append(
            f"보완 집중 분야 '{weakest['category']}' "
            f"(점검 {weakest.get('reviewedCount', weakest['count'])}/{weakest['count']}개"
            f", 참고 '{weak_level}')."
        )

    if cascade_chains:
        chain = cascade_chains[0]
        insights.append(
            f"연쇄 리스크 경로: {chain['originControlId']} → {chain['targetControlId']} — "
            f"{chain.get('connectionReason', chain.get('impact', ''))}"
        )

    if multigap_overlaps:
        top_overlap = multigap_overlaps[0]
        matched = top_overlap.get("matchedControls") or []
        matched_ids = ", ".join(str(m.get("controlId")) for m in matched[:4])
        insights.append(
            f"복합 위험 후보: '{top_overlap.get('title')}' — {top_overlap.get('matchedCount')}개 확인된 미흡 통제가 일치 "
            f"({matched_ids}). {top_overlap.get('summary', '')}"
        )
        if len(multigap_overlaps) > 1:
            insights.append(
                f"추가 겹침 패턴 {len(multigap_overlaps) - 1}건이 더 식별되었습니다. "
                "단독 통제보다 복합 사고/심사 결함으로 확대될 수 있습니다."
            )

    if top_gaps:
        gap = top_gaps[0]
        insights.append(
            f"최우선 점검 통제: {gap['controlId']} {gap['title']}({gap.get('levelLabel', '')}). "
            f"{gap.get('controlFocus', gap.get('riskIfMissing', ''))}"
        )

    area_order = sorted(
        ((g.get("areaName", ""), g.get("controlId", "")) for g in top_gaps[:8]),
        key=lambda x: x[0],
    )
    if area_order:
        insights.append(
        "상위 확인 항목은 관리체계/기술 통제/개인정보 생명주기가 혼재되어 있으므로, "
            "영역별 담당자와 함께 교차 점검하는 것이 다음 진단에 유리합니다."
        )

    return insights[:8]


def build_executive_report(
    overall_percent: float,
    readiness_label: str,
    gap_count: int,
    status_counts: dict[str, int],
    area_readiness: dict[str, float],
    weak_categories: list[dict[str, object]],
    cascade_chains: list[dict[str, object]],
    top_gaps: list[dict[str, object]],
    recommendations: list[dict[str, str]],
    multigap_overlaps: list[dict[str, object]] | None = None,
    evaluation_bands: dict[str, object] | None = None,
) -> str:
    from .report_evaluation import REPORT_DISCLAIMER, REPORT_TITLE, classify_evaluation_bands

    none_count = int(status_counts.get("none", 0))
    partial_count = int(status_counts.get("partial", 0))
    done_count = int(status_counts.get("done", 0)) + int(status_counts.get("evidenced", 0))
    unknown_count = int(status_counts.get("unknown", 0))
    reviewed = sum(int(status_counts.get(k, 0)) for k in ("none", "partial", "done", "evidenced"))
    applicable = reviewed + unknown_count
    bands = evaluation_bands or classify_evaluation_bands(weak_categories)
    counts = dict(bands.get("counts") or {})
    strengths = list(bands.get("strengths") or [])
    weaknesses = list(bands.get("weaknesses") or []) or list(weak_categories or [])
    deferred = list(bands.get("deferred") or [])

    def band_line(item: dict[str, object]) -> str:
        statuses = dict(item.get("statusCounts") or {})
        area = str(item.get("areaName") or "").strip()
        name = str(item.get("category") or "")
        label = f"{area} / {name}" if area and area != name else name
        reviewed_n = int(item.get("reviewedCount") or item.get("count") or 0)
        total_n = int(item.get("totalCount") or item.get("count") or 0)
        none_n = int(statuses.get("none", 0))
        partial_n = int(statuses.get("partial", 0))
        if none_n or partial_n:
            return (
                f"- {label}: 미이행 {none_n} · 부분 이행 {partial_n}"
                f" (점검 {reviewed_n}/{total_n})"
            )
        return f"- {label}: 점검 {reviewed_n}/{total_n}개, 미이행·부분 이행 없음"

    strength_lines = [band_line(item) for item in strengths[:6]]
    weak_lines = [band_line(item) for item in weaknesses[:6]]
    deferred_lines = [
        f"- {item.get('areaName') or item.get('category')}: "
        f"점검 {int(item.get('reviewedCount') or 0)}/{int(item.get('totalCount') or item.get('count') or 0)}개"
        for item in deferred[:5]
    ]
    gap_lines = [
        f"- {g['controlId']} {g['title']} [{g.get('levelLabel', '')}]: "
        f"{(g.get('organicAnalysis') or g.get('problem', ''))[:120]}..."
        for g in top_gaps[:6]
    ]
    rec_lines = [f"- [{r.get('priority', 'info')}] {r['title']}: {r['detail']}" for r in recommendations[:6]]
    chain_lines = [
        f"- {c['originControlId']} → {c['targetControlId']}: {c.get('impact', c.get('connectionReason', ''))}"
        for c in cascade_chains[:5]
    ]
    overlap_lines = []
    for overlap in (multigap_overlaps or [])[:4]:
        matched = overlap.get("matchedControls") or []
        ids = ", ".join(f"{m.get('controlId')}" for m in matched[:5])
        overlap_lines.append(
            f"- [{overlap.get('matchType', '')}] {overlap.get('title')}: {ids}\n"
            f"  {str(overlap.get('summary', ''))[:200]}"
        )
    linked_lines = overlap_lines + chain_lines

    observation_lines = [
        f"- 양호 중분류: {int(counts.get('strengths', len(strengths)))}개",
        f"- 미흡 중분류: {int(counts.get('weaknesses', len(weaknesses)))}개",
        f"- 판단 보류: {int(counts.get('deferred', len(deferred)))}개",
        f"- 보조 참고 구간: {overall_percent}%({readiness_label})",
        "- 인증 배점·심사 결론이 아님",
    ]
    if deferred_lines:
        observation_lines.append("- 판단 보류 분야는 양호로 해석하지 않음")

    sections = [
        REPORT_TITLE,
        "",
        "진단 배경과 목적",
        "- 목적: 입력된 ISMS-P 통제 이행 상태를 기준으로 강점과 보완 필요 영역을 사전 파악",
        "- 산출: 우선 개선과제 및 후속 확인 대상 정리",
        "",
        "1. 점검 개요 및 범위",
        f"- 점검 대상: 적용 통제 {applicable}개",
        f"- 진행 현황: {reviewed}개 점검 완료 (미점검 {unknown_count}개)",
        "- 미점검 항목은 이번 문서에서 적합 여부를 판단하지 않음",
        f"- 확인된 미흡: {gap_count}건 (미이행 {none_count} · 부분 이행 {partial_count})",
        f"- 이행 입력: {done_count}건",
        "",
        "2. 종합 점검 결과",
        *observation_lines,
        "",
        "3. 양호하게 확인된 영역",
        *(strength_lines or ["- 양호로 확정할 중분류 없음"]),
        "",
        "4. 미흡이 집중된 영역",
        *(weak_lines or ["- 미이행·부분 이행으로 확인된 중분류 없음"]),
        "",
        "5. 핵심 지적사항",
        *(gap_lines or ["- 미이행·부분 이행으로 확인된 통제 없음"]),
        "",
        "6. 반복·연계 미흡",
        *(linked_lines or ["- 복합·연쇄 미흡 없음"]),
        "",
        "7. 우선 보완 순서",
        *(rec_lines or ["- 추가 보완 순서 없음"]),
        "",
        "8. 참고 한계",
        f"- {REPORT_DISCLAIMER}",
    ]
    return "\n".join(sections)


def build_report_sections(
    key_insights: list[str],
    executive_report: str,
) -> list[dict[str, str]]:
    sections = [{"id": "insights", "title": "핵심 인사이트", "content": "\n".join(f"- {line}" for line in key_insights)}]
    for index, block in enumerate(executive_report.split("\n\n"), start=1):
        first_line = block.strip().split("\n", 1)[0]
        if not first_line or first_line.startswith("ISMS-P"):
            continue
        title = first_line
        for prefix in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. "):
            title = title.replace(prefix, "")
        if len(title) > 40:
            title = f"분석 섹션 {index}"
        sections.append({"id": f"section-{index}", "title": title[:48], "content": block.strip()})
    return sections[:8]
