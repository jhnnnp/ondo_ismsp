from isms_pii_toolkit.official_guidance import guidance_coverage, guidance_for_control


def test_guidance_excludes_public_system_only_articles() -> None:
    coverage = guidance_coverage()
    assert coverage["controlCount"] > 0
    assert "제14조~제18조" in coverage["excludedScope"]
    for control_id in coverage["controlIds"]:
        for item in guidance_for_control(control_id):
            assert item["applicability"] == "일반 개인정보처리자"
            assert "공공시스템운영기관" not in item["section"]


def test_privacy_and_safety_guides_are_mapped_to_relevant_controls() -> None:
    third_party = guidance_for_control("3.3.1")
    assert [item["guideId"] for item in third_party] == ["pipc-privacy-processing-2025-07"]
    assert "제3자 제공" in third_party[0]["summary"]

    access = guidance_for_control("2.6.4")
    assert [item["guideId"] for item in access] == ["pipc-safety-measures-2025-11"]
    assert access[0]["section"] == "제6조 접근통제"

    destruction = guidance_for_control("3.4.1")
    assert len(destruction) == 2
    assert {item["guideId"] for item in destruction} == {
        "pipc-privacy-processing-2025-07",
        "pipc-safety-measures-2025-11",
    }
