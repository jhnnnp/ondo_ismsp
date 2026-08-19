"""통제 검색용 사용자 워딩 힌트.

공식 제목만으로는 '불필요한계정제거' 같은 현장 표현이 잡히지 않는다.
안내서 확인사항/결함사례, 사례집 문구, 자주 쓰는 점검 워딩을 힌트로 붙인다.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .official_text import sanitize_official_text

_CASE_PREFIX_RE = re.compile(r"^\[.*?\]\s*")
_VENDOR_TAG_RE = re.compile(r"\((?:CELA|AWS|Azure|GCP|NCP)\)")
_INTENT_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_INTENT_STOP_WORDS = {
    "관련", "관리", "보안", "점검", "확인", "필요", "여부", "미흡", "적용",
    "운영", "정보", "시스템", "절차", "정책", "사항", "현황", "대한", "위한",
}
_INTENT_SUFFIXES = ("해주세요", "인가요", "입니다", "합니다", "했어요", "되어", "있음", "없음", "으로", "에서", "까지", "부터", "에게", "이", "가", "을", "를", "은", "는", "의", "에", "로")

# 현장 점검표, 인터뷰, 취약점 진단 결과에서 자주 쓰는 비공식 표현.
# 101개 통제 모두 최소 2개의 사용자 워딩을 갖게 하여 공식 통제명을
# 모르는 사용자도 문제/조치 중심으로 찾을 수 있게 한다.
USER_SEARCH_ALIASES: dict[str, list[str]] = {
    "1.1.1": ["경영진 승인", "대표이사 보안 참여", "정보보호 의사결정"],
    "1.1.2": ["CISO 지정", "개인정보 보호책임자 지정", "보안 책임자 선임"],
    "1.1.3": ["정보보호 조직도", "보안 담당부서 구성", "개인정보보호 조직"],
    "1.1.4": ["인증 범위", "ISMS 범위 누락", "서비스 범위 설정"],
    "1.1.5": ["정보보호 정책", "보안 규정 수립", "개인정보보호 정책"],
    "1.1.6": ["보안 예산", "정보보호 인력", "보안 자원 부족"],
    "1.2.1": ["자산 목록", "정보자산 식별", "자산대장 누락"],
    "1.2.2": ["개인정보 흐름도", "데이터 흐름 분석", "처리 현황 파악"],
    "1.2.3": ["위험평가", "리스크 분석", "위험 식별 누락"],
    "1.2.4": ["보호대책 선택", "위험처리 계획", "통제 선정"],
    "1.3.1": ["보호대책 이행", "보안조치 구현", "통제 미적용"],
    "1.3.2": ["보안정책 공유", "보호대책 공지", "담당자 전파"],
    "1.3.3": ["운영현황 보고", "보안활동 관리", "이행상태 점검"],
    "1.4.1": ["법규 준수", "컴플라이언스 검토", "법적 요구사항 누락"],
    "1.4.2": ["내부감사", "ISMS 자체점검", "관리체계 점검"],
    "1.4.3": ["시정조치", "감사 지적 개선", "재발방지"],
    "2.1.1": ["정책 개정", "보안규정 최신화", "정책 검토주기"],
    "2.1.2": ["보안조직 변경", "담당자 현행화", "조직 역할 관리"],
    "2.1.3": ["자산대장 현행화", "자산 책임자", "정보자산 변경관리"],
    "2.2.1": ["주요직무자", "보안 핵심인력 지정", "직무자 명단"],
    "2.2.2": ["직무분리", "상호 견제", "개발 운영 권한 분리"],
    "2.2.3": ["보안서약서", "비밀유지서약", "입사자 서약"],
    "2.2.4": ["보안교육", "개인정보 교육", "교육 미이수"],
    "2.2.5": [
        "퇴사자 계정 회수", "직무변경 권한 회수", "퇴직자 접근권한 삭제",
        "재직 여부 확인", "퇴사 여부 확인",
    ],
    "2.2.6": ["보안 위반 징계", "규정 위반 조치", "위반자 제재"],
    "2.3.1": ["협력업체 현황", "외주인력 목록", "수탁사 관리"],
    "2.3.2": ["보안 계약조항", "외주 계약 보안", "위탁계약서"],
    "2.3.3": ["협력사 보안점검", "수탁사 관리감독", "외주 보안 이행"],
    "2.3.4": [
        "계약종료 자료회수", "외주인력 계정삭제", "수탁사 계약 만료",
        "계약 여부 확인", "계약 만료 계정 삭제",
    ],
    "2.4.1": ["보호구역", "통제구역 지정", "서버실 보안구역"],
    "2.4.2": ["출입통제", "출입기록", "서버실 무단출입"],
    "2.4.3": ["서버실 장비 보호", "정보시스템 물리보안", "장비 접근통제"],
    "2.4.4": ["UPS", "항온항습", "화재 감지 설비"],
    "2.4.5": ["보호구역 작업", "서버실 작업기록", "외부인 작업통제"],
    "2.4.6": ["장비 반출입", "노트북 반출", "기기 반입 승인"],
    "2.4.7": ["클린데스크", "화면 잠금", "사무실 문서 방치"],
    "2.5.1": [
        "불필요한 계정 제거",
        "미사용 계정 삭제",
        "휴면 계정 삭제",
        "계정 발급 해지", "계정 정리", "사용하지 않는 아이디", "불필요 사용자 삭제",
        "퇴사자 계정 삭제",
        "계정 필요성 확인",
        "시스템 계정 잔존",
    ],
    "2.5.2": ["공용 계정", "계정 공유", "식별자 중복", "누가 접속했는지 모름"],
    "2.5.3": ["로그인 실패 제한", "MFA", "다중인증", "OTP", "인증 우회"],
    "2.5.4": ["비밀번호 복잡도", "패스워드 변경주기", "임시 비밀번호", "초기 비밀번호"],
    "2.5.5": ["관리자 그룹 최소 계정", "root 계정", "특권 계정", "wheel", "Administrators"],
    "2.5.6": ["장기 미사용 계정", "계정 정기 검토", "권한 리뷰", "휴면 계정 잠금", "과도한 권한"],
    "2.6.1": ["네트워크 접근통제", "방화벽 정책", "허용 IP", "망 접근 제한"],
    "2.6.2": ["불필요 포트", "telnet", "ftp 사용", "서버 접근제한", "SSH 접속통제"],
    "2.6.3": ["응용프로그램 권한", "업무시스템 접근", "애플리케이션 접근통제"],
    "2.6.4": ["DB 접근통제", "데이터베이스 계정", "DBA 권한", "쿼리 권한"],
    "2.6.5": ["무선랜 보안", "와이파이 비밀번호", "비인가 AP"],
    "2.6.6": ["VPN", "원격접속", "재택근무 접속", "원격제어"],
    "2.6.7": ["인터넷 차단", "유해사이트 접속", "업무망 인터넷", "외부 사이트 통제"],
    "2.7.1": ["개인정보 암호화", "전송구간 암호화", "TLS"],
    "2.7.2": ["암호키 보관", "키 교체", "암호키 노출", "KMS"],
    "2.8.1": ["개발 보안요구사항", "시큐어코딩 요구", "보안 요구 누락"],
    "2.8.2": ["보안테스트", "개발 검수", "취약점 시험", "보안 요구사항 검토"],
    "2.8.3": ["개발 운영 분리", "테스트 서버 분리", "운영망 개발접근"],
    "2.8.4": ["운영데이터 테스트 사용", "테스트 개인정보", "개발DB 개인정보"],
    "2.8.5": ["소스코드 관리", "소스 유출", "형상관리 권한", "git 접근권한"],
    "2.8.6": ["운영배포 승인", "배포 절차", "개발자 운영반영", "릴리즈 이관"],
    "2.9.1": ["변경관리", "시스템 변경 승인", "무단 변경", "변경 이력"],
    "2.9.2": ["장애관리", "용량 모니터링", "성능 저하", "장애 대응"],
    "2.9.3": ["백업 주기", "복구 테스트"],
    "2.9.4": ["접속 로그", "감사 로그", "로그 미수집", "로그 보관기간"],
    "2.9.5": ["로그 점검", "접속기록 검토", "이상 로그 확인", "로그 리뷰"],
    "2.9.6": ["NTP", "시간동기화", "서버 시간 불일치", "시각 설정"],
    "2.9.7": ["디스크 폐기", "장비 재사용", "데이터 완전삭제", "저장매체 폐기"],
    "2.10.1": ["보안장비 운영", "방화벽 관리", "IDS IPS", "보안시스템 정책"],
    "2.10.2": ["클라우드 설정", "AWS 보안", "클라우드 계정", "공개 스토리지"],
    "2.10.3": ["world writable", "웹서버 권한"],
    "2.10.4": ["전자결제 보안", "핀테크 보안", "거래정보 보호"],
    "2.10.5": ["파일 전송 보안", "이메일 개인정보", "정보 전송 승인", "대외 전송"],
    "2.10.6": ["화면보호기", "단말 암호화"],
    "2.10.7": ["USB 통제", "외장하드", "이동식 저장매체", "USB 반출"],
    "2.10.8": ["주기적 보안패치 적용", "윈도우 업데이트", "OS 패치", "보안 업데이트"],
    "2.10.9": ["백신", "안티바이러스", "EDR"],
    "2.11.1": ["침해사고 대응체계", "사고 연락망", "보안사고 매뉴얼", "CERT"],
    "2.11.2": ["취약점 진단", "모의해킹"],
    "2.11.3": ["이상행위 탐지", "보안 모니터링", "SIEM", "비정상 접속"],
    "2.11.4": ["침해사고 훈련", "모의훈련", "사고대응 개선"],
    "2.11.5": ["침해사고 신고", "사고 복구", "유출사고 대응", "증거 보존"],
    "2.12.1": ["재해재난", "비상대응", "BCP", "업무연속성"],
    "2.12.2": ["재해복구 훈련", "DR 테스트", "복구 목표", "재해복구 개선"],
    "3.1.1": ["개인정보 동의", "수집 이용 동의", "동의서", "개인정보 수집 근거"],
    "3.1.2": ["최소수집", "과도한 개인정보", "필수 선택 구분", "불필요 정보 수집"],
    "3.1.3": ["주민번호 수집", "주민등록번호 법적근거", "주민번호 저장"],
    "3.1.4": ["민감정보 동의", "고유식별정보", "건강정보 수집", "여권번호 처리"],
    "3.1.5": ["간접수집 출처 고지", "제3자로부터 수집", "개인정보 출처"],
    "3.1.6": ["CCTV", "영상정보처리기기", "CCTV 안내판", "영상 보관기간"],
    "3.1.7": ["마케팅 동의", "광고성 정보", "선택동의", "홍보 목적 수집"],
    "3.2.1": ["개인정보 처리현황", "개인정보 파일", "처리 시스템 목록"],
    "3.2.2": ["개인정보 정확성", "정보 최신화", "잘못된 개인정보", "데이터 품질"],
    "3.2.3": ["앱 접근권한", "모바일 권한", "연락처 접근", "단말기 권한"],
    "3.2.4": ["목적외 이용", "동의없는 제공", "개인정보 다른 용도", "목적 외 제공"],
    "3.2.5": ["가명처리", "가명정보 결합", "재식별", "가명정보 안전조치"],
    "3.3.1": ["제3자 제공 동의", "개인정보 제공", "제공받는 자", "제공 내역"],
    "3.3.2": ["개인정보 위탁", "수탁자 공개", "위탁계약", "처리업무 위탁"],
    "3.3.3": ["영업양도 개인정보", "합병 개인정보 이전", "사업 인수 통지"],
    "3.3.4": ["국외이전", "해외 서버", "해외 리전", "개인정보 해외 제공"],
    "3.4.1": ["개인정보 파기", "보유기간 경과 삭제"],
    "3.4.2": ["분리보관", "법정 보존", "목적달성 후 보관", "휴면 개인정보"],
    "3.5.1": ["개인정보 처리방침", "프라이버시 정책", "처리방침 공개 누락"],
    "3.5.2": ["개인정보 열람청구", "삭제 요구", "동의 철회", "정보주체 권리"],
    "3.5.3": ["개인정보 이용내역 통지", "유출 통지", "정보주체 고지"],
}


def _clip_phrase(text: str, *, max_len: int = 72) -> str:
    cleaned = sanitize_official_text(text)
    cleaned = _CASE_PREFIX_RE.sub("", cleaned)
    cleaned = _VENDOR_TAG_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·,;:-")
    if "관 리 체 계" in cleaned or "인증기준 설명" in cleaned:
        cleaned = re.split(r"관\s*리\s*체\s*계|인증기준 설명", cleaned, maxsplit=1)[0].strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip(" ,·(/") + "…"
    return cleaned


def _unique_phrases(values: list[str], *, limit: int = 48) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        phrase = _clip_phrase(str(raw or ""))
        if len(phrase) < 2:
            continue
        key = re.sub(r"\s+", "", phrase).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(phrase)
        if len(out) >= limit:
            break
    return out


def _alias_entries(control_id: str) -> list[dict[str, object]]:
    """Weighted user-language index entries for one control.

    Base phrases are strongest. Problem and audit-intent variants improve
    natural searches without giving generic single words the same authority.
    """
    entries: list[dict[str, object]] = []
    for alias in USER_SEARCH_ALIASES.get(control_id, []):
        entries.extend(
            [
                {"text": alias, "weight": 100, "kind": "alias"},
                {"text": f"{alias} 미흡", "weight": 84, "kind": "problem"},
                {"text": f"{alias} 점검", "weight": 76, "kind": "audit"},
            ]
        )
    return entries


def _intent_concepts(phrase: str) -> list[str]:
    """Extract stable concepts without relying on a global 101-control lexicon."""
    concepts: list[str] = []
    for raw in _INTENT_TOKEN_RE.findall(phrase.lower()):
        token = raw
        for suffix in _INTENT_SUFFIXES:
            if len(token) >= len(suffix) + 2 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        if len(token) < 2 or token in _INTENT_STOP_WORDS or token in concepts:
            continue
        concepts.append(token)
    return concepts


@lru_cache(maxsize=128)
def build_search_intents(control_id: str) -> tuple[dict[str, object], ...]:
    """Structured field-language intents used for long and compound findings.

    Every control gets the same representation.  This lets the client match a
    meaningful fragment of a pasted finding instead of requiring most words in
    the entire sentence to belong to a single control.
    """
    intents: list[dict[str, object]] = []
    for alias in USER_SEARCH_ALIASES.get(control_id, []):
        concepts = _intent_concepts(alias)
        if not concepts:
            compact = re.sub(r"\s+", "", alias).lower()
            if len(compact) >= 2:
                concepts = [compact]
        if not concepts:
            continue
        intents.append({
            "phrase": alias,
            "concepts": concepts,
            "weight": 100,
            "kind": "field-intent",
            "reason": f"현장 표현 ‘{alias}’와 관련",
        })
    return tuple(intents)


@lru_cache(maxsize=128)
def build_search_entries(control_id: str) -> tuple[dict[str, object], ...]:
    """Return deduplicated weighted entries, with official text as fallback."""
    entries = _alias_entries(control_id)
    seen = {re.sub(r"\s+", "", str(row["text"])).lower() for row in entries}
    for phrase in _official_search_phrases(control_id):
        key = re.sub(r"\s+", "", phrase).lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append({"text": phrase, "weight": 55, "kind": "official"})
        if len(entries) >= 48:
            break
    return tuple(entries)


def _official_search_phrases(control_id: str) -> list[str]:
    from .dual_layer import build_casebook_problems
    from .official_kb import load_control

    phrases: list[str] = []
    rec = load_control(control_id) or {}
    phrases.extend(str(item) for item in rec.get("checkQuestions") or [])
    phrases.extend(str(item) for item in rec.get("evidenceExamples") or [])
    phrases.extend(str(item) for item in rec.get("defectExamples") or [])
    requirement = str(rec.get("requirement") or "").strip()
    if requirement:
        phrases.append(requirement)
    for row in build_casebook_problems(control_id, limit=8):
        phrases.append(str(row.get("problem") or ""))
    return _unique_phrases(phrases, limit=32)


@lru_cache(maxsize=128)
def build_search_hints(control_id: str) -> tuple[str, ...]:
    """통제별 검색 힌트. 제목 외 현장 워딩을 포함한다."""
    return tuple(str(row["text"]) for row in build_search_entries(control_id))
