from __future__ import annotations

from typing import Literal

from .control_graph import (
    evidence_label_for_edge,
    find_control,
    grounding_level_for_edge,
    grounding_statement_for_edge,
    load_manual_relations,
)
from .control_insight_categories import CATEGORY_CHECKLIST_BANK
from .control_insight_category_deep import get_category_deep
from .control_insight_multigap import multigap_insights_for_control
from .control_insight_overrides import CONTROL_PROFILE_OVERRIDES
from .control_insight_verbalize import (
    build_gap_narrative,
    enrich_checklist_row,
)

from .control_insight_profiles import CONTROL_PROFILES as _GENERATED_PROFILES

AssessmentLevel = Literal["unknown", "none", "partial", "done", "evidenced"]

LEVEL_STATUS_LABEL: dict[str, str] = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
}

ChecklistDetail = dict[str, object]
GapInsights = dict[str, object]

CONTROL_PROFILES: dict[str, dict[str, object]] = {
    **_GENERATED_PROFILES,
    **CONTROL_PROFILE_OVERRIDES,
}

CASCADE_IMPACT_VARIANTS: dict[str, tuple[str, ...]] = {
    "downstream_weak": (
        "{source} 미흡으로 {target}({target_title})의 실질적 보호 수준이 함께 낮아집니다.",
        "{source} 공백은 {target}({target_title}) 통제 효과를 약화시킬 수 있습니다.",
        "{source} 결함이 남으면 {target}({target_title})만 이행해도 전체 보호 체계가 불완전해 보입니다.",
    ),
    "downstream_latent": (
        "{source} 미흡 시 {target}({target_title})은 이행 중이나 상위 통제 공백으로 운영 지속성이 심사에서 의심될 수 있습니다.",
        "{target}({target_title})은 현재 이행 중이나 {source} 기반이 약하면 '형식적 이행'으로 지적될 수 있습니다.",
    ),
    "upstream_dependency": (
        "{target}({target_title})은 {source}({source_title})에 의존합니다. 상위 통제 부족 시 연쇄 결함으로 확대될 수 있습니다.",
        "{source}({source_title}) 미흡은 {target}({target_title}) 심사에서 근본 원인 질의로 이어질 수 있습니다.",
    ),
}


def _pick_cascade_impact(template_key: str, seed: str, **kwargs: str) -> str:
    variants = CASCADE_IMPACT_VARIANTS[template_key]
    index = sum(ord(ch) for ch in seed) % len(variants)
    return variants[index].format(**kwargs)


def _cascade_explanation(
    *,
    source: dict[str, object],
    target: dict[str, object],
    source_level: str,
    target_level: str,
    relation_reason: str,
    evidence_label: str,
    grounding_note: str,
) -> dict[str, object]:
    source_id = str(source["id"])
    source_title = str(source["title"])
    source_category = str(source.get("categoryName") or "선행 통제")
    target_id = str(target["id"])
    target_title = str(target["title"])
    target_category = str(target.get("categoryName") or "후속 통제")
    source_status = LEVEL_STATUS_LABEL.get(source_level, source_level)
    target_status = LEVEL_STATUS_LABEL.get(target_level, "이행")
    relation_scope = (
        f"두 통제는 같은 ‘{source_category}’ 업무 흐름에서 선행 판단과 후속 실행으로 이어집니다."
        if source_category == target_category
        else f"‘{source_category}’의 판단 결과가 ‘{target_category}’ 통제를 설계·운영하는 입력으로 사용됩니다."
    )
    logic_steps = [
        f"{source_id} {source_title}에서 대상·범위·우선순위 또는 운영 기준을 결정합니다.",
        relation_reason,
        relation_scope,
        f"현재 선행 통제가 ‘{source_status}’이므로 {target_id} {target_title}의 적용 범위와 판단 근거가 완전하게 이어졌는지 별도 확인이 필요합니다.",
    ]
    evidence_to_check = [
        f"{source_id} {source_title}: 기준 문서, 검토·승인 기록, 최근 변경 이력",
        f"{target_id} {target_title}: 설정값 또는 운영 절차, 실행·점검 기록, 예외 처리 내역",
        "두 통제의 대상·책임자·시점이 일치하는지 보여주는 매핑표 또는 추적 기록",
    ]
    operational_impact = (
        f"{source_title}의 기준이 누락되거나 일부만 승인되면 {target_title}의 대상 선정과 적용 우선순위가 달라져, "
        "일부 시스템·계정·업무가 통제 범위에서 빠지거나 담당자별 운영 결과가 달라질 수 있습니다."
    )
    audit_impact = (
        f"심사에서는 {source_id}의 결정 근거와 {target_id}의 실행 기록을 연결해 표본을 확인합니다. "
        f"현재 대상 통제 상태가 ‘{target_status}’이더라도 두 기록의 범위·책임자·시점이 맞지 않으면 형식적 이행, "
        f"통제 설계 미흡 또는 증적 추적성 부족으로 추가 소명을 요구받을 수 있습니다. 근거 유형: {evidence_label}."
    )
    return {
        "logicSteps": logic_steps,
        "evidenceToCheck": evidence_to_check,
        "operationalImpact": operational_impact,
        "auditImpact": audit_impact,
        "groundingNote": grounding_note,
    }


def _level_assessment_text(level: str, base: str) -> str:
    label = LEVEL_STATUS_LABEL.get(level, "미흡")
    prefixes = {
        "unknown": f"【{label}】아직 점검/판단이 이뤄지지 않았습니다. ",
        "none": f"【{label}】요구 통제가 사실상 작동하지 않는 상태로 보입니다. ",
        "partial": f"【{label}】일부만 이행되어 운영/증적 연속성이 부족합니다. ",
    }
    return prefixes.get(level, "") + base


def _category_bank_item(control_id: str, category_id: str) -> ChecklistDetail | None:
    bank = CATEGORY_CHECKLIST_BANK.get(category_id, [])
    if not bank:
        return None
    index = int(control_id.rsplit(".", 1)[-1]) - 1
    return bank[min(index, len(bank) - 1)]


def _resolve_checklist(control_id: str, title: str, category_id: str) -> list[ChecklistDetail]:
    profile = CONTROL_PROFILES.get(control_id, {})
    items: list[ChecklistDetail] = list(profile.get("checklist", []))  # type: ignore[arg-type]

    bank_item = _category_bank_item(control_id, category_id)
    if bank_item and not any(str(item.get("item")) == str(bank_item.get("item")) for item in items):
        items.append(bank_item)

    fillers = [
        {
            "item": f"'{title}' 이행 상태를 정기 점검하고 개선 조치를 기록하는가",
            "operationalRisk": f"{title} 점검 없이는 미이행 상태가 방치되어 사고 시 책임 입증이 어렵습니다.",
            "auditRisk": f"{control_id} 운영 지속성/증적 충분성 부족 결함으로 이어질 수 있습니다.",
            "relatedControls": [],
            "remediation": f"{title} 자체 점검표와 시정조치(CAR) 이력을 분기별로 관리합니다.",
        },
        {
            "item": f"'{title}' 관련 교육/담당자 역할이 정의되어 있는가",
            "operationalRisk": f"담당자 불명확 시 {title} 관련 조치가 지연되거나 누락됩니다.",
            "auditRisk": "인적 보안/조직 통제와 연계 질의를 받을 수 있습니다.",
            "relatedControls": ["2.1.2", "2.2.4"],
            "remediation": f"{title} 담당자/대행자/교육 이수 기록을 유지합니다.",
        },
        {
            "item": f"'{title}' 요구사항이 실제 시스템 설정/로그/운영 화면에서 확인 가능한가",
            "operationalRisk": f"문서만 있고 현장에서 확인되지 않으면 {title} 통제가 형식적으로만 남습니다.",
            "auditRisk": "심사 샘플링 시 설정값/운영기록 대조에서 결함이 확인될 수 있습니다.",
            "relatedControls": ["1.4.2"],
            "remediation": f"{title} 이행 증적(설정 캡처/로그/점검표)을 통제별 폴더로 정리합니다.",
        },
    ]
    for filler in fillers:
        if len(items) >= 4:
            break
        if not any(str(item.get("item")) == str(filler["item"]) for item in items):
            items.append(filler)

    if not items:
        items.append(
            {
                "item": f"'{title}' 요구사항이 정책/시스템/운영에 반영되어 있는가",
                "operationalRisk": f"{title} 미이행 시 보호 공백이 발생합니다.",
                "auditRisk": f"심사에서 {control_id} 결함 가능성이 있습니다.",
                "relatedControls": [],
                "remediation": "정책/설정/운영 증적을 한 세트로 준비합니다.",
            }
        )

    return items[:6]


def _audit_question(item: str, control_id: str, title: str) -> str:
    return (
        f"심사관이 '{title}'({control_id}) 관련으로 "
        f"'{item}' 이행 여부와 최근 점검/승인/운영 기록을 요청할 수 있습니다."
    )


def _immediate_actions(checklist_breakdown: list[dict[str, object]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for row in checklist_breakdown:
        remediation = str(row.get("remediation", "")).strip()
        if remediation and remediation not in seen:
            seen.add(remediation)
            actions.append(remediation)
        if len(actions) >= 4:
            break
    return actions


def _is_template_scenario(text: str) -> bool:
    markers = (
        "관련 업무에서",
        "연쇄 지적로",
        "일관되게 제시하기 어렵습니다",
        "운영 일관성이 깨집니다",
        "심사원이 ",
        " 샘플을 요청했을 때",
    )
    return any(marker in text for marker in markers)


def _resolve_scenarios(control_id: str, title: str, category_id: str, risk_if_missing: str) -> list[str]:
    profile = CONTROL_PROFILES.get(control_id, {})
    scenarios: list[str] = list(profile.get("scenarios", []))  # type: ignore[arg-type]

    if scenarios and sum(1 for s in scenarios if _is_template_scenario(str(s))) >= 2:
        scenarios = []

    deep = get_category_deep(category_id)
    if deep:
        if not scenarios:
            scenarios = list(deep.get("scenarios", []))  # type: ignore[arg-type]
        else:
            for item in deep.get("scenarios", []):  # type: ignore[union-attr]
                if len(scenarios) >= 5:
                    break
                if str(item) not in scenarios:
                    scenarios.append(str(item))

    if not scenarios:
        scenarios = [
            f"{title}({control_id}) 통제가 미흡하면 {risk_if_missing}",
            f"심사 시 {control_id}에 대해 정책/설정/운영기록 샘플을 요구받을 때 설명이 어려워질 수 있습니다.",
            f"인접 통제와 함께 검토될 때 {category_id} 영역 전체 준비도가 낮게 평가될 수 있습니다.",
        ]
    if len(scenarios) < 3:
        scenarios.append(
            f"{cat_name_fallback(category_id)} 관점에서 {title}({control_id}) 미흡은 연관 통제 심사에서 추가 질의로 이어질 수 있습니다."
        )
    if len(scenarios) < 3:
        scenarios.append(f"방치 시 {risk_if_missing}")
    if deep and deep.get("compoundHint"):
        hint = str(deep["compoundHint"])
        if hint not in scenarios:
            scenarios.append(hint)
    return scenarios[:5]


def cat_name_fallback(category_id: str) -> str:
    names = {
        "1.1": "관리체계 기반",
        "1.2": "위험관리",
        "1.3": "관리체계 운영",
        "1.4": "점검/개선",
        "2.1": "정책/조직/자산",
        "2.2": "인적보안",
        "2.3": "외부자보안",
        "2.4": "물리보안",
        "2.5": "인증/권한",
        "2.6": "접근통제",
        "2.7": "암호화",
        "2.8": "개발보안",
        "2.9": "운영관리",
        "2.10": "서비스보안",
        "2.11": "사고대응",
        "2.12": "재해복구",
        "3.1": "수집단계",
        "3.2": "보유/이용",
        "3.3": "제공/위탁",
        "3.4": "파기",
        "3.5": "권리보장",
    }
    return names.get(category_id, "해당 영역")


def build_checklist_breakdown(
    control_id: str,
    title: str,
    category_id: str,
    level: str,
) -> list[dict[str, object]]:
    from .control_problem_engine import CHECK_KEYS

    items: list[dict[str, object]] = []
    for index, detail in enumerate(_resolve_checklist(control_id, title, category_id)):
        item_text = str(detail["item"])
        check_key = CHECK_KEYS[index] if index < len(CHECK_KEYS) else ""
        row = {
            "item": item_text,
            "statusNote": _level_assessment_text(level, str(detail["operationalRisk"])),
            "operationalRisk": detail["operationalRisk"],
            "auditRisk": detail["auditRisk"],
            "auditQuestion": _audit_question(item_text, control_id, title),
            "relatedControls": detail["relatedControls"],
            "remediation": detail["remediation"],
            "checkKey": check_key,
            "checklistItemId": str(index + 1),
            "unmet": True,
            "groundingNote": "",
        }
        items.append(enrich_checklist_row(row, control_id, title, category_id, level))
    return items


def build_cascade_risks(
    control_id: str,
    title: str,
    level: str,
    assessments: dict[str, str],
) -> list[dict[str, object]]:
    if level not in {"unknown", "none", "partial"}:
        return []

    cascades: list[dict[str, object]] = []
    seen: set[str] = set()
    relations = load_manual_relations()

    for target_id, reason in relations.get(control_id, ()):
        if target_id in seen:
            continue
        seen.add(target_id)
        target = find_control(target_id)
        if target is None:
            continue
        target_level = assessments.get(target_id, "unknown")
        template_key = "downstream_weak" if target_level in {"unknown", "none", "partial"} else "downstream_latent"
        impact = _pick_cascade_impact(
            template_key,
            f"{control_id}:{target_id}",
            source=control_id,
            target=target_id,
            target_title=str(target["title"]),
            source_title=title,
        )
        evidence_label = evidence_label_for_edge(control_id, target_id)
        grounding_note = grounding_statement_for_edge(control_id, target_id)
        explanation = _cascade_explanation(
            source={"id": control_id, "title": title, **find_control(control_id)},
            target=target,
            source_level=level,
            target_level=target_level,
            relation_reason=reason,
            evidence_label=evidence_label,
            grounding_note=grounding_note,
        )
        cascades.append(
            {
                "direction": "forward",
                "sourceControlId": control_id,
                "targetControlId": target_id,
                "targetTitle": target["title"],
                "targetLevel": target_level,
                "connectionReason": f"{reason} (근거: {evidence_label})",
                "impact": impact,
                "evidenceLabel": evidence_label,
                "groundingLevel": grounding_level_for_edge(control_id, target_id),
                "groundingNote": grounding_note,
                "severity": "critical" if target_level in {"none", "unknown"} else "high",
                **explanation,
            }
        )

    for source_id, targets in relations.items():
        for target_id, reason in targets:
            if target_id != control_id or source_id in seen:
                continue
            seen.add(source_id)
            source = find_control(source_id)
            if source is None:
                continue
            source_level = assessments.get(source_id, "unknown")
            if source_level in {"done", "evidenced"}:
                continue
            impact = _pick_cascade_impact(
                "upstream_dependency",
                f"{source_id}:{control_id}",
                source=source_id,
                source_title=str(source["title"]),
                target=control_id,
                target_title=title,
            )
            evidence_label = evidence_label_for_edge(source_id, control_id)
            grounding_note = grounding_statement_for_edge(source_id, control_id)
            explanation = _cascade_explanation(
                source=source,
                target={"id": control_id, "title": title, **find_control(control_id)},
                source_level=source_level,
                target_level=level,
                relation_reason=reason,
                evidence_label=evidence_label,
                grounding_note=grounding_note,
            )
            cascades.append(
                {
                    "direction": "reverse",
                    "sourceControlId": source_id,
                    "targetControlId": control_id,
                    "targetTitle": title,
                    "targetLevel": level,
                    "connectionReason": f"{reason} (근거: {evidence_label})",
                    "impact": impact,
                    "evidenceLabel": evidence_label,
                    "groundingLevel": grounding_level_for_edge(source_id, control_id),
                    "groundingNote": grounding_note,
                    "severity": "high",
                    **explanation,
                }
            )

    severity_order = {"critical": 0, "high": 1, "medium": 2}
    cascades.sort(key=lambda item: severity_order.get(str(item["severity"]), 9))
    return cascades[:8]


def build_detailed_summary(
    control_id: str,
    title: str,
    category_name: str,
    level: str,
    risk_if_missing: str,
    checklist_breakdown: list[dict[str, object]],
    consequence_scenarios: list[str],
    cascade_risks: list[dict[str, object]],
) -> str:
    label = LEVEL_STATUS_LABEL.get(level, "미흡")
    lines = [
        f"### {control_id} {title} — {label} 상태 심층 분석",
        "",
        f"**영역:** {category_name}",
        "",
        f"**핵심 리스크:** {risk_if_missing}",
        "",
        "**체크리스트별 점검 결과:**",
    ]
    for index, item in enumerate(checklist_breakdown, start=1):
        lines.append(f"{index}. {item['item']}")
        lines.append(f"   - 운영 리스크: {item['operationalRisk']}")
        lines.append(f"   - 심사 리스크: {item['auditRisk']}")
        if item.get("auditQuestion"):
            lines.append(f"   - 예상 질의: {item['auditQuestion']}")
        related = item.get("relatedControls") or []
        if related:
            lines.append(f"   - 연관 통제: {', '.join(str(r) for r in related)}")
        lines.append(f"   - 보완: {item['remediation']}")
        lines.append("")

    lines.append("**구체적 사고/결함 시나리오:**")
    for scenario in consequence_scenarios:
        lines.append(f"- {scenario}")
    lines.append("")

    if cascade_risks:
        lines.append("**연쇄 영향 (유기적 연결):**")
        for cascade in cascade_risks[:5]:
            lines.append(f"- → {cascade['targetControlId']} {cascade.get('targetTitle', '')}: {cascade['impact']}")
        lines.append("")

    return "\n".join(lines)


def _append_multigap_to_summary(
    detailed_summary: str,
    overlapping_risks: list[dict[str, object]],
) -> str:
    if not overlapping_risks:
        return detailed_summary
    lines = [detailed_summary, "", "**다중 갭 겹침 (복합 리스크):**"]
    for item in overlapping_risks:
        co_gaps = item.get("coGapControls") or []
        co_text = ", ".join(
            f"{g.get('controlId')} {g.get('title')}({g.get('levelLabel')})" for g in co_gaps[:4]
        )
        lines.append(f"- {item['title']} [{item.get('matchType', '')}]: {item.get('summary', '')}")
        if co_text:
            lines.append(f"  함께 미흡한 통제: {co_text}")
    lines.append("")
    return "\n".join(lines)


def build_gap_insights(
    control: dict[str, object],
    level: str,
    assessments: dict[str, str],
    multigap_overlaps: list[dict[str, object]] | None = None,
    control_checks: dict[str, bool] | None = None,
    domain_checks: dict[str, bool] | None = None,
    precomputed_findings: list[dict[str, object]] | None = None,
) -> GapInsights:
    from .causal_retrieve import CHECK_KEY_LABELS, CHECK_KEYS, findings_for_control
    from .control_problem_engine import _unchecked_check_keys

    control_id = str(control["id"])
    title = str(control["title"])
    category_id = str(control["categoryId"])
    category_name = str(control["categoryName"])
    area_name = str(control["areaName"])
    risk_if_missing = str(control.get("riskIfMissing", ""))
    level_label = LEVEL_STATUS_LABEL.get(level, "미흡")

    profile = CONTROL_PROFILES.get(control_id, {})
    deep = get_category_deep(category_id)
    default_focus = f"{title} 통제의 지속적 이행과 증적 확보"
    if deep and deep.get("focus") and control_id not in CONTROL_PROFILE_OVERRIDES:
        default_focus = str(deep["focus"])
    focus = str(profile.get("focus", default_focus))

    checklist_breakdown = build_checklist_breakdown(control_id, title, category_id, level)
    if domain_checks is not None:
        for row in checklist_breakdown:
            item_id = str(row.get("checklistItemId") or "")
            unmet = domain_checks.get(item_id, False) is not True
            row["unmet"] = unmet
            row["groundingNote"] = (
                f"도메인 체크 {item_id} 미충족 (direct_checklist)"
                if unmet
                else f"도메인 체크 {item_id} 충족"
            )
            if not unmet:
                row["statusNote"] = f"도메인 체크 {item_id} 충족으로 본다."
    else:
        unchecked_keys = set(_unchecked_check_keys(level, control_checks))
        for row in checklist_breakdown:
            key = str(row.get("checkKey") or "")
            unmet = bool(key and key in unchecked_keys)
            row["unmet"] = unmet
            if key:
                label = CHECK_KEY_LABELS.get(key, key)
                row["groundingNote"] = (
                    f"성숙도「{label}」미충족 → 이 도메인 항목을 미흡으로 본다 (maturity_proxy)"
                    if unmet
                    else f"성숙도「{label}」충족 → 이 항목은 현재 근거에서 제외"
                )
                if not unmet:
                    row["statusNote"] = f"현재 성숙도 기준으로 충족으로 본다. ({label})"

    checklist_breakdown.sort(key=lambda row: (0 if row.get("unmet") else 1, str(row.get("checklistItemId") or "")))

    consequence_scenarios = [
        _level_assessment_text(level, scenario)
        for scenario in _resolve_scenarios(control_id, title, category_id, risk_if_missing)
    ]
    cascade_risks = build_cascade_risks(control_id, title, level, assessments)
    immediate_actions = _immediate_actions([row for row in checklist_breakdown if row.get("unmet")] or checklist_breakdown)

    overlapping_risks = multigap_insights_for_control(control_id, multigap_overlaps or [])
    if precomputed_findings is not None:
        causal_findings = list(precomputed_findings)
    else:
        causal_findings = findings_for_control(
            control_id, level, control_checks, assessments, domain_checks=domain_checks
        )
    causal_basis = [str(item.get("causalStatement") or "") for item in causal_findings if item.get("causalStatement")]

    organic_analysis = (
        f"{control_id} {title}이(가) {level_label} 상태이므로, "
        f"{focus}. "
    )
    if causal_basis:
        organic_analysis += "체크 근거: " + " / ".join(causal_basis[:2]) + " "
    if cascade_risks:
        chain = " → ".join(f"{item['targetControlId']}" for item in cascade_risks[:4])
        labels = " / ".join(
            dict.fromkeys(
                str(item.get("evidenceLabel") or "수동") for item in cascade_risks[:4] if item.get("evidenceLabel")
            )
        )
        organic_analysis += f"연결된 후속 통제({chain})까지 보호 체계가 약화될 수 있습니다. "
        if labels:
            organic_analysis += f"(근거: {labels}) "
    if overlapping_risks:
        bundle_titles = ", ".join(str(item["title"]) for item in overlapping_risks[:2])
        organic_analysis += (
            f"다른 미흡 통제와 겹치는 복합 리스크 패턴({bundle_titles})에 포함되어, "
            f"단독 결함보다 사고/심사 영향이 확대될 수 있습니다. "
        )
    organic_analysis += consequence_scenarios[0] if consequence_scenarios else risk_if_missing

    narrative_report = build_gap_narrative(
        control_id,
        title,
        category_name,
        area_name,
        level,
        level_label,
        focus,
        risk_if_missing,
        organic_analysis,
        checklist_breakdown,
        consequence_scenarios,
        cascade_risks,
        immediate_actions,
    )
    if causal_basis:
        narrative_report += "\n\n[체크 근거]\n" + "\n".join(f"- {line}" for line in causal_basis[:6])
        if domain_checks is not None:
            unmet_ids = [
                str(row.get("checklistItemId") or "")
                for row in checklist_breakdown
                if row.get("unmet")
            ]
            if unmet_ids:
                narrative_report += f"\n- 미충족 도메인 체크: {', '.join(unmet_ids)} (mappingMode=direct_checklist)"
        else:
            unchecked_keys = set(_unchecked_check_keys(level, control_checks))
            unmet_keys = [key for key in CHECK_KEYS if key in unchecked_keys]
            if unmet_keys:
                labels = ", ".join(CHECK_KEY_LABELS.get(key, key) for key in unmet_keys)
                narrative_report += f"\n- 미충족 성숙도: {labels} (mappingMode=maturity_proxy)"

    detailed_summary = build_detailed_summary(
        control_id,
        title,
        category_name,
        level,
        risk_if_missing,
        checklist_breakdown,
        consequence_scenarios,
        cascade_risks,
    )
    detailed_summary = _append_multigap_to_summary(detailed_summary, overlapping_risks)

    if overlapping_risks:
        narrative_report += "\n\n[다중 갭 겹침]\n"
        for item in overlapping_risks:
            narrative_report += f"- {item['title']}: {item.get('summary', '')}\n"
            co_gaps = item.get("coGapControls") or []
            if co_gaps:
                co_text = ", ".join(f"{g.get('controlId')}" for g in co_gaps[:5])
                narrative_report += f"  동시 미흡 통제: {co_text}\n"

    return {
        "checklistBreakdown": checklist_breakdown,
        "consequenceScenarios": consequence_scenarios,
        "cascadeRisks": cascade_risks,
        "detailedSummary": detailed_summary,
        "organicAnalysis": organic_analysis,
        "controlFocus": focus,
        "immediateActions": immediate_actions,
        "narrativeReport": narrative_report,
        "overlappingRisks": overlapping_risks,
        "causalBasis": causal_basis,
        "causalFindings": causal_findings,
    }
