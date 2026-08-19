"""자가진단 참고 지표 — 내부 배점으로 구간만 산출하고, 화면에는 정성 표현을 쓴다."""

from __future__ import annotations

LEVEL_SCORES: dict[str, int] = {
    "unknown": 0,  # 미점검: 점검분 분모에서 제외, 전체 진행에서는 0으로 반영
    "none": 0,
    "partial": 50,
    "done": 100,
    "evidenced": 100,  # 레거시. UI는 done으로 정규화
    "na": 0,
}

# 내부 정렬·구간 산출용 (화면에는 노출하지 않음)
SCORE_WEIGHT_SUMMARY = "미이행 0 · 부분 이행 50 · 이행 100"

# (하한 inclusive, 라벨, UI tone) — 높은 구간부터 매칭
QUALITATIVE_BANDS: tuple[tuple[float, str, str], ...] = (
    (80.0, "양호", "ok"),
    (60.0, "보통", "mid"),
    (35.0, "보완 필요", "warn"),
    (0.0, "기초 보완 필요", "danger"),
)

OVERALL_SCORE_LABEL = "전체 진행 참고"
ASSESSED_SCORE_LABEL = "점검분 이행 참고"

SCORE_DISCLAIMER = (
    f"{OVERALL_SCORE_LABEL}·{ASSESSED_SCORE_LABEL}는 인증 신뢰도가 아닙니다. "
    "입력 상태를 양호·보통·보완 필요·기초 보완 필요로만 나눈 내부 참고 구간이며, "
    "공식 인증 점수나 인증 가능성이 아닙니다."
)

_BAND_HINT = " · ".join(label for _, label, _ in QUALITATIVE_BANDS)

OVERALL_SCORE_TOOLTIP = (
    f"{OVERALL_SCORE_LABEL}는 적용 통제 전체를 본 참고 구간입니다.\n"
    "· 아직 안 본 통제도 ‘미흡 쪽’으로 반영합니다\n"
    f"· 표시: {_BAND_HINT}\n"
    "· 인증 배점·신뢰도가 아닌 점검 진행 참고용입니다"
)
ASSESSED_SCORE_TOOLTIP = (
    f"{ASSESSED_SCORE_LABEL}는 이미 점검한 통제만 본 참고 구간입니다.\n"
    "· 미점검은 빼고 계산합니다\n"
    f"· 표시: {_BAND_HINT}\n"
    "· 인증 배점·신뢰도가 아닌 이행 수준 참고용입니다"
)


def qualitative_band(percent: float | None) -> tuple[str, str]:
    """내부 평균값 → (정성 라벨, tone). None이면 판단 보류."""
    if percent is None:
        return ("판단 보류", "muted")
    try:
        value = float(percent)
    except (TypeError, ValueError):
        return ("판단 보류", "muted")
    for threshold, label, tone in QUALITATIVE_BANDS:
        if value >= threshold:
            return (label, tone)
    return ("기초 보완 필요", "danger")


def qualitative_label(percent: float | None) -> str:
    return qualitative_band(percent)[0]


def qualitative_tone(percent: float | None) -> str:
    return qualitative_band(percent)[1]
