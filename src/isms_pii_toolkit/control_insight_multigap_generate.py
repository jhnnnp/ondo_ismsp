"""Evidence-first multi-gap bundle generation.

Generated bundles must carry an explicit basis and evidence lines.
Mechanical patterns without a documented relation/scenario reason are not emitted.
"""

from __future__ import annotations

from .control_graph import (
    CONTROL_CATEGORIES,
    SCENARIOS,
    find_control,
    load_manual_relations,
)
from .control_insight_category_deep import get_category_deep
from .control_insight_multigap import MultiGapBundle

BundleSource = str  # curated | graph_relation | scenario_flow | category_set


def _control_title(control_id: str) -> str:
    control = find_control(control_id)
    return str(control["title"]) if control else control_id


def _labels(control_ids: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(cid, _control_title(cid)) for cid in control_ids]


def _area_ids(control_ids: tuple[str, ...]) -> set[str]:
    return {cid.split(".", 1)[0] for cid in control_ids}


def _theme_for_controls(control_ids: tuple[str, ...], preferred: str | None = None) -> str:
    if preferred:
        return preferred
    areas = _area_ids(control_ids)
    has = lambda prefix: any(cid.startswith(prefix) for cid in control_ids)
    if (has("2.7") or has("2.9")) and (has("3.") or "3" in areas):
        return "기밀성/추적성 동시 붕괴"
    if (has("2.5") or has("2.6")) and (has("2.7") or has("2.9")):
        return "권한/기밀성/감사추적 동시 실패"
    if has("2.5") or has("2.6"):
        return "내부자/과다권한"
    if has("2.3") or has("3.3"):
        return "공급망/외주 경유 유출"
    if has("2.11") or has("3.5"):
        return "침해 후 대응 마비"
    if has("2.12") or has("3.4"):
        return "삭제해도 남는 개인정보"
    if has("3.1"):
        return "고유식별정보 전 구간 위험"
    if has("3.2"):
        return "식별/현황/보호조치 단절"
    if "1" in areas and areas == {"1"}:
        return "인증 근거 상실"
    if "1" in areas and ("2" in areas or "3" in areas):
        return "근거 없는 통제"
    if has("2.8") or has("2.10"):
        return "안전하지 않은 배포 파이프라인"
    return "통제 그래프 연쇄"


def _severity_for_size(size: int, area_ids: set[str]) -> str:
    if "3" in area_ids and size >= 3:
        return "critical"
    if size >= 4 or ("2" in area_ids and "3" in area_ids):
        return "critical"
    if size >= 3:
        return "high"
    return "medium"


def _priority_for_source(source: BundleSource, size: int) -> int:
    base = {"graph_relation": 7, "scenario_flow": 6, "category_set": 5}.get(source, 4)
    return min(base + max(0, size - 2), 9)


def _min_match_for_size(size: int) -> tuple[int, int]:
    if size <= 2:
        return 2, 2
    if size == 3:
        return 2, 2
    return max(2, size - 1), max(2, size - 2)


def _domain_context(control_ids: tuple[str, ...], scenario_id: str | None) -> str:
    if scenario_id:
        scenario = next((s for s in SCENARIOS if s.id == scenario_id), None)
        if scenario:
            return scenario.description or scenario.title
    areas = _area_ids(control_ids)
    if areas == {"1"}:
        return "ISMS-P 관리체계 수립/운영"
    if "3" in areas:
        return "개인정보 처리 전 구간"
    if "2" in areas:
        return "보호대책 운영"
    return "정보보호/개인정보보호 운영"


def _build_narrative_fields(
    *,
    title: str,
    control_ids: tuple[str, ...],
    basis: str,
    evidence: tuple[str, ...],
    scenario_id: str | None,
    flow_hint: str,
) -> dict[str, object]:
    labeled = _labels(control_ids)
    id_text = ", ".join(f"{cid} {name}" for cid, name in labeled)
    ctx = _domain_context(control_ids, scenario_id)
    evidence_text = " / ".join(evidence) if evidence else basis

    compound = (
        f"【근거】 {basis} "
        f"【연결 사유】 {evidence_text} "
        f"【맥락】 {ctx}. {flow_hint} "
        f"다음 통제({id_text})가 동시에 미점검/미이행/부분 이행이면 "
        f"단일 통제 보완만으로는 연결 업무 흐름의 보호 공백을 닫기 어렵습니다."
    )

    if _area_ids(control_ids) == {"1"}:
        operational = (
            f"운영상 {labeled[0][1]}부터 {labeled[-1][1]}까지 범위/정책/자산/점검 근거가 끊기면 "
            f"이후 2.x/3.x 기술/개인정보 통제의 선정/이행 증적을 설명하기 어렵습니다."
        )
        audit = (
            f"심사에서는 {id_text}를 한 세트로 샘플링해 범위서/정책/자산목록/자체점검표를 교차 확인합니다. "
            f"연결 사유({evidence_text})가 증적으로 이어지지 않으면 후속 영역 샘플링이 확대됩니다."
        )
        scenarios = (
            f"{ctx}에서 {control_ids[0]}/{control_ids[-1]}가 동시에 미흡해 인증 범위/자산/정책 근거가 불일치",
            f"연결 사유 '{evidence[0] if evidence else basis}'가 문서/증적에 반영되지 않은 채 부분 이행만 제출",
            f"동일 분기 내 {id_text} 개선 조치 없이 동일 유형 지적 반복",
        )
    else:
        operational = (
            f"운영 현장에서는 {labeled[0][1]}({labeled[0][0]})부터 {labeled[-1][1]}({labeled[-1][0]})까지 "
            f"같은 업무 흐름에서 연속 실패할 수 있습니다. "
            f"앞뒤 통제가 비어 있으면 탐지/차단/추적/통지 중 2개 이상이 동시에 지연됩니다."
        )
        audit = (
            f"심사에서는 {id_text}를 한 세트로 샘플링해 정책/설정/운영기록/점검표를 교차 확인합니다. "
            f"근거({evidence_text})에 대응하는 증적이 빠지면 연계성 부족 결함으로 확대될 수 있습니다."
        )
        scenarios = (
            f"{ctx}에서 {control_ids[0]}/{control_ids[-1]} 구간이 동시에 미흡해 보호/추적/통지 중 일부가 무력화",
            f"연결 사유 '{evidence[0] if evidence else basis}'가 운영 절차/점검표에 반영되지 않음",
            f"동일 분기 내 {id_text} CAR 없이 동일 유형 경고 반복",
        )

    remediation = (
        f"{control_ids[0]}~{control_ids[-1]}를 하나의 증적 패키지(정책/설정/운영기록/점검표)로 묶어 분기 점검",
        f"연결 사유를 문서에 명시: {evidence[0] if evidence else basis}",
        "미충족 체크리스트 항목을 통제별 CAR(시정조치)로 등록하고 담당/일정을 연결",
    )

    return {
        "summary": (
            f"{title}: {len(control_ids)}개 통제가 동시에 약하면 "
            f"'{basis}' 근거로 복합 리스크가 커집니다."
        ),
        "compound_analysis": compound,
        "operational_impact": operational,
        "audit_impact": audit,
        "incident_scenarios": scenarios,
        "remediation_path": remediation,
    }


def _make_bundle(
    *,
    bundle_id: str,
    title: str,
    theme: str,
    control_ids: tuple[str, ...],
    source: BundleSource,
    basis: str,
    evidence: tuple[str, ...],
    scenario_id: str | None,
    flow_hint: str,
) -> MultiGapBundle:
    if len(control_ids) < 2:
        raise ValueError("multigap bundle requires at least 2 controls")
    if not basis.strip():
        raise ValueError(f"bundle {bundle_id} requires basis")
    if not evidence:
        raise ValueError(f"bundle {bundle_id} requires evidence")

    unique = tuple(dict.fromkeys(control_ids))
    min_match, partial_min = _min_match_for_size(len(unique))
    area_ids = _area_ids(unique)
    fields = _build_narrative_fields(
        title=title,
        control_ids=unique,
        basis=basis,
        evidence=evidence,
        scenario_id=scenario_id,
        flow_hint=flow_hint,
    )
    return MultiGapBundle(
        id=bundle_id,
        title=title,
        theme=_theme_for_controls(unique, theme),
        required_controls=unique,
        min_match=min_match,
        partial_min=partial_min,
        priority=_priority_for_source(source, len(unique)),
        severity=_severity_for_size(len(unique), area_ids),
        summary=str(fields["summary"]),
        compound_analysis=str(fields["compound_analysis"]),
        operational_impact=str(fields["operational_impact"]),
        audit_impact=str(fields["audit_impact"]),
        incident_scenarios=tuple(str(s) for s in fields["incident_scenarios"]),  # type: ignore[arg-type]
        remediation_path=tuple(str(r) for r in fields["remediation_path"]),  # type: ignore[arg-type]
        related_scenario_ids=(scenario_id,) if scenario_id else (),
        source=source,
        basis=basis,
        evidence=evidence,
    )


def _relation_bundles() -> list[MultiGapBundle]:
    """Bundles grounded only in evidenced relation reasons."""
    bundles: list[MultiGapBundle] = []

    for source_id, targets in load_manual_relations().items():
        target_ids = tuple(target for target, _ in targets)
        reasons = tuple(reason for _, reason in targets)
        group = (source_id, *target_ids)
        if len(group) < 2:
            continue
        basis = f"관계 증거 그래프: {source_id} → {', '.join(target_ids)}"
        flow = (
            f"{_control_title(source_id)}({source_id})을(를) 중심으로 "
            f"문서화된 연결 사유가 있는 인접 통제를 함께 점검합니다. "
        )
        bundles.append(
            _make_bundle(
                bundle_id=f"rel-{source_id.replace('.', '-')}-hub",
                title=f"{_control_title(source_id)} 중심 연쇄 겹침",
                theme=_theme_for_controls(group),
                control_ids=group,
                source="graph_relation",
                basis=basis,
                evidence=reasons,
                scenario_id=None,
                flow_hint=flow,
            )
        )

        for target_id, reason in targets:
            pair = (source_id, target_id)
            bundles.append(
                _make_bundle(
                    bundle_id=f"rel-{source_id.replace('.', '-')}-{target_id.replace('.', '-')}",
                    title=f"{source_id}→{target_id} 연결 겹침",
                    theme=_theme_for_controls(pair),
                    control_ids=pair,
                    source="graph_relation",
                    basis=f"관계 증거 연결: {source_id}↔{target_id}",
                    evidence=(reason,),
                    scenario_id=None,
                    flow_hint=f"{reason} ",
                )
            )
    return bundles


def _scenario_flow_bundles() -> list[MultiGapBundle]:
    """Scenario path windows — evidence = scenario adjacency description."""
    bundles: list[MultiGapBundle] = []
    for scenario in SCENARIOS:
        ids = list(scenario.control_ids)
        if len(ids) < 2:
            continue
        sid = scenario.id
        desc = scenario.description[:160] if scenario.description else scenario.title

        if len(ids) == 2:
            pair = (ids[0], ids[1])
            bundles.append(
                _make_bundle(
                    bundle_id=f"sc-{sid}-pair-0",
                    title=f"{scenario.title[:28]}, {pair[0]}→{pair[1]}",
                    theme=_theme_for_controls(pair),
                    control_ids=pair,
                    source="scenario_flow",
                    basis=f"시나리오 경로 인접: {sid}",
                    evidence=(f"시나리오 '{scenario.title}' 인접 통제", desc),
                    scenario_id=sid,
                    flow_hint=f"'{scenario.title}' 업무 흐름에서 연속 검토되는 통제입니다. ",
                )
            )
            continue

        # Prefer 3-control windows (stronger compound signal than every adjacent pair).
        for index in range(len(ids) - 2):
            window = tuple(ids[index : index + 3])
            evidence = (
                f"시나리오 '{scenario.title}' {index + 1}~{index + 3}번 연속 구간",
                desc,
            )
            bundles.append(
                _make_bundle(
                    bundle_id=f"sc-{sid}-w3-{index}",
                    title=f"{scenario.title[:24]}, {window[0]}~{window[-1]}",
                    theme=_theme_for_controls(window),
                    control_ids=window,
                    source="scenario_flow",
                    basis=f"시나리오 경로 3연속: {sid}",
                    evidence=evidence,
                    scenario_id=sid,
                    flow_hint=(
                        f"'{scenario.title}'에서 {window[0]}→{window[-1]} 구간이 "
                        f"한 줄로 연결됩니다. "
                    ),
                )
            )
    return bundles


def _category_set_bundles() -> list[MultiGapBundle]:
    """Category-wide sets only when category_deep compoundHint exists."""
    bundles: list[MultiGapBundle] = []
    for category in CONTROL_CATEGORIES:
        deep = get_category_deep(category.category_id)
        if not deep:
            continue
        hint = str(deep.get("compoundHint") or "").strip()
        focus = str(deep.get("focus") or category.category_name).strip()
        if not hint:
            continue
        control_ids = tuple(
            f"{category.category_id}.{index + 1}" for index in range(len(category.control_titles))
        )
        if len(control_ids) < 2:
            continue
        # Prefer a compact core of first 3 (or all if fewer) — still evidence-backed by deep hint
        core = control_ids[: min(3, len(control_ids))]
        evidence = (
            f"분류 심층 힌트({category.category_id}): {hint}",
            f"분류 초점: {focus}",
        )
        bundles.append(
            _make_bundle(
                bundle_id=f"cat-{category.category_id.replace('.', '-')}-core",
                title=f"{category.category_name} 핵심 통제 동시 미흡",
                theme=_theme_for_controls(core, focus[:32] if focus else None),
                control_ids=core,
                source="category_set",
                basis=f"분류 {category.category_id} 심층 compoundHint",
                evidence=evidence,
                scenario_id=None,
                flow_hint=f"'{category.category_name}' 분류를 한 영역으로 묶어 검토합니다. ",
            )
        )
    return bundles


def build_generated_bundles() -> tuple[MultiGapBundle, ...]:
    merged: list[MultiGapBundle] = []
    seen: set[frozenset[str]] = set()

    def add(bundle: MultiGapBundle) -> None:
        key = frozenset(bundle.required_controls)
        if key in seen:
            return
        if not bundle.basis or not bundle.evidence:
            return
        seen.add(key)
        merged.append(bundle)

    for builder in (_relation_bundles, _scenario_flow_bundles, _category_set_bundles):
        for bundle in builder():
            add(bundle)

    return tuple(merged)


def merge_multigap_bundles(
    curated: tuple[MultiGapBundle, ...],
    generated: tuple[MultiGapBundle, ...],
    limit: int = 100,
) -> tuple[MultiGapBundle, ...]:
    """Prefer curated, then graph relations, scenario flows, category sets."""
    merged: list[MultiGapBundle] = []
    seen: set[frozenset[str]] = set()

    def add(bundle: MultiGapBundle) -> bool:
        key = frozenset(bundle.required_controls)
        if key in seen:
            return False
        seen.add(key)
        merged.append(bundle)
        return True

    for bundle in curated:
        add(bundle)

    by_source = {
        "graph_relation": [b for b in generated if b.source == "graph_relation"],
        "category_set": [b for b in generated if b.source == "category_set"],
        "scenario_flow": [b for b in generated if b.source == "scenario_flow"],
    }
    for source in ("graph_relation", "category_set", "scenario_flow"):
        for bundle in by_source[source]:
            if len(merged) >= limit:
                return tuple(merged)
            add(bundle)

    return tuple(merged)
