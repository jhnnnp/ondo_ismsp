from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "isms_pii_toolkit" / "web" / "control_map"
client = TestClient(app)


def test_control_map_html_has_required_modular_ui_contract() -> None:
    response = client.get("/controls/map")

    assert response.status_code == 200
    assert 'id="profileForm"' in response.text
    assert 'id="sessionPicker"' in response.text
    assert 'id="diagnosisSessionList"' in response.text
    assert 'id="diagnosisSessionPager"' in response.text
    assert 'id="createDiagnosisSessionBtn"' in response.text
    assert 'id="manageSessionsBtn"' in response.text
    assert 'id="assessList"' in response.text
    assert 'id="analyzeHero"' in response.text
    assert 'id="reportReviewQueue"' not in response.text
    assert 'id="executiveReportStream"' in response.text
    assert 'id="reportEditorReactRoot"' in response.text
    assert 'class="report-editor-bridge"' in response.text
    assert '/controls/map/assets/react-dist/report-editor.js' in response.text
    assert "진단 결과 보고서" in response.text
    assert "AI로 초안 작성" in response.text
    assert 'id="reportComposeOverlay"' in response.text
    assert 'id="reportReturnBar"' in response.text
    assert 'id="linkedProblemsPanel"' in response.text
    assert 'id="linkedProblemsSummary"' in response.text
    assert 'id="categoryCoverageList"' in response.text
    assert 'id="categoryCoverageSummary"' in response.text
    assert 'id="categoryViewActions"' in response.text
    assert 'id="categoryListCount"' in response.text
    assert 'data-category-view="expand"' in response.text
    assert 'data-category-view="collapse"' in response.text
    assert 'class="analysis-deep-dive"' not in response.text
    assert "추가 상세 보기" not in response.text
    assert "legacy-analysis-detail" not in response.text
    assert 'id="areaHeatmap"' not in response.text
    assert "점검 진행 현황" in response.text
    assert "중분류별 미흡 통제" in response.text
    assert "미점검 통제는 제외되며" in response.text
    assert "우선 보완 통제에서 바로 점검" in response.text
    assert 'id="weakCategories"' not in response.text
    assert "연계 문제" in response.text
    assert 'id="returnToReportBtn"' in response.text
    assert "우선 통제 목록을 준비하고 있습니다" in response.text
    assert 'id="reRunAnalyzeBtn"' in response.text
    assert 'id="sessionBundleBar"' in response.text
    assert 'data-bundle-mode="chain"' in response.text
    assert 'data-bundle-mode="area"' in response.text
    assert 'data-bundle-mode="theme"' in response.text
    assert 'id="certPanel"' in response.text
    assert "/controls/map/assets/app.js" in response.text
    assert 'href="/controls/map/assets/control_map.css"' in response.text
    assert 'id="questPanel"' not in response.text


@pytest.mark.parametrize(
    ("asset_path", "content_type", "expected"),
    [
        ("control_map.css", "text/css", '@import url("./styles/tokens.css")'),
        ("styles/tokens.css", "text/css", ":root"),
        ("styles/layout.css", "text/css", "body"),
        ("styles/sessions.css", "text/css", ".diagnosis-launcher"),
        ("styles/profile.css", "text/css", ".profile-inline"),
        ("styles/assessment.css", "text/css", ".assess-shell"),
        ("styles/analysis.css", "text/css", ".session-bundle-chip"),
        ("styles/certification.css", "text/css", ".cert-phase-card.is-visible"),
        ("app.js", "text/javascript", 'import { bootstrap } from "./core/router.js"'),
        ("core/router.js", "text/javascript", "export async function bootstrap"),
        ("core/routes.js", "text/javascript", "export function navigateTo"),
        (
            "core/session-model.js",
            "text/javascript",
            "export function normalizeDiagnosisSessionName",
        ),
        (
            "features/assessment/actions.js",
            "text/javascript",
            "export function applyChecksToControl",
        ),
        (
            "features/assessment/controller.js",
            "text/javascript",
            "export function renderAssessList",
        ),
        (
            "features/analysis/report-review.js",
            "text/javascript",
            "export function buildReportReviewItems",
        ),
        (
            "features/sessions/view.js",
            "text/javascript",
            "export function renderDiagnosisSessionPicker",
        ),
    ],
)
def test_control_map_modular_assets_are_served(
    asset_path: str,
    content_type: str,
    expected: str,
) -> None:
    response = client.get(f"/controls/map/assets/{asset_path}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert expected in response.text


def test_assessment_ui_loads_legal_basis_from_internal_api_only() -> None:
    view = client.get("/controls/map/assets/features/assessment/view.js")
    controller = client.get("/controls/map/assets/features/assessment/controller.js")

    assert view.status_code == 200
    assert "법적 근거 및 참고자료" in view.text
    assert "officialLawUrl" in view.text
    assert controller.status_code == 200
    assert "/legal-basis" in controller.text
    assert 'data-open-law-article' in view.text
    assert "개인정보위·KISA의 공식 학습·참고 사례" in view.text
    assert "casebookExamples" in view.text
    assert "관련 공식 안내서" in view.text
    assert "officialGuidance" in view.text
    assert "공식 참고자료" in view.text
    assert 'class="legal-resource-disclosure-body legal-reference-list"' in view.text
    assert 'class="legal-interpretation-card legal-casebook-card official-guidance-card"' in view.text
    assert "일반 개인정보처리자용 실무 해설" in view.text
    assert "legal-resource-counts" in view.text
    assert "legal-resource-disclosure" in view.text
    assert 'class="legal-article-detail"' not in view.text
    assert 'dialog.id = "lawArticleDialog"' in controller.text
    assert "dialog.showModal()" in controller.text
    assert "data-law-dialog-close" in controller.text
    assert "apis.data.go.kr" not in view.text + controller.text
    assert "serviceKey" not in view.text + controller.text


def test_removed_and_unsupported_assets_return_404() -> None:
    assert client.get(
        "/controls/map/assets/features/session/quest-view.js"
    ).status_code == 404
    assert client.get("/controls/map/assets/styles/missing.css").status_code == 404
    assert client.get("/controls/map/assets/styles/tokens.txt").status_code == 404


def test_refresh_does_not_auto_analyze_but_analyze_view_shows_results() -> None:
    router = (WEB_ROOT / "core" / "router.js").read_text(encoding="utf-8")
    assessment = (
        WEB_ROOT / "features" / "assessment" / "controller.js"
    ).read_text(encoding="utf-8")
    html = client.get("/controls/map").text

    bootstrap = router.split("export async function bootstrap()", maxsplit=1)[1]
    assert "await runAnalysis(false" not in bootstrap
    assert "ensureAnalyzeResults()" in router
    assert "skipAutoAnalyze" in router
    assert "hooks.runAnalysis(false" not in assessment
    assert "hooks.markAnalysisStale?.()" in assessment
    assert "확인 목록을 만들 준비가 됐습니다" not in html
    assert "확인 목록을 만들 준비가 됐습니다" not in router


def test_report_review_control_navigation_has_a_return_path() -> None:
    router = (WEB_ROOT / "core" / "router.js").read_text(encoding="utf-8")
    assessment = (
        WEB_ROOT / "features" / "assessment" / "controller.js"
    ).read_text(encoding="utf-8")
    review = (
        WEB_ROOT / "features" / "analysis" / "report-review.js"
    ).read_text(encoding="utf-8")

    assert "state.reportReturn =" in review
    assert "renderReportReturnBar();" in assessment
    assert "function returnToReportReview()" in router
    assert 'el("returnToReportBtn")?.addEventListener("click", returnToReportReview)' in router


def test_analysis_navigation_uses_sidebar_without_duplicate_detail_page() -> None:
    html = client.get("/controls/map").text
    presentation = (
        WEB_ROOT / "features" / "analysis" / "presentation.js"
    ).read_text(encoding="utf-8")

    assert 'class="analyze-section-nav"' not in html
    assert 'data-analyze-sec="detail"' not in html
    assert 'data-analyze-panel="detail"' not in html
    assert 'class="analysis-deep-dive"' not in html
    assert "추가 상세 보기" not in html
    assert 'problems: "overview"' in presentation
    assert '["actions", "overview"].includes(next)' in presentation
    assert 'event.target.closest("[data-scroll-target]")' in presentation
    assert 'switchAnalyzeDetailTab(tabsByPanel[detailTab.dataset.scrollTarget]' in presentation


def test_dashboard_exposes_priority_insights_and_binds_all_review_buttons() -> None:
    html = client.get("/controls/map").text
    session_view = (
        WEB_ROOT / "features" / "session" / "view.js"
    ).read_text(encoding="utf-8")

    assert 'id="dashboardInsights"' in html
    assert 'id="dashboardPriorityList"' in html
    assert 'id="dashboardSignalGrid"' in html
    assert 'id="dashboardCategoryList"' in html
    assert 'id="dashboardAreaTemps"' in html
    assert 'id="dashboardQueueTitle"' in html
    assert 'data-dashboard-review-all' in html
    assert 'querySelectorAll("[data-progress-weak]")' in session_view
    assert 'href="/controls/map/dashboard"' in html
    assert 'href="/controls/map/scope"' in html
    assert 'href="/controls/map/assessment"' in html
    assert 'href="/controls/map/results"' in html
    assert 'href="/controls/map/evidence"' in html
    assert 'href="/controls/map/report"' in html
    assert 'data-route="dashboard"' in html
    assert 'navigateTo("assessment")' in session_view
    assert 'dashboardPriorityList.querySelectorAll("[data-dashboard-control]")' in session_view
    assert 'dashboardAreaTemps.querySelectorAll("[data-dashboard-area-control]")' in session_view


def test_analysis_overview_uses_one_bounded_scroll_region() -> None:
    styles = (WEB_ROOT / "styles" / "analysis.css").read_text(encoding="utf-8")
    layout = (WEB_ROOT / "styles" / "layout.css").read_text(encoding="utf-8")

    assert "height: clamp(430px, 58vh, 620px)" in styles
    assert "height: 100%" in styles
    assert "flex: 1 1 auto" in styles
    assert "overflow-y: auto" in styles
    assert ".category-coverage-list" in styles
    assert "overscroll-behavior: contain" in styles
    assert ".coverage-overview-strip" in layout
    assert ".category-area-progress" in layout
    assert ".category-summary-progress" in layout
    assert "flex-direction: column" in layout
    assert "flex: 0 0 auto" in layout


def test_analysis_loading_reports_real_work_without_staged_ai_progress() -> None:
    router = (WEB_ROOT / "core" / "router.js").read_text(encoding="utf-8")
    controller = (
        WEB_ROOT / "features" / "analysis" / "controller.js"
    ).read_text(encoding="utf-8")
    presentation = (
        WEB_ROOT / "features" / "analysis" / "presentation.js"
    ).read_text(encoding="utf-8")
    html = client.get("/controls/map").text

    assert 'loadingMode: "priority"' in router
    assert "우선 진단 항목을 준비하고 있습니다" in presentation
    assert "확인 목록을 만들고 있습니다" in presentation
    assert "규칙 엔진이 현재 저장된 진단 데이터를 처리하고 있습니다." in presentation
    assert "ANALYSIS_STEPS" not in controller
    assert "await sleep(420)" not in controller
    assert 'id="verbalizeToggle"' not in html
    assert "AI 리포트" not in html
    assert 'id="writeAiReportBtn"' in html
    assert "AI로 초안 작성" in html
    assert 'id="reportComposeOverlay"' in html
    assert 'data-write-ai-report' in html
    assert "AI는 진단 수치와 판정을 변경하지 않습니다" in html
    assert "AI로 재작성" in presentation
    assert "AI로 다시 작성" in presentation
    assert 'fetchJson("/controls/report"' in controller
    assert "export function executeAiReport" in controller
    assert 'fetchJson("/controls/verbalize"' not in controller
    assert "export function cancelActiveAnalysis" in controller
    assert "cancelActiveAnalysis()" in router
    assert "wantAiReport" not in controller
    assert 'loadingMode || "priority"' in controller


@pytest.mark.parametrize(
    "page",
    ["dashboard", "scope", "assessment", "results", "evidence", "report", "sessions"],
)
def test_control_map_workspace_pages_serve_the_same_app_shell(page: str) -> None:
    response = client.get(f"/controls/map/{page}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="sessionPicker"' in response.text
    assert 'href="/controls/map/dashboard"' in response.text
    assert 'data-route="assessment"' in response.text


def test_unknown_control_map_page_returns_404() -> None:
    assert client.get("/controls/map/not-a-page").status_code == 404


def test_workspace_navigation_uses_history_api() -> None:
    router = (WEB_ROOT / "core" / "router.js").read_text(encoding="utf-8")
    routes = (WEB_ROOT / "core" / "routes.js").read_text(encoding="utf-8")

    assert 'path: `${APP_BASE}/dashboard`' in routes
    assert 'id: "assessment"' in routes
    assert "window.history[method]" in router
    assert 'window.addEventListener("popstate"' in router
    assert "export function navigateTo" in routes


def test_all_control_map_javascript_has_valid_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for frontend syntax validation.")

    scripts = sorted(WEB_ROOT.rglob("*.js"))
    assert scripts
    for script in scripts:
        subprocess.run(
            [node, "--check", str(script)],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )


def test_destructive_actions_use_project_confirmation_dialog() -> None:
    scripts = "\n".join(path.read_text(encoding="utf-8") for path in WEB_ROOT.rglob("*.js"))
    layout = (WEB_ROOT / "styles" / "layout.css").read_text(encoding="utf-8")

    assert "window.confirm(" not in scripts
    assert "window.alert(" not in scripts
    assert "window.prompt(" not in scripts
    assert "export function confirmAction" in scripts
    assert 'tone: "danger"' in scripts
    assert ".app-confirm-dialog" in layout
