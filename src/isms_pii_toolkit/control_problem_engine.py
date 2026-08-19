"""JSON KB 기반 체크리스트/복합 문제 합성 엔진."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .control_graph import (
    SCENARIOS,
    evidence_label_for_edge,
    find_control,
    find_scenario,
    grounding_level_for_edge,
    grounding_statement_for_edge,
    load_manual_relations,
    relation_evidence_for,
)
from .organization_profile import OrganizationContext
from .profile_prioritization import bundle_priority_delta, priority_delta

WEAK_LEVELS = frozenset({"unknown", "none", "partial"})
CHECK_KEYS = ("reviewed", "policy", "implemented", "evidence")
CHECK_KEY_LABELS = {
    "reviewed": "검토",
    "policy": "정책/절차",
    "implemented": "구현/운영",
    "evidence": "증적",
}
LEVEL_LABELS = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
    "done": "이행",
    "evidenced": "증적 확보",
}
DATA_ROOT = Path(__file__).resolve().parent / "data" / "problem_kb"


@lru_cache(maxsize=1)
def _load_index() -> dict[str, object]:
    return json.loads((DATA_ROOT / "index.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_compounds() -> list[dict[str, object]]:
    return json.loads((DATA_ROOT / "compounds.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=128)
def _load_control(control_id: str) -> dict[str, object] | None:
    file_name = control_id.replace(".", "_") + ".json"
    path = DATA_ROOT / "controls" / file_name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _compound_index() -> dict[str, dict[str, object]]:
    return {str(item["compoundKey"]): item for item in _load_compounds()}


def _severity_for_level(level: str) -> str:
    if level == "none":
        return "critical"
    if level == "unknown":
        return "high"
    return "medium"


def _unchecked_check_keys(level: str, checks: dict[str, bool] | None) -> list[str]:
    if checks:
        return [key for key in CHECK_KEYS if not checks.get(key, False)]
    if level == "unknown":
        return list(CHECK_KEYS)
    if level == "none":
        return list(CHECK_KEYS)
    if level == "partial":
        return ["implemented", "evidence"]
    return []


def _annotate_checklist_item(item: dict[str, object], index: int) -> dict[str, object]:
    """KB 항목에 checkKey를 명시. 없으면 성숙도 프록시 키를 부여(조용한 인덱스 매핑 금지)."""
    annotated = dict(item)
    raw_key = str(annotated.get("checkKey") or "").strip()
    if raw_key in CHECK_KEYS:
        annotated["checkKey"] = raw_key
    elif index < len(CHECK_KEYS):
        annotated["checkKey"] = CHECK_KEYS[index]
    else:
        annotated["checkKey"] = ""
    annotated["itemId"] = str(annotated.get("itemId") or str(index + 1))
    annotated["item"] = str(annotated.get("item") or "")
    return annotated


def _checklist_by_check_key(record: dict[str, object]) -> dict[str, dict[str, object]]:
    """checkKey → checklist item. 동일 키가 여러 개면 첫 항목만 사용."""
    by_key: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(record.get("checklistItems", [])):
        item = _annotate_checklist_item(dict(raw), index)
        key = str(item.get("checkKey") or "")
        if key and key not in by_key:
            by_key[key] = item
    return by_key


def _resolve_domain_unchecked_items(
    record: dict[str, object],
    domain_checks: dict[str, bool],
) -> list[dict[str, object]]:
    """도메인 체크리스트 직접 응답 기준. True=충족, False/미기재=미충족."""
    items: list[dict[str, object]] = []
    for index, raw in enumerate(record.get("checklistItems", [])):
        item = _annotate_checklist_item(dict(raw), index)
        item_id = str(item.get("itemId") or "")
        if domain_checks.get(item_id, False) is True:
            continue
        enriched = dict(item)
        enriched["_matchedCheckKey"] = ""
        enriched["_mappingMode"] = "direct_checklist"
        items.append(enriched)
    return items


def _resolve_unchecked_items(
    record: dict[str, object],
    level: str,
    checks: dict[str, bool] | None,
    domain_checks: dict[str, bool] | None = None,
) -> list[dict[str, object]]:
    """미충족 항목 선택.

    - domain_checks가 있으면 도메인 문항 직접 매핑 (mappingMode=direct_checklist)
    - 없으면 성숙도 checkKey 프록시 (mappingMode=maturity_proxy)
    """
    if domain_checks is not None:
        return _resolve_domain_unchecked_items(record, domain_checks)

    by_key = _checklist_by_check_key(record)
    if not by_key:
        return []

    unchecked_keys = _unchecked_check_keys(level, checks)
    if not unchecked_keys and level in WEAK_LEVELS:
        unchecked_keys = _unchecked_check_keys(level, None)

    items: list[dict[str, object]] = []
    for key in CHECK_KEYS:
        if key not in unchecked_keys:
            continue
        item = by_key.get(key)
        if item is None:
            continue
        enriched = dict(item)
        enriched["_matchedCheckKey"] = key
        enriched["_mappingMode"] = "maturity_proxy"
        items.append(enriched)
    return items


def _relation_reason(source_id: str, target_id: str) -> str:
    relations = load_manual_relations()
    for target, reason in relations.get(source_id, ()):
        if target == target_id:
            return reason
    for target, reason in relations.get(target_id, ()):
        if target == source_id:
            return reason
    return f"{source_id}와 {target_id}는 연관 통제로 함께 점검됩니다."


def _build_may_cause(
    control_id: str,
    related_ids: list[str],
    assessments: dict[str, str],
) -> list[dict[str, object]]:
    may_cause: list[dict[str, object]] = []
    seen: set[str] = set()
    relations = load_manual_relations()

    for target_id in related_ids:
        if not target_id or target_id == control_id or target_id in seen:
            continue
        seen.add(target_id)
        label = evidence_label_for_edge(control_id, target_id)
        may_cause.append(
            {
                "targetControlId": target_id,
                "reason": _relation_reason(control_id, target_id),
                "relationSource": "relation_evidence",
                "evidenceLabel": label,
                "targetLevel": assessments.get(target_id),
            }
        )

    for target_id, reason in relations.get(control_id, ()):
        if target_id in seen:
            continue
        seen.add(target_id)
        edge = relation_evidence_for(control_id, target_id)
        may_cause.append(
            {
                "targetControlId": target_id,
                "reason": reason,
                "relationSource": "relation_evidence",
                "evidenceLabel": evidence_label_for_edge(control_id, target_id),
                "evidenceGrade": (edge or {}).get("strength"),
                "targetLevel": assessments.get(target_id),
            }
        )
        if len(may_cause) >= 5:
            break

    return may_cause[:5]


def _build_impacts(operational: str, audit: str) -> list[dict[str, str]]:
    impacts: list[dict[str, str]] = []
    if operational:
        impacts.append({"type": "operational", "text": operational})
    if audit:
        impacts.append({"type": "audit", "text": audit})
    return impacts


def _build_causal_statement(
    control_id: str,
    title: str,
    because: list[dict[str, object]],
    problem: str,
    impacts: list[dict[str, str]],
    mapping_mode: str,
) -> str:
    maturity = next((b for b in because if b.get("kind") == "maturity_unchecked"), None)
    checklist = next((b for b in because if b.get("kind") == "checklist_item"), None)
    level_basis = next((b for b in because if b.get("kind") == "assessment_level"), None)
    impact_text = impacts[0]["text"] if impacts else ""

    if checklist and maturity:
        proxy_note = (
            " (성숙도↔도메인 항목은 checkKey 프록시)"
            if mapping_mode == "maturity_proxy"
            else ""
        )
        head = (
            f"{control_id} {title}에서 성숙도「{maturity.get('label')}」미충족을 근거로 "
            f"「{checklist.get('checklistItem')}」항목이 미흡한 것으로 봅니다{proxy_note}."
        )
    elif checklist:
        head = (
            f"{control_id} {title}에서 「{checklist.get('checklistItem')}」항목을 "
            f"충족하지 않았기 때문에"
        )
    elif level_basis:
        head = (
            f"{control_id} {title}의 자가진단이 "
            f"「{level_basis.get('label', level_basis.get('level'))}」이므로"
        )
    else:
        head = f"{control_id} {title} 미흡으로"

    body = (problem or "").strip()
    impact = (impact_text or "").strip()
    chunks = [head.rstrip(".")]
    if body:
        chunks.append(body.rstrip("."))
    if impact:
        chunks.append(f"이로 인해 {impact.rstrip('.')}")
    return ". ".join(chunks) + "."


def _finding_from_checklist_item(
    *,
    control_id: str,
    title: str,
    level: str,
    severity: str,
    item: dict[str, object],
    assessments: dict[str, str],
) -> dict[str, object]:
    unchecked_block = dict(item.get("ifUnchecked", {}))
    check_key = str(item.get("_matchedCheckKey") or item.get("checkKey") or "")
    mapping_mode = str(item.get("_mappingMode") or ("maturity_proxy" if check_key else "direct_checklist"))
    item_id = str(item.get("itemId", ""))
    item_text = str(item.get("item", ""))
    problems = [str(p) for p in unchecked_block.get("problems", []) if str(p).strip()]
    operational = str(unchecked_block.get("operationalImpact", "")).strip()
    audit = str(unchecked_block.get("auditImpact", "")).strip()
    remediation = str(unchecked_block.get("remediation", "")).strip()
    related = [str(cid) for cid in unchecked_block.get("relatedControls", []) if str(cid).strip()]
    source_refs = [
        dict(item)
        for item in list(unchecked_block.get("sourceRefs") or [])
        if isinstance(item, dict)
    ]
    impacts = _build_impacts(operational, audit)
    primary_problem = problems[0] if problems else (operational or f"{title} 체크리스트 미흡")

    because: list[dict[str, object]] = [
        {
            "kind": "assessment_level",
            "controlId": control_id,
            "level": level,
            "label": LEVEL_LABELS.get(level, level),
        }
    ]
    if mapping_mode == "maturity_proxy" and check_key:
        because.append(
            {
                "kind": "maturity_unchecked",
                "controlId": control_id,
                "checkKey": check_key,
                "label": CHECK_KEY_LABELS.get(check_key, check_key),
                "level": level,
            }
        )
    because.append(
        {
            "kind": "checklist_item",
            "controlId": control_id,
            "checklistItemId": item_id,
            "checklistItem": item_text,
            "checkKey": check_key or None,
            "level": level,
            "mappingMode": mapping_mode,
        }
    )

    may_cause = _build_may_cause(control_id, related, assessments)
    # risk alternatives: related cascade targets as alternative risk paths
    risk_alternatives = [
        f"{edge['targetControlId']}: {edge['reason']}" for edge in may_cause[:3]
    ]
    causal_statement = _build_causal_statement(
        control_id, title, because, primary_problem, impacts, mapping_mode
    )

    return {
        "findingId": f"{control_id}:{item_id or check_key or 'item'}",
        "controlId": control_id,
        "title": title,
        "level": level,
        "checklistItemId": item_id,
        "checklistItem": item_text,
        "problems": problems,
        "problem": primary_problem,
        "remediation": remediation,
        "operationalImpact": operational,
        "auditImpact": audit,
        "severity": severity,
        "source": "checklist",
        "mappingMode": mapping_mode,
        "because": because,
        "impacts": impacts,
        "mayCause": may_cause,
        "riskAlternatives": risk_alternatives,
        "causalStatement": causal_statement,
        "sourceRefs": source_refs,
    }


def _finding_from_level(
    *,
    control_id: str,
    title: str,
    level: str,
    severity: str,
    record: dict[str, object],
    assessments: dict[str, str],
) -> dict[str, object]:
    level_block = dict(record.get("levelProblems", {}).get(level, {}))
    problems = [str(p) for p in level_block.get("problems", []) if str(p).strip()]
    operational = str(record.get("riskIfMissing", "")).strip()
    remediation = str(record.get("focus", "")).strip()
    summary = str(level_block.get("summary", f"{title} 통제 미흡"))
    primary_problem = problems[0] if problems else summary
    impacts = _build_impacts(operational, "")
    because = [
        {
            "kind": "assessment_level",
            "controlId": control_id,
            "level": level,
            "label": LEVEL_LABELS.get(level, level),
        }
    ]
    related = [str(cid) for cid in record.get("relatedControlIds", []) if str(cid).strip()]
    may_cause = _build_may_cause(control_id, related, assessments)
    mapping_mode = "level_only"
    causal_statement = _build_causal_statement(
        control_id, title, because, primary_problem, impacts, mapping_mode
    )
    source_refs = [
        dict(item)
        for item in list(level_block.get("sourceRefs") or [])
        if isinstance(item, dict)
    ]

    return {
        "findingId": f"{control_id}:level:{level}",
        "controlId": control_id,
        "title": title,
        "level": level,
        "checklistItemId": "",
        "checklistItem": summary,
        "problems": problems,
        "problem": primary_problem,
        "remediation": remediation,
        "operationalImpact": operational,
        "auditImpact": "",
        "severity": severity,
        "source": "level",
        "mappingMode": mapping_mode,
        "because": because,
        "impacts": impacts,
        "mayCause": may_cause,
        "causalStatement": causal_statement,
        "sourceRefs": source_refs,
    }


def extract_individual_problems(
    assessments: dict[str, str],
    control_checks: dict[str, dict[str, bool]] | None = None,
    organization_context: OrganizationContext | None = None,
    domain_checks: dict[str, dict[str, bool]] | None = None,
) -> list[dict[str, object]]:
    problems: list[dict[str, object]] = []
    control_checks = control_checks or {}
    domain_checks = domain_checks or {}

    for control_id, level in assessments.items():
        if level not in WEAK_LEVELS:
            continue
        record = _load_control(control_id)
        if record is None:
            continue

        title = str(record["title"])
        severity = _severity_for_level(level)
        checks = control_checks.get(control_id)
        domain = domain_checks.get(control_id)

        unchecked = _resolve_unchecked_items(record, level, checks, domain)
        if unchecked:
            for item in unchecked:
                problems.append(
                    _finding_from_checklist_item(
                        control_id=control_id,
                        title=title,
                        level=level,
                        severity=severity,
                        item=item,
                        assessments=assessments,
                    )
                )
        else:
            # domain 전부 충족이어도 level이 weak면 level finding 유지
            if domain is not None and all(bool(v) for v in domain.values()) and domain:
                continue
            problems.append(
                _finding_from_level(
                    control_id=control_id,
                    title=title,
                    level=level,
                    severity=severity,
                    record=record,
                    assessments=assessments,
                )
            )

    severity_order = {"critical": 0, "high": 1, "medium": 2}
    problems.sort(
        key=lambda row: (
            severity_order.get(str(row["severity"]), 9),
            -priority_delta(str(row["controlId"]), organization_context),
            str(row["controlId"]),
            str(row["checklistItemId"]),
        )
    )
    return problems


def findings_for_control(
    control_id: str,
    level: str,
    checks: dict[str, bool] | None = None,
    assessments: dict[str, str] | None = None,
    organization_context: OrganizationContext | None = None,
    domain_checks: dict[str, bool] | None = None,
) -> list[dict[str, object]]:
    """단일 통제에 대한 CausalFinding 목록 (갭 경로 grounding용)."""
    scoped_assessments = {control_id: level}
    if assessments:
        scoped_assessments = dict(assessments)
        scoped_assessments[control_id] = level
    scoped_checks = {control_id: checks} if checks is not None else None
    scoped_domain = {control_id: domain_checks} if domain_checks is not None else None
    return [
        row
        for row in extract_individual_problems(
            scoped_assessments,
            scoped_checks,
            organization_context,
            scoped_domain,
        )
        if str(row.get("controlId")) == control_id
    ]


def preview_check_impact(
    assessments: dict[str, str],
    control_checks: dict[str, dict[str, bool]] | None,
    *,
    control_id: str,
    check_key: str,
    checked: bool = True,
    organization_context: OrganizationContext | None = None,
) -> dict[str, object]:
    """특정 성숙도 체크를 켰을/껐을 때 사라지거나 남는 문제를 미리 계산."""
    if check_key not in CHECK_KEYS:
        raise ValueError(f"unsupported checkKey: {check_key}")
    if control_id not in assessments:
        raise ValueError(f"controlId not in assessments: {control_id}")

    before_checks = {cid: dict(values) for cid, values in (control_checks or {}).items()}
    if control_id not in before_checks:
        before_checks[control_id] = {
            key: key not in _unchecked_check_keys(assessments[control_id], None)
            for key in CHECK_KEYS
        }

    after_checks = {cid: dict(values) for cid, values in before_checks.items()}
    after_checks[control_id] = dict(after_checks.get(control_id) or {})
    after_checks[control_id][check_key] = checked

    before_rows = extract_individual_problems(assessments, before_checks, organization_context)
    after_rows = extract_individual_problems(assessments, after_checks, organization_context)

    def _ids(rows: list[dict[str, object]]) -> set[str]:
        return {str(row.get("findingId") or f"{row.get('controlId')}:{row.get('checklistItemId')}") for row in rows}

    before_ids = _ids(before_rows)
    after_ids = _ids(after_rows)
    resolved_ids = before_ids - after_ids
    introduced_ids = after_ids - before_ids

    scoped_before = [row for row in before_rows if str(row.get("controlId")) == control_id]
    scoped_after = [row for row in after_rows if str(row.get("controlId")) == control_id]

    return {
        "controlId": control_id,
        "checkKey": check_key,
        "checkLabel": CHECK_KEY_LABELS.get(check_key, check_key),
        "checked": checked,
        "beforeCount": len(scoped_before),
        "afterCount": len(scoped_after),
        "resolvedFindings": [row for row in scoped_before if str(row.get("findingId")) in resolved_ids],
        "remainingFindings": scoped_after,
        "introducedFindings": [row for row in scoped_after if str(row.get("findingId")) in introduced_ids],
        "summary": (
            f"{control_id}에서 성숙도「{CHECK_KEY_LABELS.get(check_key, check_key)}」를 "
            f"{'충족' if checked else '미충족'}으로 바꾸면 "
            f"관련 문제 {len([r for r in scoped_before if str(r.get('findingId')) in resolved_ids])}건이 해소되고 "
            f"{len(scoped_after)}건이 남습니다."
        ),
    }


def assemble_causal_findings(
    individual_problems: list[dict[str, object]],
    *,
    limit: int = 80,
) -> list[dict[str, object]]:
    """Individual problem rows를 CausalFinding 리스트로 정규화(이미 enrich된 경우 그대로).

    계약(because/problem/impacts/causalStatement)을 충족하지 못하면 제외한다.
    """
    from .causal_contract import filter_valid_causal_findings

    findings: list[dict[str, object]] = []
    for row in individual_problems[: max(limit * 2, limit)]:
        finding = dict(row)
        finding.setdefault(
            "findingId",
            f"{row.get('controlId')}:{row.get('checklistItemId') or row.get('level')}",
        )
        problems = [str(p) for p in (row.get("problems") or []) if str(p).strip()]
        if not finding.get("problem"):
            finding["problem"] = problems[0] if problems else str(row.get("checklistItem") or "")
        finding.setdefault("because", [])
        finding.setdefault(
            "impacts",
            _build_impacts(
                str(row.get("operationalImpact") or ""),
                str(row.get("auditImpact") or ""),
            ),
        )
        finding.setdefault("mayCause", [])
        finding.setdefault("source", "checklist" if row.get("checklistItemId") else "level")
        finding.setdefault(
            "mappingMode",
            "level_only" if row.get("source") == "level" else "maturity_proxy",
        )
        if not finding.get("title"):
            finding["title"] = str(row.get("title") or row.get("controlId") or "")
        if not finding.get("causalStatement"):
            finding["causalStatement"] = _build_causal_statement(
                str(row.get("controlId") or ""),
                str(finding.get("title") or ""),
                list(finding.get("because") or []),
                str(finding.get("problem") or ""),
                list(finding.get("impacts") or []),
                str(finding.get("mappingMode") or "maturity_proxy"),
            )
        findings.append(finding)

    valid, _rejected = filter_valid_causal_findings(findings)  # type: ignore[arg-type]
    return valid[:limit]


def _weak_control_ids(assessments: dict[str, str]) -> set[str]:
    return {cid for cid, level in assessments.items() if level in WEAK_LEVELS}


def _build_weak_adjacency(weak_ids: set[str]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {cid: set() for cid in weak_ids}
    relations = load_manual_relations()

    for source_id, targets in relations.items():
        if source_id not in weak_ids:
            continue
        for target_id, _ in targets:
            if target_id in weak_ids:
                graph[source_id].add(target_id)
                graph[target_id].add(source_id)

    for scenario in SCENARIOS:
        ids = [cid for cid in scenario.control_ids if cid in weak_ids]
        for index in range(len(ids) - 1):
            left, right = ids[index], ids[index + 1]
            graph[left].add(right)
            graph[right].add(left)

    by_category: dict[str, list[str]] = {}
    for cid in weak_ids:
        cat = cid.rsplit(".", 1)[0]
        by_category.setdefault(cat, []).append(cid)
    for cat_ids in by_category.values():
        if len(cat_ids) < 2:
            continue
        sorted_ids = sorted(cat_ids)
        for left, right in zip(sorted_ids, sorted_ids[1:], strict=False):
            graph[left].add(right)
            graph[right].add(left)

    return graph


def _connected_clusters(weak_ids: set[str]) -> list[list[str]]:
    if len(weak_ids) < 2:
        return []

    graph = _build_weak_adjacency(weak_ids)
    visited: set[str] = set()
    clusters: list[list[str]] = []

    for start in sorted(weak_ids):
        if start in visited:
            continue
        stack = [start]
        component: list[str] = []
        visited.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(graph.get(node, ())):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        if len(component) >= 2:
            clusters.append(sorted(component))

    clusters.sort(key=lambda group: (-len(group), group[0]))
    return clusters[:20]


def _lookup_compound(control_ids: tuple[str, ...]) -> dict[str, object] | None:
    key = "|".join(sorted(control_ids))
    hit = _compound_index().get(key)
    if hit:
        return hit

    weak_set = set(control_ids)
    best: dict[str, object] | None = None
    best_score = 0
    for compound in _load_compounds():
        compound_ids = set(compound.get("controlIds", []))
        if not compound_ids <= weak_set:
            continue
        score = len(compound_ids)
        if score > best_score:
            best_score = score
            best = compound
    return best


def _bridge_problems(
    cluster: list[str],
    individual: list[dict[str, object]],
) -> list[str]:
    by_control: dict[str, list[str]] = {}
    for row in individual:
        cid = str(row["controlId"])
        by_control.setdefault(cid, []).extend(str(p) for p in row.get("problems", [])[:2])

    bridges: list[str] = []
    for left, right in zip(cluster, cluster[1:], strict=False):
        left_probs = by_control.get(left, [])
        right_probs = by_control.get(right, [])
        if left_probs and right_probs:
            left_snip = left_probs[0][:48] + ("…" if len(left_probs[0]) > 48 else "")
            right_snip = right_probs[0][:48] + ("…" if len(right_probs[0]) > 48 else "")
            bridges.append(
                f"{left}의 '{left_snip}'와 {right}의 '{right_snip}'가 동시에 남으면 "
                f"단일 통제 보완만으로는 연결 업무 흐름 전체 리스크를 닫기 어렵습니다."
            )
    return bridges[:4]


def synthesize_compounds(
    assessments: dict[str, str],
    individual_problems: list[dict[str, object]],
    scenario_id: str | None = None,
    organization_context: OrganizationContext | None = None,
) -> list[dict[str, object]]:
    weak_ids = _weak_control_ids(assessments)
    if len(weak_ids) < 2:
        return []

    clusters = _connected_clusters(weak_ids)
    compounds: list[dict[str, object]] = []
    compound_lookup = _compound_index()
    seen_keys: set[str] = set()
    grade_rank = {"strong": 3, "medium": 2, "weak": 1}

    def append_synthesis(cluster: list[str], reason: str) -> None:
        key = "|".join(cluster)
        if key in seen_keys:
            return

        matched = _lookup_compound(tuple(cluster))
        evidence_grade = str((matched or {}).get("evidenceGrade") or "weak")
        evidence_refs = list((matched or {}).get("evidenceRefs") or [])
        # Skip KB rules that have no evidence trail (legacy template leftovers).
        if matched and evidence_grade == "weak" and not evidence_refs:
            matched = None
            evidence_grade = "weak"
            evidence_refs = []

        # Require either an evidenced KB hit or at least one evidenced edge in the cluster.
        if matched is None:
            has_edge = False
            for left, right in zip(cluster, cluster[1:]):
                if relation_evidence_for(left, right):
                    has_edge = True
                    break
            if not has_edge and len(cluster) >= 2:
                # category adjacency fallback still allowed at runtime but marked weak
                evidence_grade = "weak"
            elif has_edge:
                evidence_grade = "medium"

        seen_keys.add(key)
        cluster_problems = [row for row in individual_problems if str(row["controlId"]) in cluster]
        connection_reason = str(matched.get("connectionReason", "")).strip() if matched else ""
        compound_problems: list[str] = []
        if connection_reason:
            compound_problems.append(connection_reason)
        if matched:
            for item in matched.get("compoundProblems", []):
                text = str(item).strip()
                if not text or text == connection_reason:
                    continue
                if "단일 결함이 아니라 연결된 업무 흐름 전체의 보호 공백" in text:
                    continue
                if "탐지/차단/추적/통지/복구 중 2개 이상이 동시에 무력화" in text:
                    continue
                compound_problems.append(text)
        compound_scenarios = list(matched.get("compoundScenarios", [])) if matched else []
        integrated = list(matched.get("integratedRemediation", [])) if matched else []

        if not compound_problems:
            titles = ", ".join(
                f"{cid} {find_control(cid)['title'] if find_control(cid) else ''}" for cid in cluster[:4]
            )
            compound_problems = [
                reason,
                f"{len(cluster)}개 통제({titles})가 동시에 미흡하면 개별 보완만으로 연결 흐름 리스크를 닫기 어렵습니다.",
            ]

        bridges = _bridge_problems(cluster, cluster_problems)
        compound_problems = list(dict.fromkeys(compound_problems + bridges))[:8]

        if not integrated:
            integrated = [
                f"{' / '.join(cluster)} 통제를 하나의 증적 패키지로 묶어 분기 점검",
                "체크리스트 미충족 항목을 통제별 CAR(시정조치)로 등록",
                "관계 근거(사례집/결함우선/수동)에 따라 담당/승인/운영 로그를 순서대로 연결",
            ]

        evidence_labels: list[str] = []
        grounding_levels: list[str] = []
        for left, right in zip(cluster, cluster[1:]):
            label = evidence_label_for_edge(left, right)
            if label and label not in evidence_labels:
                evidence_labels.append(label)
            level = grounding_level_for_edge(left, right)
            if level not in grounding_levels:
                grounding_levels.append(level)
        if matched and matched.get("groundingLevel"):
            gl = str(matched.get("groundingLevel"))
            if gl not in grounding_levels:
                grounding_levels.insert(0, gl)
        if "casebook_cite" in grounding_levels:
            primary_grounding = "casebook_cite"
        elif "category_adjacent" in grounding_levels:
            primary_grounding = "category_adjacent"
        else:
            primary_grounding = grounding_levels[0] if grounding_levels else "interpret"
        grounding_note = str(
            (matched or {}).get("groundingNote")
            or grounding_statement_for_edge(cluster[0], cluster[1] if len(cluster) > 1 else cluster[0])
        )

        titles_short = ", ".join(cluster[:5])
        narrative_parts = [
            grounding_note,
            f"다음 {len(cluster)}개 통제가 동시에 약합니다: {titles_short}.",
            f"개별 체크리스트에서 도출된 문제 {len(cluster_problems)}건이 겹칩니다.",
        ]
        if matched:
            narrative_parts.append(str(matched.get("connectionReason", reason)))
        if evidence_labels:
            narrative_parts.append(f"연결 근거 레벨: {', '.join(evidence_labels)}.")
        narrative_parts.append(
            "문서의 개별 문제 서술을 조합해 유기적 리스크로 재구성한 것이며, "
            "우선 이 클러스터를 하나의 개선 과제로 묶어 담당/일정/증적을 연결하는 것이 효과적입니다."
        )

        because = [
            {
                "kind": "weak_control",
                "controlId": cid,
                "level": assessments.get(cid),
                "label": LEVEL_LABELS.get(str(assessments.get(cid)), str(assessments.get(cid))),
            }
            for cid in cluster
        ]
        because_checklist_refs = [
            {
                "controlId": str(row.get("controlId")),
                "checklistItemId": str(row.get("checklistItemId") or ""),
                "checklistItem": str(row.get("checklistItem") or ""),
            }
            for row in cluster_problems
            if row.get("source") == "checklist"
        ][:12]
        titles = [
            f"{cid}({LEVEL_LABELS.get(str(assessments.get(cid)), assessments.get(cid))})"
            for cid in cluster[:4]
        ]
        causal_statement = (
            f"{', '.join(titles)} 통제가 동시에 미흡하기 때문에 "
            f"{compound_problems[0] if compound_problems else '연결 업무 흐름 리스크가 커집니다.'}"
        )

        compounds.append(
            {
                "clusterId": f"syn-{cluster[0].replace('.', '')}-{len(cluster)}",
                "controlIds": cluster,
                "matchedCompoundKey": str(matched.get("compoundKey", "")) if matched else None,
                "individualProblemCount": len(cluster_problems),
                "compoundProblems": compound_problems,
                "compoundScenarios": compound_scenarios[:5],
                "connectionReasons": [reason] + ([str(matched.get("connectionReason", ""))] if matched else []),
                "integratedRemediation": integrated[:6],
                "synthesisNarrative": " ".join(part for part in narrative_parts if part),
                "because": because,
                "becauseChecklistRefs": because_checklist_refs,
                "causalStatement": causal_statement,
                "evidenceGrade": evidence_grade if matched or evidence_labels else "weak",
                "evidenceRefs": evidence_refs[:12],
                "evidenceLabels": evidence_labels,
                "groundingLevel": primary_grounding,
                "groundingNote": grounding_note,
            }
        )

    for cluster in clusters:
        reason = f"관계 증거 그래프/시나리오/분류로 묶인 {len(cluster)}개 동시 갭"
        append_synthesis(cluster, reason)

    if scenario_id:
        scenario = find_scenario(scenario_id)
        if scenario:
            scenario_weak = [
                str(cid)
                for cid in scenario.get("controlIds", [])
                if str(cid) in weak_ids
            ]
            if len(scenario_weak) >= 2:
                append_synthesis(
                    scenario_weak[: min(6, len(scenario_weak))],
                    f"{scenario.get('title', scenario_id)} 시나리오 경로상 연속/동시 미흡",
                )

    for compound in compound_lookup.values():
        if str(compound.get("evidenceGrade") or "") == "weak" and not compound.get("evidenceRefs"):
            continue
        ids = sorted(str(cid) for cid in compound.get("controlIds", []))
        if len(ids) < 2:
            continue
        if not all(cid in weak_ids for cid in ids):
            continue
        append_synthesis(ids, str(compound.get("connectionReason", "복합 규칙 KB 매칭")))

    compounds.sort(
        key=lambda row: (
            -grade_rank.get(str(row.get("evidenceGrade") or "weak"), 0),
            -bundle_priority_delta(list(row["controlIds"]), organization_context),
            -len(row["controlIds"]),
            -row["individualProblemCount"],
        )
    )
    return compounds[:15]


def build_integrated_guidance(
    individual_problems: list[dict[str, object]],
    compound_syntheses: list[dict[str, object]],
    assessments: dict[str, str],
    organization_context: OrganizationContext | None = None,
) -> dict[str, object]:
    weak_count = sum(1 for level in assessments.values() if level in WEAK_LEVELS)
    checklist_gaps = sum(1 for row in individual_problems if row.get("source") == "checklist")

    action_scores: dict[str, int] = {}
    for row in individual_problems:
        remediation = str(row.get("remediation", "")).strip()
        if not remediation:
            continue
        weight = {"critical": 3, "high": 2, "medium": 1}.get(str(row.get("severity")), 1)
        weight += priority_delta(str(row.get("controlId", "")), organization_context)
        action_scores[remediation] = action_scores.get(remediation, 0) + weight

    for synthesis in compound_syntheses:
        for action in synthesis.get("integratedRemediation", []):
            text = str(action).strip()
            if text:
                action_scores[text] = action_scores.get(text, 0) + 5

    prioritized = [
        action for action, _ in sorted(action_scores.items(), key=lambda item: (-item[1], item[0]))
    ][:12]

    compound_count = len(compound_syntheses)
    summary = (
        f"미흡 통제 {weak_count}건에서 체크리스트 기반 문제 {checklist_gaps}건, "
        f"복합 합성 클러스터 {compound_count}건을 도출했습니다."
    )
    if compound_count:
        summary += " 복합 클러스터는 개별 CAR보다 묶음 개선 과제로 처리하는 것을 권장합니다."

    narrative_lines = [
        summary,
        f"개별 문제 {len(individual_problems)}건 중 critical {sum(1 for r in individual_problems if r.get('severity') == 'critical')}건을 우선 처리하세요.",
    ]
    if compound_syntheses:
        top = compound_syntheses[0]
        narrative_lines.append(
            f"최우선 복합 클러스터: {' / '.join(top['controlIds'][:4])} — {top['synthesisNarrative'][:200]}"
        )
    if prioritized:
        narrative_lines.append(f"1순위 조치: {prioritized[0]}")

    return {
        "summary": summary,
        "prioritizedActions": prioritized,
        "executiveNarrative": " ".join(narrative_lines),
    }


def analyze_problems(
    assessments: dict[str, str],
    scenario_id: str | None = None,
    control_checks: dict[str, dict[str, bool]] | None = None,
    organization_context: OrganizationContext | None = None,
    domain_checks: dict[str, dict[str, bool]] | None = None,
) -> dict[str, object]:
    individual = extract_individual_problems(
        assessments, control_checks, organization_context, domain_checks
    )
    causal_findings = assemble_causal_findings(individual, limit=80)
    compounds = synthesize_compounds(assessments, individual, scenario_id, organization_context)
    guidance = build_integrated_guidance(individual, compounds, assessments, organization_context)

    index = _load_index()
    return {
        "individualProblems": individual[:80],
        "causalFindings": causal_findings,
        "compoundSyntheses": compounds,
        "integratedGuidance": guidance,
        "stats": {
            "kbVersion": index.get("version", 1),
            "totalControlsInKb": index.get("totalControls", 101),
            "totalCompoundRules": index.get("totalCompounds", 0),
            "weakControlCount": sum(1 for level in assessments.values() if level in WEAK_LEVELS),
            "individualProblemCount": len(individual),
            "causalFindingCount": len(causal_findings),
            "compoundClusterCount": len(compounds),
            "checklistDerivedCount": sum(1 for row in individual if row.get("source") == "checklist"),
        },
    }
