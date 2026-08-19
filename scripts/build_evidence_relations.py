#!/usr/bin/env python3
"""Build relation_evidence.json from casebook + defect weights + MANUAL seed.

Evidence grades:
  strong — casebook cross-mention or explicit curated seed with casebook/official ref
  medium — manual seed preserved, or high-defect pair with keyword bridge
  weak   — scenario adjacency only (optional; not written by default)

Does NOT invent causal claims from defect co-occurrence alone.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isms_pii_toolkit.control_graph import (  # noqa: E402
    CONTROL_CATEGORIES,
    MANUAL_RELATIONS_SEED,
    SCENARIOS,
    list_controls,
)

CASEBOOK = ROOT / "사례집.md"
CROSSWALK = ROOT / "src/isms_pii_toolkit/data/problem_kb/casebook_crosswalk.json"
WEIGHTS = ROOT / "src/isms_pii_toolkit/data/problem_kb/defect_weights.json"
OFFICIAL_DIR = ROOT / "src/isms_pii_toolkit/data/official_kb/controls"
OUT = ROOT / "src/isms_pii_toolkit/data/problem_kb/relation_evidence.json"

CONTROL_ID_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")

# Keyword bridges: when case text under source mentions these, link to target.
KEYWORD_BRIDGES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "2.5.5": [("2.5.6", ("정기적으로 검토", "권한 검토", "접근권한 검토", "사용 여부를 정기"))],
    "2.5.6": [("2.5.5", ("특수권한", "특수 권한", "관리자 및 특수"))],
    "2.5.1": [("2.5.6", ("장기 미사용", "접근권한 검토", "계정"))],
    "2.5.3": [("2.5.4", ("비밀번호", "패스워드"))],
    "2.5.4": [("2.5.3", ("인증", "로그인"))],
    "2.9.4": [
        ("2.9.5", ("검토 주기", "점검", "모니터링")),
        ("2.10.1", ("보안시스템", "보안 시스템", "방화벽")),
        ("2.11.3", ("이상", "탐지", "모니터링")),
    ],
    "2.9.5": [("2.9.4", ("로그", "접속기록"))],
    "2.10.1": [
        ("2.10.8", ("패치", "업데이트")),
        ("2.11.3", ("모니터링", "이벤트", "탐지")),
        ("2.9.4", ("로그", "기록")),
    ],
    "2.10.8": [
        ("2.10.1", ("보안시스템", "보안 시스템", "방화벽")),
        ("2.10.9", ("백신", "악성코드", "패치")),
    ],
    "2.10.9": [("2.10.8", ("패치", "업데이트"))],
    "2.6.1": [("2.6.2", ("서버", "정보시스템")), ("2.6.3", ("응용프로그램", "응용 프로그램"))],
    "2.6.2": [
        ("2.6.1", ("네트워크", "망분리")),
        ("2.6.3", ("응용프로그램", "응용 프로그램")),
        ("2.5.5", ("관리자", "특수권한", "특수 권한")),
    ],
    "2.6.3": [("2.6.2", ("서버", "정보시스템")), ("2.8.2", ("시험", "취약점"))],
    "1.4.1": [("1.4.2", ("점검", "검토")), ("1.4.3", ("개선", "시정"))],
    "1.2.1": [("1.2.2", ("흐름", "현황"))],
    "1.2.3": [("1.2.4", ("보호대책", "대책 선정"))],
}

# High-defect pairs that should be adopted when keyword/casebook evidence exists.
PRIORITY_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("2.10.1", "2.10.8", "보안시스템 운영과 패치관리는 취약점 차단 흐름으로 이어집니다."),
    ("2.10.8", "2.10.9", "패치와 악성코드 통제는 단말/서버 보안 운영으로 함께 점검됩니다."),
    ("2.5.5", "2.5.6", "특수 계정·권한은 정기 접근권한 검토 대상입니다."),
    ("2.6.1", "2.6.2", "네트워크 접근과 정보시스템 접근은 연속된 접근통제 구간입니다."),
    ("2.6.2", "2.6.3", "서버 접근과 응용프로그램 접근은 동일 업무 흐름의 인접 통제입니다."),
    ("2.9.4", "2.10.1", "보안시스템 이벤트/접속기록은 로그 관리 대상입니다."),
    ("1.4.1", "1.4.2", "법적 요구사항 검토 결과는 관리체계 점검으로 이어집니다."),
    ("1.2.1", "1.2.2", "자산 식별 결과는 현황·흐름분석의 입력입니다."),
)


def parse_casebook(text: str) -> dict[str, dict[str, object]]:
    parts = re.split(r"(?m)^(?=\d+\.\d+\.\d+\.\s)", text)
    out: dict[str, dict[str, object]] = {}
    for part in parts:
        head = re.match(r"^(\d+\.\d+\.\d+)\.\s*(.+?)(?:\s*▶.*)?\s*$", part, re.M)
        if not head:
            continue
        control_id = head.group(1)
        title = head.group(2).strip()
        cases: list[dict[str, object]] = []
        for line in part.splitlines()[1:]:
            m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
            if not m:
                continue
            body = m.group(2).strip()
            if re.match(r"^\d+\.\d+", body):
                continue
            cases.append({"n": int(m.group(1)), "text": body})
        out[control_id] = {"title": title, "cases": cases}
    return out


def _edge_key(source: str, target: str) -> str:
    return f"{source}->{target}"


def _add_edge(
    edges: dict[str, dict[str, object]],
    *,
    source: str,
    target: str,
    reason: str,
    evidence_type: str,
    strength: str,
    refs: list[dict[str, object]],
) -> None:
    if source == target:
        return
    key = _edge_key(source, target)
    existing = edges.get(key)
    if existing is None:
        edges[key] = {
            "source": source,
            "target": target,
            "reason": reason,
            "strength": strength,
            "evidence": [{"type": evidence_type, "refs": refs}],
        }
        return
    # Upgrade strength if stronger evidence arrives.
    order = {"weak": 0, "medium": 1, "strong": 2}
    if order.get(strength, 0) > order.get(str(existing.get("strength")), 0):
        existing["strength"] = strength
        if reason and len(reason) >= len(str(existing.get("reason") or "")):
            existing["reason"] = reason
    evid = list(existing.get("evidence") or [])
    evid.append({"type": evidence_type, "refs": refs})
    # de-dupe by type
    seen: set[str] = set()
    merged = []
    for item in evid:
        t = str(item.get("type"))
        if t in seen:
            # merge refs
            for m in merged:
                if m.get("type") == t:
                    refs_m = list(m.get("refs") or [])
                    for r in item.get("refs") or []:
                        if r not in refs_m:
                            refs_m.append(r)
                    m["refs"] = refs_m[:8]
                    break
            continue
        seen.add(t)
        merged.append(item)
    existing["evidence"] = merged


def seed_manual(edges: dict[str, dict[str, object]]) -> None:
    for source, targets in MANUAL_RELATIONS_SEED.items():
        for target, reason in targets:
            _add_edge(
                edges,
                source=source,
                target=target,
                reason=reason,
                evidence_type="manual",
                strength="medium",
                refs=[{"doc": "control_graph.MANUAL_RELATIONS_SEED", "note": "curated seed"}],
            )


def from_casebook_keywords(
    edges: dict[str, dict[str, object]],
    casebook: dict[str, dict[str, object]],
) -> None:
    for source, bridges in KEYWORD_BRIDGES.items():
        block = casebook.get(source) or {}
        cases = list(block.get("cases") or [])
        for target, keywords in bridges:
            for case in cases:
                text = str(case.get("text") or "")
                if not any(kw in text for kw in keywords):
                    continue
                reason = (
                    f"사례집 {source} 사례에서 '{keywords[0]}' 등 표현이 "
                    f"{target} 통제와 연결됩니다."
                )
                _add_edge(
                    edges,
                    source=source,
                    target=target,
                    reason=reason,
                    evidence_type="casebook",
                    strength="strong",
                    refs=[
                        {
                            "doc": "사례집.md",
                            "controlId": source,
                            "caseNo": int(case["n"]),
                            "ref": f"사례집.md#{source}.{int(case['n'])}",
                            "snippet": text[:120],
                        }
                    ],
                )
                break


def from_explicit_ids(
    edges: dict[str, dict[str, object]],
    casebook: dict[str, dict[str, object]],
    known_ids: set[str],
) -> None:
    for source, block in casebook.items():
        for case in block.get("cases") or []:
            text = str(case.get("text") or "")
            for match in CONTROL_ID_RE.findall(text):
                if match == source or match not in known_ids:
                    continue
                _add_edge(
                    edges,
                    source=source,
                    target=match,
                    reason=f"사례집 {source} 사례 본문에 통제 {match}가 명시됩니다.",
                    evidence_type="casebook",
                    strength="strong",
                    refs=[
                        {
                            "doc": "사례집.md",
                            "controlId": source,
                            "caseNo": int(case["n"]),
                            "ref": f"사례집.md#{source}.{int(case['n'])}",
                            "snippet": text[:120],
                        }
                    ],
                )


def _category_neighbors() -> set[tuple[str, str]]:
    neighbors: set[tuple[str, str]] = set()
    for category in CONTROL_CATEGORIES:
        ids = [f"{category.category_id}.{i}" for i in range(1, len(category.control_titles) + 1)]
        for left, right in zip(ids, ids[1:]):
            neighbors.add(tuple(sorted((left, right))))
    return neighbors


def from_priority_pairs(
    edges: dict[str, dict[str, object]],
    casebook: dict[str, dict[str, object]],
    weights: dict[str, object],
) -> None:
    controls = weights.get("controls") or {}
    neighbors = _category_neighbors()
    for a, b, reason in PRIORITY_PAIRS:
        key_ab = _edge_key(a, b)
        key_ba = _edge_key(b, a)
        has = key_ab in edges or key_ba in edges
        evidence_type = "defect_priority"
        refs: list[dict[str, object]] = []
        if not has:
            for src, tgt in ((a, b), (b, a)):
                bridges = KEYWORD_BRIDGES.get(src, [])
                kws = next((k for t, k in bridges if t == tgt), ())
                if not kws:
                    continue
                for case in (casebook.get(src) or {}).get("cases") or []:
                    if any(kw in str(case.get("text") or "") for kw in kws):
                        has = True
                        evidence_type = "casebook"
                        refs.append(
                            {
                                "doc": "사례집.md",
                                "controlId": src,
                                "caseNo": int(case["n"]),
                                "ref": f"사례집.md#{src}.{int(case['n'])}",
                            }
                        )
                        break
                if has:
                    break
        if not has and tuple(sorted((a, b))) in neighbors:
            # Official taxonomy adjacency + high-defect priority (not co-occurrence causality).
            has = True
            evidence_type = "category_adjacent"
            refs.append(
                {
                    "doc": "ISMS-P 인증기준 분류",
                    "controlIds": [a, b],
                    "note": "동일 통제영역 내 인접 항목 + 결함우선 쌍",
                }
            )
        if not has:
            continue
        da = int((controls.get(a) or {}).get("defectCount") or 0)
        db = int((controls.get(b) or {}).get("defectCount") or 0)
        strength = "strong" if evidence_type in {"casebook", "defect_priority"} and (da + db) >= 10 else "medium"
        if evidence_type == "category_adjacent":
            strength = "medium"
        refs.append(
            {
                "doc": "defect_weights.json",
                "controlIds": [a, b],
                "defectCounts": {a: da, b: db},
                "note": "priority pair adopted with casebook/keyword/category bridge",
            }
        )
        _add_edge(
            edges,
            source=a,
            target=b,
            reason=reason,
            evidence_type=evidence_type,
            strength=strength,
            refs=refs,
        )


def from_official_related(
    edges: dict[str, dict[str, object]],
    known_ids: set[str],
) -> None:
    """If official defectExamples mention another control id, add soft evidence."""
    for path in OFFICIAL_DIR.glob("*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        source = str(rec.get("controlId") or "")
        if source not in known_ids:
            continue
        blob = " ".join(str(x) for x in (rec.get("defectExamples") or []))
        for match in CONTROL_ID_RE.findall(blob):
            if match == source or match not in known_ids:
                continue
            _add_edge(
                edges,
                source=source,
                target=match,
                reason=f"인증기준 안내서 {source} 결함 예시에 {match} 관련 서술이 있습니다.",
                evidence_type="official",
                strength="medium",
                refs=[{"doc": "official_kb", "controlId": source, "file": path.name}],
            )


def from_scenarios(edges: dict[str, dict[str, object]]) -> None:
    for scenario in SCENARIOS:
        ids = list(scenario.control_ids)
        for left, right in zip(ids, ids[1:]):
            # Only attach scenario evidence if edge already exists (do not invent).
            key = _edge_key(left, right)
            if key not in edges and _edge_key(right, left) not in edges:
                continue
            _add_edge(
                edges,
                source=left,
                target=right,
                reason=f"{scenario.title} 시나리오에서 함께 검토되는 인접 통제입니다.",
                evidence_type="scenario",
                strength="medium",
                refs=[{"doc": "control_graph.SCENARIOS", "scenarioId": scenario.id}],
            )


def _grounding_level(edge: dict[str, object]) -> str:
    types = {str(item.get("type") or "") for item in (edge.get("evidence") or [])}
    if "casebook" in types:
        return "casebook_cite"
    if "category_adjacent" in types or "scenario" in types or "official" in types:
        return "category_adjacent"
    return "interpret"


def build() -> dict[str, object]:
    controls = list_controls()
    known_ids = {str(c["id"]) for c in controls}
    titles = {str(c["id"]): str(c["title"]) for c in controls}
    casebook = parse_casebook(CASEBOOK.read_text(encoding="utf-8")) if CASEBOOK.is_file() else {}
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8")) if WEIGHTS.is_file() else {"controls": {}}
    cross = json.loads(CROSSWALK.read_text(encoding="utf-8")) if CROSSWALK.is_file() else {}

    edges: dict[str, dict[str, object]] = {}
    seed_manual(edges)
    from_casebook_keywords(edges, casebook)
    from_explicit_ids(edges, casebook, known_ids)
    from_priority_pairs(edges, casebook, weights)
    from_official_related(edges, known_ids)
    from_scenarios(edges)

    cleaned = [e for e in edges.values() if e["source"] in known_ids and e["target"] in known_ids]
    for edge in cleaned:
        edge["groundingLevel"] = _grounding_level(edge)
    cleaned.sort(key=lambda e: (str(e["source"]), str(e["target"])))

    relation_map: dict[str, list[dict[str, object]]] = defaultdict(list)
    for e in cleaned:
        relation_map[str(e["source"])].append(
            {
                "targetControlId": e["target"],
                "reason": e["reason"],
                "strength": e["strength"],
                "groundingLevel": e["groundingLevel"],
                "evidenceTypes": [x.get("type") for x in (e.get("evidence") or [])],
            }
        )

    return {
        "version": 2,
        "purpose": "Evidence-tagged control relations for organic/compound analysis",
        "groundingLevels": {
            "casebook_cite": "사례집 텍스트에 상대 통제 영역 키워드/명시가 있는 연결",
            "category_adjacent": "인증기준 분류·시나리오상 인접 연결",
            "interpret": "결함우선·수동 관계 기반 해석형 연결 (CSV는 인과가 아니라 weight)",
        },
        "defectCsvRole": (
            "defect_weights/CSV는 통제별 빈도·우선순위만 제공한다. "
            "유기적 인과(원인→결과)는 사례집/분류/수동 relation으로 정의하고, "
            "CSV는 그 연결의 대응 우선순위를 조정하는 weight로만 사용한다."
        ),
        "sources": [
            "control_graph.MANUAL_RELATIONS_SEED",
            "사례집.md",
            "defect_weights.json",
            "casebook_crosswalk.json",
            "official_kb/controls",
        ],
        "pilotControls": [p.get("controlId") for p in (cross.get("pilotControls") or [])],
        "titles": titles,
        "edgeCount": len(cleaned),
        "edges": cleaned,
        "relationMap": dict(relation_map),
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {payload['edgeCount']} edges to {OUT}")
    # Highlight priority pairs
    edge_set = {(e["source"], e["target"]) for e in payload["edges"]}
    for a, b, _ in PRIORITY_PAIRS:
        hit = (a, b) in edge_set or (b, a) in edge_set
        print(f"  priority {a}↔{b}: {'OK' if hit else 'MISSING'}")


if __name__ == "__main__":
    main()
