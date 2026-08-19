from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .control_graph import find_control
from .organization_profile import OrganizationContext
from .profile_prioritization import bundle_priority_delta

AssessmentLevel = Literal["unknown", "none", "partial", "done", "evidenced"]
BundleSource = Literal["curated", "graph_relation", "scenario_flow", "category_set"]

WEAK_LEVELS: frozenset[str] = frozenset({"none", "partial"})

LEVEL_LABEL: dict[str, str] = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
}

SOURCE_LABEL: dict[str, str] = {
    "curated": "수작업 복합 패턴",
    "graph_relation": "통제 그래프 연결",
    "scenario_flow": "시나리오 흐름",
    "category_set": "분류 심층 힌트",
}


@dataclass(frozen=True, slots=True)
class MultiGapBundle:
    id: str
    title: str
    theme: str
    required_controls: tuple[str, ...]
    min_match: int
    partial_min: int
    priority: int
    severity: str
    summary: str
    compound_analysis: str
    operational_impact: str
    audit_impact: str
    incident_scenarios: tuple[str, ...]
    remediation_path: tuple[str, ...]
    related_scenario_ids: tuple[str, ...] = ()
    source: BundleSource = "curated"
    basis: str = ""
    evidence: tuple[str, ...] = ()


MULTIGAP_BUNDLES: tuple[MultiGapBundle, ...] = (
    MultiGapBundle(
        id="crypto-log-pii",
        title="암호화/키관리/로그 보호 공백",
        theme="기밀성/추적성 동시 붕괴",
        required_controls=("2.7.1", "2.7.2", "2.9.4", "2.9.5"),
        min_match=3,
        partial_min=2,
        priority=10,
        severity="critical",
        summary=(
            "저장/전송 암호화, 키관리, 로그 수집/점검이 동시에 약하면 "
            "개인정보가 평문으로 남고, 유출 후에도 원인/범위/시점을 복원하기 어렵습니다."
        ),
        compound_analysis=(
            "암호정책(2.7.1)과 키관리(2.7.2)가 함께 미흡하면 DB/파일/전송 구간 어디에 평문이 남는지 "
            "조직 스스로 설명하기 어렵습니다. 여기에 로그 수집(2.9.4)/로그 점검(2.9.5)까지 비어 있으면, "
            "설령 상담/API/배치 로그에 주민번호/연락처가 기록되더라도 탐지/마스킹/보관/검토의 어느 단계에서도 "
            "통제가 작동하지 않는 상태가 됩니다. DB는 암호화돼 있어도 애플리케이션 로그/디버그 출력/CSV 덤프처럼 "
            "비정형 평문 구간은 별도 보호 체계 없이 방치될 수 있으며, 이 조합은 PII 유출의 전형적인 사각지대입니다."
        ),
        operational_impact=(
            "운영 관점에서는 장애 분석/개발 디버깅 과정에서 request body, 상담 내용, 사용자 입력값이 "
            "로그에 그대로 남고, 암호화/마스킹/키 분리가 없어 내부 접근자/외주/SIEM 운영자까지 평문 PII에 "
            "노출될 수 있습니다. 사고 발생 시 '언제부터/누가/어떤 시스템에서' 유출됐는지 로그로 증명할 수 없어 "
            "통지/신고/피해 범위 산정이 지연됩니다."
        ),
        audit_impact=(
            "심사에서는 2.7 암호화, 2.9 운영관리, 3.2 개인정보 현황/보호조치를 연속 샘플링합니다. "
            "암호정책서/키관리 절차/로그 보관 정책/월간 로그 점검표/마스킹 적용 화면을 동시에 요구받을 때 "
            "하나라도 연결되지 않으면 '형식적 암호화' 또는 '로그 통제 미작동'으로 중/대 결함 판정을 받기 쉽습니다."
        ),
        incident_scenarios=(
            "고객센터 상담 로그에 주민번호/휴대전화가 평문 기록됐으나 암호화 정책/로그 마스킹/수집 범위가 없어 "
            "유출 사실을 인지하지 못한 채 6개월간 보관",
            "개발자가 디버그 모드로 배포한 API가 request body 전체를 로그에 남겼고, 키가 소스에 하드코딩돼 "
            "로그 유출과 함께 암호화 토큰까지 일괄 복호화 가능",
            "SIEM에는 인증 로그만 수집되고 애플리케이션 로그는 누락돼, PII 노출 구간의 접속기록/처리기록을 "
            "심사/수사 시 제출하지 못함",
            "로그 점검(2.9.5) 없이 디스크 풀/로테이션 오류로 접속기록이 유실, 개인정보보호위원회 조사에서 "
            "사실관계 규명 지적",
        ),
        remediation_path=(
            "암호정책서에 저장/전송/로그 마스킹 대상과 알고리즘을 정의하고 DB/TLS/로그 파이프라인 적용 화면을 증적으로 연결",
            "키를 KMS/HSM/비밀관리로 분리하고 소스/환경변수 하드코딩 점검표를 분기 운영",
            "개인정보 처리 시스템/관리자/Bastion/API gateway 로그 수집 범위와 보관기간을 문서화",
            "월간 로그 수집율/미수집 시스템/PII 패턴 샘플링 점검표(2.9.5)와 PII scan 결과를 연결",
        ),
        related_scenario_ids=("retail-cs-log-pii",),
    ),
    MultiGapBundle(
        id="log-pii-lifecycle",
        title="로그/개인정보 생명주기/마스킹 겹침",
        theme="식별/현황/보호조치 단절",
        required_controls=("2.9.4", "2.9.5", "3.2.1", "3.2.3"),
        min_match=3,
        partial_min=2,
        priority=9,
        severity="critical",
        summary=(
            "로그에 남는 개인정보를 현황표/마스킹 정책/점검 체계와 연결하지 못하면 "
            "'어디에 무엇이 있는지'조차 설명할 수 없습니다."
        ),
        compound_analysis=(
            "개인정보 보유 현황(3.2.1)에 로그/백업/상담 녹취/텍스트 덤프가 빠져 있고, "
            "로그 관리(2.9.4)/로그 점검(2.9.5)이 미흡하면, 실제 운영에서는 평문 PII가 시스템 밖으로 "
            "새는데 문서상으로는 '관리 중'인 것처럼 보이는 불일치가 생깁니다. "
            "가명/마스킹(3.2.3)까지 비어 있으면 로그/리포트/분석용 데이터에 식별정보가 그대로 남습니다."
        ),
        operational_impact=(
            "마케팅/CS/데이터팀이 각자 로그/CSV/대시보드에 개인정보를 쌓아도 중앙에서 파악/통제하지 못합니다. "
            "탈퇴/파기 요청 시 DB만 지우고 로그/백업/SIEM에는 잔존하는 불완전 파기가 반복됩니다."
        ),
        audit_impact=(
            "3.2 영역 심사에서 현황표/흐름도/마스킹 적용 증적을 요구할 때 로그/백업 누락이 발견되면 "
            "2.9 로그 통제와 함께 연쇄 결함으로 확대됩니다. 개인정보 처리방침/내부 기준과 실제 보관 위치 불일치 지적을 받습니다."
        ),
        incident_scenarios=(
            "멤버십 탈퇴 후 DB 레코드는 삭제됐으나 상담 로그/백업 테이프에 연락처/주소가 남아 재식별 가능",
            "BI 팀 export 파일에 마스킹 없이 이메일/전화번호가 포함됐으나 3.2.3/3.2.1에 해당 자산이 없음",
            "로그 점검 없이 Elasticsearch에 PII가 1년간 적재, GDPR/개인정보보호법 보관/파기 위반 소지",
        ),
        remediation_path=(
            "현황표에 애플리케이션 로그/백업/외부 SaaS/상담 녹취를 포함하고 분기 갱신",
            "로그/리포트/분석용 데이터에 대한 마스킹/토큰화 기준을 3.2.3과 2.9.4에 동시 반영",
            "PII 1차 스캔(예: sample.log) 결과를 로그 점검표 항목으로 편입",
        ),
        related_scenario_ids=("membership-data-lifecycle", "retail-cs-log-pii"),
    ),
    MultiGapBundle(
        id="access-crypto-log",
        title="접근권한/DB접근/암호화/로그 4중 공백",
        theme="권한/기밀성/감사추적 동시 실패",
        required_controls=("2.5.6", "2.6.4", "2.7.1", "2.9.4"),
        min_match=3,
        partial_min=2,
        priority=9,
        severity="critical",
        summary=(
            "누가 DB/로그에 접근했는지 모르고, 데이터는 평문이며, 접근기록도 없으면 "
            "내부자/외주에 의한 대량 유출을 막거나 사후 추적할 수 없습니다."
        ),
        compound_analysis=(
            "접근권한 검토(2.5.6)와 DB 접근통제(2.6.4)가 약한 상태에서 암호화(2.7.1)까지 미흡하면, "
            "운영/개발/외주 계정이 과다 권한으로 DB를 직접 조회할 수 있습니다. "
            "로그(2.9.4)까지 없으면 '누가 언제 어떤 데이터를 봤는지' 증명 불가능합니다. "
            "네 가지 갭이 겹치면 내부자 유출/권한 상승/DB 덤프 사고의 완벽한 조건이 됩니다."
        ),
        operational_impact=(
            "DBA/개발자/외주가 bastion 없이 운영 DB에 접속해 CSV export 후 유출해도 탐지/차단/추적이 어렵습니다. "
            "퇴직자/계약 종료 외주 계정이 방치되면 장기간 잔존 접근 경로가 됩니다."
        ),
        audit_impact=(
            "2.5/2.6/2.7/2.9를 묶어 샘플링하는 심사 패턴에 취약합니다. "
            "권한 매트릭스/DB ACL/암호화 설정/DB 접속 로그를 교차 대조할 때 연쇄 결함으로 보고됩니다."
        ),
        incident_scenarios=(
            "외주 개발자 퇴사 후 VPN/DB 계정 미회수, 3개월간 회원 DB 조회 후 유출",
            "관리자 공유 계정으로 야간 대량 SELECT 실행, 접속기록/DB 감사로그 미수집",
            "암호화 미적용 컬럼에 주민번호 저장, 백업 파일까지 평문으로 외부 반출",
        ),
        remediation_path=(
            "운영 DB 직접 접근 차단, bastion/4-eyes/MFA 적용",
            "분기별 권한 검토와 DB 계정/역할 매트릭스 운영",
            "DB/관리자/Bastion 접속 로그 SIEM 연동 및 보관기간 정책화",
        ),
        related_scenario_ids=("external-developer-access",),
    ),
    MultiGapBundle(
        id="mgmt-foundation",
        title="관리체계 기반/범위/자산/점검 공백",
        theme="인증 근거 상실",
        required_controls=("1.1.4", "1.1.5", "1.2.1", "1.4.2"),
        min_match=3,
        partial_min=2,
        priority=8,
        severity="high",
        summary=(
            "범위/정책/자산/점검이 동시에 없으면 이후 모든 기술/개인정보 통제의 "
            "선정 근거와 이행 증적을 심사에서 설명할 수 없습니다."
        ),
        compound_analysis=(
            "인증 범위(1.1.4)가 불명확하고 정책(1.1.5)/자산 식별(1.2.1)이 없으며 자체 점검(1.4.2)도 없으면, "
            "심사 초기 단계에서 '무엇을 왜 보호하는지'부터 질의받습니다. "
            "2.x/3.x 통제를 아무리 구현해도 위험평가/보호대책 선정 근거가 없어 형식적 이행으로 평가됩니다."
        ),
        operational_impact=(
            "신규 서비스/클라우드/외주 시스템이 범위 밖으로 방치되거나, 반대로 범위만 넓고 실제 통제는 없습니다. "
            "팀별로 제각각 보안 기준을 적용해 CS/멤버십/마케팅 로그 PII 문제가 반복됩니다."
        ),
        audit_impact=(
            "1영역 집중 심사에서 범위서/정책 승인/자산 목록/자체점검표 불일치 시 후속 영역 샘플링 범위가 확대됩니다."
        ),
        incident_scenarios=(
            "클라우드 이벤트 페이지가 인증 범위에 없어 개인정보 수집/로그 보관이 통제 밖",
            "자산 목록에 상담 로그/S3 버킷 누락, 유출 후 '관리 대상 아님' 주장 불가",
            "자체 점검 없이 동일 결함이 갱신심사까지 방치",
        ),
        remediation_path=(
            "인증 범위서에 서비스/시스템/조직/물리/클라우드 경계 명시",
            "정보보호/개인정보보호 정책/지침 승인 및 버전 관리",
            "정보자산/개인정보 흐름도 작성, 분기 자체점검/CAR 추적",
        ),
        related_scenario_ids=("security-review-certification", "cloud-campaign-page"),
    ),
    MultiGapBundle(
        id="external-vendor-chain",
        title="외부자/계약/접근/로그 연쇄 취약",
        theme="공급망/외주 경유 유출",
        required_controls=("2.3.2", "2.3.3", "2.6.6", "2.9.4"),
        min_match=3,
        partial_min=2,
        priority=8,
        severity="high",
        summary=(
            "외주/수탁사 보안 조항/이행 점검/원격접근/로그가 동시에 약하면 "
            "제3자 경유 유출과 책임 추적 불가가 동시에 발생합니다."
        ),
        compound_analysis=(
            "외부자 계약 보안(2.3.2)/이행 관리(2.3.3) 없이 원격접근(2.6.6)만 열려 있고 로그(2.9.4)도 없으면, "
            "외주 개발자/CS BPO/클라우드 MSP가 운영망에 접속해도 계약상 의무/접속기록/사고 통지 체계가 작동하지 않습니다."
        ),
        operational_impact=(
            "외주 VPN/공유 계정/장기 유효 토큰이 방치되고, 계약 만료 후에도 접근이 남습니다. "
            "수탁사 사고 시 '우리가 통제 주체인지 수탁사인지' 책임 소재가 불분명해집니다."
        ),
        audit_impact=(
            "2.3/2.6/3.3 위탁 관리와 연계 질의. 계약서/점검표/접속로그/사고통지 조항을 동시에 요구받습니다."
        ),
        incident_scenarios=(
            "외주 개발자 노트북 분실, VPN/Git/운영 bastion 자격증명 동시 유출",
            "CS 위탁사 상담 시스템에서 녹취/로그를 자사로 전송하지 않아 유출 범위 규명 불가",
            "클라우드 MSP root key 공유, 접속기록 미보관",
        ),
        remediation_path=(
            "외주/수탁 계약에 보안/재위탁/파기/사고통지/로그 제공 조항 포함",
            "원격접근 MFA/기간 제한/bastion 경유",
            "외부자 접속 로그 수집/분기 점검/계약 만료 시 자동 회수",
        ),
        related_scenario_ids=("external-developer-access",),
    ),
    MultiGapBundle(
        id="incident-log-chain",
        title="사고대응/로그/통지/개선 겹침",
        theme="침해 후 대응 마비",
        required_controls=("2.11.1", "2.11.5", "2.9.4", "3.5.4"),
        min_match=3,
        partial_min=2,
        priority=8,
        severity="critical",
        summary=(
            "사고 대응 체계/로그/정보주체 통지가 동시에 약하면 유출 인지/통지/복구/재발방지가 모두 지연됩니다."
        ),
        compound_analysis=(
            "사고 예방/대응체계(2.11.1)와 대응/복구(2.11.5)가 있어도 로그(2.9.4)가 없으면 "
            "침해 범위/시점/경로를 특정할 수 없습니다. 정보주체 통지(3.5.4)까지 미흡하면 "
            "법적 통지 의무/과징금 리스크가 겹칩니다. 네 통제가 동시에 약하면 '사고가 나도 대응 못 하는 조직'으로 보입니다."
        ),
        operational_impact=(
            "로그 PII 유출을 CS/보안팀이 인지하지 못하거나, 인지해도 통지 대상/내용/시한을 정하지 못합니다. "
            "모의훈련 없이 실제 사고 시 연락망/에스컬레이션이 작동하지 않습니다."
        ),
        audit_impact=(
            "2.11/2.9/3.5 연계 심사. 대응 절차서/훈련 결과/로그 샘플/통지 기록을 동시 요구합니다."
        ),
        incident_scenarios=(
            "로그에서 PII 유출 패턴 발견됐으나 대응 조직/Playbook 없어 72시간 통지 시한 초과",
            "백업/로그 유실로 침해 범위 산정 불가, 정보주체 통지 문구 작성 불가",
            "동일 유형 사고 반복, CAR/재발방지(1.4.3) 미연계",
        ),
        remediation_path=(
            "개인정보 유출 시나리오 Playbook/RACI/연락망 정비",
            "로그/접속기록 보존으로 침해 타임라인 복원 가능하게 구성",
            "통지 템플릿/SLA/권리행사 채널과 연계",
        ),
        related_scenario_ids=("retail-cs-log-pii",),
    ),
    MultiGapBundle(
        id="dev-change-crypto",
        title="개발보안/변경관리/암호화 배포 겹침",
        theme="안전하지 않은 배포 파이프라인",
        required_controls=("2.8.2", "2.8.3", "2.9.1", "2.7.1"),
        min_match=3,
        partial_min=2,
        priority=7,
        severity="high",
        summary=(
            "보안 시험/환경 분리/변경관리/암호화가 동시에 약하면 "
            "로그 마스킹/암호화 로직이 검증 없이 운영에 반영됩니다."
        ),
        compound_analysis=(
            "보안 요구사항 검토(2.8.2)/시험/운영 분리(2.8.3) 없이 변경관리(2.9.1)만 형식적으로 있고 "
            "암호화(2.7.1)도 미흡하면, 긴급 패치/핫픽스 과정에서 PII 처리 코드/로그 설정이 깨진 채 배포됩니다."
        ),
        operational_impact=(
            "스테이징에서는 마스킹되는데 운영만 빠지는 설정 drift. "
            "CI 테스트는 통과하지만 로그/예외 메시지에 PII가 남는 회귀가 반복됩니다."
        ),
        audit_impact=(
            "2.8/2.9/2.7 교차 심사. 변경 요청서/보안 테스트/환경 분리/배포 승인/암호화 설정 대조."
        ),
        incident_scenarios=(
            "로그 마스킹 PR이 변경관리 없이 야간 배포, 롤백 실패로 48시간 평문 로그 적재",
            "시험 DB에 실개인정보 사용(2.8.4) + 암호화 미적용으로 개발자 PC 유출",
            "운영 이관(2.8.6) 체크리스트 누락으로 TLS/암호화 옵션 미적용",
        ),
        remediation_path=(
            "SDLC 보안 게이트/CI pytest/정적 분석을 2.8.2 증적으로 연결",
            "변경관리 양식에 PII/암호화/로그 영향 항목 포함",
            "환경별 구성 차이표/배포 체크리스트 운영",
        ),
        related_scenario_ids=("external-developer-access",),
    ),
    MultiGapBundle(
        id="rrn-collection-storage",
        title="주민번호/수집/암호화/파기 겹침",
        theme="고유식별정보 전 구간 위험",
        required_controls=("3.1.3", "2.7.1", "3.2.1", "3.4.1"),
        min_match=3,
        partial_min=2,
        priority=9,
        severity="critical",
        summary=(
            "주민번호 처리 제한/암호화/현황/파기가 동시에 약하면 "
            "법령 위반/과징금/형사 리스크가 겹칩니다."
        ),
        compound_analysis=(
            "주민번호 처리 제한(3.1.3) 위반 가능성에 암호화(2.7.1)까지 없고, "
            "현황(3.2.1)에 로그/백업이 빠지며 파기(3.4.1)도 미흡하면, "
            "수집/저장/로그/백업/파기 전 구간에서 주민번호가 무방비로 남습니다."
        ),
        operational_impact=(
            "이벤트/CS/멤버십에서 불필요한 주민번호 수집, 로그/CSV/백업에 잔존, 탈퇴 후에도 복원 가능."
        ),
        audit_impact=(
            "3.1/3.2/3.4/2.7 집중 심사. 수집 화면/법적 근거/암호화/파기 로그/현황표 교차 확인."
        ),
        incident_scenarios=(
            "프로모션 페이지에서 주민번호 수집, DB/로그/백업 삼중 평문 보관",
            "탈퇴 후 DB 삭제만 하고 로그/백업에 주민번호 잔존",
            "법적 근거 없이 주민번호 수집 후 암호화/접근통제 없이 외주에 전달",
        ),
        remediation_path=(
            "주민번호 수집 금지 원칙 점검, 불가피 시 법령 근거/별도 보관/암호화",
            "현황표/흐름도에 로그/백업 포함",
            "파기 범위에 로그/백업/위탁 반환 데이터 포함",
        ),
        related_scenario_ids=("cloud-campaign-page", "membership-data-lifecycle"),
    ),
    MultiGapBundle(
        id="backup-disposal-residual",
        title="백업/암호화/파기/로그 잔존",
        theme="삭제해도 남는 개인정보",
        required_controls=("2.9.3", "2.7.1", "3.4.1", "3.4.2"),
        min_match=3,
        partial_min=2,
        priority=7,
        severity="high",
        summary=(
            "백업/암호화/파기/파기 로그가 동시에 약하면 "
            "탈퇴/파기 후에도 백업/로그/스냅샷에 개인정보가 무기한 잔존합니다."
        ),
        compound_analysis=(
            "백업(2.9.3)은 되지만 암호화(2.7.1)/파기(3.4.1/3.4.2)가 없으면 "
            "운영 DB에서 삭제해도 백업 테이프/스냅샷/DR site에 PII가 그대로 남습니다. "
            "로그까지 포함하지 않으면 '완전 파기'를 증명할 수 없습니다."
        ),
        operational_impact=(
            "GDPR/개인정보보호법 삭제 요청 처리 후에도 백업 복원으로 재등장. "
            "랜섬웨어 복구 시 파기된 회원 데이터까지 함께 복원."
        ),
        audit_impact=(
            "3.4/2.9/2.7 연계. 파기 기준/실행 로그/백업 보관/암호화/복구 시험 기록 대조."
        ),
        incident_scenarios=(
            "회원 탈퇴 파기 후 90일 백업 retention으로 주민번호 복원 가능",
            "파기 로그 없이 '삭제 완료' 보고, 심사에서 백업 샘플 복호화 후 PII 발견",
            "클라우드 스냅샷/AMI에 DB 디스크 이미지 장기 보관",
        ),
        remediation_path=(
            "파기 범위에 DB/로그/백업/캐시/위탁 반환 포함",
            "백업 암호화/retention/파기 연계 정책",
            "파기 실행/검증/승인 3단계 기록",
        ),
        related_scenario_ids=("membership-data-lifecycle",),
    ),
    MultiGapBundle(
        id="cloud-public-exposure",
        title="클라우드/공개서버/전송/로그 노출",
        theme="외부 노출면 확대",
        required_controls=("2.10.2", "2.10.3", "2.10.5", "2.9.4"),
        min_match=3,
        partial_min=2,
        priority=7,
        severity="high",
        summary=(
            "클라우드/공개서버/전송/로그 통제가 동시에 약하면 "
            "이벤트/캠페인/API가 인터넷에 노출되고 PII가 평문으로 흐릅니다."
        ),
        compound_analysis=(
            "클라우드(2.10.2)/공개서버(2.10.3) 보안과 전송(2.10.5)/로그(2.9.4)가 함께 약하면, "
            "S3 public bucket/WAF 미적용/TLS 미설정/access log 미수집이 겹쳐 "
            "캠페인 페이지/API gateway에서 수집한 PII가 외부에 노출될 수 있습니다."
        ),
        operational_impact=(
            "마케팅이 급히 올린 이벤트 페이지에 HTTPS/입력값 검증/로그 마스킹 없음. "
            "클라우드 설정 drift로 storage public 전환."
        ),
        audit_impact=(
            "2.10/3.1/2.9 교차. 클라우드 CSPM/WAF/TLS/로그/수집 동의 화면 동시 확인."
        ),
        incident_scenarios=(
            "이벤트 API가 HTTP로 PII 전송, CDN/proxy 로그에 평문 기록",
            "S3 버킷 public 설정으로 신청 CSV 유출",
            "WAF 없이 SQLi/IDOR로 회원 정보 유출, access log 없음",
        ),
        remediation_path=(
            "클라우드/공개서버 보안 baseline/CSPM/분기 점검",
            "TLS/mTLS/API gateway 로그/마스킹",
            "캠페인/랜딩 인프라를 인증 범위/자산 목록에 포함",
        ),
        related_scenario_ids=("cloud-campaign-page",),
    ),
    MultiGapBundle(
        id="risk-treatment-gap",
        title="위험평가/보호대책/구현 단절",
        theme="근거 없는 통제",
        required_controls=("1.2.3", "1.2.4", "1.3.1", "1.4.2"),
        min_match=3,
        partial_min=2,
        priority=7,
        severity="high",
        summary=(
            "위험평가/보호대책 선정/구현/점검이 끊기면 "
            "로그 PII/암호화 등 기술 통제가 '왜 필요한지' 설명되지 않습니다."
        ),
        compound_analysis=(
            "위험평가(1.2.3)/보호대책 선정(1.2.4) 없이 구현(1.3.1)만 하거나, "
            "자체 점검(1.4.2)이 없으면, PII scan/암호화 도입도 '프로젝트'로만 남고 "
            "조직 통제로 정착하지 못합니다."
        ),
        operational_impact=(
            "로그 PII 문제를 알지만 위험 등급/예산/담당/일정이 없어 개선이 무기한 연기."
        ),
        audit_impact=(
            "1.2/1.3/1.4 연속 질의. 위험평가표/보호대책 매트릭스/이행 계획/점검표 연결 요구."
        ),
        incident_scenarios=(
            "로그 PII 유출 사고 후 '위험평가에 없던 자산'이라 대응 우선순위 미정",
            "암호화 프로젝트만 완료하고 키관리/로그/접근통제는 미연계",
        ),
        remediation_path=(
            "로그/텍스트 덤프 PII를 정보자산/위험평가 항목에 명시",
            "보호대책 선정표에 2.7/2.9/3.2 연계",
            "분기 자체점검에 비정형 데이터 점검 포함",
        ),
        related_scenario_ids=("security-review-certification",),
    ),
    MultiGapBundle(
        id="auth-privilege-chain",
        title="계정/특권/권한검토/DB접근 겹침",
        theme="내부자/과다권한",
        required_controls=("2.5.1", "2.5.5", "2.5.6", "2.6.4"),
        min_match=3,
        partial_min=2,
        priority=8,
        severity="critical",
        summary=(
            "계정/특권/권한검토/DB접근이 동시에 약하면 "
            "로그/DB/백업에 대한 내부자 접근을 통제/감사할 수 없습니다."
        ),
        compound_analysis=(
            "계정 관리(2.5.1)/특수 계정(2.5.5)/권한 검토(2.5.6)/DB 접근(2.6.4)이 겹치면, "
            "관리자/DBA/개발 공유 계정이 로그 저장소/DB/백업에 무제한 접근할 수 있습니다. "
            "PII가 평문으로 남는 환경과 결합 시 내부 유출/오남용 위험이 극대화됩니다."
        ),
        operational_impact=(
            "퇴직/전배 후 권한 미회수, 공유 admin으로 누가 조회했는지 불명, "
            "로그 시스템/SIEM에 대한 과다 권한으로 PII 열람."
        ),
        audit_impact=(
            "2.5/2.6 집중. 계정 프로비저닝/특권/분기 검토/DB role/감사로그 샘플링."
        ),
        incident_scenarios=(
            "DBA가 회원 테이블+상담 로그 export, 권한 검토 2년 미실시",
            "root/admin 공유, SIEM 담당자가 raw log에서 PII 열람",
            "퇴사자 VPN/DB/AWS IAM 미회수",
        ),
        remediation_path=(
            "계정 발급/변경/말소 승인 워크플로",
            "특권 MFA/PAM/세션 기록",
            "분기 권한 검토/DB role 최소화",
        ),
        related_scenario_ids=("external-developer-access",),
    ),
    MultiGapBundle(
        id="consent-collection-flow",
        title="수집/동의/목적/현황 불일치",
        theme="법적 정당성/현황 괴리",
        required_controls=("3.1.1", "3.1.2", "3.2.1", "3.2.2"),
        min_match=3,
        partial_min=2,
        priority=7,
        severity="high",
        summary=(
            "수집/동의/목적/현황이 동시에 약하면 "
            "로그/캐시/분석 데이터에 불법/초과 수집 PII가 쌓입니다."
        ),
        compound_analysis=(
            "적법 수집(3.1.1)/동의(3.1.2) 없이 목적 외(3.2.2)로 로그/분석에 PII를 쓰고, "
            "현황(3.2.1)에도 없으면, CS/마케팅/추천 엔진용 로그가 법적 근거 없이 방치됩니다."
        ),
        operational_impact=(
            "서비스 로그를 마케팅/추천에 재사용, 동의 범위 초과. "
            "캠페인 페이지 수집 항목과 DB/로그 불일치."
        ),
        audit_impact=(
            "3.1/3.2/3.5 연계. 동의 화면/처리방침/현황표/로그 샘플/목적 외 이용 기록."
        ),
        incident_scenarios=(
            "CS 로그를 품질 분석/교육에 재사용, 동의/목적 외 통제 없음",
            "이벤트에서 수집한 항목이 CRM/로그에 추가 항목으로 확장",
        ),
        remediation_path=(
            "수집 항목/목적/동의/DB/로그 1:1 매핑표",
            "목적 외 이용 승인/기록",
            "현황표 분기 갱신에 로그/분석 파이프라인 포함",
        ),
        related_scenario_ids=("cloud-campaign-page", "membership-data-lifecycle"),
    ),
    MultiGapBundle(
        id="vuln-patch-exposure",
        title="취약점/패치/악성코드/로그 tampering",
        theme="침해/증적 훼손",
        required_controls=("2.11.2", "2.10.8", "2.10.9", "2.9.5"),
        min_match=3,
        partial_min=2,
        priority=6,
        severity="high",
        summary=(
            "취약점/패치/악성코드/로그 점검이 동시에 약하면 "
            "침해 후 로그 삭제/변조까지 탐지하지 못합니다."
        ),
        compound_analysis=(
            "취약점(2.11.2)/패치(2.10.8) 미흡으로 침입 경로가 열리고, "
            "악성코드(2.10.9) 통제/로그 점검(2.9.5)까지 없으면 "
            "공격자가 로그를 삭제하거나 PII를 exfiltration 해도 남는 증적이 없습니다."
        ),
        operational_impact=(
            "알려진 CVE 미패치 API/관리자 페이지 침해, "
            "침해 후 access log/app log 삭제, PII exfiltration 미탐."
        ),
        audit_impact=(
            "2.11/2.10/2.9. 취약점 scan/패치/EDR/로그 무결성/점검표."
        ),
        incident_scenarios=(
            "Log4j 미패치 web app 침해, app log에서 PII exfil",
            "랜섬웨어 후 백업/로그 동시 암호화, 점검 없어 장기간 미인지",
        ),
        remediation_path=(
            "취약점 scan/패치 SLA/EDR/로그 무결성/WORM 검토",
            "로그 점검에 삭제/gap/무결성 항목 포함",
        ),
        related_scenario_ids=("retail-cs-log-pii",),
    ),
    MultiGapBundle(
        id="physical-media-log",
        title="물리/매체/로그/반출 겹침",
        theme="오프라인 유출",
        required_controls=("2.4.6", "2.10.7", "2.9.4", "3.2.1"),
        min_match=3,
        partial_min=2,
        priority=5,
        severity="medium",
        summary=(
            "매체 반출/보조저장매체/로그/현황이 약하면 "
            "USB/노트북/백업 tape 경로로 PII가 조직 밖으로 나갑니다."
        ),
        compound_analysis=(
            "반출입(2.4.6)/보조저장매체(2.10.7) 통제 없이 로그/현황도 없으면, "
            "CS export/DB dump/백업 tape가 물리적으로 반출돼도 추적 불가."
        ),
        operational_impact=(
            "개발자 노트북에 sample.log/DB dump, USB 반출 통제 없음."
        ),
        audit_impact=(
            "2.4/2.10/3.2. 매체 등록/암호화/반출 승인/현황표."
        ),
        incident_scenarios=(
            "CS 팀원 USB에 상담 export, 분실 후 유출",
            "백업 tape 분실, 암호화/등록/반출 기록 없음",
        ),
        remediation_path=(
            "매체 등록/암호화/반출 승인",
            "현황표에 오프라인/백업 매체 포함",
            "DLP/USB 통제",
        ),
        related_scenario_ids=("retail-cs-log-pii",),
    ),
    MultiGapBundle(
        id="human-external-log",
        title="인적보안/외부자/교육/로그 PII",
        theme="사람/프로세스 실패",
        required_controls=("2.2.4", "2.3.1", "2.2.3", "2.9.4"),
        min_match=3,
        partial_min=2,
        priority=6,
        severity="medium",
        summary=(
            "교육/서약/외부자 관리/로그가 동시에 약하면 "
            "직원/외주가 PII를 로그/파일로 무의식적으로 유출합니다."
        ),
        compound_analysis=(
            "교육(2.2.4)/서약(2.2.3)/외부자(2.3.1) 관리 없이 로그(2.9.4)도 없으면, "
            "개발/CS/외주가 '로그에 PII 남기면 안 된다'는 인식 없이 디버그/상담 로그를 쌓습니다."
        ),
        operational_impact=(
            "신입 개발자가 console.log에 user 객체 출력, CS BPO가 상담 내용을 개인 파일 저장."
        ),
        audit_impact=(
            "2.2/2.3/2.9. 교육 이수/서약/외부자 목록/로그 샘플/마스킹 정책."
        ),
        incident_scenarios=(
            "교육 미이수 개발자가 production debug ON",
            "외주 CS가 녹취/스크린샷을 개인 클라우드 저장",
        ),
        remediation_path=(
            "PII/로그 보안 교육/서약/퀴즈",
            "외부자 목록/접근/교육 이수",
            "코드/운영 가이드에 로그 마스킹 필수",
        ),
        related_scenario_ids=("retail-cs-log-pii", "external-developer-access"),
    ),
    MultiGapBundle(
        id="pii-tool-bridge",
        title="PII 탐지 구현/로그/암호화/현황 미연계",
        theme="기술/관리 갭",
        required_controls=("2.7.1", "2.9.4", "3.2.1", "1.3.1"),
        min_match=3,
        partial_min=2,
        priority=8,
        severity="high",
        summary=(
            "PII scan/암호화 코드만 있고 로그 통제/현황/운영 이행과 연결되지 않으면 "
            "학습용 구현이 조직 통제로 정착하지 못합니다."
        ),
        compound_analysis=(
            "본 프로젝트처럼 PII 탐지/AES-GCM redact 구현(2.7.1)이 있어도 "
            "로그 관리(2.9.4)/현황(3.2.1)/보호대책 구현(1.3.1)이 미흡하면 "
            "examples/sample.log 수준의 점검은 가능하지만 운영 로그 파이프라인/담당자/점검/증적까지 "
            "연결되지 않아 심사에서 '미이행'으로 판단됩니다. 기술 통제와 관리 통제의 전형적 갭입니다."
        ),
        operational_impact=(
            "데모/PoC만 있고 cron/CI/SIEM 연동 없음. "
            "탐지 결과를 CAR/현황표/로그 점검표에 반영하지 않음."
        ),
        audit_impact=(
            "구현 코드/API/테스트는 있으나 운영 절차/정기 점검/담당자 지정 없음 지적."
        ),
        incident_scenarios=(
            "PII scan API는 있으나 운영 로그 경로에 미적용, 평문 PII 지속 적재",
            "redact 키가 API body로 전달, 키관리(2.7.2)와 미연계",
        ),
        remediation_path=(
            "PII scan을 로그 점검/배치/CI 파이프라인에 편입",
            "redact/암호화를 2.7.1, 현황/로그를 3.2.1/2.9.4와 문서로 연결",
            "1.3.1 이행 계획/담당/점검 주기 명시",
        ),
        related_scenario_ids=("retail-cs-log-pii", "security-review-certification"),
    ),
)

_CURATED_MULTIGAP_BUNDLES = MULTIGAP_BUNDLES


def _enrich_curated_bundle(bundle: MultiGapBundle) -> MultiGapBundle:
    """Attach explicit basis/evidence to hand-authored bundles."""
    evidence = bundle.evidence
    if not evidence:
        evidence = (
            f"수작업 복합 패턴: {bundle.title}",
            *bundle.incident_scenarios[:2],
        )
    basis = bundle.basis or bundle.summary
    return replace(
        bundle,
        source="curated",
        basis=basis,
        evidence=tuple(evidence),
        priority=min(bundle.priority + 2, 12),
    )


def _load_multigap_bundles() -> tuple[MultiGapBundle, ...]:
    from .control_insight_multigap_generate import build_generated_bundles, merge_multigap_bundles

    curated = tuple(_enrich_curated_bundle(bundle) for bundle in _CURATED_MULTIGAP_BUNDLES)
    generated = build_generated_bundles()
    return merge_multigap_bundles(curated, generated, limit=100)


MULTIGAP_BUNDLES = _load_multigap_bundles()


def _control_snapshot(control_id: str, assessments: dict[str, str]) -> dict[str, str] | None:
    control = find_control(control_id)
    if control is None:
        return None
    level = assessments.get(control_id, "unknown")
    return {
        "controlId": control_id,
        "title": str(control["title"]),
        "level": level,
        "levelLabel": LEVEL_LABEL.get(level, level),
    }


def _format_matched_controls(snapshots: list[dict[str, str]]) -> str:
    return ", ".join(f"{s['controlId']} {s['title']}({s['levelLabel']})" for s in snapshots)


def _bundle_match(
    bundle: MultiGapBundle,
    assessments: dict[str, str],
) -> tuple[int, list[dict[str, str]], str]:
    snapshots: list[dict[str, str]] = []
    for control_id in bundle.required_controls:
        snap = _control_snapshot(control_id, assessments)
        if snap and snap["level"] in WEAK_LEVELS:
            snapshots.append(snap)

    count = len(snapshots)
    if count >= bundle.min_match:
        match_type = "full"
    elif count >= bundle.partial_min:
        match_type = "partial"
    else:
        match_type = "none"

    return count, snapshots, match_type


def _control_title(control_id: str) -> str:
    control = find_control(control_id)
    return str(control["title"]) if control else control_id


def _build_overlap_narrative(
    bundle: MultiGapBundle,
    snapshots: list[dict[str, str]],
    match_type: str,
) -> str:
    matched_text = _format_matched_controls(snapshots)
    weak_ids = {s["controlId"] for s in snapshots}
    position_note = ""
    controls = bundle.required_controls
    if len(controls) >= 3:
        weak_positions = [
            f"{idx + 1}번({controls[idx]} {_control_title(controls[idx])})"
            for idx in range(len(controls))
            if controls[idx] in weak_ids
        ]
        if weak_positions:
            position_note = f" 흐름상 {', '.join(weak_positions)}이(가) 미흡합니다."
        if controls[0] in weak_ids and controls[2] in weak_ids and controls[1] not in weak_ids:
            position_note += (
                f" 1번/3번({controls[0]}, {controls[2]})만 미이행이고 "
                f"2번({controls[1]})은 이행 중이어도 연결성 결함으로 지적될 수 있습니다."
            )

    source_label = SOURCE_LABEL.get(bundle.source, bundle.source)
    intro = (
        f"[다중 갭 겹침 분석] '{bundle.title}' — "
        f"현재 {len(snapshots)}개 통제가 동시에 미흡 상태입니다: {matched_text}.{position_note}"
    )
    if match_type == "partial":
        intro += (
            f" (부분 겹침: {bundle.min_match}개 이상 동시 미흡 시 최대 리스크로 분류되며, "
            f"현재 {len(snapshots)}개가 해당됩니다.)"
        )

    evidence_block = "\n".join(f"  - {line}" for line in bundle.evidence) or "  - (근거 미기재)"
    scenario_block = "\n".join(f"  - {s}" for s in bundle.incident_scenarios)
    remediation_block = "\n".join(f"  {i + 1}. {r}" for i, r in enumerate(bundle.remediation_path))

    return "\n".join(
        [
            intro,
            "",
            "[출처/근거]",
            f"출처: {source_label}",
            f"묶음 기준: {bundle.basis or bundle.summary}",
            evidence_block,
            "",
            "[겹침 종합]",
            bundle.compound_analysis,
            "",
            "[운영 영향]",
            bundle.operational_impact,
            "",
            "[심사/법적 영향]",
            bundle.audit_impact,
            "",
            "[복합 사고 시나리오]",
            scenario_block,
            "",
            "[우선 통합 보완]",
            remediation_block,
        ]
    )


def detect_multigap_overlaps(
    assessments: dict[str, str],
    scenario_id: str | None = None,
    organization_context: OrganizationContext | None = None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    for bundle in MULTIGAP_BUNDLES:
        if scenario_id and bundle.related_scenario_ids and scenario_id not in bundle.related_scenario_ids:
            continue

        count, snapshots, match_type = _bundle_match(bundle, assessments)
        if match_type == "none":
            continue

        severity = bundle.severity if match_type == "full" else (
            "high" if bundle.severity == "critical" else "medium"
        )
        source_bonus = {"curated": 20, "graph_relation": 10, "scenario_flow": 6, "category_set": 4}.get(
            bundle.source, 0
        )
        score = (
            count * bundle.priority
            + (10 if match_type == "full" else 0)
            + source_bonus
            + bundle_priority_delta(bundle.required_controls, organization_context)
        )

        results.append(
            {
                "bundleId": bundle.id,
                "title": bundle.title,
                "theme": bundle.theme,
                "source": bundle.source,
                "sourceLabel": SOURCE_LABEL.get(bundle.source, bundle.source),
                "basis": bundle.basis or bundle.summary,
                "evidence": list(bundle.evidence),
                "matchType": match_type,
                "matchedCount": count,
                "requiredCount": len(bundle.required_controls),
                "matchedControls": snapshots,
                "controlIds": [s["controlId"] for s in snapshots],
                "severity": severity,
                "priorityScore": score,
                "summary": bundle.summary,
                "compoundAnalysis": bundle.compound_analysis,
                "operationalImpact": bundle.operational_impact,
                "auditImpact": bundle.audit_impact,
                "incidentScenarios": list(bundle.incident_scenarios),
                "remediationPath": list(bundle.remediation_path),
                "overlapNarrative": _build_overlap_narrative(bundle, snapshots, match_type),
                "relatedScenarioIds": list(bundle.related_scenario_ids),
            }
        )

    results.sort(key=lambda item: (-int(item["priorityScore"]), -int(item["matchedCount"])))
    return results[:25]


def multigap_insights_for_control(
    control_id: str,
    overlaps: list[dict[str, object]],
) -> list[dict[str, object]]:
    related: list[dict[str, object]] = []
    for overlap in overlaps:
        if control_id in overlap.get("controlIds", []):
            others = [
                s for s in overlap.get("matchedControls", [])
                if str(s.get("controlId")) != control_id
            ]
            related.append(
                {
                    "bundleId": overlap["bundleId"],
                    "title": overlap["title"],
                    "theme": overlap["theme"],
                    "matchType": overlap["matchType"],
                    "coGapControls": others,
                    "summary": overlap.get("basis") or overlap["summary"],
                    "excerpt": str(overlap.get("compoundAnalysis", ""))[:280] + "...",
                }
            )
    return related[:4]
