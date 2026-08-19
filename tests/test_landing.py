from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app, create_app


client = TestClient(app)


def test_root_page_serves_ondo_landing() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ONDO°" in response.text
    assert "<title>ONDO°</title>" in response.text
    assert "ISMS-P Readiness Platform" not in response.text
    assert "ISMS-P 인증 준비" in response.text
    assert "한 화면에서" in response.text
    assert "101개 통제항목" in response.text
    assert "무료 자가진단 시작하기" in response.text
    assert "DIAGNOSE" in response.text
    assert "NAVIGATE" in response.text
    assert "OPTIMIZE" in response.text
    assert "Organizational" not in response.text
    assert "브라우저 진단 저장" not in response.text
    assert "LOCAL-FIRST" not in response.text
    assert "진단 결과 보고서" in response.text
    assert "ISMS-P 자체 점검 결과 보고서" in response.text
    assert "진단이 끝나면" in response.text
    assert "보고서 초안이 생성됩니다" in response.text
    assert "초안 생성" in response.text
    assert "내보내기" in response.text
    assert "현재 진단 50/101 기준" in response.text
    assert "2. 종합 점검 결과" in response.text
    assert "4. 미흡이 집중된 영역" in response.text
    assert "Markdown 또는 Word" in response.text
    assert "역할과 범위" not in response.text
    assert "개인정보 보호법 제29조" in response.text
    assert "2.5.1 사용자 계정 관리" in response.text
    assert 'data-product-dot="0"' in response.text
    assert "2.5.3 접근권한 정기점검" in response.text
    assert "회원가입 없이 시작" in response.text
    assert "실제 진단 화면 살펴보기" in response.text
    assert 'href="/controls/map"' in response.text
    assert "/landing/assets/landing.css" in response.text
    assert "mock-app" in response.text
    assert "data-hero-demo" in response.text
    assert 'data-temp-band="cold"' in response.text
    assert "냉랭" in response.text
    assert "16개 중 이행 13" in response.text
    assert "보호대책 선정" in response.text
    assert "본 서비스의 결과는 사용자가 입력한 답변을 기반으로 한 자체 점검 결과이며" in response.text
    assert "이행 현황 집계에서 끝내지 않습니다" in response.text
    assert "점검 결과에는 수치와" in response.text
    assert "보고서 문맥만 교정합니다" in response.text
    assert "경영진의 정보보호 관리체계 참여 및 의사결정 여부" in response.text
    assert "계정 발급·변경·삭제 절차 수립 및 승인 기록 보존 여부" in response.text
    assert "미확인" in response.text
    assert "점수를 만드는" not in response.text
    assert "숫자로만" not in response.text
    assert "아직 모름" not in response.text
    assert "참여하고 있나요" not in response.text
    assert "관찰 메모" not in response.text
    assert "합격" not in response.text
    assert "인증 가능" not in response.text


def test_landing_assets_are_served() -> None:
    css = client.get("/landing/assets/landing.css")
    js = client.get("/landing/assets/landing.js")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "--color-accent: #168f74" in css.text
    assert "--space-9: 96px" in css.text
    assert "scroll-behavior: smooth" in css.text
    assert "text-rendering: optimizeLegibility" in css.text
    assert "prefers-reduced-motion: reduce" in css.text
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
    assert "data-nav-toggle" in js.text
    assert "IntersectionObserver" in js.text
    assert "data-hero-demo" in js.text
    assert "temperatureBand" in js.text
    assert "data-temp-band" in css.text
    assert "data-product-demo" in js.text
    assert "data-product-dot" in js.text
    assert ".mock-app" in css.text


def test_landing_asset_rejects_unknown_or_unsafe_paths() -> None:
    from isms_pii_toolkit.api import _load_landing_asset

    assert client.get("/landing/assets/missing.css").status_code == 404
    assert client.get("/landing/assets/landing.txt").status_code == 404
    try:
        _load_landing_asset("../control_map/control_map.css")
        raise AssertionError("traversal path should be rejected")
    except FileNotFoundError:
        pass


def test_control_map_remains_at_dedicated_path() -> None:
    response = client.get("/controls/map")
    assert response.status_code == 200
    assert "진단을 선택하세요" in response.text


def test_landing_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("PII_TOOLKIT_ENABLE_DEMO", "0")
    disabled = TestClient(create_app())
    assert disabled.get("/").status_code == 404
    assert disabled.get("/landing/assets/landing.css").status_code == 404
