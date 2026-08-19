"""조직 입력을 진단 엔진이 사용할 수 있는 결정론적 컨텍스트로 정규화한다.

현재 control_map UI는 usesCloud / hasOnPremFacility만 받는다.
headcount·industry·pii·outsourcing·remote·rrn은 dormant 기본값이며
사용자 맞춤 입력이 아니다. 우선순위/시나리오 내부 힌트에만 쓰인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

HEADCOUNT_BANDS = frozenset({"1-50", "51-300", "301+"})
INDUSTRIES = frozenset({"general", "retail", "healthcare", "public", "finance", "technology"})
PII_VOLUMES = frozenset({"low", "medium", "high"})

HEADCOUNT_LABELS = {
    "1-50": "1~50인(초기/소규모)",
    "51-300": "51~300인(성장/중견)",
    "301+": "301인 이상(대규모 조직)",
}

INDUSTRY_LABELS = {
    "general": "일반",
    "retail": "유통/리테일",
    "healthcare": "의료",
    "public": "공공",
    "finance": "금융",
    "technology": "IT/SaaS",
}

# 법적 임계값이 아니라 자체진단용 대략 기준(정보주체/처리 규모 감각).
PII_VOLUME_GUIDE = {
    "low": {
        "label": "소규모",
        "short": "정보주체 약 1만 명 미만",
        "detail": "직원/소규모 회원/내부 업무 위주. 배치/대고객 연계가 거의 없음",
    },
    "medium": {
        "label": "중규모",
        "short": "정보주체 약 1만~100만 명",
        "detail": "일반 B2C/회원제/예약/상담 등 정기 수집/이용. DB/로그/백업 관리 필요",
    },
    "high": {
        "label": "대규모",
        "short": "정보주체 약 100만 명 이상 또는 상시 대량",
        "detail": "플랫폼/금융/통신급 상시 수집/연계/배치. 암호화/접근통제/현황관리 부담 큼",
    },
}


def pii_volume_label(volume: str, *, with_short: bool = True) -> str:
    guide = PII_VOLUME_GUIDE.get(volume)
    if not guide:
        return volume
    if with_short:
        return f"{guide['label']} ({guide['short']})"
    return str(guide["label"])


@dataclass(frozen=True)
class OrganizationContext:
    headcount_band: str
    industry: str
    pii_volume: str
    uses_cloud: bool = False
    uses_outsourcing: bool = False
    uses_remote_access: bool = False
    processes_rrn: bool = False
    has_on_prem_facility: bool = False

    @property
    def tags(self) -> frozenset[str]:
        tags = {
            f"size:{self.headcount_band}",
            f"industry:{self.industry}",
            f"pii:{self.pii_volume}",
        }
        if self.uses_cloud:
            tags.add("cloud")
        if self.uses_outsourcing:
            tags.add("outsourcing")
        if self.uses_remote_access:
            tags.add("remote-access")
        if self.processes_rrn:
            tags.add("rrn")
        if self.has_on_prem_facility:
            tags.add("on-prem-facility")
        elif self.uses_cloud:
            tags.add("cloud-only-no-dc")
        return frozenset(tags)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "headcountBand": self.headcount_band,
            "industry": self.industry,
            "piiVolume": self.pii_volume,
            "usesCloud": self.uses_cloud,
            "usesOutsourcing": self.uses_outsourcing,
            "usesRemoteAccess": self.uses_remote_access,
            "processesRrn": self.processes_rrn,
            "hasOnPremFacility": self.has_on_prem_facility,
            "tags": sorted(self.tags),
        }


def normalize_organization_profile(profile: Mapping[str, object] | None) -> OrganizationContext | None:
    if profile is None:
        return None

    headcount = str(profile.get("headcountBand", profile.get("headcount_band", "1-50")))
    industry = str(profile.get("industry", "general"))
    pii_volume = str(profile.get("piiVolume", profile.get("pii_volume", "low")))
    if headcount not in HEADCOUNT_BANDS:
        raise ValueError(f"Unsupported headcount band: {headcount}")
    if industry not in INDUSTRIES:
        raise ValueError(f"Unsupported industry: {industry}")
    if pii_volume not in PII_VOLUMES:
        raise ValueError(f"Unsupported PII volume: {pii_volume}")

    def flag(camel: str, snake: str) -> bool:
        return bool(profile.get(camel, profile.get(snake, False)))

    return OrganizationContext(
        headcount_band=headcount,
        industry=industry,
        pii_volume=pii_volume,
        uses_cloud=flag("usesCloud", "uses_cloud"),
        uses_outsourcing=flag("usesOutsourcing", "uses_outsourcing"),
        uses_remote_access=flag("usesRemoteAccess", "uses_remote_access"),
        processes_rrn=flag("processesRrn", "processes_rrn"),
        has_on_prem_facility=flag("hasOnPremFacility", "has_on_prem_facility"),
    )
