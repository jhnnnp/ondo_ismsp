from __future__ import annotations

from fastapi.testclient import TestClient

from isms_pii_toolkit.api import app
from isms_pii_toolkit.control_graph import list_controls

client = TestClient(app)


def test_control_catalog_contains_2024_isms_p_101_controls() -> None:
    controls = list_controls()

    assert len(controls) == 101
    assert controls[0]["id"] == "1.1.1"
    assert controls[0]["title"] == "경영진의 참여"
    assert controls[-1]["id"] == "3.5.3"
    assert controls[-1]["title"] == "정보주체에 대한 통지"


def test_controls_endpoint_returns_full_catalog_and_filters() -> None:
    response = client.get("/controls")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 101

    filtered = client.get("/controls", params={"category": "2.7"}).json()
    assert filtered["total"] == 2
    assert [control["id"] for control in filtered["controls"]] == ["2.7.1", "2.7.2"]


def test_control_detail_keeps_encryption_as_study_mapping() -> None:
    response = client.get("/controls/2.7.1")
    payload = response.json()

    assert response.status_code == 200
    assert payload["title"] == "암호정책 적용"
    assert payload["categoryName"] == "암호화 적용"
    assert payload["implementationStatus"] == "study_mapped"
    assert "pii-detection-redaction" not in payload["evidenceIds"]
    assert "2.7.2" in payload["relatedControlIds"]


def test_evidences_endpoint_links_artifacts_to_controls() -> None:
    response = client.get("/controls/evidences")
    evidences = response.json()["evidences"]

    assert response.status_code == 200
    ci_evidence = next(item for item in evidences if item["id"] == "test-coverage-ci")
    assert "pyproject.toml" in ci_evidence["artifactRefs"]
    assert "1.3.1" in ci_evidence["controlIds"]


def test_retail_scenario_graph_returns_connected_controls() -> None:
    response = client.get("/controls/graph", params={"scenario": "retail-cs-log-pii"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["scenario"]["id"] == "retail-cs-log-pii"
    assert {node["id"] for node in payload["nodes"]} >= {"2.7.1", "3.2.1", "2.11.3"}
    assert any(edge["source"] == "2.9.4" and edge["target"] == "2.9.5" for edge in payload["edges"])


def test_unknown_control_and_scenario_return_404() -> None:
    assert client.get("/controls/9.9.9").status_code == 404
    assert client.get("/controls/graph", params={"scenario": "missing"}).status_code == 404


def test_control_map_page_returns_interactive_ui() -> None:
    response = client.get("/workspace")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ISMS-P" in response.text
    assert "/controls/map/assets/control_map.css" in response.text
    assert "/controls/map/assets/app.js" in response.text
    assert 'script type="module"' in response.text
    assert "<style>" not in response.text
    assert "<script>" not in response.text
    assert "포트폴리오" not in response.text
    assert 'id="questPanel"' not in response.text


def test_control_map_assets_return_styles_script_and_core_modules() -> None:
    styles = client.get("/controls/map/assets/control_map.css")
    script = client.get("/controls/map/assets/app.js")
    router = client.get("/controls/map/assets/core/router.js")
    state_module = client.get("/controls/map/assets/core/state.js")
    analysis_utils = client.get("/controls/map/assets/features/analysis/utils.js")
    analysis_gaps = client.get("/controls/map/assets/features/analysis/gaps.js")
    analysis_controller = client.get("/controls/map/assets/features/analysis/controller.js")
    analysis_overlaps = client.get("/controls/map/assets/features/analysis/overlaps.js")
    analysis_presentation = client.get("/controls/map/assets/features/analysis/presentation.js")
    analysis_summary = client.get("/controls/map/assets/features/analysis/summary.js")
    report_review = client.get(
        "/controls/map/assets/features/analysis/report-review.js"
    )
    problem_view = client.get("/controls/map/assets/features/analysis/problems.js")
    certification_controller = client.get("/controls/map/assets/features/certification/controller.js")
    certification_view = client.get("/controls/map/assets/features/certification/view.js")
    assessment_module = client.get("/controls/map/assets/features/assessment/model.js")
    filter_module = client.get("/controls/map/assets/features/assessment/filter.js")
    assessment_view = client.get("/controls/map/assets/features/assessment/view.js")
    assessment_actions = client.get("/controls/map/assets/features/assessment/actions.js")
    assessment_controller = client.get(
        "/controls/map/assets/features/assessment/controller.js"
    )
    profile_module = client.get("/controls/map/assets/features/profile/view.js")
    session_module = client.get("/controls/map/assets/features/session/model.js")
    session_view = client.get("/controls/map/assets/features/session/view.js")

    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")
    assert '@import url("./styles/assessment.css")' in styles.text
    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert 'import { bootstrap } from "./core/router.js"' in script.text
    assert router.status_code == 200
    assert "export async function bootstrap" in router.text
    assert state_module.status_code == 200
    assert state_module.headers["content-type"].startswith("text/javascript")
    assert "export const state" in state_module.text
    assert analysis_utils.status_code == 200
    assert "export function shortRiskTip" in analysis_utils.text
    assert "export function renderResultEmptyState" in analysis_utils.text
    assert "export function gapClusterEmptyMarkup" in analysis_utils.text
    assert "export function linkedProblemEmptyMarkup" in analysis_utils.text
    assert analysis_gaps.status_code == 200
    assert "export function renderAnalyzeGaps" in analysis_gaps.text
    assert analysis_controller.status_code == 200
    assert "export function executeAnalysis" in analysis_controller.text
    assert analysis_overlaps.status_code == 200
    assert "export function renderMultiGapOverlaps" in analysis_overlaps.text
    assert analysis_presentation.status_code == 200
    assert "export function renderAnalysisLoading" in analysis_presentation.text
    assert "ANALYSIS_STEPS" not in analysis_controller.text
    assert "await sleep(420)" not in analysis_controller.text
    assert analysis_summary.status_code == 200
    assert "export function renderAnalysisSummary" in analysis_summary.text
    assert report_review.status_code == 200
    assert "export function buildReportReviewItems" in report_review.text
    assert problem_view.status_code == 200
    assert "export function renderProblemAnalysis" in problem_view.text
    assert certification_controller.status_code == 200
    assert "export async function loadCertificationGuide" in certification_controller.text
    assert certification_view.status_code == 200
    assert "export function renderCertificationGuide" in certification_view.text
    assert assessment_module.status_code == 200
    assert "export function deriveLevel" in assessment_module.text
    assert filter_module.status_code == 200
    assert "export function filteredChecklist" in filter_module.text
    assert assessment_view.status_code == 200
    assert "export function renderControlAssessRow" in assessment_view.text
    assert assessment_actions.status_code == 200
    assert "export function applyChecksToControl" in assessment_actions.text
    assert assessment_controller.status_code == 200
    assert "export function renderAssessList" in assessment_controller.text
    assert profile_module.status_code == 200
    assert "export function openProfilePanel" in profile_module.text
    assert session_module.status_code == 200
    assert "export function backlogControls" in session_module.text
    assert session_view.status_code == 200
    assert "export function renderConfirmationActions" in session_view.text


def test_control_map_assets_reject_unknown_or_unsafe_paths() -> None:
    assert client.get("/controls/map/assets/missing.js").status_code == 404
    assert client.get("/controls/map/assets/core/state.txt").status_code == 404


def test_checklist_endpoint_returns_risk_and_checklist_items() -> None:
    response = client.get("/controls/checklist")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 101
    encryption = next(item for item in payload["controls"] if item["id"] == "2.7.1")
    assert encryption["title"] == "암호정책 적용"
    assert len(encryption["checklistItems"]) >= 2
    assert encryption.get("officialRequirement")
    assert "암호화" in encryption["riskIfMissing"] or "암호" in encryption["riskIfMissing"]
    assert encryption["recommendedActions"]
    assert any("암호" in item for item in encryption["checklistItems"])


def test_certification_guide_returns_five_phases() -> None:
    response = client.get("/controls/certification-guide")
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["phases"]) == 5
    assert payload["phases"][0]["id"] == "prepare"
    assert payload["totalControls"] == 101


def test_bootstrap_assessment_marks_project_controls_done() -> None:
    response = client.get("/controls/bootstrap-assessment")
    payload = response.json()["assessments"]

    assert response.status_code == 200
    assert len(payload) == 101
    assert payload["2.7.1"] == "done"
    assert payload["3.2.1"] == "done"
    assert "unknown" not in set(payload.values())
    assert set(payload.values()) <= {"done", "partial", "none"}


def test_analyze_endpoint_returns_gaps_and_portfolio_summary() -> None:
    bootstrap = {control["id"]: "done" for control in list_controls()}
    bootstrap["1.1.1"] = "none"
    bootstrap["2.5.1"] = "partial"
    bootstrap["2.9.4"] = "none"

    response = client.post("/controls/analyze", json={"assessments": bootstrap})
    payload = response.json()

    assert response.status_code == 200
    assert 0 <= payload["overallReadiness"] <= 100
    assert payload["gapCount"] >= 1
    assert payload["topGaps"]
    assert "ISMS-P 학습/셀프진단 포트폴리오 요약" in payload["portfolioSummary"]
    assert any(gap["controlId"] == "1.1.1" for gap in payload["criticalGaps"])

    focused_assessments = {control["id"]: "done" for control in list_controls()}
    focused_assessments["2.9.4"] = "none"
    focused_assessments["2.9.5"] = "partial"
    focused = client.post("/controls/analyze", json={"assessments": focused_assessments}).json()
    log_gap = next(gap for gap in focused["topGaps"] if gap["controlId"] == "2.9.4")
    assert log_gap["checklistBreakdown"]
    assert len(log_gap["checklistBreakdown"]) >= 3
    assert log_gap["consequenceScenarios"]
    assert log_gap["organicAnalysis"]
    assert log_gap["detailedSummary"]
    assert log_gap.get("immediateActions")
    assert log_gap.get("narrativeReport")
    assert "[통제 진단]" in log_gap["narrativeReport"]
    assert log_gap["checklistBreakdown"][0].get("auditQuestion")
    assert log_gap["checklistBreakdown"][0].get("verificationMethod")
    assert log_gap["checklistBreakdown"][0].get("evidenceHint")
    assert any("2.9.5" in item["targetControlId"] for item in log_gap["cascadeRisks"])
    assert focused["cascadeChains"]
    assert focused["keyInsights"]
    cascade_card = next(item for item in focused["reviewItems"] if item["kind"] == "cascade")
    assert cascade_card["pathNodes"][0]["title"]
    assert cascade_card["pathNodes"][1]["title"]
    assert cascade_card["pathNodes"][0]["controlId"] != cascade_card["pathNodes"][1]["controlId"]
    assert cascade_card["pathNodes"][0]["levelLabel"]
    assert cascade_card["pathNodes"][1]["levelLabel"]
    assert cascade_card["title"] == "연결 위험 확인"
    assert cascade_card["routeLabel"] == "통제 간 영향 경로"
    assert cascade_card["relationLabel"] == "영향 가능성"
    assert cascade_card["pathNodes"][0]["role"] == "확인된 약점"
    assert cascade_card["headline"].endswith("영향을 줄 수 있습니다.")
    assert cascade_card["nextAction"]
    assert cascade_card["action"]["controlId"] == cascade_card["pathNodes"][1]["controlId"]
    assert cascade_card["action"]["label"] == "영향 통제 점검"
    assert all(chain["validationCriteria"] for chain in focused["cascadeChains"])
    assert all(chain["rejectionCriteria"] for chain in focused["cascadeChains"])
    assert all("groundingLevel" in chain for chain in focused["cascadeChains"])
    assert all(chain["sourceArtifacts"] for chain in focused["cascadeChains"])
    assert all(chain["targetArtifacts"] for chain in focused["cascadeChains"])
    assert all(chain["comparisonRows"] for chain in focused["cascadeChains"])
    assert all(chain["decisionRule"] for chain in focused["cascadeChains"])
    assert focused["executiveReport"]
    assert "ISMS-P 자가진단 확인 요약" in focused["executiveReport"]
    assert focused["reportSections"]
    assert focused["gapClusters"]
    assert all(
        cluster["noneCount"] + cluster["partialCount"] == cluster["gapCount"]
        for cluster in focused["gapClusters"]
    )
    assert all(len(cluster["controls"]) == cluster["gapCount"] for cluster in focused["gapClusters"])
    assert all(cluster["primaryControl"]["controlId"] for cluster in focused["gapClusters"])
    assert all(cluster["primaryControl"]["selectionReasons"] for cluster in focused["gapClusters"])
    assert all(cluster["primaryControl"]["riskIfMissing"] for cluster in focused["gapClusters"])
    assert all(cluster["primaryControl"]["defectEvidence"] for cluster in focused["gapClusters"])
    assert all(
        cluster["primaryControl"]["defectEvidence"]["sourceDoc"]
        for cluster in focused["gapClusters"]
    )
    assert all(
        cluster["controlIds"] == sorted(
            cluster["controlIds"],
            key=lambda control_id: tuple(map(int, control_id.split("."))),
        )
        for cluster in focused["gapClusters"]
    )
    assert focused["certPhaseHint"]
    assert focused["certPhaseHint"]["phaseId"]

    rec_assessments = {control["id"]: "done" for control in list_controls()}
    rec_assessments["2.7.1"] = "none"
    rec_assessments["2.7.2"] = "none"
    rec_focused = client.post("/controls/analyze", json={"assessments": rec_assessments}).json()
    rec_271 = next(r for r in rec_focused["recommendations"] if "2.7.1" in r["title"])
    rec_272 = next(r for r in rec_focused["recommendations"] if "2.7.2" in r["title"])
    assert rec_271["detail"] != rec_272["detail"]

    scenario_focused = client.post(
        "/controls/analyze",
        json={"assessments": focused_assessments, "scenarioId": "retail-cs-log-pii"},
    ).json()
    assert scenario_focused["scenarioFocus"]
    assert scenario_focused["scenarioFocus"]["scenarioId"] == "retail-cs-log-pii"
    assert scenario_focused["scenarioFocus"]["relevantGapCount"] >= 1
    assert any(gap.get("scenarioRelevant") for gap in scenario_focused["topGaps"])


def test_unreviewed_controls_are_not_reported_as_confirmed_findings() -> None:
    response = client.post("/controls/analyze", json={"assessments": {}})
    payload = response.json()

    assert response.status_code == 200
    assert payload["gapCount"] == 0
    assert payload["reviewedControlCount"] == 0
    assert payload["unreviewedControlCount"] == payload["applicableControlCount"]
    assert payload["assessmentCompletionPercent"] == 0
    assert payload["multiGapOverlaps"] == []
    assert payload["cascadeChains"] == []
    assert payload["weakCategories"] == []
    assert payload["topGaps"] == []
    assert payload["reviewItems"] == []
    assert "공식 인증 점수" in payload["scoreDisclaimer"]


def test_review_items_separate_confirmed_findings_from_unreviewed_controls() -> None:
    assessments = {"1.1.1": "none", "1.1.2": "partial", "1.1.3": "done"}
    payload = client.post("/controls/analyze", json={"assessments": assessments}).json()

    assert payload["gapCount"] == 2
    assert payload["reviewedControlCount"] == 3
    assert payload["unreviewedControlCount"] > 0
    assert {gap["controlId"] for gap in payload["confirmedGaps"]} == {"1.1.1", "1.1.2"}
    finding = next(item for item in payload["reviewItems"] if item["kind"] == "finding")
    assert finding["classification"] == "verified_finding"
    assert finding["metric"] == 2
    assert "미점검 통제는 제외" in finding["explanation"]


def test_scenario_focus_separates_unreviewed_candidates_from_confirmed_gaps() -> None:
    payload = client.post(
        "/controls/analyze",
        json={"assessments": {}, "scenarioId": "retail-cs-log-pii"},
    ).json()

    assert payload["gapCount"] == 0
    assert payload["scenarioFocus"]["relevantGapCount"] == 0
    assert payload["scenarioFocus"]["highlightedControlIds"] == []
    assert payload["scenarioFocus"]["unreviewedCandidateCount"] > 0


def test_category_coverage_includes_all_101_controls() -> None:
    payload = client.post("/controls/analyze", json={"assessments": {}}).json()

    categories = payload["categoryCoverage"]
    assert len(categories) == 21
    assert sum(item["totalCount"] for item in categories) == 101
    assert sum(item["reviewedCount"] for item in categories) == 0
    assert all(item["coveragePercent"] == 0 for item in categories)
    assert {item["areaId"] for item in categories} == {"1", "2", "3"}
    assert len({item["categoryId"] for item in categories}) == 21
    assert next(item for item in categories if item["categoryId"] == "2.10")["category"] == "시스템 및 서비스 보안관리"


def test_weak_category_action_targets_a_reviewed_weak_control() -> None:
    payload = client.post(
        "/controls/analyze",
        json={"assessments": {"1.1.2": "partial"}},
    ).json()

    weak = payload["weakCategories"][0]
    weak_card = next(item for item in payload["reviewItems"] if item["kind"] == "weak")
    area = weak["category"]

    assert weak["firstControlId"] == "1.1.2"
    assert weak_card["action"]["controlId"] == "1.1.2"
    assert weak["reviewedCount"] == 1
    assert weak["statusCounts"]["partial"] == 1
    assert weak["areaId"] == "1"
    assert weak["areaName"] == "관리체계 수립 및 운영"
    assert weak_card["coveragePercent"] == weak["coveragePercent"]
    assert weak_card.get("metricLabel") == "분야 점검 완료율"
    assert weak_card["title"] == "보완 집중 분야"
    assert {stat["label"] for stat in weak_card["stats"]} == {
        "미이행",
        "부분 이행",
        "이행·증적",
    }
    assert payload["areaCoverage"]["관리체계 수립 및 운영"]["reviewedCount"] == 1
    assert payload["areaCoverage"]["관리체계 수립 및 운영"]["totalCount"] > 1
    assert area == "관리체계 기반 마련"


def test_fully_implemented_category_is_not_labeled_as_weak() -> None:
    payload = client.post(
        "/controls/analyze",
        json={"assessments": {"2.5.1": "done", "2.5.2": "done", "2.5.3": "done", "2.5.4": "done", "2.5.5": "done", "2.5.6": "done"}},
    ).json()

    assert not any(item["kind"] == "weak" for item in payload["reviewItems"])


def test_cascade_chains_reject_self_references() -> None:
    from isms_pii_toolkit.control_assessment import _build_cascade_chains

    chains = _build_cascade_chains(
        [
            {
                "controlId": "2.3.2",
                "title": "보안 요구사항 검토",
                "cascadeRisks": [
                    {"targetControlId": "2.3.2", "connectionReason": "self"},
                    {"targetControlId": "2.3.3", "connectionReason": "valid"},
                ],
            }
        ]
    )

    assert len(chains) == 1
    assert chains[0]["originControlId"] == "2.3.2"
    assert chains[0]["targetControlId"] == "2.3.3"


def test_analyze_without_profile_preserves_existing_scoring_contract() -> None:
    assessments = {control["id"]: "done" for control in list_controls()}
    assessments["1.1.4"] = "none"
    response = client.post("/controls/analyze", json={"assessments": assessments})
    payload = response.json()

    assert response.status_code == 200
    assert payload["gapCount"] == 1
    assert payload["topGaps"][0]["controlId"] == "1.1.4"
    # Without org profile, priority is defect-weight only (not profile boost).
    from isms_pii_toolkit.defect_priority import defect_priority_delta

    assert payload["topGaps"][0]["profilePriority"] == defect_priority_delta("1.1.4")
    assert payload["topGaps"][0]["profileRelevance"] == []
    assert payload["profileContext"] is None
    assert payload["scopeDraft"] is None
    assert payload["suggestedScenarioIds"] == []
    assert payload.get("institutionHints")


def test_profile_aware_analyze_prioritizes_scope_and_returns_draft() -> None:
    assessments = {control["id"]: "done" for control in list_controls()}
    for control_id in ("1.1.4", "1.2.1", "2.4.7", "2.10.2"):
        assessments[control_id] = "none"

    response = client.post(
        "/controls/analyze",
        json={
            "assessments": assessments,
            "organizationProfile": {
                "headcountBand": "1-50",
                "industry": "technology",
                "piiVolume": "medium",
                "usesCloud": True,
                "hasOnPremFacility": False,
                "usesOutsourcing": False,
                "usesRemoteAccess": False,
                "processesRrn": False,
            },
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["profileContext"]["headcountBand"] == "1-50"
    assert payload["scopeDraft"]["status"] == "draft"
    assert "cloud-campaign-page" in payload["suggestedScenarioIds"]
    assert "tech-saas-tenant" in payload["suggestedScenarioIds"]
    assert payload["minimumEvidencePack"]["requiredCount"] >= 1
    assert payload["scopeDraft"]["candidateItems"]
    by_id = {gap["controlId"]: gap for gap in payload["topGaps"]}
    assert by_id["1.1.4"]["profilePriority"] > by_id["2.4.7"]["profilePriority"]
    assert by_id["2.10.2"]["profileRelevance"]
    assert payload["naControlCount"] >= 1
    assert any(note["controlId"] == "2.4.1" for note in payload["applicabilityNotes"])


def test_industry_scenarios_are_listed_and_traceable() -> None:
    scenarios = client.get("/controls/scenarios").json()["scenarios"]
    by_id = {row["id"]: row for row in scenarios}
    assert "healthcare-emr-access" in by_id
    assert "public-citizen-service" in by_id
    assert "finance-customer-data" in by_id
    assert "tech-saas-tenant" in by_id
    assert "healthcare" in by_id["healthcare-emr-access"]["industries"]

    trace = client.get("/controls/trace/healthcare-emr-access")
    assert trace.status_code == 200
    assert len(trace.json()["steps"]) >= 5


def test_multigap_registry_is_evidence_backed() -> None:
    from collections import Counter

    from isms_pii_toolkit.control_insight_multigap import MULTIGAP_BUNDLES, _CURATED_MULTIGAP_BUNDLES

    assert len(_CURATED_MULTIGAP_BUNDLES) >= 15
    assert len(MULTIGAP_BUNDLES) >= 40

    sources = Counter(bundle.source for bundle in MULTIGAP_BUNDLES)
    assert sources["curated"] >= 15
    assert sources["graph_relation"] >= 10
    assert "anchor" not in "".join(bundle.id for bundle in MULTIGAP_BUNDLES)
    assert not any(bundle.theme == "통제별 앵커" for bundle in MULTIGAP_BUNDLES)

    for bundle in MULTIGAP_BUNDLES:
        assert bundle.basis.strip()
        assert len(bundle.evidence) >= 1
        assert bundle.source in {"curated", "graph_relation", "scenario_flow", "category_set"}
        assert len(bundle.required_controls) >= 2


def test_analyze_returns_multigap_overlaps_for_crypto_log_bundle() -> None:
    assessments = {control["id"]: "done" for control in list_controls()}
    for control_id in ("2.7.1", "2.7.2", "2.9.4", "2.9.5"):
        assessments[control_id] = "none"

    response = client.post("/controls/analyze", json={"assessments": assessments})
    payload = response.json()

    assert response.status_code == 200
    assert payload["multiGapOverlaps"]
    crypto_overlap = next(o for o in payload["multiGapOverlaps"] if o["bundleId"] == "crypto-log-pii")
    assert crypto_overlap["matchType"] == "full"
    assert crypto_overlap["matchedCount"] >= 3
    assert crypto_overlap["source"] == "curated"
    assert crypto_overlap["basis"]
    assert crypto_overlap["evidence"]
    assert "[출처/근거]" in crypto_overlap["overlapNarrative"]
    assert crypto_overlap["overlapNarrative"]
    assert len(crypto_overlap["incidentScenarios"]) >= 3
    assert crypto_overlap["remediationPath"]
    overlap_card = next(item for item in payload["reviewItems"] if item["kind"] == "overlap")
    assert overlap_card["controlNodes"]
    assert all(node["title"] and node["levelLabel"] for node in overlap_card["controlNodes"])
    assert {stat["label"] for stat in overlap_card["stats"]} == {
        "일치 통제",
        "위험 수준",
        "판정 유형",
    }

    log_gap = next(g for g in payload["topGaps"] if g["controlId"] == "2.9.4")
    assert log_gap["overlappingRisks"]
    assert any(item["bundleId"] == "crypto-log-pii" for item in log_gap["overlappingRisks"])
    assert "다중 갭 겹침" in payload["executiveReport"]


def test_multigap_graph_relation_exposes_manual_reason() -> None:
    from isms_pii_toolkit.control_insight_multigap import detect_multigap_overlaps

    assessments = {control["id"]: "done" for control in list_controls()}
    assessments["1.1.4"] = "none"
    assessments["1.2.1"] = "none"

    overlaps = detect_multigap_overlaps(assessments)
    pair = next(o for o in overlaps if o["bundleId"] == "rel-1-1-4-1-2-1")
    assert pair["source"] == "graph_relation"
    assert any("자산 식별" in line for line in pair["evidence"])
    assert "관계 증거" in pair["basis"] or "MANUAL_RELATIONS" in pair["basis"] or "1.1.4" in pair["basis"]


def test_category_deep_scenarios_replace_template_profiles() -> None:
    from isms_pii_toolkit.control_insight_kb import build_gap_insights

    control = next(c for c in list_controls() if c["id"] == "2.6.1")
    insights = build_gap_insights(dict(control), "none", {"2.6.1": "none"})

    scenarios = insights["consequenceScenarios"]
    assert len(scenarios) >= 3
    assert not all("관련 업무에서" in s for s in scenarios)
    assert any("DB" in s or "접근" in s or "로그" in s for s in scenarios)


def test_analyze_checklist_breakdown_covers_all_controls() -> None:
    assessments = {control["id"]: "none" for control in list_controls()}

    response = client.post("/controls/analyze", json={"assessments": assessments})
    payload = response.json()

    assert response.status_code == 200
    assert payload["gapCount"] == 101
    for gap in payload["topGaps"]:
        assert gap["checklistBreakdown"]
        assert len(gap["checklistBreakdown"]) >= 3
        assert gap["consequenceScenarios"]
        assert len(gap["consequenceScenarios"]) >= 3
        assert gap["organicAnalysis"]
        assert gap["controlFocus"]


def test_all_controls_have_insight_profiles() -> None:
    from isms_pii_toolkit.control_insight_kb import CONTROL_PROFILES, build_checklist_breakdown, build_gap_insights

    controls = list_controls()
    assert len(CONTROL_PROFILES) == 101
    assessments = {control["id"]: "none" for control in controls}
    for control in controls:
        cid = str(control["id"])
        profile = CONTROL_PROFILES[cid]
        assert profile.get("focus")
        assert profile.get("scenarios")
        assert len(profile["scenarios"]) >= 2  # type: ignore[arg-type]
        breakdown = build_checklist_breakdown(cid, str(control["title"]), str(control["categoryId"]), "none")
        assert len(breakdown) >= 3
        insights = build_gap_insights(dict(control), "none", assessments)
        assert len(insights["consequenceScenarios"]) >= 3
        assert insights.get("narrativeReport")
        assert insights["checklistBreakdown"][0].get("verificationMethod")


def test_dashboard_endpoint_returns_learning_stats() -> None:
    response = client.get("/controls/dashboard")
    payload = response.json()

    assert response.status_code == 200
    assert payload["totalControls"] == 101
    assert payload["scenarioCount"] == 9
    assert payload["implemented"] >= 1


def test_trace_endpoint_returns_ordered_scenario_flow() -> None:
    response = client.get("/controls/trace/retail-cs-log-pii")
    payload = response.json()

    assert response.status_code == 200
    assert payload["scenario"]["id"] == "retail-cs-log-pii"
    assert len(payload["steps"]) == 9
    assert payload["steps"][0]["controlId"] == "1.2.1"
    assert payload["steps"][1]["linkFromPrevious"] is not None


def test_problem_kb_has_101_control_json_files() -> None:
    from pathlib import Path

    from isms_pii_toolkit.control_problem_engine import DATA_ROOT, _load_index

    index = _load_index()
    controls_dir = DATA_ROOT / "controls"
    assert index["totalControls"] == 101
    assert len(list(controls_dir.glob("*.json"))) == 101
    assert (DATA_ROOT / "compounds.json").is_file()
    assert (DATA_ROOT / "relation_evidence.json").is_file()
    # Evidence-based rebuild intentionally drops template-only compounds.
    assert index["totalCompounds"] >= 40
    assert index.get("compoundsEvidenceVersion", 1) >= 2


def test_analyze_returns_problem_analysis_from_json_kb() -> None:
    assessments = {control["id"]: "done" for control in list_controls()}
    assessments["2.7.1"] = "none"
    assessments["2.7.2"] = "none"
    assessments["2.9.4"] = "partial"
    assessments["2.9.5"] = "none"

    response = client.post(
        "/controls/analyze",
        json={
            "assessments": assessments,
            "controlChecks": {
                "2.9.4": {
                    "reviewed": True,
                    "policy": True,
                    "implemented": False,
                    "evidence": False,
                }
            },
        },
    )
    payload = response.json()

    assert response.status_code == 200
    analysis = payload["problemAnalysis"]
    assert analysis["stats"]["totalControlsInKb"] == 101
    assert analysis["stats"]["individualProblemCount"] >= 4
    assert analysis["individualProblems"]
    assert any(row["controlId"] == "2.9.4" for row in analysis["individualProblems"])
    assert analysis["compoundSyntheses"]
    assert analysis["integratedGuidance"]["prioritizedActions"]
    assert "미흡 통제" in analysis["integratedGuidance"]["summary"]

    crypto_cluster = next(
        (
            syn
            for syn in analysis["compoundSyntheses"]
            if "2.7.1" in syn["controlIds"] and "2.7.2" in syn["controlIds"]
        ),
        None,
    )
    assert crypto_cluster is not None
    assert crypto_cluster["compoundProblems"]
    assert crypto_cluster["integratedRemediation"]
