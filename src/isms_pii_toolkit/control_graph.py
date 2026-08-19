from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

ControlStatus = Literal["implemented", "evidence_mapped", "study_mapped"]

_RELATION_EVIDENCE_PATH = (
    Path(__file__).resolve().parent / "data" / "problem_kb" / "relation_evidence.json"
)


@dataclass(frozen=True, slots=True)
class ControlCategory:
    area_id: str
    area_name: str
    category_id: str
    category_name: str
    control_titles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    title: str
    description: str
    artifact_refs: tuple[str, ...]
    control_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DomainScenario:
    id: str
    title: str
    description: str
    control_ids: tuple[str, ...]
    industries: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


# Backward-compatible alias used by older imports/docs.
RetailScenario = DomainScenario


CONTROL_CATEGORIES: tuple[ControlCategory, ...] = (
    ControlCategory(
        "1",
        "관리체계 수립 및 운영",
        "1.1",
        "관리체계 기반 마련",
        ("경영진의 참여", "최고책임자의 지정", "조직 구성", "범위 설정", "정책 수립", "자원 할당"),
    ),
    ControlCategory(
        "1",
        "관리체계 수립 및 운영",
        "1.2",
        "위험 관리",
        ("정보자산 식별", "현황 및 흐름분석", "위험 평가", "보호대책 선정"),
    ),
    ControlCategory(
        "1",
        "관리체계 수립 및 운영",
        "1.3",
        "관리체계 운영",
        ("보호대책 구현", "보호대책 공유", "운영현황 관리"),
    ),
    ControlCategory(
        "1",
        "관리체계 수립 및 운영",
        "1.4",
        "관리체계 점검 및 개선",
        ("법적 요구사항 준수 검토", "관리체계 점검", "관리체계 개선"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.1",
        "정책, 조직, 자산 관리",
        ("정책의 유지관리", "조직의 유지관리", "정보자산 관리"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.2",
        "인적 보안",
        ("주요 직무자 지정 및 관리", "직무 분리", "보안 서약", "인식제고 및 교육훈련", "퇴직 및 직무변경 관리", "보안 위반 시 조치"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.3",
        "외부자 보안",
        ("외부자 현황 관리", "외부자 계약 시 보안", "외부자 보안 이행 관리", "외부자 계약 변경 및 만료 시 보안"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.4",
        "물리 보안",
        ("보호구역 지정", "출입통제", "정보시스템 보호", "보호설비 운영", "보호구역 내 작업", "반출입 기기 통제", "업무환경 보안"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.5",
        "인증 및 권한관리",
        ("사용자 계정 관리", "사용자 식별", "사용자 인증", "비밀번호 관리", "특수 계정 및 권한관리", "접근권한 검토"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.6",
        "접근통제",
        ("네트워크 접근", "정보시스템 접근", "응용프로그램 접근", "데이터베이스 접근", "무선 네트워크 접근", "원격접근 통제", "인터넷 접속 통제"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.7",
        "암호화 적용",
        ("암호정책 적용", "암호키 관리"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.8",
        "정보시스템 도입 및 개발 보안",
        ("보안 요구사항 정의", "보안 요구사항 검토 및 시험", "시험과 운영 환경 분리", "시험 데이터 보안", "소스 프로그램 관리", "운영환경 이관"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.9",
        "시스템 및 서비스 운영관리",
        ("변경관리", "성능 및 장애관리", "백업 및 복구관리", "로그 및 접속기록 관리", "로그 및 접속기록 점검", "시간 동기화", "정보자산의 재사용 및 폐기"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.10",
        "시스템 및 서비스 보안관리",
        ("보안시스템 운영", "클라우드 보안", "공개서버 보안", "전자거래 및 핀테크 보안", "정보전송 보안", "업무용 단말기기 보안", "보조저장매체 관리", "패치관리", "악성코드 통제"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.11",
        "사고 예방 및 대응",
        ("사고 예방 및 대응체계 구축", "취약점 점검 및 조치", "이상행위 분석 및 모니터링", "사고 대응 훈련 및 개선", "사고 대응 및 복구"),
    ),
    ControlCategory(
        "2",
        "보호대책 요구사항",
        "2.12",
        "재해 복구",
        ("재해/재난 대비 안전조치", "재해 복구 시험 및 개선"),
    ),
    ControlCategory(
        "3",
        "개인정보 처리 단계별 요구사항",
        "3.1",
        "개인정보 수집 시 보호조치",
        ("개인정보 수집/이용", "개인정보 수집 제한", "주민등록번호 처리 제한", "민감정보 및 고유식별정보의 처리 제한", "개인정보 간접수집", "영상정보처리기기 설치/운영", "마케팅 목적의 개인정보 수집/이용"),
    ),
    ControlCategory(
        "3",
        "개인정보 처리 단계별 요구사항",
        "3.2",
        "개인정보 보유 및 이용 시 보호조치",
        ("개인정보 현황관리", "개인정보 품질보장", "이용자 단말기 접근 보호", "개인정보 목적 외 이용 및 제공", "가명정보 처리"),
    ),
    ControlCategory(
        "3",
        "개인정보 처리 단계별 요구사항",
        "3.3",
        "개인정보 제공 시 보호조치",
        ("개인정보 제3자 제공", "개인정보 처리 업무 위탁", "영업의 양도 등에 따른 개인정보 이전", "개인정보 국외이전"),
    ),
    ControlCategory(
        "3",
        "개인정보 처리 단계별 요구사항",
        "3.4",
        "개인정보 파기 시 보호조치",
        ("개인정보 파기", "처리목적 달성 후 보유 시 조치"),
    ),
    ControlCategory(
        "3",
        "개인정보 처리 단계별 요구사항",
        "3.5",
        "정보주체 권리보호",
        ("개인정보 처리방침 공개", "정보주체 권리보장", "정보주체에 대한 통지"),
    ),
)


EVIDENCES: tuple[Evidence, ...] = (
    Evidence(
        "test-coverage-ci",
        "테스트 커버리지와 CI 검증",
        "pytest와 GitHub Actions로 보호대책 구현 결과를 반복 점검하고 개선하는 증적입니다.",
        ("pyproject.toml", ".github/workflows/python-ci.yml", "tests/"),
        ("1.3.1", "1.4.2", "1.4.3", "2.8.2"),
    ),
    Evidence(
        "scope-risk-readme",
        "범위, 비목표, 운영 한계 문서화",
        "인증/권한, 감사추적 등 현재 구현하지 않은 범위를 명시하여 위험관리 관점의 한계를 남깁니다.",
        ("README.md",),
        ("1.1.4", "1.2.2", "1.2.3", "2.1.1"),
    ),
)


RETAIL_SCENARIOS: tuple[DomainScenario, ...] = (
    DomainScenario(
        "retail-cs-log-pii",
        "고객센터 상담 로그 개인정보 노출",
        "상담 로그와 운영 산출물에 주민등록번호, 휴대전화번호, 이메일이 섞이는 상황을 가정한 탐지/비식별화 흐름입니다.",
        ("1.2.1", "1.2.2", "1.2.3", "2.7.1", "2.9.4", "2.9.5", "2.11.3", "3.2.1", "3.4.1"),
        industries=("retail", "general"),
        tags=("log", "pii", "ops"),
    ),
    DomainScenario(
        "membership-data-lifecycle",
        "백화점 멤버십 개인정보 생명주기",
        "회원 가입부터 보유/이용, 제공, 파기, 정보주체 권리보장까지 개인정보 처리 단계별 요구사항을 연결합니다.",
        ("1.1.4", "1.2.2", "2.5.1", "2.6.4", "2.7.1", "3.1.1", "3.1.2", "3.2.1", "3.3.1", "3.4.1", "3.5.1", "3.5.2"),
        industries=("retail", "finance"),
        tags=("lifecycle", "pii"),
    ),
    DomainScenario(
        "external-developer-access",
        "외주 개발자 운영 시스템 접근",
        "외부 개발자가 운영 시스템과 개인정보 처리 시스템에 접근할 때 필요한 계약, 계정, 권한, 작업 이력 통제를 연결합니다.",
        ("2.3.1", "2.3.2", "2.3.3", "2.3.4", "2.5.1", "2.5.5", "2.5.6", "2.6.2", "2.6.3", "2.9.4"),
        industries=("retail", "technology", "public"),
        tags=("outsourcing", "access"),
    ),
    DomainScenario(
        "cloud-campaign-page",
        "클라우드 기반 이벤트 페이지 운영",
        "마케팅 이벤트 페이지를 클라우드에 배포할 때 보안 요구사항, 공개서버, 전송구간, 사고대응, 재해복구 통제를 연결합니다.",
        ("1.2.3", "2.8.1", "2.8.2", "2.8.6", "2.10.2", "2.10.3", "2.10.5", "2.11.2", "2.11.5", "2.12.1"),
        industries=("retail", "technology"),
        tags=("cloud", "public-server"),
    ),
    DomainScenario(
        "security-review-certification",
        "보안성 검토 및 인증 대응 증적 정리",
        "개발된 통제가 ISMS-P 심사에서 어떤 증적으로 설명될 수 있는지 정리하는 학습 시나리오입니다.",
        ("1.1.5", "1.2.4", "1.3.1", "1.4.1", "1.4.2", "1.4.3", "2.1.1", "2.8.1", "2.8.2", "2.11.4"),
        industries=("general", "retail", "technology", "healthcare", "public", "finance"),
        tags=("certification", "evidence"),
    ),
)

INDUSTRY_SCENARIOS: tuple[DomainScenario, ...] = (
    DomainScenario(
        "healthcare-emr-access",
        "의료 EMR/진료기록 접근 통제",
        "전자의무기록/진료지원 시스템에 대한 접근권한, 로그, 암호화, 위탁 운영을 연결하는 의료 특화 시나리오입니다.",
        ("1.1.4", "1.2.1", "1.2.2", "2.5.1", "2.5.6", "2.7.1", "2.7.2", "2.9.4", "2.9.5", "3.1.3", "3.2.1", "3.4.1"),
        industries=("healthcare",),
        tags=("emr", "rrn", "access"),
    ),
    DomainScenario(
        "public-citizen-service",
        "공공 민원/대민 서비스 개인정보 처리",
        "대민 창구/온라인 민원에서 수집/보유/파기/정보주체 권리와 외주 운영 경계를 연결합니다.",
        ("1.1.4", "1.1.5", "1.2.2", "2.3.1", "2.3.2", "2.5.1", "2.9.4", "3.1.1", "3.2.1", "3.4.1", "3.5.1", "3.5.2"),
        industries=("public",),
        tags=("citizen", "outsourcing"),
    ),
    DomainScenario(
        "finance-customer-data",
        "금융 고객정보/거래기록 보호",
        "고객 식별정보와 거래기록이 저장/전송/조회되는 경로에서 암호화, 접근통제, 로그, 현황관리를 연결합니다.",
        ("1.2.1", "1.2.3", "2.5.1", "2.5.3", "2.6.1", "2.7.1", "2.7.2", "2.9.4", "2.9.5", "3.1.3", "3.2.1", "3.2.2"),
        industries=("finance",),
        tags=("customer-data", "crypto"),
    ),
    DomainScenario(
        "tech-saas-tenant",
        "SaaS 멀티테넌트/클라우드 운영",
        "테넌트 분리, 관리자 접근, 클라우드 책임분담, 공개 API, 장애/사고 대응을 연결하는 IT/SaaS 시나리오입니다.",
        ("1.1.4", "1.2.3", "2.5.1", "2.6.2", "2.8.1", "2.9.4", "2.10.2", "2.10.3", "2.11.2", "2.11.5", "2.12.1", "3.2.1"),
        industries=("technology",),
        tags=("saas", "cloud", "tenant"),
    ),
)

SCENARIOS: tuple[DomainScenario, ...] = RETAIL_SCENARIOS + INDUSTRY_SCENARIOS


# Curated seed. Prefer relation_evidence.json when present (see load_manual_relations).
MANUAL_RELATIONS_SEED: dict[str, tuple[tuple[str, str], ...]] = {
    "1.1.4": (("1.2.1", "인증 범위가 자산 식별의 경계를 정합니다."), ("1.2.2", "범위 설정 후 개인정보 흐름을 분석합니다.")),
    "1.1.5": (("2.1.1", "정책 수립 결과는 운영 정책 유지관리로 이어집니다."), ("3.5.1", "개인정보 처리방침 공개와 정책 체계가 연결됩니다.")),
    "1.2.1": (("2.1.3", "식별된 정보자산은 자산관리 통제의 기준입니다."), ("3.2.1", "개인정보 현황관리의 입력값입니다.")),
    "1.2.2": (("3.2.1", "개인정보 흐름분석은 현황관리와 함께 관리됩니다."), ("3.3.2", "처리 흐름은 위탁 관계 식별로 이어집니다.")),
    "1.2.3": (("1.2.4", "평가된 위험을 기준으로 보호대책을 선정합니다."), ("2.8.1", "개발 보안 요구사항은 위험평가 결과를 반영합니다.")),
    "1.2.4": (("1.3.1", "선정한 보호대책은 구현 단계에서 실행됩니다."),),
    "1.3.1": (("1.4.2", "구현된 보호대책은 점검 대상이 됩니다."), ("2.8.2", "구현 결과는 보안 시험으로 검증합니다.")),
    "1.4.2": (("1.4.3", "점검 결과는 개선 활동으로 이어집니다."),),
    "2.5.1": (("2.5.6", "발급된 계정은 정기 권한검토 대상입니다."),),
    "2.5.3": (("2.5.4", "인증 수단은 비밀번호 정책과 함께 운영됩니다."),),
    "2.6.3": (("2.8.2", "응용프로그램 접근통제는 보안 시험으로 검증합니다."),),
    "2.7.1": (("2.7.2", "암호정책은 키 관리 기준과 함께 운영됩니다."), ("3.1.3", "주민등록번호 처리 제한과 암호화 통제가 연결됩니다."), ("3.2.1", "보유 개인정보 현황에 따라 암호화 대상을 정합니다.")),
    "2.8.1": (("2.8.2", "정의한 보안 요구사항은 검토와 시험으로 확인합니다."),),
    "2.9.4": (("2.9.5", "수집한 로그는 정기 점검 대상으로 이어집니다."), ("2.11.3", "로그는 이상행위 분석의 주요 입력입니다.")),
    "2.10.1": (("2.11.3", "보안시스템 운영 결과는 모니터링과 사고 분석으로 이어집니다."),),
    "2.10.2": (("2.12.1", "클라우드 운영은 재해/재난 대비와 함께 검토합니다."),),
    "2.11.1": (("2.11.4", "대응체계는 훈련으로 검증합니다."), ("2.11.5", "대응체계는 실제 사고 대응과 복구의 기준입니다.")),
    "2.12.1": (("2.12.2", "재해 대비 조치는 복구 시험으로 확인합니다."),),
    "3.1.1": (("3.2.1", "수집한 개인정보는 보유 현황으로 관리됩니다."),),
    "3.1.3": (("2.7.1", "주민등록번호 처리는 암호화 적용 검토 대상입니다."),),
    "3.2.1": (("3.4.1", "보유 현황은 파기 대상 식별의 기준입니다."), ("3.5.1", "처리 현황은 처리방침 공개와 연결됩니다.")),
    "3.2.5": (("2.7.1", "가명정보 처리 시 식별 가능성 완화를 위한 기술적 조치를 함께 검토합니다."),),
    "3.3.2": (("2.3.2", "개인정보 처리 위탁은 외부자 계약 보안과 연결됩니다."),),
    "3.4.1": (("2.9.7", "파기와 정보자산 재사용/폐기는 함께 증적화합니다."),),
    "3.5.2": (("3.5.3", "권리보장 처리 결과는 정보주체 통지와 연결됩니다."),),
}


@lru_cache(maxsize=1)
def load_relation_evidence() -> dict[str, object]:
    if not _RELATION_EVIDENCE_PATH.is_file():
        return {}
    return json.loads(_RELATION_EVIDENCE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_manual_relations() -> dict[str, tuple[tuple[str, str], ...]]:
    """Forward edges for graph/cascade. Prefer evidence file; else seed."""
    payload = load_relation_evidence()
    relation_map = payload.get("relationMap") if payload else None
    if isinstance(relation_map, dict) and relation_map:
        built: dict[str, list[tuple[str, str]]] = {}
        for source, rows in relation_map.items():
            pairs: list[tuple[str, str]] = []
            for row in rows or []:
                target = str(row.get("targetControlId") or "")
                reason = str(row.get("reason") or "").strip()
                if target and reason:
                    pairs.append((target, reason))
            if pairs:
                # de-dupe by target, keep first (strongest usually first from builder)
                seen: set[str] = set()
                deduped: list[tuple[str, str]] = []
                for target, reason in pairs:
                    if target in seen:
                        continue
                    seen.add(target)
                    deduped.append((target, reason))
                built[str(source)] = deduped
        return {k: tuple(v) for k, v in built.items()}
    return MANUAL_RELATIONS_SEED


def relation_evidence_for(source_id: str, target_id: str) -> dict[str, object] | None:
    payload = load_relation_evidence()
    for edge in payload.get("edges") or []:
        if str(edge.get("source")) == source_id and str(edge.get("target")) == target_id:
            return dict(edge)
        if str(edge.get("source")) == target_id and str(edge.get("target")) == source_id:
            return dict(edge)
    return None


def evidence_label_for_edge(source_id: str, target_id: str) -> str:
    edge = relation_evidence_for(source_id, target_id)
    if not edge:
        return "해석"
    level = str(edge.get("groundingLevel") or "")
    if level:
        return {
            "casebook_cite": "사례집 인용",
            "category_adjacent": "분류/시나리오 인접",
            "interpret": "결함우선/해석",
        }.get(level, level)
    types = []
    for item in edge.get("evidence") or []:
        t = str(item.get("type") or "")
        if t and t not in types:
            types.append(t)
    if not types:
        return str(edge.get("strength") or "해석")
    mapping = {
        "casebook": "사례집 인용",
        "defect_priority": "결함우선/해석",
        "manual": "수동(해석)",
        "official": "인증기준",
        "scenario": "분류/시나리오 인접",
        "category_adjacent": "분류/시나리오 인접",
    }
    return " / ".join(mapping.get(t, t) for t in types[:3])


def grounding_level_for_edge(source_id: str, target_id: str) -> str:
    """Return casebook_cite | category_adjacent | interpret."""
    edge = relation_evidence_for(source_id, target_id)
    if not edge:
        return "interpret"
    explicit = str(edge.get("groundingLevel") or "").strip()
    if explicit in {"casebook_cite", "category_adjacent", "interpret"}:
        return explicit
    types = {str(item.get("type") or "") for item in (edge.get("evidence") or [])}
    if "casebook" in types:
        return "casebook_cite"
    if "category_adjacent" in types or "scenario" in types or "official" in types:
        return "category_adjacent"
    return "interpret"


def grounding_statement_for_edge(source_id: str, target_id: str) -> str:
    level = grounding_level_for_edge(source_id, target_id)
    if level == "casebook_cite":
        return (
            f"이 연결({source_id}↔{target_id})은 사례집 텍스트 근거가 있는 유기 연결입니다."
        )
    if level == "category_adjacent":
        return (
            f"이 연결({source_id}↔{target_id})은 인증기준 분류·시나리오상 인접에 기반한 "
            f"실무상 유기 연결입니다."
        )
    return (
        f"이 연결({source_id}↔{target_id})은 결함 우선순위·수동 관계를 바탕으로 한 "
        f"해석형 유기 연결입니다. (결함 통계는 인과가 아니라 가중치로만 사용)"
    )


# Backward-compatible name: resolved at import from evidence file when present.
MANUAL_RELATIONS: dict[str, tuple[tuple[str, str], ...]] = load_manual_relations()


def _control_id(category_id: str, index: int) -> str:
    return f"{category_id}.{index}"


def _default_tags(category: ControlCategory, title: str) -> list[str]:
    tags = [category.area_name, category.category_name]
    for keyword in ("개인정보", "암호", "접근", "로그", "외부자", "클라우드", "사고", "위험", "정책"):
        if keyword in title or keyword in category.category_name:
            tags.append(keyword)
    return list(dict.fromkeys(tags))


def _evidence_ids_by_control() -> dict[str, list[str]]:
    evidence_ids: dict[str, list[str]] = {}
    for evidence in EVIDENCES:
        for control_id in evidence.control_ids:
            evidence_ids.setdefault(control_id, []).append(evidence.id)
    return evidence_ids


def _scenario_ids_by_control() -> dict[str, list[str]]:
    scenario_ids: dict[str, list[str]] = {}
    for scenario in SCENARIOS:
        for control_id in scenario.control_ids:
            scenario_ids.setdefault(control_id, []).append(scenario.id)
    return scenario_ids


def _implementation_status(control_id: str, evidence_ids: list[str], scenario_ids: list[str]) -> ControlStatus:
    implemented_evidence = {"test-coverage-ci"}
    if implemented_evidence.intersection(evidence_ids):
        return "implemented"
    if evidence_ids:
        return "evidence_mapped"
    if scenario_ids:
        return "study_mapped"
    return "study_mapped"


def _study_note(title: str, category: ControlCategory, status: ControlStatus) -> str:
    if status == "implemented":
        return f"{title} 통제를 현재 API, 테스트, 문서 증적 중 하나와 연결해 구현 관점으로 학습했습니다."
    if status == "evidence_mapped":
        return f"{title} 통제는 문서화된 범위/위험/운영 한계 증적과 연결해 인증 대응 관점으로 정리했습니다."
    return f"{title} 통제는 {category.category_name} 흐름에서 다른 통제와 함께 검토할 학습 항목으로 남겼습니다."


def _build_relation_map() -> dict[str, list[dict[str, str]]]:
    relation_map: dict[str, list[dict[str, str]]] = {}
    for source_id, targets in load_manual_relations().items():
        for target_id, reason in targets:
            relation_map.setdefault(source_id, []).append({"targetControlId": target_id, "reason": reason})
            relation_map.setdefault(target_id, []).append({"targetControlId": source_id, "reason": reason})

    for scenario in SCENARIOS:
        for previous_id, next_id in zip(scenario.control_ids, scenario.control_ids[1:]):
            reason = f"{scenario.title} 시나리오에서 함께 검토되는 인접 통제입니다."
            relation_map.setdefault(previous_id, []).append({"targetControlId": next_id, "reason": reason})
            relation_map.setdefault(next_id, []).append({"targetControlId": previous_id, "reason": reason})

    for control_id, relations in relation_map.items():
        deduped: dict[str, str] = {}
        for relation in relations:
            target_id = relation["targetControlId"]
            if target_id != control_id:
                deduped.setdefault(target_id, relation["reason"])
        relation_map[control_id] = [
            {"targetControlId": target_id, "reason": reason}
            for target_id, reason in sorted(deduped.items(), key=lambda item: _sort_key(item[0]))
        ]
    return relation_map


def _sort_key(control_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in control_id.split("."))


@lru_cache(maxsize=1)
def list_controls() -> tuple[dict[str, object], ...]:
    evidence_by_control = _evidence_ids_by_control()
    scenario_by_control = _scenario_ids_by_control()
    relations = _build_relation_map()
    controls: list[dict[str, object]] = []

    for category in CONTROL_CATEGORIES:
        for index, title in enumerate(category.control_titles, start=1):
            control_id = _control_id(category.category_id, index)
            evidence_ids = evidence_by_control.get(control_id, [])
            scenario_ids = scenario_by_control.get(control_id, [])
            status = _implementation_status(control_id, evidence_ids, scenario_ids)
            controls.append(
                {
                    "id": control_id,
                    "areaId": category.area_id,
                    "areaName": category.area_name,
                    "categoryId": category.category_id,
                    "categoryName": category.category_name,
                    "title": title,
                    "tags": _default_tags(category, title),
                    "relatedControlIds": [item["targetControlId"] for item in relations.get(control_id, [])],
                    "relations": relations.get(control_id, []),
                    "evidenceIds": evidence_ids,
                    "scenarioIds": scenario_ids,
                    "implementationStatus": status,
                    "studyNote": _study_note(title, category, status),
                }
            )

    return tuple(sorted(controls, key=lambda control: _sort_key(str(control["id"]))))


def find_control(control_id: str) -> dict[str, object] | None:
    return next((control for control in list_controls() if control["id"] == control_id), None)


def filter_controls(area_id: str | None = None, category_id: str | None = None, query: str | None = None) -> list[dict[str, object]]:
    normalized_query = query.strip().lower() if query else None
    controls = list(list_controls())
    if area_id:
        controls = [control for control in controls if control["areaId"] == area_id]
    if category_id:
        controls = [control for control in controls if control["categoryId"] == category_id]
    if normalized_query:
        controls = [
            control
            for control in controls
            if normalized_query in str(control["id"]).lower()
            or normalized_query in str(control["title"]).lower()
            or normalized_query in str(control["categoryName"]).lower()
            or any(normalized_query in str(tag).lower() for tag in control["tags"])
        ]
    return controls


def list_evidences() -> list[dict[str, object]]:
    return [
        {
            "id": evidence.id,
            "title": evidence.title,
            "description": evidence.description,
            "artifactRefs": list(evidence.artifact_refs),
            "controlIds": list(evidence.control_ids),
        }
        for evidence in EVIDENCES
    ]


def list_scenarios() -> list[dict[str, object]]:
    return [
        {
            "id": scenario.id,
            "title": scenario.title,
            "description": scenario.description,
            "controlIds": list(scenario.control_ids),
            "industries": list(scenario.industries),
            "tags": list(scenario.tags),
        }
        for scenario in SCENARIOS
    ]


def find_scenario(scenario_id: str) -> dict[str, object] | None:
    return next((scenario for scenario in list_scenarios() if scenario["id"] == scenario_id), None)


def graph_for_scenario(scenario_id: str | None = None) -> dict[str, object]:
    controls = list_controls()
    if scenario_id:
        scenario = find_scenario(scenario_id)
        if scenario is None:
            return {"nodes": [], "edges": [], "scenario": None}
        allowed_ids = set(scenario["controlIds"])
        scenario_payload: dict[str, object] | None = scenario
    else:
        allowed_ids = {str(control["id"]) for control in controls}
        scenario_payload = None

    nodes = [control for control in controls if control["id"] in allowed_ids]
    edge_keys: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []
    for control in nodes:
        source_id = str(control["id"])
        for relation in control["relations"]:
            target_id = relation["targetControlId"]
            if target_id not in allowed_ids:
                continue
            edge_key = tuple(sorted((source_id, target_id)))
            if edge_key in edge_keys:
                continue
            edge_keys.add(edge_key)
            edges.append({"source": source_id, "target": target_id, "reason": relation["reason"]})

    return {"nodes": nodes, "edges": edges, "scenario": scenario_payload}


def _relation_reason(source_id: str, target_id: str) -> str | None:
    control = find_control(source_id)
    if control is None:
        return None
    for relation in control.get("relations", []):
        if relation["targetControlId"] == target_id:
            return str(relation["reason"])
    return None


def trace_scenario(scenario_id: str) -> dict[str, object] | None:
    scenario = find_scenario(scenario_id)
    if scenario is None:
        return None

    control_by_id = {str(control["id"]): control for control in list_controls()}
    steps: list[dict[str, object]] = []
    control_ids = list(scenario["controlIds"])

    for index, control_id in enumerate(control_ids):
        control = control_by_id.get(control_id)
        if control is None:
            continue

        link_reason = None
        if index > 0:
            previous_id = control_ids[index - 1]
            link_reason = _relation_reason(previous_id, control_id)
            if link_reason is None:
                link_reason = f"{scenario['title']} 시나리오에서 함께 검토되는 인접 통제입니다."

        steps.append(
            {
                "order": index + 1,
                "controlId": control_id,
                "title": control["title"],
                "categoryName": control["categoryName"],
                "areaName": control["areaName"],
                "implementationStatus": control["implementationStatus"],
                "studyNote": control["studyNote"],
                "evidenceIds": control["evidenceIds"],
                "relatedControlIds": control["relatedControlIds"],
                "linkFromPrevious": link_reason,
            }
        )

    return {"scenario": scenario, "steps": steps}


def dashboard_stats() -> dict[str, object]:
    controls = list_controls()
    status_counts = Counter(str(control["implementationStatus"]) for control in controls)
    area_counts = Counter(str(control["areaName"]) for control in controls)
    return {
        "totalControls": len(controls),
        "implemented": status_counts.get("implemented", 0),
        "evidenceMapped": status_counts.get("evidence_mapped", 0),
        "studyMapped": status_counts.get("study_mapped", 0),
        "scenarioCount": len(SCENARIOS),
        "evidenceCount": len(EVIDENCES),
        "areaBreakdown": dict(area_counts),
    }
