from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from typing import Literal

from .applicability import apply_na_to_assessments
from .control_graph import find_scenario, list_controls
from .causal_retrieve import (
    index_findings_by_control,
    project_causal_ssot_onto_gaps,
    run_structured_retrieve,
)
from .control_insight_kb import build_gap_insights
from .control_insight_multigap import detect_multigap_overlaps
from .control_insight_verbalize import (
    build_executive_report,
    build_key_insights,
    build_review_items,
    build_report_sections,
)
from .report_evaluation import classify_evaluation_bands
from .organization_profile import normalize_organization_profile
from .profile_evidence import build_minimum_evidence_pack
from .profile_prioritization import priority_delta, relevance_reasons, suggested_scenario_ids
from .quest_kb import (
    build_confirmation_actions,
    build_control_session_details,
    build_priority_quests,
    merge_quest_checks_into_control_checks,
    summarize_input_confidence,
)
from .scope_drafting import build_scope_draft

AssessmentLevel = Literal["unknown", "none", "partial", "done", "evidenced", "na"]

from .score_metrics import (
    ASSESSED_SCORE_TOOLTIP,
    LEVEL_SCORES,
    OVERALL_SCORE_LABEL,
    OVERALL_SCORE_TOOLTIP,
    SCORE_DISCLAIMER,
    qualitative_label,
)

LEVEL_LABELS: dict[str, str] = {
    "unknown": "미점검",
    "none": "미이행",
    "partial": "부분 이행",
    "done": "이행",
    "evidenced": "증적 확보",
    "na": "해당 없음",
}


def checklist_as_statement(text: str) -> str:
    """체크박스용 문장: 의문형(~가)을 서술형(~다)으로 맞춘다."""
    t = str(text or "").strip().rstrip("?.! ")
    if not t:
        return t
    swaps = (
        ("되어 있는가", "되어 있다"),
        ("정해져 있는가", "정해져 있다"),
        ("공유되었는가", "공유되어 있다"),
        ("이뤄지는가", "이뤄진다"),
        ("갱신했는가", "갱신했다"),
        ("나뉘는가", "나뉜다"),
        ("하드코딩되지 않는가", "하드코딩되지 않는다"),
        ("노출이 없는가", "노출이 없다"),
        ("실개인정보가 없는가", "실개인정보가 없다"),
        ("실제로 오는가", "실제로 온다"),
        ("알림이 오는가", "알림이 온다"),
        ("서약을 받는가", "서약을 받는다"),
        ("거치는가", "거친다"),
        ("쓰는가", "쓴다"),
        ("맞는가", "맞다"),
        ("드러나는가", "드러난다"),
        ("남는가", "남는다"),
        ("있는가", "있다"),
        ("인가", "이다"),
        ("하는가", "한다"),
        ("되는가", "된다"),
        ("는가", "다"),
    )
    for old, new in swaps:
        if t.endswith(old):
            return t[: -len(old)] + new
    return t


PRIORITY_WEIGHTS: dict[str, int] = {
    "3": 3,
    "2.7": 3,
    "2.5": 2,
    "2.6": 2,
    "2.11": 2,
    "1.2": 2,
}

CATEGORY_META: dict[str, dict[str, object]] = {
    "1.1": {
        "riskIfMissing": "관리체계 기반이 없으면 인증 범위/정책/책임이 문서화되지 않아 심사 초기 결함이 집중됩니다.",
        "checklist": [
            "경영진이 정보보호/개인정보보호 활동에 참여하고 승인한 기록이 있다",
            "CISO/개인정보보호책임자 등 최고책임자가 지정되어 있다",
            "인증 범위와 조직 구성이 문서로 정의되어 있다",
        ],
        "recommendations": [
            "정보보호위원회 또는 유사 협의체 운영 기록을 남깁니다.",
            "정책/지침에 경영진 승인일과 버전을 명시합니다.",
        ],
    },
    "1.2": {
        "riskIfMissing": "자산/흐름/위험 식별이 없으면 보호대책 선정 근거가 없어 기술 통제가 형식적으로만 남습니다.",
        "checklist": [
            "정보자산 목록과 개인정보 흐름도가 최신 상태이다",
            "위험 평가 결과와 보호대책 선정 근거가 연결되어 있다",
            "신규 서비스 도입 시 위험평가 절차가 있다",
        ],
        "recommendations": [
            "고객센터 로그/멤버십 DB 등 핵심 자산부터 흐름도를 작성합니다.",
            "위험 등급별로 필요한 통제를 매트릭스로 정리합니다.",
        ],
    },
    "1.3": {
        "riskIfMissing": "보호대책이 문서에만 있고 운영되지 않으면 심사 시 이행 증적 부재로 결함이 발생합니다.",
        "checklist": [
            "선정한 보호대책이 실제 시스템/조직에 반영되어 있다",
            "담당자에게 보호대책이 공유되어 있다",
            "운영 현황을 주기적으로 관리한다",
        ],
        "recommendations": [
            "통제별 담당자와 점검 주기를 RACI 형태로 정리합니다.",
            "구현 결과를 변경관리/테스트 증적과 연결합니다.",
        ],
    },
    "1.4": {
        "riskIfMissing": "점검/개선 체계가 없으면 동일 결함이 반복되고 갱신심사에서 큰 리스크가 됩니다.",
        "checklist": [
            "법적 요구사항 변경을 주기적으로 검토한다",
            "내부심사 또는 자체 점검 결과가 있다",
            "결함에 대한 개선 조치와 재발방지가 기록된다",
        ],
        "recommendations": [
            "분기별 자체 점검 체크리스트를 운영합니다.",
            "결함/시정조치(CAR) 추적표를 만듭니다.",
        ],
    },
    "2.1": {
        "riskIfMissing": "정책/조직/자산 관리가 없으면 누가 무엇을 보호하는지 불명확해집니다.",
        "checklist": ["정보보호 정책/지침이 최신이다", "조직/역할이 정의되어 있다", "정보자산 등급이 관리된다"],
        "recommendations": ["정책-지침-가이드 3단계 체계를 정리합니다."],
    },
    "2.2": {
        "riskIfMissing": "인적 보안 미흡 시 내부자에 의한 정보 유출/권한 남용이 발생할 수 있습니다.",
        "checklist": ["보안 서약/교육 이수 기록이 있다", "퇴직/직무변경 시 권한 회수가 된다", "직무 분리가 적용된다"],
        "recommendations": ["입/퇴사 시 계정/권한 회수 절차를 자동화합니다."],
    },
    "2.3": {
        "riskIfMissing": "외부자 통제 부재 시 외주/협력사 경유 유출과 무단 접근이 발생합니다.",
        "checklist": ["외부자 목록과 접근 범위가 관리된다", "계약서에 보안 조항이 포함된다", "계약 종료 시 권한이 회수된다"],
        "recommendations": ["수탁사/외주 개발자 접근은 별도 계정/기간 제한을 적용합니다."],
    },
    "2.4": {
        "riskIfMissing": "물리 보안 미흡 시 서버실/문서 유출, 매체 반출 사고가 발생합니다.",
        "checklist": ["보호구역과 출입통제가 운영된다", "반출입 기기 통제가 있다", "CCTV/출입기록이 보관된다"],
        "recommendations": ["DC/사무실 출입권한을 직무별로 최소화합니다."],
    },
    "2.5": {
        "riskIfMissing": "계정/권한 관리 미흡 시 횡적 이동/권한 상승으로 대량 유출이 가능합니다.",
        "checklist": ["계정 발급/변경/삭제 절차가 있다", "특권 계정이 통제된다", "접근권한을 정기 검토한다"],
        "recommendations": ["관리자 계정 MFA와 분기별 권한 검토를 도입합니다."],
    },
    "2.6": {
        "riskIfMissing": "접근통제 미흡 시 비인가 접근, DB 직접 조회, 원격 접근 사고가 발생합니다.",
        "checklist": ["네트워크/시스템/DB/앱 접근이 최소권한이다", "원격/무선 접근이 통제된다", "인터넷 접속이 통제된다"],
        "recommendations": ["운영 DB 직접 접근을 차단하고 bastion을 경유합니다."],
    },
    "2.7": {
        "riskIfMissing": "암호화 미적용 시 개인정보/주요정보 평문 노출, 전송 구간 도청 리스크가 큽니다.",
        "checklist": [
            "암호화 대상과 알고리즘이 정책에 정의되어 있다",
            "저장/전송 시 암호화가 적용된다",
            "암호키 생성/보관/폐기 절차가 있다",
        ],
        "recommendations": [
            "주민번호/연락처 등 식별정보는 저장 시 암호화 또는 토큰화를 검토합니다.",
            "키는 애플리케이션 코드가 아닌 KMS/환경변수로 분리합니다.",
        ],
    },
    "2.8": {
        "riskIfMissing": "개발 보안 미흡 시 OWASP 취약점, 하드코딩된 비밀정보, 테스트 데이터 유출이 발생합니다.",
        "checklist": ["보안 요구사항이 정의/검토된다", "시험/운영 환경이 분리된다", "시험 데이터에 실개인정보가 없다"],
        "recommendations": ["SDLC에 보안 검토 게이트를 추가합니다.", "CI에서 정적 분석/의존성 스캔을 실행합니다."],
    },
    "2.9": {
        "riskIfMissing": "운영관리 미흡 시 로그 미수집/백업 실패/변경 추적 불가로 사고 대응이 지연됩니다.",
        "checklist": ["변경관리와 백업/복구가 운영된다", "로그/접속기록이 수집/보관된다", "시간 동기화가 되어 있다"],
        "recommendations": ["운영 로그 보관 기간과 점검 주기를 정책에 명시합니다."],
    },
    "2.10": {
        "riskIfMissing": "서비스 보안관리 미흡 시 웹/클라우드/단말 취약점과 악성코드 감염이 발생합니다.",
        "checklist": ["보안솔루션이 운영/모니터링된다", "패치/악성코드 통제가 된다", "공개서버/클라우드 보안이 점검된다"],
        "recommendations": ["WAF/EDR/취약점 스캔 결과를 월간 리포트로 관리합니다."],
    },
    "2.11": {
        "riskIfMissing": "사고 대응 체계 부재 시 침해 확산, 통지 지연, 복구 지연이 발생합니다.",
        "checklist": ["사고 대응 조직/절차가 정의되어 있다", "취약점 점검/조치가 주기적으로 이뤄진다", "모의훈련이 수행된다"],
        "recommendations": ["개인정보 유출 시나리오 모의훈련을 연 1회 이상 수행합니다."],
    },
    "2.12": {
        "riskIfMissing": "재해복구 미흡 시 장애/재난 시 서비스 중단이 장기화됩니다.",
        "checklist": ["재해/재난 대비 조치가 있다", "복구 시험이 주기적으로 수행된다"],
        "recommendations": ["RTO/RPO를 정의하고 복구 시험 결과를 문서화합니다."],
    },
    "3.1": {
        "riskIfMissing": "수집 단계 통제 미흡 시 동의 없는 수집, 과다 수집, 주민번호 불법 처리가 발생합니다.",
        "checklist": ["수집/이용 목적과 동의가 적법한가", "수집 항목이 최소화되어 있다", "주민번호/민감정보 처리가 제한된다"],
        "recommendations": ["수집 화면별 동의 항목과 실제 DB 컬럼을 대조합니다."],
    },
    "3.2": {
        "riskIfMissing": "보유/이용 통제 미흡 시 목적 외 이용, 로그 내 개인정보 노출, 현황 불일치가 발생합니다.",
        "checklist": ["개인정보 현황이 관리된다", "목적 외 이용/제공이 통제된다", "가명/마스킹 등 보호조치가 적용된다"],
        "recommendations": ["운영 로그/상담 기록에 대한 PII 탐지/마스킹 파이프라인을 검토합니다."],
    },
    "3.3": {
        "riskIfMissing": "제공/위탁 통제 미흡 시 제3자 제공/국외이전 관련 법적 리스크가 큽니다.",
        "checklist": ["제3자 제공/위탁 계약과 통지가 이뤄진다", "수탁사 관리 점검이 있다"],
        "recommendations": ["위탁 계약서에 재위탁/파기/사고통지 조항을 포함합니다."],
    },
    "3.4": {
        "riskIfMissing": "파기 통제 미흡 시 퇴원/탈퇴 후에도 개인정보가 잔존해 유출됩니다.",
        "checklist": ["보유기간 경과 시 파기가 수행된다", "파기 방법과 결과가 기록된다"],
        "recommendations": ["DB/백업/로그까지 포함한 파기 범위를 정의합니다."],
    },
    "3.5": {
        "riskIfMissing": "정보주체 권리보장 미흡 시 열람/정정/삭제 요청 대응 지연과 과징금 리스크가 있습니다.",
        "checklist": ["처리방침이 공개/최신이다", "권리 행사 절차와 통지가 운영된다"],
        "recommendations": ["고객센터/웹 채널별 권리 행사 처리 SLA를 정합니다."],
    },
}

CERTIFICATION_PHASES: tuple[dict[str, object], ...] = (
    {
        "id": "prepare",
        "order": 1,
        "title": "인증 준비",
        "duration": "2~4개월",
        "summary": "범위를 정하고, 지금 상태를 점검한 뒤 정책/위험평가를 먼저 갖춥니다.",
        "activities": [
            "인증에 넣을 서비스/시스템을 확정한다 (1.1.4)",
            "101개 통제 기준으로 자체 진단을 한다 (1.4.2)",
            "정보보호/개인정보보호 정책/지침을 정리한다 (1.1.5, 2.1.1)",
            "정보자산과 개인정보 흐름을 정리한다 (1.2.1, 1.2.2)",
        ],
        "relatedControlIds": ["1.1.4", "1.1.5", "1.2.1", "1.2.2", "1.2.3", "1.4.2"],
    },
    {
        "id": "implement",
        "order": 2,
        "title": "보호대책 이행",
        "duration": "3~6개월",
        "summary": "위험평가에서 고른 대책을 시스템/업무에 넣고, 보여줄 증적을 모읍니다.",
        "activities": [
            "접근통제/암호화/로그 등 기술 통제를 적용한다 (2.5~2.10)",
            "개인정보 생명주기별 보호조치를 이행한다 (3.1~3.5)",
            "테스트/점검으로 실제로 돌아가는지 확인한다 (1.3.1, 2.8.2)",
        ],
        "relatedControlIds": ["1.2.4", "1.3.1", "2.7.1", "2.9.4", "3.2.1"],
    },
    {
        "id": "apply",
        "order": 3,
        "title": "심사 신청/사전준비",
        "duration": "1~2개월",
        "summary": "심사기관과 일정을 맞추고, 증적 묶음과 사전 점검을 마무리합니다.",
        "activities": [
            "심사 범위/일정/수수료를 계약한다",
            "통제별 증적 목록을 정리하고 샘플을 준비한다",
            "사전 모의심사 또는 내부 점검을 한다",
        ],
        "relatedControlIds": ["1.4.1", "1.4.2", "2.1.1"],
    },
    {
        "id": "audit",
        "order": 4,
        "title": "인증 심사",
        "duration": "2~4주",
        "summary": "심사원이 이행과 증적을 확인하고, 나온 미흡을 보완합니다.",
        "activities": [
            "시작회의/종료회의를 진행한다",
            "인터뷰/시스템 점검/증적 확인에 대응한다",
            "결함보고서를 검토하고 보완조치를 한다",
        ],
        "relatedControlIds": ["1.4.2", "1.4.3", "2.11.4"],
    },
    {
        "id": "maintain",
        "order": 5,
        "title": "사후관리/갱신",
        "duration": "3년 주기",
        "summary": "인증을 유지하도록 점검/훈련/변경 관리를 계속합니다.",
        "activities": [
            "연간 자체 점검/모의훈련을 한다",
            "변경이 생기면 위험평가/통제를 다시 본다",
            "갱신심사 전에 갭 분석을 다시 한다",
        ],
        "relatedControlIds": ["1.3.3", "1.4.2", "1.4.3", "2.11.2"],
    },
)


def _priority_for_control(control_id: str, category_id: str, area_id: str) -> int:
    weight = 1
    if area_id == "3":
        weight = 3
    elif category_id in PRIORITY_WEIGHTS:
        weight = PRIORITY_WEIGHTS[category_id]
    elif area_id == "1":
        weight = 2
    if str(control_id) in {"2.7.1", "2.7.2", "3.1.3", "3.2.1", "1.2.3"}:
        weight += 1
    return weight


CONTROL_CHECKLIST: dict[str, list[str]] = {
    "1.1.1": [
        "경영진이 정보보호/개인정보보호 활동에 참여한 회의/승인 기록이 있다",
        "위원회(또는 유사 협의체) 안건에 보안/개인정보 항목이 포함된다",
        "경영진 승인 정책/범위 문서의 버전/일자가 관리된다",
    ],
    "1.1.2": [
        "CISO 또는 개인정보 보호책임자가 문서로 지정되어 있다",
        "책임자의 역할/권한이 정책/조직도에 명시되어 있다",
        "직원에게 책임자 연락처/보고 체계가 공유되어 있다",
    ],
    "1.1.3": [
        "정보보호/개인정보보호 관련 조직/역할이 정의되어 있다",
        "겸직/대행 관계가 R&R 또는 조직도에 드러난다",
        "역할 변경 시 문서가 갱신된다",
    ],
    "1.1.4": [
        "인증 포함 서비스/시스템/조직이 범위서에 적혀 있다",
        "제외 범위와 제외 사유가 문서화되어 있다",
        "범위 문서의 승인자/승인일이 남아 있다",
    ],
    "1.1.5": [
        "정보보호/개인정보보호 정책 문서가 있다",
        "승인일/버전/승인자가 문서에 남아 있다",
        "직원이 접근 가능한 공유 위치가 있다",
    ],
    "1.2.1": [
        "시스템/DB/저장소/계정 등 핵심 자산 목록이 있다",
        "자산마다 담당자(또는 팀)가 지정되어 있다",
        "개인정보 포함 자산이 구분되어 있다",
    ],
    "1.2.2": [
        "수집/저장/이용/제공/파기 흐름도가 있다",
        "흐름도에 실제 시스템명이 적혀 있다",
        "최근 서비스 변경 이후 흐름도를 갱신했다",
    ],
    "1.2.3": [
        "위험 평가 기준(발생가능성×영향 등)이 정해져 있다",
        "최근 위험 평가 결과표(또는 회의록)가 있다",
        "높은 위험에 대응 보호대책이 연결되어 있다",
    ],
    "1.2.4": [
        "위험별 보호대책(통제 ID 또는 조치명)이 선정되어 있다",
        "대책마다 담당자와 목표 일정이 있다",
        "위험→대책 연결표가 있다",
    ],
    "2.3.1": [
        "외부자/수탁사 목록과 접근 범위가 있다",
        "계약서에 보안/개인정보 조항이 포함된다",
        "계약 종료/퇴사 시 계정/권한 회수 절차가 있다",
    ],
    "2.5.1": [
        "계정 발급/변경/삭제 절차가 있다",
        "관리자/특권 계정은 별도 승인 후 발급한다",
        "주기적으로 계정/권한을 점검한다",
    ],
    "2.5.3": [
        "업무 시스템 로그인에 인증 수단이 적용된다",
        "관리자/원격 접근에 강화 인증(MFA 등)이 있다",
        "인증 실패/잠금 정책이 설정되어 있다",
    ],
    "2.5.4": [
        "비밀번호 복잡성/최소 길이가 시스템에 강제된다",
        "비밀번호 변경 주기 또는 알림이 운영된다",
        "중요 시스템에 MFA가 적용된다",
    ],
    "2.5.6": [
        "접근권한 정기 검토 주기가 정해져 있다",
        "검토 결과와 회수/조정이 기록된다",
        "특권 계정 검토가 별도로 수행된다",
    ],
    "2.6.1": [
        "운영/개발/관리 네트워크 구간이 분리되어 있다",
        "관리자 접근이 VPN 또는 허용 IP로 제한된다",
        "보안그룹/방화벽 규칙이 문서/캡처로 남아 있다",
    ],
    "2.6.2": [
        "중요 시스템에 최소 권한이 적용된다",
        "관리자 계정과 일반 계정이 분리되어 있다",
        "퇴사/직무변경 시 권한 회수 절차가 있다",
    ],
    "2.6.3": [
        "앱/어드민 기능별 권한이 역할에 따라 나뉜다",
        "불필요한 관리 기능 노출이 차단된다",
        "권한 변경이 승인/기록된다",
    ],
    "2.6.4": [
        "DB 직접 접근이 최소화되어 있다",
        "DB 접근 계정이 업무별로 분리되어 있다",
        "DB 접속/쿼리 기록이 남는다",
    ],
    "2.6.6": [
        "원격 접근 경로(VPN/ZTNA 등)가 정해져 있다",
        "원격 접근에 MFA 또는 동등 통제가 있다",
        "원격 접속 기록이 보관/점검된다",
    ],
    "2.7.1": [
        "암호화 대상과 알고리즘이 정책에 정의되어 있다",
        "저장/전송 구간 암호화가 실제로 적용된다",
        "개인정보 등 중요정보 평문 저장이 점검된다",
    ],
    "2.7.2": [
        "암호키 생성/보관/교체/폐기 절차가 있다",
        "키가 소스코드/평문 설정에 하드코딩되지 않는다",
        "KMS/HSM 등 키 분리 보관이 적용된다",
    ],
    "2.9.4": [
        "중요 시스템/관리자/개인정보 접근 로그가 수집된다",
        "로그 보관 기간이 정책에 정의되어 있다",
        "로그 내 개인정보 마스킹/최소화가 검토된다",
    ],
    "2.9.5": [
        "로그/접속기록 점검 주기가 정해져 있다",
        "이상 접근에 대한 조치 기록이 남는다",
        "미수집/누락 시스템에 대한 보완이 추적된다",
    ],
    "3.1.1": [
        "수집/이용 목적과 동의가 화면/문서에 맞다",
        "수집 항목과 실제 DB 컬럼이 일치한다",
        "목적 변경 시 재동의/고지 절차가 있다",
    ],
    "3.1.3": [
        "주민등록번호 수집/저장 금지 원칙이 있다",
        "불가피 수집 시 법령 근거가 문서화되어 있다",
        "저장/전송 시 암호화/별도 보관이 적용된다",
    ],
    "3.2.1": [
        "시스템별 개인정보 항목/보유량이 표로 있다",
        "항목마다 이용 목적/보유기간이 적혀 있다",
        "현황표를 주기적으로 갱신한다",
    ],
    "3.2.2": [
        "잘못된/중복 개인정보를 고치는 기준이 있다",
        "회원정보 수정/검증이 실제 운영된다",
        "로그/화면에서 불필요 개인정보가 마스킹된다",
    ],
    "3.3.1": [
        "제3자 제공 시 동의/고지와 계약이 있다",
        "제공 항목/목적/기간이 기록된다",
        "제공 현황을 주기적으로 점검한다",
    ],
    "3.3.2": [
        "위탁 계약에 보안/재위탁/파기/사고통지 조항이 있다",
        "수탁사별 처리 업무와 접근 범위가 관리된다",
        "수탁사 점검 또는 관리 기록이 있다",
    ],
    "3.4.1": [
        "항목별 보유기간과 파기 시점이 정해져 있다",
        "기간 경과 시 삭제/파기가 수행된다",
        "파기 일시/대상/방법이 기록된다",
    ],
    "3.4.2": [
        "목적 달성 후 보유 사유(법령/계약)가 문서에 있다",
        "일반 서비스 DB와 분리 보관 또는 접근 제한한다",
        "분리 보관 데이터 접근 권한이 최소화되어 있다",
    ],
    "3.5.1": [
        "개인정보 처리방침이 웹 등에 공개되어 있다",
        "처리방침이 실제 처리와 일치하도록 갱신된다",
        "변경 이력이 관리된다",
    ],

    "1.3.1": [
        "선정한 보호대책이 시스템/업무에 반영되어 있다",
        "대책별 담당자가 지정되어 있다",
        "반영 여부를 점검한 기록이 있다",
    ],
    "1.4.2": [
        "자체 점검 주기/체크리스트가 있다",
        "최근 자체 점검 결과가 있다",
        "발견된 미흡에 대한 조치가 추적된다",
    ],
    "2.5.2": [
        "사용자별 고유 계정이 있다",
        "공용/공유 계정 사용이 제한된다",
        "계정과 실사용자 매핑이 있다",
    ],
    "2.5.5": [
        "특수/특권 계정 목록이 있다",
        "일상 업무에 특권 계정 사용을 제한한다",
        "특권 계정 사용이 기록/검토된다",
    ],
    "2.5.6": [
        "접근권한 정기 검토 주기가 있다",
        "검토 결과와 회수/조정이 기록된다",
        "특권 계정 검토가 별도로 수행된다",
    ],
    "2.6.3": [
        "앱/어드민 권한이 역할별로 나뉜다",
        "불필요한 관리 기능 노출이 차단된다",
        "권한 변경이 승인/기록된다",
    ],
    "2.11.1": [
        "사고 대응 조직/연락망이 있다",
        "탐지→보고→대응→복구 절차가 문서화되어 있다",
        "핵심 담당자에게 절차가 공유되어 있다",
    ],
    "2.11.2": [
        "취약점 점검 주기/범위가 있다",
        "취약점 조치 기록이 있다",
        "미조치 항목이 추적된다",
    ],
    "3.1.2": [
        "수집 항목이 목적에 필요한 범위인지 검토한다",
        "불필요 입력란/컬럼을 최소화한다",
        "신규 기능 추가 시 수집 항목을 재검토한다",
    ],
    "3.1.4": [
        "민감/고유식별정보 처리 현황이 있다",
        "처리 목적이 제한되고 동의가 맞다",
        "별도 접근통제/암호화가 적용된다",
    ],
    "3.2.4": [
        "목적 외 이용/제공 기준이 정책에 있다",
        "목적 외 이용 시 승인/동의 절차가 있다",
        "목적 외 이용/제공 기록이 남는다",
    ],
    "3.3.1": [
        "제3자 제공 시 동의/고지가 있다",
        "제공 계약/조건이 문서화되어 있다",
        "제공 항목/목적/기간 기록이 있다",
    ],
    "3.5.2": [
        "권리 행사 접수/처리 절차가 있다",
        "처리 기한(SLA)이 정해져 있다",
        "요청/처리 결과가 기록된다",
    ],
    "3.5.3": [
        "통지 기준/대상/기한이 정해져 있다",
        "통지 채널/템플릿이 준비되어 있다",
        "모의 또는 실제 통지 기록이 있다",
    ],

    "1.1.6": [
        "보안/개인정보 업무 담당 인력이 지정되어 있다",
        "관련 예산 또는 도구 비용이 배정되어 있다",
        "자원 부족 이슈가 경영진에 보고된다",
    ],
    "1.3.2": [
        "보호대책 목록/책임이 공유되어 있다",
        "관련 팀에 설명/공유한 기록이 있다",
        "최신본을 찾을 수 있는 위치가 있다",
    ],
    "1.3.3": [
        "통제 운영 현황(점검표/대시보드)이 있다",
        "현황 점검 주기가 정해져 있다",
        "이상/장애 시 조치가 기록된다",
    ],
    "1.4.1": [
        "법령/고시 변경을 검토하는 주기가 있다",
        "최근 검토 기록이 있다",
        "변경 사항을 정책/시스템에 반영한다",
    ],
    "1.4.3": [
        "시정/개선 조치 추적표가 있다",
        "조치 완료와 확인이 기록된다",
        "재발방지 조치가 남아 있다",
    ],
    "2.6.5": [
        "무선망 인증이 적용되어 있다",
        "게스트망과 업무망이 분리되어 있다",
        "무선 접속 기준이 문서화되어 있다",
    ],
    "2.6.7": [
        "인터넷 사용 기준이 정해져 있다",
        "유해/불필요 목적지 차단이 적용되어 있다",
        "인터넷 접속 기록이 남는다",
    ],
    "2.11.3": [
        "모니터링 대상이 정해져 있다",
        "이상행위 알림이 실제로 온다",
        "알림 대응 절차가 있다",
    ],
    "2.11.4": [
        "훈련 주기/시나리오가 정해져 있다",
        "최근 훈련 기록이 있다",
        "훈련 후 개선 조치가 남아 있다",
    ],
    "2.11.5": [
        "복구/통지 절차가 문서에 있다",
        "복구/통지 담당자가 지정되어 있다",
        "복구/통지 기록이 남을 양식이 있다",
    ],
    "3.1.5": [
        "간접수집 출처/목적이 기록된다",
        "적법성을 확인한다",
        "필요한 경우 정보주체 고지를 한다",
    ],
    "3.1.6": [
        "촬영 안내판/고지가 있다",
        "관리책임자/보관기간이 정해져 있다",
        "열람 권한이 제한/기록된다",
    ],
    "3.1.7": [
        "마케팅 동의가 필수 동의와 분리되어 있다",
        "수신거부/철회가 가능한가",
        "동의/철회 기록이 남는다",
    ],
    "3.2.3": [
        "단말 권한 요청 목록이 관리된다",
        "권한은 최소만 요청한다",
        "권한 요청 시 목적이 안내된다",
    ],
    "3.2.5": [
        "가명처리 기준/절차가 있다",
        "가명정보와 추가정보가 분리 관리된다",
        "재식별 가능 정보 접근이 제한된다",
    ],
    "3.3.3": [
        "이전 시 고지/이전 절차가 문서에 있다",
        "정보주체 고지 방법이 준비되어 있다",
        "이전 범위/일자가 기록된다",
    ],
    "3.3.4": [
        "국외이전 대상 서비스/국가가 파악되어 있다",
        "국외이전 고지/동의가 있다",
        "이전 시 보호조치/계약이 있다",
    ],
    "2.1.1": [
        "정책 개정 주기 또는 트리거가 있다",
        "최신 버전이 공유 위치에 있다",
        "주요 변경이 직원에게 안내된다",
    ],
    "2.2.4": [
        "교육 대상/주기가 정해져 있다",
        "최근 교육 이수 기록이 있다",
        "신규 입사자 교육이 있다",
    ],
    "2.2.5": [
        "퇴사/직무변경 체크리스트가 있다",
        "계정/권한이 실제로 회수된다",
        "회수 완료 기록이 남는다",
    ],
    "2.3.2": [
        "표준 보안/개인정보 조항이 있다",
        "신규 계약에 조항이 포함된다",
        "중요 계약은 보안 검토를 거친다",
    ],
    "2.8.3": [
        "개발/스테이징/운영이 분리되어 있다",
        "운영 환경 접근이 제한된다",
        "환경 구성이 문서화되어 있다",
    ],
    "2.8.4": [
        "시험 데이터 사용 기준이 있다",
        "실개인정보 대신 마스킹/더미를 쓴다",
        "시험 환경 개인정보 잔존을 점검한다",
    ],
    "2.9.1": [
        "변경 요청/승인 절차가 있다",
        "변경 이력이 기록된다",
        "롤백/긴급변경 기준이 있다",
    ],
    "2.9.3": [
        "백업 대상/주기가 정해져 있다",
        "백업이 실제로 수행된다",
        "복구 시험을 한 기록이 있다",
    ],
    "2.10.2": [
        "클라우드 계정/리전 구성이 문서화되어 있다",
        "관리자 권한이 최소화되어 있다",
        "클라우드 감사 로그가 수집된다",
    ],

    "2.1.2": [
        "조직/역할 문서가 최신이다",
        "조직 변경 시 갱신 절차가 있다",
        "최신본이 공유되어 있다",
    ],
    "2.1.3": [
        "자산 목록이 정기 갱신된다",
        "자산 등급/중요도가 표시되어 있다",
        "자산 담당자가 지정되어 있다",
    ],
    "2.2.1": [
        "주요 직무자 목록이 있다",
        "직무별 책임이 적혀 있다",
        "직무자 변경 시 목록을 갱신한다",
    ],
    "2.2.2": [
        "직무 분리 기준이 있다",
        "실제 권한/업무에 분리가 반영되어 있다",
        "불가피 겸직 시 보완통제가 있다",
    ],
    "2.2.3": [
        "보안/개인정보 서약서가 있다",
        "입사 시 서약을 받는다",
        "서약서가 보관된다",
    ],
    "2.2.6": [
        "위반 시 조치 절차가 있다",
        "조사/조치 기록이 남는다",
        "재발방지 조치가 있다",
    ],
    "2.3.3": [
        "수탁사 점검 주기/항목이 있다",
        "최근 점검 또는 확인 기록이 있다",
        "미흡 시 조치가 추적된다",
    ],
    "2.3.4": [
        "계약 변경/만료 시 체크리스트가 있다",
        "종료 시 계정/권한이 회수된다",
        "데이터 반환/파기 확인이 있다",
    ],
    "2.4.1": [
        "보호구역이 지정/표시되어 있다",
        "보호구역 기준이 문서화되어 있다",
        "구역 도면/목록이 있다",
    ],
    "2.4.2": [
        "출입 권한이 최소화되어 있다",
        "출입 기록이 남는다",
        "출입 권한을 주기적으로 검토한다",
    ],
    "2.4.3": [
        "랙/장비 잠금 또는 동등 보호가 있다",
        "중요 장비가 보호구역 내에 있다",
        "점검 기록이 있다",
    ],
    "2.4.4": [
        "보호설비 목록이 있다",
        "정기 점검이 수행된다",
        "점검/장애 기록이 남는다",
    ],
    "2.4.5": [
        "보호구역 작업 승인 절차가 있다",
        "외부 작업자 동행/감독이 있다",
        "작업 기록이 남는다",
    ],
    "2.4.6": [
        "반출입 기록이 있다",
        "반출입 기준이 문서화되어 있다",
        "무단 반출을 점검한다",
    ],
    "2.4.7": [
        "클린데스크/화면보호 기준이 있다",
        "화면잠금/자리비움 습관이 안내된다",
        "점검을 한 기록이 있다",
    ],
    "2.8.1": [
        "보안 요구사항 정의 절차가 있다",
        "인증/권한/로그/암호화 등이 포함된다",
        "이슈/티켓에 보안 요구가 남는다",
    ],
    "2.8.2": [
        "배포 전 보안 검토가 있다",
        "보안 시험(또는 체크리스트)을 한다",
        "미흡 시 배포가 보류된다",
    ],
    "2.8.5": [
        "저장소 권한이 최소화되어 있다",
        "커밋/PR 이력이 남는다",
        "시크릿이 코드에 없는지 점검한다",
    ],
    "2.8.6": [
        "운영 이관/배포 절차가 있다",
        "배포 승인이 있다",
        "배포 이력이 남는다",
    ],
    "2.9.2": [
        "성능/장애 모니터링이 있다",
        "장애 알림이 온다",
        "장애 조치/사후 기록이 남는다",
    ],
    "2.9.6": [
        "NTP 등 시간 동기화가 적용되어 있다",
        "주요 시스템의 시간 일치를 점검한다",
        "시간 동기화 기준이 문서화되어 있다",
    ],
    "2.9.7": [
        "폐기/재사용 시 데이터 삭제 기준이 있다",
        "실제 삭제/파기 절차가 수행된다",
        "폐기 기록이 남는다",
    ],
    "2.10.1": [
        "운영 중인 보안시스템 목록이 있다",
        "상태/알림을 모니터링한다",
        "규칙/정책을 주기적으로 점검한다",
    ],
    "2.10.3": [
        "공개서버 하드닝 기준이 있다",
        "패치/취약점이 관리된다",
        "불필요 포트/관리페이지 노출이 없다",
    ],
    "2.10.4": [
        "전자거래/결제 구간이 식별되어 있다",
        "거래 구간 인증/암호화/권한이 적용된다",
        "거래/접근 로그가 남는다",
    ],
    "2.10.5": [
        "대외 전송에 TLS 등이 적용된다",
        "전송 암호화 기준이 정책에 있다",
        "평문 전송 여부를 점검한다",
    ],
    "2.10.6": [
        "화면잠금/자동잠금이 강제된다",
        "디스크 암호화 또는 동등 보호가 있다",
        "분실/퇴사 시 단말 회수/원격조치 절차가 있다",
    ],
    "2.10.7": [
        "보조저장매체 사용 기준이 있다",
        "사용이 제한되거나 승인제로 운영된다",
        "사용/반출 기록이 있다",
    ],
    "2.10.8": [
        "패치 주기/책임이 정해져 있다",
        "중요 패치가 적용된다",
        "미적용 패치가 추적된다",
    ],
    "2.10.9": [
        "악성코드 방지 솔루션이 배포되어 있다",
        "엔진/정책이 갱신된다",
        "탐지 알림/조치 절차가 있다",
    ],
    "2.12.1": [
        "재해/재난 대비 계획이 있다",
        "RTO/RPO 또는 복구 목표가 있다",
        "중요 시스템의 백업/이중화가 있다",
    ],
    "2.12.2": [
        "복구 시험 주기가 정해져 있다",
        "최근 복구 시험 기록이 있다",
        "시험 후 개선 조치가 남는다",
    ],
}


def enrich_control(control: dict[str, object]) -> dict[str, object]:
    category_id = str(control["categoryId"])
    control_id = str(control["id"])
    title = str(control["title"])
    meta = CATEGORY_META.get(category_id, {})
    # Prefer official 인증기준 안내서 주요 확인사항 when available.
    from .official_kb import (
        official_check_statements,
        official_evidence_examples,
        official_requirement,
    )

    official_checks = official_check_statements(control_id)
    if official_checks:
        checklist = official_checks
    else:
        specific = CONTROL_CHECKLIST.get(control_id)
        if specific:
            checklist = [checklist_as_statement(str(item)) for item in specific]
        else:
            checklist = [checklist_as_statement(str(item)) for item in list(meta.get("checklist", []))]
            checklist.append(checklist_as_statement(f"{title} 운영 절차/담당자/증적 위치가 정해져 있다"))
    evidence_examples = official_evidence_examples(control_id)
    requirement = official_requirement(control_id)
    from .control_search import build_search_entries, build_search_hints, build_search_intents
    from .dual_layer import build_official_checks

    return {
        **control,
        "checklistItems": checklist,
        "officialChecks": build_official_checks(control_id),
        "officialRequirement": requirement,
        "officialEvidenceExamples": evidence_examples,
        "searchHints": list(build_search_hints(control_id)),
        "searchEntries": list(build_search_entries(control_id)),
        "searchIntents": list(build_search_intents(control_id)),
        "riskIfMissing": str(
            meta.get(
                "riskIfMissing",
                f"{title} 통제가 미흡하면 {control['categoryName']} 영역 전체의 보호 수준이 낮아집니다.",
            )
        ),
        "recommendedActions": list(meta.get("recommendations", ["통제 요구사항을 정책/지침에 반영하고 이행 증적을 확보합니다."])),
        "priority": _priority_for_control(control_id, category_id, str(control["areaId"])),
    }


@lru_cache(maxsize=1)
def _cached_checklist_controls() -> tuple[dict[str, object], ...]:
    """Build the immutable reference checklist once per server process."""
    return tuple(enrich_control(dict(control)) for control in list_controls())


def list_checklist_controls() -> list[dict[str, object]]:
    return list(_cached_checklist_controls())


def certification_guide() -> dict[str, object]:
    from .official_kb import institution_public_payload

    institution = institution_public_payload()
    phases = list(CERTIFICATION_PHASES)
    # Align prepare-phase copy with 제도 안내서 (2개월 운영 증적)
    if phases:
        prepare = dict(phases[0])
        prepare["summary"] = (
            "범위를 정하고 관리체계를 구축/운영합니다. "
            "신청 전 최소 2개월 이상 운영 증적과 준비상태 점검을 확인하세요."
        )
        activities = list(prepare.get("activities") or [])
        if "관리체계 2개월 이상 운영 증적을 확인한다" not in activities:
            activities = ["관리체계 2개월 이상 운영 증적을 확인한다", *activities]
        prepare["activities"] = activities
        phases[0] = prepare
    return {
        "title": "인증은 이렇게 흘러갑니다",
        "description": (
            "준비 → 이행 → 신청 → 심사 → 유지 순서입니다. "
            "지금 단계에서 확인할 통제/서류/증적을 먼저 보세요. "
            "(실제 심사/의무 판정을 대체하지 않습니다.)"
        ),
        "phases": phases,
        "totalControls": 101,
        "areas": [
            {"id": "1", "name": "관리체계 수립 및 운영", "count": 16},
            {"id": "2", "name": "보호대책 요구사항", "count": 64},
            {"id": "3", "name": "개인정보 처리 단계별 요구사항", "count": 21},
        ],
        "sourceDoc": institution.get("sourceDoc"),
        "disclaimer": institution.get("disclaimer"),
        "preparationChecks": institution.get("preparationChecks") or [],
        "confirmationQuestions": institution.get("confirmationQuestions") or [],
        "obligationSummary": institution.get("obligationSummary") or [],
        "scopeRules": institution.get("scopeRules") or [],
    }


CONTROL_RECOMMENDATION_DETAILS: dict[str, str] = {
    "2.7.1": "암호정책서에 저장/전송 암호화 대상과 알고리즘을 정의하고, DB/TLS 적용 화면을 증적으로 연결하세요.",
    "2.7.2": "키는 KMS/HSM에 분리 보관하고 소스코드/환경변수 하드코딩 여부를 점검/문서화하세요.",
    "2.9.4": "개인정보 DB/관리자/Bastion 접근 로그 수집 범위를 정의하고, PII scan 결과와 로그 마스킹 정책을 연결하세요.",
    "2.9.5": "로그 수집율/보관기간/미수집 시스템을 월간 점검표로 관리하고 조치 이력을 남기세요.",
    "3.1.3": "주민등록번호 수집/저장 금지 원칙을 확인하고, 불가피 시 법령 근거/별도 보관/암호화를 증명하세요.",
    "3.2.1": "시스템/로그/백업까지 포함한 개인정보 보유 현황표를 분기 갱신하세요.",
    "1.1.4": "인증 범위에 서비스/시스템/조직/물리적 범위를 문서화하고 경계를 명확히 하세요.",
    "1.2.1": "정보자산 목록에 개인정보 파일/DB/API를 포함하고 담당자를 지정하세요.",
    "2.5.1": "계정 발급/변경/말소 승인 절차와 권한 매트릭스를 운영 기록과 함께 관리하세요.",
}


def analyze_assessment(
    assessments: dict[str, str],
    scenario_id: str | None = None,
    control_checks: dict[str, dict[str, bool]] | None = None,
    organization_profile: dict[str, object] | None = None,
    scope_review: dict[str, object] | None = None,
    verbalize: bool = False,
    verbalize_client=None,
    domain_checks: dict[str, dict[str, bool]] | None = None,
    verbalize_consistency: bool = False,
    quest_checks: dict[str, dict[str, bool]] | None = None,
    input_confidence: dict[str, str] | None = None,
    evidence_slots: dict[str, dict[str, object]] | None = None,
    verbalize_max_gaps: int = 12,
    verbalize_include_quests: bool = True,
    view: str = "full",
    session_bundle_mode: str | None = None,
) -> dict[str, object]:
    organization_context = normalize_organization_profile(organization_profile)
    enriched = list_checklist_controls()
    control_ids = [str(c["id"]) for c in enriched]
    assessments, applicability_notes = apply_na_to_assessments(
        dict(assessments), organization_context, control_ids
    )
    merged_control_checks = merge_quest_checks_into_control_checks(quest_checks, control_checks)
    # 1) Structured retrieve first (single pass) — SSOT for because→problem→impacts
    problem_analysis = run_structured_retrieve(
        assessments,
        scenario_id,
        merged_control_checks,
        organization_context,
        domain_checks,
    )
    findings_by_control = index_findings_by_control(
        list(problem_analysis.get("causalFindings") or [])
    )
    multigap_overlaps = detect_multigap_overlaps(assessments, scenario_id, organization_context)
    scope_draft = (
        build_scope_draft(organization_context, scope_review) if organization_context else None
    )
    scope_priority_ids = set(scope_draft["priorityControlIds"]) if scope_draft else set()
    gaps: list[dict[str, object]] = []
    area_scores: dict[str, list[int]] = {}
    area_totals: Counter[str] = Counter()
    category_scores: dict[str, list[int]] = {}
    category_totals: Counter[str] = Counter()
    category_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    category_first_reviewed_control: dict[str, str] = {}
    category_first_weak_control: dict[str, str] = {}
    category_names: dict[str, str] = {}
    category_area_ids: dict[str, str] = {}
    category_area_names: dict[str, str] = {}
    status_counts = Counter()
    applicable_controls = 0

    for control in enriched:
        control_id = str(control["id"])
        level = assessments.get(control_id, "unknown")
        if level not in LEVEL_SCORES:
            level = "unknown"
        status_counts[level] += 1
        if level == "na":
            continue
        applicable_controls += 1
        score = LEVEL_SCORES[level]
        area_name = str(control["areaName"])
        area_id = str(control["areaId"])
        category_name = str(control["categoryName"])
        category_id = str(control.get("categoryId", category_name))
        area_totals[area_name] += 1
        category_totals[category_id] += 1
        category_status_counts[category_id][level] += 1
        category_names.setdefault(category_id, category_name)
        category_area_ids.setdefault(category_id, area_id)
        category_area_names.setdefault(category_id, area_name)
        if level in {"none", "partial", "done", "evidenced"}:
            area_scores.setdefault(area_name, []).append(score)
            category_scores.setdefault(category_id, []).append(score)
            category_first_reviewed_control.setdefault(category_id, control_id)
        if level in {"none", "partial"}:
            category_first_weak_control.setdefault(category_id, control_id)

        if level in {"unknown", "none", "partial"}:
            severity = "critical" if level == "none" else ("high" if level == "unknown" else "medium")
            recommended_actions = list(control["recommendedActions"])
            insights = build_gap_insights(
                control,
                level,
                assessments,
                multigap_overlaps,
                merged_control_checks.get(control_id),
                (domain_checks or {}).get(control_id),
                precomputed_findings=findings_by_control.get(control_id),
            )
            from .dual_layer import dual_layer_for_control

            dual = dual_layer_for_control(control_id)
            profile_priority = priority_delta(control_id, organization_context)
            if control_id in scope_priority_ids:
                profile_priority += 1
            gaps.append(
                {
                    "controlId": control_id,
                    "title": control["title"],
                    "categoryName": category_name,
                    "areaName": area_name,
                    "level": level,
                    "levelLabel": LEVEL_LABELS[level],
                    "severity": severity,
                    "priority": int(control["priority"]) + profile_priority,
                    "riskIfMissing": control["riskIfMissing"],
                    "problem": insights["organicAnalysis"],
                    "logicalBasis": _logical_basis(control, level),
                    "expectedIssue": _expected_issue(control, level),
                    "recommendedActions": recommended_actions,
                    "auditEvidenceNeeded": _audit_evidence_needed(control),
                    "relatedControlIds": control["relatedControlIds"][:5],
                    "projectHint": _project_hint(control_id, level),
                    "controlFocus": insights["controlFocus"],
                    "checklistBreakdown": insights["checklistBreakdown"],
                    "consequenceScenarios": insights["consequenceScenarios"],
                    "cascadeRisks": insights["cascadeRisks"],
                    "detailedSummary": insights["detailedSummary"],
                    "organicAnalysis": insights["organicAnalysis"],
                    "immediateActions": insights["immediateActions"],
                    "narrativeReport": insights["narrativeReport"],
                    "overlappingRisks": insights.get("overlappingRisks", []),
                    "causalBasis": insights.get("causalBasis", []),
                    "causalFindingIds": [
                        str(item.get("findingId"))
                        for item in findings_by_control.get(control_id, [])
                        if item.get("findingId")
                    ][:12],
                    "officialChecks": dual["officialChecks"],
                    "casebookProblems": dual["casebookProblems"],
                    "evidenceNote": _evidence_note(control, level),
                    "scenarioRelevant": False,
                    "profileRelevance": relevance_reasons(control_id, organization_context),
                    "profilePriority": profile_priority,
                }
            )

    scenario_control_ids: set[str] = set()
    scenario_focus: dict[str, object] | None = None
    if scenario_id:
        scenario = find_scenario(scenario_id)
        if scenario:
            scenario_control_ids = {str(control_id) for control_id in scenario["controlIds"]}
            for gap in gaps:
                gap["scenarioRelevant"] = str(gap["controlId"]) in scenario_control_ids
            scenario_gaps = [
                gap
                for gap in gaps
                if gap.get("scenarioRelevant") and gap.get("level") in {"none", "partial"}
            ]
            scenario_unreviewed = [
                gap
                for gap in gaps
                if gap.get("scenarioRelevant") and gap.get("level") == "unknown"
            ]
            scenario_focus = {
                "scenarioId": scenario_id,
                "title": scenario["title"],
                "description": scenario["description"],
                "relevantGapCount": len(scenario_gaps),
                "highlightedControlIds": [str(gap["controlId"]) for gap in scenario_gaps[:12]],
                "unreviewedCandidateCount": len(scenario_unreviewed),
            }

    gaps.sort(
        key=lambda item: (
            0 if item.get("scenarioRelevant") else 1,
            {"critical": 0, "high": 1, "medium": 2}[str(item["severity"])],
            -int(item.get("profilePriority", 0)),
            -int(item["priority"]),
        )
    )

    confirmed_gaps = [gap for gap in gaps if gap.get("level") in {"none", "partial"}]
    unreviewed_gaps = [gap for gap in gaps if gap.get("level") == "unknown"]
    reviewed_count = sum(
        int(status_counts.get(level, 0)) for level in ("none", "partial", "done", "evidenced")
    )
    total_score = sum(
        LEVEL_SCORES.get(assessments.get(str(c["id"]), "unknown"), 0)
        for c in enriched
        if assessments.get(str(c["id"]), "unknown") != "na"
    )
    overall_percent = round(total_score / applicable_controls, 1) if applicable_controls else 0.0
    assessed_total_score = sum(
        LEVEL_SCORES.get(assessments.get(str(c["id"]), "unknown"), 0)
        for c in enriched
        if assessments.get(str(c["id"]), "unknown") in {"none", "partial", "done", "evidenced"}
    )
    assessed_percent = (
        round(assessed_total_score / reviewed_count, 1) if reviewed_count else None
    )
    assessment_completion_percent = (
        round(reviewed_count / applicable_controls * 100, 1) if applicable_controls else 0.0
    )

    area_readiness = {
        area: round(sum(scores) / len(scores), 1) for area, scores in area_scores.items() if scores
    }
    area_coverage = {
        area: {
            "reviewedCount": len(area_scores.get(area, [])),
            "totalCount": total,
            "coveragePercent": round(len(area_scores.get(area, [])) / total * 100, 1),
        }
        for area, total in area_totals.items()
    }
    category_coverage = [
        {
            "category": category_names[category_id],
            "categoryId": category_id,
            "areaId": category_area_ids[category_id],
            "areaName": category_area_names[category_id],
            "reviewedCount": len(category_scores.get(category_id, [])),
            "totalCount": total,
            "coveragePercent": round(
                len(category_scores.get(category_id, [])) / total * 100,
                1,
            ),
            "statusCounts": dict(category_status_counts[category_id]),
        }
        for category_id, total in category_totals.items()
    ]
    weak_categories = sorted(
        (
            {
                "category": category_names[category_id],
                "categoryId": category_id,
                "areaId": category_area_ids[category_id],
                "areaName": category_area_names[category_id],
                "score": round(sum(scores) / len(scores), 1),
                "qualitativeLabel": qualitative_label(round(sum(scores) / len(scores), 1)),
                "count": category_totals[category_id],
                "reviewedCount": len(scores),
                "coveragePercent": round(len(scores) / category_totals[category_id] * 100, 1),
                "firstControlId": category_first_weak_control.get(
                    category_id, category_first_reviewed_control[category_id]
                ),
                "statusCounts": dict(category_status_counts[category_id]),
            }
            for category_id, scores in category_scores.items()
            if scores
        ),
        key=lambda item: (item["score"], -item["reviewedCount"]),
    )[:8]
    weak_gap_categories = [
        category
        for category in weak_categories
        if int((category.get("statusCounts") or {}).get("none", 0))
        + int((category.get("statusCounts") or {}).get("partial", 0))
        > 0
    ]

    evaluation_bands = classify_evaluation_bands(category_coverage)
    cascade_chains = _build_cascade_chains(confirmed_gaps[:12])
    recommendations = (
        _build_recommendations(confirmed_gaps, weak_gap_categories, assessed_percent or 0.0)
        if reviewed_count
        else []
    )
    # 2) Project problem-KB causal SSOT onto gap cards (align gap tab ↔ problem tab)
    gaps = project_causal_ssot_onto_gaps(
        gaps, list(problem_analysis.get("causalFindings") or [])
    )
    confirmed_gaps = [gap for gap in gaps if gap.get("level") in {"none", "partial"}]
    unreviewed_gaps = [gap for gap in gaps if gap.get("level") == "unknown"]
    confirmed_gaps_slice = confirmed_gaps[:50]
    key_insights = build_key_insights(
        overall_percent,
        _readiness_label(overall_percent),
        len(confirmed_gaps),
        dict(status_counts),
        weak_gap_categories,
        cascade_chains,
        confirmed_gaps_slice,
        multigap_overlaps,
    )
    executive_report = build_executive_report(
        overall_percent,
        _readiness_label(overall_percent),
        len(confirmed_gaps),
        dict(status_counts),
        area_readiness,
        weak_gap_categories,
        cascade_chains,
        confirmed_gaps_slice,
        recommendations,
        multigap_overlaps,
        evaluation_bands,
    )
    report_sections = build_report_sections(key_insights, executive_report)
    review_items = build_review_items(
        applicable_count=applicable_controls,
        reviewed_count=reviewed_count,
        overall_percent=overall_percent,
        assessed_percent=assessed_percent,
        status_counts=dict(status_counts),
        weak_categories=weak_gap_categories,
        cascade_chains=cascade_chains,
        confirmed_gaps=confirmed_gaps_slice,
        unreviewed_gaps=unreviewed_gaps,
        multigap_overlaps=multigap_overlaps,
    )
    gap_clusters = _build_gap_clusters(confirmed_gaps)
    weak_reviewed = int(status_counts.get("none", 0)) + int(status_counts.get("partial", 0))
    cert_phase_hint = (
        _cert_phase_hint_from_weak_ratio(weak_reviewed, reviewed_count)
        if reviewed_count and assessment_completion_percent >= 80
        else {
            "phaseId": "assessment-in-progress",
            "title": "진단 진행 중",
            "summary": (
                f"적용 통제의 {assessment_completion_percent}%를 점검했습니다. "
                "인증 단계 해석보다 미점검 통제의 판정을 먼저 완료하세요."
            ),
            "relatedControlIds": [],
        }
    )
    suggested_scenarios = suggested_scenario_ids(organization_context)
    evidence_pack = build_minimum_evidence_pack(organization_context)
    confirmation_actions, confirmation_action_meta = build_confirmation_actions(
        gaps=gaps,
        quest_checks=quest_checks,
        evidence_slots=evidence_slots,  # type: ignore[arg-type]
        input_confidence=input_confidence,
        controls=enriched,
        session_bundle_mode=session_bundle_mode,
        organization_context=organization_context,
    )
    control_session_details = build_control_session_details(enriched)
    priority_quests, priority_quest_candidates = build_priority_quests(
        assessments=assessments,
        organization_context=organization_context,
        quest_checks=quest_checks,
        evidence_slots=evidence_slots,  # type: ignore[arg-type]
        input_confidence=input_confidence,
        controls=enriched,
    )
    confidence_summary = summarize_input_confidence(assessments, input_confidence)

    from .official_kb import institution_public_payload, simple_cert_hints
    from .verbalize_inference import apply_verbalizing

    institution_hints = institution_public_payload() or None
    cert_hints = simple_cert_hints(
        organization_context.tags if organization_context else frozenset()
    )

    structured = {
        "overallReadiness": overall_percent,
        "readinessLabel": qualitative_label(overall_percent),
        "scoreDisclaimer": SCORE_DISCLAIMER,
        "scoreWeightSummary": "양호 · 보통 · 보완 필요 · 기초 보완 필요",
        "overallScoreTooltip": OVERALL_SCORE_TOOLTIP,
        "assessedScoreTooltip": ASSESSED_SCORE_TOOLTIP,
        "assessedReadiness": assessed_percent,
        "assessedReadinessLabel": qualitative_label(assessed_percent),
        "assessmentCompletionPercent": assessment_completion_percent,
        "reviewedControlCount": reviewed_count,
        "unreviewedControlCount": len(unreviewed_gaps),
        "statusCounts": dict(status_counts),
        "areaReadiness": area_readiness,
        "areaCoverage": area_coverage,
        "categoryCoverage": category_coverage,
        "weakCategories": weak_gap_categories,
        "evaluationBands": evaluation_bands,
        "gapCount": len(confirmed_gaps),
        "analysisCandidateCount": len(gaps),
        "criticalGaps": [
            gap for gap in confirmed_gaps_slice if gap["severity"] == "critical"
        ][:15],
        "topGaps": confirmed_gaps_slice,
        "confirmedGaps": confirmed_gaps_slice,
        "cascadeChains": cascade_chains,
        "recommendations": recommendations,
        "portfolioSummary": build_portfolio_summary(
            assessments, overall_percent, confirmed_gaps
        ),
        "keyInsights": key_insights,
        "reviewItems": review_items,
        "executiveReport": executive_report,
        "reportSections": report_sections,
        "gapClusters": gap_clusters,
        "multiGapOverlaps": multigap_overlaps,
        "scenarioFocus": scenario_focus,
        "certPhaseHint": cert_phase_hint,
        "problemAnalysis": problem_analysis,
        "profileContext": organization_context.to_public_dict() if organization_context else None,
        "scopeDraft": scope_draft,
        "suggestedScenarioIds": suggested_scenarios,
        "minimumEvidencePack": evidence_pack,
        "confirmationActions": confirmation_actions,
        "confirmationActionMeta": confirmation_action_meta,
        "controlSessionDetails": control_session_details,
        "inputConfidenceSummary": confidence_summary,
        "applicabilityNotes": applicability_notes,
        "priorityQuests": priority_quests,
        "priorityQuestMeta": {
            "shown": len(priority_quests),
            "candidates": priority_quest_candidates,
            "limit": 10,
            "gapCount": len(confirmed_gaps),
        },
        "applicableControlCount": applicable_controls,
        "naControlCount": int(status_counts.get("na", 0)),
        "institutionHints": institution_hints,
        "simpleCertHints": cert_hints,
        "pipelineMeta": {
            "stages": [
                "retrieve",
                "causal",
                "gap_ssot",
                "quests",
                "template",
                "verbalize" if verbalize else "verbalize_skipped",
            ],
            "view": view if view in {"full", "quest", "causal", "report"} else "full",
            "verbalizeMaxGaps": max(1, min(50, int(verbalize_max_gaps or 12))),
            "verbalizeIncludeQuests": bool(verbalize_include_quests),
        },
    }
    structured = _apply_analyze_view(structured, view)
    structured = apply_verbalizing(
        structured,
        enabled=verbalize,
        chat_client=verbalize_client,
        consistency_samples=2 if verbalize_consistency else 1,
        max_gaps=max(1, min(50, int(verbalize_max_gaps or 12))),
        include_quests=bool(verbalize_include_quests),
    )
    # 상세 탭: official_kb 템플릿 해설(판정 불변). LLM 업그레이드는 /controls/report.
    from .detail_narrative import apply_detail_narratives

    return apply_detail_narratives(structured, enabled=False)


def _apply_analyze_view(structured: dict[str, object], view: str) -> dict[str, object]:
    """Soft view projection — keep AssessResponse shape, trim heavy sections for thin clients."""
    normalized = view if view in {"full", "quest", "causal", "report"} else "full"
    if normalized == "full":
        return structured
    result = dict(structured)
    if normalized == "quest":
        result["topGaps"] = list(result.get("topGaps") or [])[:8]
        result["criticalGaps"] = list(result.get("criticalGaps") or [])[:5]
        result["cascadeChains"] = []
        result["multiGapOverlaps"] = []
        result["gapClusters"] = []
        result["executiveReport"] = None
        result["reportSections"] = []
        result["keyInsights"] = list(result.get("keyInsights") or [])[:3]
    elif normalized == "causal":
        result["confirmationActions"] = []
        result["priorityQuests"] = []
        result["confirmationActionMeta"] = {
            "shown": 0,
            "candidates": 0,
            "limit": 10,
            "mode": "chain",
            "bundleTitle": "",
            "bundleSummary": "",
            "areaLabel": None,
            "themeId": None,
            "chainPath": [],
        }
        result["priorityQuestMeta"] = {"shown": 0, "candidates": 0, "limit": 10, "gapCount": 0}
        result["executiveReport"] = None
        result["reportSections"] = []
        result["recommendations"] = []
    elif normalized == "report":
        result["confirmationActions"] = []
        result["priorityQuests"] = []
        result["confirmationActionMeta"] = {
            "shown": 0,
            "candidates": 0,
            "limit": 10,
            "mode": "chain",
            "bundleTitle": "",
            "bundleSummary": "",
            "areaLabel": None,
            "themeId": None,
            "chainPath": [],
        }
        result["priorityQuestMeta"] = {"shown": 0, "candidates": 0, "limit": 10, "gapCount": 0}
        result["topGaps"] = list(result.get("topGaps") or [])[:12]
        result["criticalGaps"] = list(result.get("criticalGaps") or [])[:8]
    return result


def _build_cascade_chains(top_gaps: list[dict[str, object]]) -> list[dict[str, object]]:
    from .control_graph import relation_evidence_for
    from .official_kb import official_chunks, official_evidence_examples

    def comparison_plan(source_id: str, target_id: str, reason: str) -> tuple[list[dict[str, str]], str]:
        text = f"{source_id}>{target_id} {reason}"
        if source_id == "1.2.3" and target_id == "1.2.4":
            return ([
                {"key": "위험 ID", "source": "위험평가 결과의 위험 식별번호", "target": "보호대책 이행계획의 연결 위험번호", "fail": "누락되거나 다른 번호"},
                {"key": "처리 결정", "source": "위험도·수용기준·감소/회피/전가/수용 결정", "target": "선정된 대책과 선정 사유", "fail": "위험도와 무관한 대책 또는 사유 없음"},
                {"key": "실행 책임", "source": "위험 소유자와 승인자", "target": "담당부서·담당자·경영진 승인", "fail": "책임자 불일치 또는 승인 누락"},
                {"key": "이행 조건", "source": "평가일·우선순위", "target": "완료기한·예산·진행상태", "fail": "고위험 항목의 기한·예산 누락"},
            ], "표본 위험 중 수용기준을 초과한 항목이 보호대책 이행계획에 빠졌거나 핵심 필드가 추적되지 않으면 연계 문제로 확인합니다.")
        if "로그" in text or "기록" in text or target_id in {"2.9.5", "2.11.3"}:
            return ([
                {"key": "대상", "source": "로그를 생성하는 시스템·계정 목록", "target": "수집·검토 대상 목록", "fail": "생성 대상이 수집/검토 범위에서 누락"},
                {"key": "시간", "source": "발생 시각·보존기간", "target": "수집 주기·점검 주기", "fail": "사고 구간을 재현할 기록 부재"},
                {"key": "식별자", "source": "사용자·이벤트·자산 식별자", "target": "분석 규칙과 조치 티켓", "fail": "이벤트에서 조치 기록까지 추적 불가"},
            ], "동일 표본 이벤트를 발생 기록에서 검토·조치 기록까지 추적할 수 없으면 연계 문제로 확인합니다.")
        if "점검" in text or "개선" in text or target_id in {"1.4.2", "1.4.3"}:
            return ([
                {"key": "점검 항목", "source": "기준 변경·점검 대상과 판단 결과", "target": "점검표·개선과제의 항목 ID", "fail": "확인 대상이 후속 목록에서 누락"},
                {"key": "조치", "source": "발견사항·위험도", "target": "담당자·기한·완료 증적", "fail": "발견사항이 종결 기록과 연결되지 않음"},
                {"key": "재검증", "source": "승인된 기준/결정", "target": "개선 후 재점검 결과", "fail": "완료 표시만 있고 효과 확인 없음"},
            ], "발견사항 표본이 후속 조치와 재검증 결과까지 이어지지 않으면 연계 문제로 확인합니다.")
        return ([
            {"key": "대상 식별자", "source": "선행 문서의 시스템·업무·자산 ID", "target": "후속 실행 기록의 동일 ID", "fail": "대상 누락 또는 식별 불가"},
            {"key": "결정과 실행", "source": "승인된 판단·요구사항", "target": "설정·절차·작업 결과", "fail": "승인 내용과 실제 실행 불일치"},
            {"key": "책임과 시점", "source": "승인자·승인일", "target": "담당자·실행일·검토일", "fail": "실행 선후관계 또는 책임 추적 불가"},
        ], "동일한 표본을 선행 결정에서 후속 실행까지 추적할 수 없거나 승인 내용과 실행 결과가 다르면 연계 문제로 확인합니다.")

    chains: list[dict[str, object]] = []
    seen: set[str] = set()
    for gap in top_gaps:
        control_id = str(gap["controlId"])
        for cascade in gap.get("cascadeRisks", []):
            target_id = str(cascade["targetControlId"])
            if not target_id or target_id == control_id:
                continue
            key = f"{control_id}->{target_id}"
            if key in seen:
                continue
            seen.add(key)
            relation_evidence = relation_evidence_for(control_id, target_id) or {}
            source_official = official_chunks(control_id, max_checks=0, max_evidence=0, max_defects=3, max_laws=0)
            target_official = official_chunks(target_id, max_checks=0, max_evidence=0, max_defects=3, max_laws=0)
            source_examples = [str(row["text"]) for row in source_official.get("chunks", []) if row.get("kind") == "defectExample"]
            target_examples = [str(row["text"]) for row in target_official.get("chunks", []) if row.get("kind") == "defectExample"]
            comparison_rows, decision_rule = comparison_plan(control_id, target_id, str(cascade.get("connectionReason") or ""))
            chains.append(
                {
                    "originControlId": control_id,
                    "originTitle": gap["title"],
                    "originLevel": gap.get("level"),
                    "originLevelLabel": gap.get("levelLabel"),
                    "targetControlId": target_id,
                    "targetTitle": cascade.get("targetTitle"),
                    "targetLevel": cascade.get("targetLevel"),
                    "targetLevelLabel": LEVEL_LABELS.get(
                        str(cascade.get("targetLevel")), "미점검"
                    ),
                    "connectionReason": cascade.get("connectionReason"),
                    "impact": cascade.get("impact"),
                    "logicSteps": list(cascade.get("logicSteps") or []),
                    "evidenceToCheck": list(cascade.get("evidenceToCheck") or []),
                    "operationalImpact": cascade.get("operationalImpact"),
                    "auditImpact": cascade.get("auditImpact"),
                    "evidenceLabel": cascade.get("evidenceLabel"),
                    "groundingNote": cascade.get("groundingNote"),
                    "groundingLevel": cascade.get("groundingLevel"),
                    "relationEvidence": list(relation_evidence.get("evidence") or []),
                    "sourceDefectExamples": source_examples,
                    "targetDefectExamples": target_examples,
                    "validationCriteria": [
                        f"{control_id}에서 승인된 대상·범위가 {target_id}의 적용 대상과 식별자 기준으로 일치합니다.",
                        "선행 결정의 승인 시점이 후속 실행보다 빠르고, 변경 이력이 서로 추적됩니다.",
                        "예외·제외 대상과 책임자가 양쪽 기록에서 동일하며 실제 표본으로 재현됩니다.",
                    ],
                    "rejectionCriteria": [
                        "두 통제가 서로 다른 대상·시스템·업무에 적용되어 입력과 산출물을 공유하지 않습니다.",
                        "후속 통제가 독립된 승인 기준과 완전한 운영 증적을 갖고 있어 선행 통제 결함의 영향을 받지 않습니다.",
                    ],
                    "sourceArtifacts": official_evidence_examples(control_id)[:4],
                    "targetArtifacts": official_evidence_examples(target_id)[:4],
                    "comparisonRows": comparison_rows,
                    "decisionRule": decision_rule,
                    "severity": cascade.get("severity"),
                }
            )
    return chains[:15]


def _project_hint(control_id: str, level: str) -> str | None:
    hints = {
        "1.4.2": "셀프진단 체크리스트 결과를 관리체계 점검 학습 증적으로 활용할 수 있습니다.",
        "2.7.1": "이 프로젝트의 AES-GCM 비식별화(redact) 구현을 암호정책 적용 증적으로 연결할 수 있습니다.",
        "2.7.2": "API 요청 본문 키 주입 방식의 한계를 README에 문서화해 키관리 갭을 설명할 수 있습니다.",
        "2.8.2": "pytest/CI 테스트를 보안 요구사항 검증 증적으로 연결할 수 있습니다.",
        "2.9.4": "PII scan API로 examples/sample.log 등에서 탐지된 패턴을 로그 내 개인정보 노출 식별 증적으로 연결할 수 있습니다.",
        "2.10.3": "API 입력 검증/레이트 리밋을 공개서버 보호 통제 학습에 연결할 수 있습니다.",
        "3.1.3": "redact API의 마스킹/토큰화를 주민번호 등 고유식별정보 처리 제한 논의에 활용할 수 있습니다.",
        "3.2.1": "PII 탐지 API 응답 구조를 개인정보 현황/노출 식별 증적으로 활용할 수 있습니다.",
    }
    if level in {"done", "evidenced"}:
        return None
    return hints.get(control_id)


def _evidence_note(control: dict[str, object], level: str) -> str | None:
    evidence_ids = list(control.get("evidenceIds", []))
    if not evidence_ids or level in {"done", "evidenced"}:
        return None
    refs = ", ".join(str(item) for item in evidence_ids[:4])
    status = str(control.get("implementationStatus", ""))
    if status == "implemented":
        return (
            f"코드/구현 증적({refs})은 있으나 운영 절차/정기 점검/담당자 지정 기록까지 연결해야 "
            f"심사에서 이행으로 인정받기 쉽습니다."
        )
    if status == "evidence_mapped":
        return f"문서/매핑 증적({refs})은 있으나 실제 운영 설정/로그/점검표와의 일치를 확인하세요."
    return None


def _gap_recommendation_detail(gap: dict[str, object]) -> str:
    control_id = str(gap["controlId"])
    immediate = gap.get("immediateActions") or []
    if immediate:
        return str(immediate[0])
    if control_id in CONTROL_RECOMMENDATION_DETAILS:
        return CONTROL_RECOMMENDATION_DETAILS[control_id]
    recommended = gap.get("recommendedActions") or []
    if recommended:
        return str(recommended[0])
    return str(gap.get("riskIfMissing", ""))


def _build_gap_clusters(gaps: list[dict[str, object]]) -> list[dict[str, object]]:
    from .defect_priority import defect_mapping_meta
    from .official_kb import official_chunks

    by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    for gap in gaps:
        by_category[str(gap["categoryName"])].append(gap)

    clusters: list[dict[str, object]] = []
    for category, items in sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(items) < 2:
            continue
        none_count = sum(1 for item in items if item.get("level") == "none")
        partial_count = sum(1 for item in items if item.get("level") == "partial")
        severities = [str(item["severity"]) for item in items]
        top_severity = "critical" if "critical" in severities else ("high" if "high" in severities else "medium")
        lead = items[0]
        selection_reasons: list[str] = []
        if lead.get("scenarioRelevant"):
            selection_reasons.append("선택한 진단 시나리오에 직접 관련된 통제입니다.")
        if lead.get("level") == "none":
            selection_reasons.append("미이행으로 확인되어 부분 이행 통제보다 먼저 보완합니다.")
        else:
            selection_reasons.append("부분 이행 통제 중 통제 중요도와 조직 적용 우선도가 가장 높습니다.")
        profile_relevance = [str(reason) for reason in lead.get("profileRelevance", []) if reason]
        if profile_relevance:
            selection_reasons.append(f"조직 프로필 관련성: {profile_relevance[0]}")
        cascade_count = len(lead.get("cascadeRisks", []))
        if cascade_count:
            selection_reasons.append(f"후속 통제에 영향을 줄 수 있는 연결 경로가 {cascade_count}개 있습니다.")
        ordered_items = sorted(
            items,
            key=lambda item: tuple(int(part) for part in str(item["controlId"]).split(".")),
        )
        mapping_meta = defect_mapping_meta(str(lead["controlId"]))
        official = official_chunks(str(lead["controlId"]), max_checks=0, max_evidence=0, max_defects=4, max_laws=0)
        defect_evidence = {
            **mapping_meta,
            "examples": [
                str(chunk["text"])
                for chunk in official.get("chunks", [])
                if chunk.get("kind") == "defectExample"
            ],
            "sourceDoc": official.get("sourceDoc"),
            "pages": official.get("pages") or [],
        }
        cluster_controls = [
            {
                "controlId": str(item["controlId"]),
                "title": str(item["title"]),
                "level": str(item["level"]),
                "levelLabel": str(item["levelLabel"]),
                "nextAction": _gap_recommendation_detail(item),
            }
            for item in ordered_items
        ]
        clusters.append(
            {
                "theme": category,
                "gapCount": len(items),
                "noneCount": none_count,
                "partialCount": partial_count,
                "controlIds": [item["controlId"] for item in cluster_controls],
                "controls": cluster_controls,
                "primaryControl": {
                    "controlId": str(lead["controlId"]),
                    "title": str(lead["title"]),
                    "level": str(lead["level"]),
                    "levelLabel": str(lead["levelLabel"]),
                    "nextAction": _gap_recommendation_detail(lead),
                    "riskIfMissing": str(lead.get("riskIfMissing") or ""),
                    "selectionReasons": selection_reasons,
                    "defectEvidence": defect_evidence if mapping_meta["defectCount"] or defect_evidence["examples"] else None,
                },
                "summary": (
                    f"{category} 중분류에서 미이행 {none_count}개, 부분 이행 {partial_count}개가 확인되었습니다. "
                    f"우선 {lead['controlId']} {lead['title']}({lead['levelLabel']})부터 보완하세요."
                ),
                "severity": top_severity,
            }
        )
    return clusters[:6]


def _cert_phase_hint_from_weak_ratio(
    weak_reviewed: int, reviewed_count: int
) -> dict[str, object]:
    """점수%가 아니라 점검분 중 미이행·부분 비율로 준비 단계만 힌트한다."""
    weak_ratio = (weak_reviewed / reviewed_count * 100) if reviewed_count else 100.0
    if weak_ratio >= 75:
        phase = CERTIFICATION_PHASES[0]
    elif weak_ratio >= 45:
        phase = CERTIFICATION_PHASES[1]
    elif weak_ratio >= 25:
        phase = CERTIFICATION_PHASES[2]
    elif weak_ratio >= 10:
        phase = CERTIFICATION_PHASES[3]
    else:
        phase = CERTIFICATION_PHASES[4]
    return {
        "phaseId": phase["id"],
        "title": phase["title"],
        "summary": (
            f"{phase['summary']} "
            f"(점검분 미흡 비율 {round(weak_ratio, 1)}% — 참고 힌트이며 인증 판정이 아닙니다.)"
        ),
        "relatedControlIds": list(phase["relatedControlIds"]),
    }


def _logical_basis(control: dict[str, object], level: str) -> str:
    checklist_items = list(control.get("checklistItems", []))
    evidence_ids = list(control.get("evidenceIds", []))
    checklist_summary = " / ".join(str(item) for item in checklist_items[:2])
    if level == "unknown":
        return (
            f"자가진단에서 아직 점검하지 않았습니다. 최소한 '{control['categoryName']}' 분야의 확인사항"
            f"({checklist_summary})을 확인하고, 적용 여부를 판단해야 합니다."
        )
    if level == "none":
        return (
            f"통제가 미이행으로 표시되었습니다. ISMS-P 심사에서는 정책/절차/시스템 설정/운영기록 중 "
            f"하나 이상의 객관적 증적이 요구되지만 현재 확인된 증적이 없습니다."
        )
    if evidence_ids:
        return (
            f"일부 구현 또는 문서 증적({', '.join(str(item) for item in evidence_ids)})은 있으나, "
            f"운영 절차/담당자/정기 점검 기록까지 연결되지 않아 부분 이행으로 판단됩니다."
        )
    return (
        f"통제 방향은 인지했지만 증적 수준이 부족합니다. 체크리스트({checklist_summary})를 기준으로 "
        f"정책, 설정값, 테스트 결과, 점검 기록을 보강해야 합니다."
    )


def _expected_issue(control: dict[str, object], level: str) -> str:
    prefix = {
        "unknown": "점검 누락 상태가 지속되면 실제 이행 여부를 설명할 수 없어 심사 대응 리스크가 생깁니다.",
        "none": "미이행 상태에서는 결함 가능성이 높고 관련 통제까지 연쇄적으로 취약해질 수 있습니다.",
        "partial": "부분 이행 상태에서는 구현은 있어도 운영 지속성/증적 충분성 부족으로 결함이 발생할 수 있습니다.",
    }.get(level, "통제 미흡 상태입니다.")
    return f"{prefix} {control['riskIfMissing']}"


def _audit_evidence_needed(control: dict[str, object]) -> list[str]:
    category_id = str(control["categoryId"])
    defaults = ["정책/지침 문서", "담당자/승인 기록", "정기 점검 또는 운영 로그"]
    category_evidence = {
        "1.1": ["인증 범위서", "정보보호 정책 승인 기록", "조직도/역할 책임표"],
        "1.2": ["정보자산 목록", "개인정보 흐름도", "위험평가표와 보호대책 선정표"],
        "1.3": ["보호대책 이행 계획", "담당자 공유 기록", "운영현황 대장"],
        "1.4": ["자체점검표", "법적 요구사항 검토표", "시정조치 이력"],
        "2.5": ["계정 발급/변경/삭제 신청서", "권한 매트릭스", "정기 권한검토 결과"],
        "2.6": ["방화벽/ACL 설정", "DB 접근 통제 설정", "원격접근 승인/접속 기록"],
        "2.7": ["암호정책서", "암호화 적용 화면/코드/설정", "키관리 절차와 키 접근권한 기록"],
        "2.8": ["보안 요구사항 정의서", "보안 테스트 결과", "운영 이관 승인 기록"],
        "2.9": ["변경관리 이력", "로그 보관 정책", "로그 점검 결과"],
        "2.10": ["보안솔루션 운영 현황", "취약점/패치 조치 결과", "클라우드 보안 설정 점검표"],
        "2.11": ["사고 대응 절차서", "취약점 점검 결과", "모의훈련 결과와 개선 조치"],
        "2.12": ["재해복구 계획", "백업 정책", "복구 시험 결과"],
        "3.1": ["수집 동의 화면", "수집 항목/목적 매핑표", "주민번호/민감정보 처리 근거"],
        "3.2": ["개인정보 보유 현황표", "목적 외 이용 통제 기록", "마스킹/가명처리 적용 증적"],
        "3.3": ["제3자 제공/위탁 계약서", "수탁사 점검 결과", "국외이전 고지/동의 기록"],
        "3.4": ["파기 기준표", "파기 실행 로그", "백업/로그 파기 검토 기록"],
        "3.5": ["개인정보 처리방침", "권리 행사 접수/처리 이력", "정보주체 통지 기록"],
    }
    return category_evidence.get(category_id, defaults)


def _readiness_label(percent: float) -> str:
    return qualitative_label(percent)


def _build_recommendations(
    gaps: list[dict[str, object]],
    weak_categories: list[dict[str, object]],
    overall_percent: float,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if overall_percent < 35:
        items.append(
            {
                "priority": "urgent",
                "title": "인증 범위와 정책 체계부터 수립",
                "detail": "1.1.4 범위 설정, 1.1.5 정책 수립, 1.2.1 자산 식별을 먼저 완료하세요.",
            }
        )
    if weak_categories:
        weakest = weak_categories[0]
        weak_level = str(weakest.get("qualitativeLabel") or qualitative_label(weakest.get("score")))
        items.append(
            {
                "priority": "high",
                "title": f"확인된 미흡 집중 보완: {weakest['category']}",
                "detail": (
                    f"해당 분야에 미이행 또는 부분 이행 통제가 있으며 참고 구간은 '{weak_level}'입니다. "
                    "확인된 미흡 통제부터 체크리스트와 증적을 보완하세요."
                ),
            }
        )
    for gap in gaps[:5]:
        items.append(
            {
                "priority": str(gap["severity"]),
                "title": f"{gap['controlId']} {gap['title']} — {gap['levelLabel']}",
                "detail": _gap_recommendation_detail(gap),
            }
        )
    return items[:12]


def bootstrap_assessment() -> dict[str, str]:
    """Fill all 101 controls from portfolio implementation metadata.

    - project-owned / implemented → done
    - evidence_mapped → partial
    - study_mapped (or other) → none
    No ``unknown`` left: the UI button promises a filled baseline.
    """
    project_done = {
        "2.7.1",
        "2.7.2",
        "3.2.1",
        "3.1.3",
        "2.8.2",
        "2.10.3",
        "2.9.4",
        "1.4.2",
    }
    assessments: dict[str, str] = {}
    for control in list_checklist_controls():
        control_id = str(control["id"])
        status = str(control.get("implementationStatus") or "")
        if control_id in project_done or status == "implemented":
            assessments[control_id] = "done"
        elif status == "evidence_mapped":
            assessments[control_id] = "partial"
        else:
            assessments[control_id] = "none"
    return assessments


def build_portfolio_summary(
    assessments: dict[str, str],
    overall_percent: float,
    gaps: list[dict[str, object]],
) -> str:
    reviewed = sum(1 for level in assessments.values() if level not in {"unknown", "na"})
    evidenced = sum(1 for level in assessments.values() if level == "evidenced")
    done = sum(1 for level in assessments.values() if level in {"done", "evidenced"})
    na_count = sum(1 for level in assessments.values() if level == "na")
    applicable = max(len(assessments) - na_count, 1)
    critical = sum(1 for gap in gaps if gap["severity"] == "critical")

    lines = [
        "## ISMS-P 학습/셀프진단 포트폴리오 요약",
        "",
        f"- {OVERALL_SCORE_LABEL}: **{qualitative_label(overall_percent)}** ({SCORE_DISCLAIMER})",
        f"- 참고 구간: 양호 · 보통 · 보완 필요 · 기초 보완 필요",
        f"- 점검 완료 통제: {reviewed}/{applicable} (해당 없음 {na_count}개 제외)",
        f"- 이행/증적 확보: {done}개 (증적 확보 {evidenced}개)",
        f"- 미이행/부분 이행 갭: {len(gaps)}개 (미이행 {critical}개)",
        "",
        "### 학습 내용",
        "- ISMS-P 101개 인증기준을 관리체계/보호대책/개인정보 생명주기 관점으로 구조화했습니다.",
        "- 리테일 IT 시나리오(고객센터 로그, 멤버십, 외주 접근 등)별 통제 연결 흐름을 설계했습니다.",
        "- PII 탐지/비식별화 구현을 2.7 암호화, 3.2 보유/이용 통제와 매핑했습니다.",
        "",
        "### 주요 갭 (상위)",
    ]
    for gap in gaps[:8]:
        lines.append(f"- **{gap['controlId']} {gap['title']}** ({gap['levelLabel']}): {gap['riskIfMissing']}")
    lines.extend(
        [
            "",
            "### 다음 액션",
            "- 미점검/미이행 통제부터 체크리스트를 채우고 증적 파일을 연결합니다.",
            "- 암호화/접근통제/개인정보 생명주기(3.x) 영역을 우선 보완합니다.",
            "- 인증 운영 흐름(준비→이행→심사→사후관리)에 맞춰 증적 패키지를 정리합니다.",
        ]
    )
    return "\n".join(lines)
