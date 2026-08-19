from __future__ import annotations

from typing import Any


PRIVACY_GUIDE = {
    "guideId": "pipc-privacy-processing-2025-07",
    "title": "개인정보 처리 통합 안내서",
    "publisher": "개인정보보호위원회",
    "publishedAt": "2025-07",
    "sourceDocument": "개인정보_처리_통합_안내서_2025-07.pdf",
}

SAFETY_GUIDE = {
    "guideId": "pipc-safety-measures-2025-11",
    "title": "개인정보의 안전성 확보조치 기준 안내서",
    "publisher": "개인정보보호위원회",
    "publishedAt": "2025-11",
    "sourceDocument": "개인정보의_안전성_확보조치_기준_안내서_2025-11.pdf",
}


def _item(
    guide: dict[str, str],
    section: str,
    pages: list[int],
    summary: str,
    checkpoints: list[str],
) -> dict[str, Any]:
    return {
        **guide,
        "section": section,
        "pages": pages,
        "summary": summary,
        "checkpoints": checkpoints,
        "applicability": "일반 개인정보처리자",
    }


_SAFETY_SECTIONS = {
    "plan": _item(
        SAFETY_GUIDE,
        "제4조 내부 관리계획의 수립·시행 및 점검",
        [35, 57],
        "개인정보 처리 규모와 위험을 반영한 내부 관리계획을 수립하고, 시행 여부를 정기적으로 점검·개선해야 합니다.",
        ["내부 관리계획의 승인·개정 이력이 있는지 확인", "연 1회 이상 이행 실태를 점검하고 개선 결과를 남겼는지 확인"],
    ),
    "rights": _item(
        SAFETY_GUIDE,
        "제5조 접근 권한의 관리",
        [58, 64],
        "개인정보처리시스템 접근 권한은 업무상 필요한 범위로 차등 부여하고 부여·변경·말소 내역을 관리해야 합니다.",
        ["인사변경 시 권한을 지체 없이 변경·말소하는지 확인", "권한 이력과 인증수단 적용 기록을 보관하는지 확인"],
    ),
    "access": _item(
        SAFETY_GUIDE,
        "제6조 접근통제",
        [65, 80],
        "개인정보처리시스템에 대한 불법 접근과 침해사고를 예방하도록 접속 경로와 단말, 네트워크 접근을 통제해야 합니다.",
        ["접속 권한과 경로를 제한하고 차단 정책을 운영하는지 확인", "외부·원격 접속 시 안전한 인증과 보호조치를 적용하는지 확인"],
    ),
    "crypto": _item(
        SAFETY_GUIDE,
        "제7조 개인정보의 암호화",
        [81, 90],
        "인증정보와 고유식별정보 등 보호대상 개인정보는 저장·전송 구간의 위험에 맞는 방식으로 암호화해야 합니다.",
        ["비밀번호를 안전한 일방향 방식으로 저장하는지 확인", "암호키의 생성·보관·사용·폐기 절차를 분리하여 관리하는지 확인"],
    ),
    "logs": _item(
        SAFETY_GUIDE,
        "제8조 접속기록의 보관 및 점검",
        [91, 95],
        "개인정보 처리 내역을 확인할 수 있는 접속기록을 보관하고 위·변조 방지와 정기 점검 조치를 적용해야 합니다.",
        ["접속자·일시·처리내역 등 필요한 항목이 기록되는지 확인", "접속기록 점검 결과와 이상 징후 조치 내역을 남기는지 확인"],
    ),
    "malware": _item(
        SAFETY_GUIDE,
        "제9조 악성프로그램 등 방지",
        [96, 99],
        "개인정보 처리에 이용되는 시스템과 단말에 악성프로그램 예방·탐지·치료 기능을 운영하고 최신 상태를 유지해야 합니다.",
        ["보안 프로그램의 자동 갱신과 실시간 검사를 적용하는지 확인", "탐지·치료·예외처리 내역을 확인할 수 있는지 점검"],
    ),
    "physical": _item(
        SAFETY_GUIDE,
        "제10조 물리적 안전조치",
        [100, 102],
        "개인정보가 보관된 장소와 매체에 출입통제, 보관시설 또는 잠금장치 등 물리적 보호조치를 적용해야 합니다.",
        ["보관 장소의 출입 권한과 출입기록을 관리하는지 확인", "서류·매체를 잠금 가능한 설비에 보관하는지 확인"],
    ),
    "disaster": _item(
        SAFETY_GUIDE,
        "제11조 재해·재난 대비 안전조치",
        [103, 105],
        "재해·재난 발생 시 개인정보처리시스템을 보호하고 가용성을 회복할 수 있는 대응 절차와 보호조치를 마련해야 합니다.",
        ["위기 대응 및 복구 절차와 책임자를 정했는지 확인", "백업자료의 안전한 보관과 복구 가능성을 점검하는지 확인"],
    ),
    "print": _item(
        SAFETY_GUIDE,
        "제12조 출력·복사시 안전조치",
        [106, 107],
        "개인정보 출력·복사 시 목적과 필요 범위를 확인하고 출력물과 복사본의 유출·오남용을 방지해야 합니다.",
        ["출력·복사 권한과 용도를 제한하는지 확인", "출력물의 보관·반출·파기 절차를 운영하는지 확인"],
    ),
    "destroy": _item(
        SAFETY_GUIDE,
        "제13조 개인정보의 파기",
        [108, 111],
        "파기 사유가 발생한 개인정보는 매체 특성에 맞는 복구 불가능한 방법으로 안전하게 파기하고 기록을 관리해야 합니다.",
        ["전자파일과 종이·매체별 파기 방법을 정했는지 확인", "파기 대상·일시·방법·담당자 기록을 관리하는지 확인"],
    ),
}

_PRIVACY_SECTIONS = {
    "collect": _item(
        PRIVACY_GUIDE,
        "개인정보의 수집·이용 및 동의",
        [22, 60, 113, 132],
        "개인정보 수집·이용은 동의 또는 법률상 근거를 구분하고, 동의를 받을 때 필수 고지사항을 명확히 제시해야 합니다.",
        ["처리 목적별 법적 근거를 식별했는지 확인", "동의사항을 다른 내용과 구분하여 알기 쉽게 고지하는지 확인"],
    ),
    "minimum": _item(
        PRIVACY_GUIDE,
        "개인정보의 수집 제한",
        [61, 65],
        "처리 목적 달성에 필요한 최소한의 개인정보만 수집하고, 최소정보 외 수집에 동의하지 않았다는 이유로 서비스를 거부해서는 안 됩니다.",
        ["수집 항목별 필요성을 설명할 수 있는지 확인", "선택정보 미동의자에게 불이익을 주지 않는지 확인"],
    ),
    "special": _item(
        PRIVACY_GUIDE,
        "민감정보·고유식별정보·주민등록번호의 처리 제한",
        [140, 160],
        "민감정보와 고유식별정보는 별도 동의 또는 구체적인 법적 근거를 확인하고, 주민등록번호는 법령상 허용 범위에서만 처리해야 합니다.",
        ["일반 개인정보 동의와 별도로 처리 근거를 확인하는지 점검", "주민등록번호 처리의 구체적인 법령 근거를 기록했는지 확인"],
    ),
    "provide": _item(
        PRIVACY_GUIDE,
        "개인정보의 제공 및 목적 외 이용·제공 제한",
        [66, 102],
        "제3자 제공 여부와 처리 목적을 구분하고, 제공받는 자·목적·항목·보유기간 등 필요한 사항을 고지해야 합니다.",
        ["위탁과 제3자 제공을 실질에 따라 구분했는지 확인", "목적 외 이용·제공 시 별도 근거와 기록을 관리하는지 확인"],
    ),
    "outsource": _item(
        PRIVACY_GUIDE,
        "업무위탁에 따른 개인정보의 처리 제한",
        [161, 186],
        "개인정보 처리업무를 위탁할 때 문서에 필수 보호사항을 반영하고 수탁자의 처리 현황을 관리·감독해야 합니다.",
        ["위탁 목적·범위·재위탁·파기·감독 사항을 계약에 반영했는지 확인", "수탁자 교육·점검 및 종료 후 반환·파기를 확인했는지 점검"],
    ),
    "transfer": _item(
        PRIVACY_GUIDE,
        "영업양도 등에 따른 개인정보의 이전 제한",
        [187, 194],
        "영업양도·합병 등으로 개인정보가 이전되는 경우 이전 사실과 정보주체가 알아야 할 사항을 적법한 방법으로 통지해야 합니다.",
        ["이전받는 자와 연락처, 이전 목적·방법을 통지하는지 확인", "양도자와 양수자의 처리 범위 및 파기 책임을 확인"],
    ),
    "destroy": _item(
        PRIVACY_GUIDE,
        "개인정보의 파기",
        [103, 112],
        "보유기간 경과 또는 처리 목적 달성 등 파기 사유가 발생하면 지체 없이 개인정보를 파기해야 합니다.",
        ["보유기간과 파기 트리거를 개인정보별로 관리하는지 확인", "다른 법령에 따른 보존정보는 분리하여 관리하는지 확인"],
    ),
}


_CONTROL_SECTION_KEYS: dict[str, list[tuple[str, str]]] = {
    "1.1.2": [("safety", "plan")], "1.1.3": [("safety", "plan")],
    "1.1.5": [("safety", "plan")], "1.2.3": [("safety", "plan")],
    "1.2.4": [("safety", "plan")], "1.3.1": [("safety", "plan")],
    "1.3.3": [("safety", "plan")], "1.4.1": [("safety", "plan")],
    "1.4.2": [("safety", "plan")], "1.4.3": [("safety", "plan")],
    "2.1.1": [("safety", "plan")], "2.1.2": [("safety", "plan")],
    "2.2.1": [("safety", "rights")], "2.2.4": [("safety", "plan")],
    "2.2.5": [("safety", "rights")],
    "2.3.2": [("privacy", "outsource")], "2.3.3": [("privacy", "outsource")],
    "2.3.4": [("privacy", "outsource")],
    "2.4.1": [("safety", "physical")], "2.4.2": [("safety", "physical")],
    "2.4.3": [("safety", "physical")], "2.4.5": [("safety", "physical")],
    "2.4.6": [("safety", "physical")], "2.4.7": [("safety", "physical")],
    "2.5.1": [("safety", "rights")], "2.5.2": [("safety", "rights")],
    "2.5.3": [("safety", "rights")], "2.5.4": [("safety", "rights")],
    "2.5.5": [("safety", "rights")], "2.5.6": [("safety", "rights")],
    "2.6.1": [("safety", "access")], "2.6.2": [("safety", "access")],
    "2.6.3": [("safety", "access")], "2.6.4": [("safety", "access")],
    "2.6.5": [("safety", "access")], "2.6.6": [("safety", "access")],
    "2.6.7": [("safety", "access")],
    "2.7.1": [("safety", "crypto")], "2.7.2": [("safety", "crypto")],
    "2.8.4": [("safety", "access")],
    "2.9.4": [("safety", "logs")], "2.9.5": [("safety", "logs")],
    "2.9.7": [("safety", "destroy")],
    "2.10.5": [("safety", "crypto")], "2.10.6": [("safety", "malware")],
    "2.10.7": [("safety", "physical")], "2.10.9": [("safety", "malware")],
    "2.11.3": [("safety", "logs")],
    "2.12.1": [("safety", "disaster")], "2.12.2": [("safety", "disaster")],
    "3.1.1": [("privacy", "collect")], "3.1.2": [("privacy", "minimum")],
    "3.1.3": [("privacy", "special")], "3.1.4": [("privacy", "special")],
    "3.1.7": [("privacy", "collect")],
    "3.2.4": [("privacy", "provide")],
    "3.3.1": [("privacy", "provide")],
    "3.3.2": [("privacy", "outsource"), ("safety", "plan")],
    "3.3.3": [("privacy", "transfer")],
    "3.4.1": [("privacy", "destroy"), ("safety", "destroy")],
    "3.4.2": [("privacy", "destroy")],
}


def guidance_for_control(control_id: str) -> list[dict[str, Any]]:
    """Return only guidance applicable to ordinary private-sector processors.

    Public-system-only articles 14 through 18 are deliberately absent from the
    source registry, so they cannot leak into ordinary ISMS-P control results.
    """
    registries = {"privacy": _PRIVACY_SECTIONS, "safety": _SAFETY_SECTIONS}
    return [dict(registries[source][section]) for source, section in _CONTROL_SECTION_KEYS.get(control_id, [])]


def guidance_coverage() -> dict[str, Any]:
    return {
        "controlCount": len(_CONTROL_SECTION_KEYS),
        "controlIds": sorted(_CONTROL_SECTION_KEYS),
        "excludedScope": "공공시스템운영기관 추가조치(제14조~제18조)",
    }
