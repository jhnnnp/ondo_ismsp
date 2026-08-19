"""official_kb 문구 sanitize / 세부문항 품질 회귀."""

from __future__ import annotations

from isms_pii_toolkit.control_graph import list_controls
from isms_pii_toolkit.dual_layer import build_official_checks
from isms_pii_toolkit.official_kb import load_control, official_check_statements, official_evidence_examples
from isms_pii_toolkit.official_text import (
    is_usable_evidence,
    merge_check_questions,
    sanitize_official_text,
)
from isms_pii_toolkit.quest_kb import build_control_session_details


def test_sanitize_replaces_ocr_and_page_footer() -> None:
    text = sanitize_official_text(
        "침해사고대응지침■절차 182 정보보호 및 개인정보보호 관리체계 인증제도 안내서"
    )
    assert "■" not in text
    assert "·" in text or "절차" in text
    assert "인증제도 안내서" not in text


def test_merge_recovers_laws_as_check_questions() -> None:
    merged = merge_check_questions(
        ["연간 교육 계획을 수립하고 경영진의 승인을 받고 있는가?"],
        [
            "및 규정의 중대한 변경 시 이에 대한 추가교육을 수행하고 있는가?",
            "개인정보 보호법 제28조(개인정보 취급자에 대한 감독)",
        ],
    )
    assert len(merged) >= 2
    assert any("중대한 변경" in q for q in merged)
    assert all("개인정보 보호법" not in q for q in merged)


def test_reject_placeholder_evidence() -> None:
    assert not is_usable_evidence("1 예시")
    assert is_usable_evidence("교육결과보고서")


def test_224_has_full_check_questions() -> None:
    load_control.cache_clear()
    stmts = official_check_statements("2.2.4")
    assert len(stmts) >= 4
    assert any("추가교육" in s for s in stmts)


def test_session_details_have_no_ocr_or_placeholder() -> None:
    load_control.cache_clear()
    catalog = build_control_session_details(list_controls())
    assert len(catalog) == 101
    for cid, entry in catalog.items():
        details = entry.get("detailChecks") or []
        assert details, cid
        content = [d for d in details if d.get("checkId") != "evidence"]
        assert content, cid
        for row in details:
            text = str(row.get("question") or row.get("label") or "")
            assert "■" not in text, f"{cid}: {text}"
            assert "1 예시" not in text, f"{cid}: {text}"
            if row.get("checkId") == "evidence":
                assert text.startswith("준비할 증적"), f"{cid}: {text}"


def test_build_official_checks_evidence_label() -> None:
    load_control.cache_clear()
    rows = build_official_checks("2.11.1")
    evidence = next(r for r in rows if r["checkId"] == "evidence")
    assert str(evidence["label"]).startswith("준비할 증적 예시:")
    assert "■" not in str(evidence["label"])
    assert official_evidence_examples("2.5.3")
