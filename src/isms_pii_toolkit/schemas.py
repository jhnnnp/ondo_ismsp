from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ControlImplementationStatus = Literal["implemented", "evidence_mapped", "study_mapped"]
AssessmentLevel = Literal["unknown", "none", "partial", "done", "evidenced", "na"]
InputConfidence = Literal["confirmed", "assumed", "unknown"]
GapSeverity = Literal["critical", "high", "medium"]
HeadcountBand = Literal["1-50", "51-300", "301+"]
Industry = Literal["general", "retail", "healthcare", "public", "finance", "technology"]
PiiVolume = Literal["low", "medium", "high"]
MAX_ASSESS_PAYLOAD_BYTES = 200_000


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(ApiModel):
    status: str
    version: str


class LawReferenceResponse(ApiModel):
    law_name: str = Field(alias="lawName")
    article: str | None = None
    paragraph: str | None = None
    item: str | None = None
    basis_type: str = Field(default="DIRECT", alias="basisType")
    article_title: str | None = Field(default=None, alias="articleTitle")
    article_text: str | None = Field(default=None, alias="articleText")
    effective_date: str | None = Field(default=None, alias="effectiveDate")
    promulgation_date: str | None = Field(default=None, alias="promulgationDate")
    ministry: str | None = None
    document_type: str | None = Field(default=None, alias="documentType")
    current_status: str | None = Field(default=None, alias="currentStatus")
    collected_at: str | None = Field(default=None, alias="collectedAt")
    source_url: str | None = Field(default=None, alias="sourceUrl")


class LegalGuideSourceResponse(ApiModel):
    document: str | None = None
    pages: list[int] = Field(default_factory=list)


class LegalSourceResponse(ApiModel):
    provider: str
    original_url: str | None = Field(default=None, alias="originalUrl")
    collected_at: str | None = Field(default=None, alias="collectedAt")


class LegalInterpretationResponse(ApiModel):
    interpretation_id: str = Field(alias="interpretationId")
    serial_number: str = Field(alias="serialNumber")
    case_number: str | None = Field(default=None, alias="caseNumber")
    title: str
    question_agency: str | None = Field(default=None, alias="questionAgency")
    response_agency: str | None = Field(default=None, alias="responseAgency")
    response_date: str | None = Field(default=None, alias="responseDate")
    question: str | None = None
    answer: str | None = None
    reasoning: str | None = None
    related_laws: list[LawReferenceResponse] = Field(default_factory=list, alias="relatedLaws")
    source: LegalSourceResponse
    temporal_status: str = Field(alias="temporalStatus")
    warning: str | None = None
    match_score: int | None = Field(default=None, alias="matchScore")
    match_reasons: list[str] = Field(default_factory=list, alias="matchReasons")
    review_status: str | None = Field(default=None, alias="reviewStatus")


class LegalInterpretationListResponse(ApiModel):
    total: int
    items: list[LegalInterpretationResponse]
    disclaimer: str


class LegalInterpretationDetailResponse(LegalInterpretationResponse):
    disclaimer: str


class LegalCasebookSourceResponse(ApiModel):
    provider: str
    document: str
    published_at: str = Field(alias="publishedAt")
    source_type: str = Field(alias="sourceType")


class LegalCasebookExampleResponse(ApiModel):
    case_id: str = Field(alias="caseId")
    section: str
    title: str
    question: str | None = None
    answer: str | None = None
    reasoning: str | None = None
    control_ids: list[str] = Field(default_factory=list, alias="controlIds")
    source_page: int | None = Field(default=None, alias="sourcePage")
    source: LegalCasebookSourceResponse
    warning: str | None = None


class OfficialGuidanceResponse(ApiModel):
    guide_id: str = Field(alias="guideId")
    title: str
    publisher: str
    published_at: str = Field(alias="publishedAt")
    source_document: str = Field(alias="sourceDocument")
    section: str
    pages: list[int] = Field(default_factory=list)
    summary: str
    checkpoints: list[str] = Field(default_factory=list)
    applicability: str


class ControlLegalBasisResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    control_title: str = Field(default="", alias="controlTitle")
    requirement_summary: str | None = Field(default=None, alias="requirementSummary")
    audit_questions: list[str] = Field(default_factory=list, alias="auditQuestions")
    evidence_examples: list[str] = Field(default_factory=list, alias="evidenceExamples")
    defect_examples: list[str] = Field(default_factory=list, alias="defectExamples")
    guide_source: LegalGuideSourceResponse = Field(default_factory=LegalGuideSourceResponse, alias="guideSource")
    laws: list[LawReferenceResponse]
    interpretations: list[LegalInterpretationResponse]
    casebook_examples: list[LegalCasebookExampleResponse] = Field(default_factory=list, alias="casebookExamples")
    official_guidance: list[OfficialGuidanceResponse] = Field(default_factory=list, alias="officialGuidance")
    casebook_corpus_size: int = Field(default=0, alias="casebookCorpusSize")
    interpretation_corpus_size: int = Field(default=0, alias="interpretationCorpusSize")
    interpretation_data_status: str = Field(default="UNKNOWN", alias="interpretationDataStatus")
    last_updated_at: str | None = Field(default=None, alias="lastUpdatedAt")
    disclaimer: str


class ControlRelationResponse(ApiModel):
    target_control_id: str = Field(alias="targetControlId")
    reason: str


class ControlResponse(ApiModel):
    id: str
    area_id: str = Field(alias="areaId")
    area_name: str = Field(alias="areaName")
    category_id: str = Field(alias="categoryId")
    category_name: str = Field(alias="categoryName")
    title: str
    tags: list[str]
    related_control_ids: list[str] = Field(alias="relatedControlIds")
    relations: list[ControlRelationResponse]
    evidence_ids: list[str] = Field(alias="evidenceIds")
    scenario_ids: list[str] = Field(alias="scenarioIds")
    implementation_status: ControlImplementationStatus = Field(alias="implementationStatus")
    study_note: str = Field(alias="studyNote")


class ControlListResponse(ApiModel):
    total: int
    controls: list[ControlResponse]


class EvidenceResponse(ApiModel):
    id: str
    title: str
    description: str
    artifact_refs: list[str] = Field(alias="artifactRefs")
    control_ids: list[str] = Field(alias="controlIds")


class EvidenceListResponse(ApiModel):
    evidences: list[EvidenceResponse]


class ScenarioResponse(ApiModel):
    id: str
    title: str
    description: str
    control_ids: list[str] = Field(alias="controlIds")
    industries: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ScenarioListResponse(ApiModel):
    scenarios: list[ScenarioResponse]


class GraphEdgeResponse(ApiModel):
    source: str
    target: str
    reason: str


class ControlGraphResponse(ApiModel):
    nodes: list[ControlResponse]
    edges: list[GraphEdgeResponse]
    scenario: ScenarioResponse | None = None


class TraceStepResponse(ApiModel):
    order: int
    control_id: str = Field(alias="controlId")
    title: str
    category_name: str = Field(alias="categoryName")
    area_name: str = Field(alias="areaName")
    implementation_status: ControlImplementationStatus = Field(alias="implementationStatus")
    study_note: str = Field(alias="studyNote")
    evidence_ids: list[str] = Field(alias="evidenceIds")
    related_control_ids: list[str] = Field(alias="relatedControlIds")
    link_from_previous: str | None = Field(alias="linkFromPrevious")


class ScenarioTraceResponse(ApiModel):
    scenario: ScenarioResponse
    steps: list[TraceStepResponse]


class DashboardResponse(ApiModel):
    total_controls: int = Field(alias="totalControls")
    implemented: int
    evidence_mapped: int = Field(alias="evidenceMapped")
    study_mapped: int = Field(alias="studyMapped")
    scenario_count: int = Field(alias="scenarioCount")
    evidence_count: int = Field(alias="evidenceCount")
    area_breakdown: dict[str, int] = Field(alias="areaBreakdown")


class ChecklistControlResponse(ControlResponse):
    checklist_items: list[str] = Field(alias="checklistItems")
    risk_if_missing: str = Field(alias="riskIfMissing")
    recommended_actions: list[str] = Field(alias="recommendedActions")
    priority: int
    official_requirement: str | None = Field(default=None, alias="officialRequirement")
    official_evidence_examples: list[str] = Field(
        default_factory=list,
        alias="officialEvidenceExamples",
    )
    search_hints: list[str] = Field(default_factory=list, alias="searchHints")
    search_entries: list[dict[str, object]] = Field(default_factory=list, alias="searchEntries")
    search_intents: list[dict[str, object]] = Field(default_factory=list, alias="searchIntents")


class ChecklistResponse(ApiModel):
    total: int
    controls: list[ChecklistControlResponse]


class CertificationPhaseResponse(ApiModel):
    id: str
    order: int
    title: str
    duration: str
    summary: str
    activities: list[str]
    related_control_ids: list[str] = Field(alias="relatedControlIds")


class CertificationGuideResponse(ApiModel):
    title: str
    description: str
    phases: list[CertificationPhaseResponse]
    total_controls: int = Field(alias="totalControls")
    areas: list[dict[str, object]]
    source_doc: str | None = Field(default=None, alias="sourceDoc")
    disclaimer: str | None = None
    preparation_checks: list[str] = Field(default_factory=list, alias="preparationChecks")
    confirmation_questions: list[str] = Field(default_factory=list, alias="confirmationQuestions")
    obligation_summary: list[str] = Field(default_factory=list, alias="obligationSummary")
    scope_rules: list[dict[str, object]] = Field(default_factory=list, alias="scopeRules")


class InstitutionGuideResponse(ApiModel):
    source_doc: str | None = Field(default=None, alias="sourceDoc")
    disclaimer: str | None = None
    cert_types: list[dict[str, object]] = Field(default_factory=list, alias="certTypes")
    obligation_summary: list[str] = Field(default_factory=list, alias="obligationSummary")
    scope_rules: list[dict[str, object]] = Field(default_factory=list, alias="scopeRules")
    process_phases: list[dict[str, object]] = Field(default_factory=list, alias="processPhases")
    preparation_checks: list[str] = Field(default_factory=list, alias="preparationChecks")
    confirmation_questions: list[str] = Field(default_factory=list, alias="confirmationQuestions")


class SimpleCertHintsResponse(ApiModel):
    enabled: bool = False
    mode: str | None = None
    relaxed_control_ids: list[str] = Field(default_factory=list, alias="relaxedControlIds")
    tips: list[str] = Field(default_factory=list)
    confirmation_hints: list[str] = Field(default_factory=list, alias="confirmationHints")
    notes: list[str] = Field(default_factory=list)
    disclaimer: str | None = None
    source_doc: str | None = Field(default=None, alias="sourceDoc")


class OrganizationProfileRequest(ApiModel):
    headcount_band: HeadcountBand = Field(alias="headcountBand")
    industry: Industry = "general"
    pii_volume: PiiVolume = Field(default="low", alias="piiVolume")
    uses_cloud: bool = Field(default=False, alias="usesCloud")
    uses_outsourcing: bool = Field(default=False, alias="usesOutsourcing")
    uses_remote_access: bool = Field(default=False, alias="usesRemoteAccess")
    processes_rrn: bool = Field(default=False, alias="processesRrn")
    has_on_prem_facility: bool = Field(
        default=False,
        alias="hasOnPremFacility",
        description="자체 전산실/IDC/서버룸 보유 여부. False이고 usesCloud면 물리/전산실 통제 N/A.",
    )


class OrganizationProfileResponse(OrganizationProfileRequest):
    tags: list[str] = Field(default_factory=list)


class ScopeBoundaryResponse(ApiModel):
    type: str
    title: str
    draft: str


class ScopeCandidateItemResponse(ApiModel):
    id: str
    type: str
    title: str
    draft: str
    related_control_ids: list[str] = Field(alias="relatedControlIds")
    default_included: bool = Field(alias="defaultIncluded")
    included: bool = False


class ScopeConfirmationItemResponse(ApiModel):
    id: str
    prompt: str
    answered: bool = False


class MinimumEvidenceItemResponse(ApiModel):
    id: str
    title: str
    why: str
    related_control_ids: list[str] = Field(alias="relatedControlIds")
    required: bool


class MinimumEvidencePackResponse(ApiModel):
    summary: str
    items: list[MinimumEvidenceItemResponse]
    required_count: int = Field(alias="requiredCount")
    total_count: int = Field(alias="totalCount")


class ScopeReviewRequest(ApiModel):
    included_item_ids: list[str] | None = Field(default=None, alias="includedItemIds")
    answered_question_ids: list[str] | None = Field(default=None, alias="answeredQuestionIds")


class ScopeDraftResponse(ApiModel):
    status: Literal["draft"]
    disclaimer: str
    boundaries: list[ScopeBoundaryResponse]
    candidate_items: list[ScopeCandidateItemResponse] = Field(default_factory=list, alias="candidateItems")
    confirmation_questions: list[str] = Field(alias="confirmationQuestions")
    confirmation_items: list[ScopeConfirmationItemResponse] = Field(
        default_factory=list,
        alias="confirmationItems",
    )
    included_item_ids: list[str] = Field(default_factory=list, alias="includedItemIds")
    answered_question_ids: list[str] = Field(default_factory=list, alias="answeredQuestionIds")
    unanswered_questions: list[str] = Field(default_factory=list, alias="unansweredQuestions")
    review_notes: list[str] = Field(default_factory=list, alias="reviewNotes")
    priority_control_ids: list[str] = Field(alias="priorityControlIds")
    suggested_scenario_ids: list[str] = Field(alias="suggestedScenarioIds")
    minimum_evidence_pack: MinimumEvidencePackResponse | None = Field(
        default=None,
        alias="minimumEvidencePack",
    )


class ScopeDraftRequest(ApiModel):
    organization_profile: OrganizationProfileRequest = Field(alias="organizationProfile")
    scope_review: ScopeReviewRequest | None = Field(default=None, alias="scopeReview")


class AssessRequest(ApiModel):
    assessments: dict[str, AssessmentLevel] = Field(max_length=150)
    scenario_id: str | None = Field(default=None, max_length=100, alias="scenarioId")
    control_checks: dict[str, dict[str, bool]] | None = Field(
        default=None,
        max_length=150,
        alias="controlChecks",
    )
    domain_checks: dict[str, dict[str, bool]] | None = Field(
        default=None,
        max_length=150,
        alias="domainChecks",
        description="통제별 도메인 체크리스트 직접 응답 {itemId: bool}. 있으면 maturity_proxy 대신 direct_checklist.",
    )
    quest_checks: dict[str, dict[str, bool]] | None = Field(
        default=None,
        max_length=150,
        alias="questChecks",
        description="퀘스트 체크 {controlId: {checkId: bool}}. mapsToCheckKey로 controlChecks에 반영.",
    )
    input_confidence: dict[str, InputConfidence] | None = Field(
        default=None,
        max_length=150,
        alias="inputConfidence",
        description="통제별 입력 신뢰도 confirmed|assumed|unknown",
    )
    evidence_slots: dict[str, "EvidenceSlotMetaRequest"] | None = Field(
        default=None,
        max_length=300,
        alias="evidenceSlots",
        description="로컬 증적 스텁 메타 {slotId: {fileName, controlId, uploadedAt}}",
    )
    organization_profile: OrganizationProfileRequest | None = Field(default=None, alias="organizationProfile")
    scope_review: ScopeReviewRequest | None = Field(default=None, alias="scopeReview")
    session_bundle_mode: Literal["area", "chain", "theme"] = Field(
        default="chain",
        alias="sessionBundleMode",
        description="이번 세션 우선 통제 묶음 방식: area(영역) | chain(연결 줄기) | theme(업무 테마).",
    )
    view: Literal["full", "quest", "causal", "report"] = Field(
        default="full",
        description="응답 소프트 뷰. Lab은 full. 얇은 클라이언트는 quest|causal|report.",
    )

    @model_validator(mode="after")
    def validate_payload_budget(self) -> "AssessRequest":
        payload_size = len(self.model_dump_json(by_alias=True).encode("utf-8"))
        if payload_size > MAX_ASSESS_PAYLOAD_BYTES:
            raise ValueError("assessment payload exceeds the 200 KB limit")
        return self


class EvidenceSlotMetaRequest(ApiModel):
    file_name: str = Field(alias="fileName")
    control_id: str = Field(alias="controlId")
    uploaded_at: str | None = Field(default=None, alias="uploadedAt")
    content_type: str | None = Field(default=None, alias="contentType")


class ConfirmationDetailCheckResponse(ApiModel):
    check_id: str = Field(alias="checkId")
    question: str
    label: str = ""
    recommended: bool = False


class ControlSessionDetailResponse(ApiModel):
    """자가진단 카드용 전 통제 세부 문항/질문 (우선 confirmationActions와 독립)."""

    title: str = ""
    question: str = ""
    action_guide: str | None = Field(default=None, alias="actionGuide")
    detail_checks: list[ConfirmationDetailCheckResponse] = Field(
        default_factory=list, alias="detailChecks"
    )


class ConfirmationActionResponse(ApiModel):
    action_id: str = Field(alias="actionId")
    priority: int
    control_id: str = Field(alias="controlId")
    title: str = ""
    question: str
    ask_who: list[str] = Field(default_factory=list, alias="askWho")
    evidence_hint: str | None = Field(default=None, alias="evidenceHint")
    confidence: InputConfidence = "unknown"
    why_it_matters: str = Field(alias="whyItMatters")
    related_finding_ids: list[str] = Field(default_factory=list, alias="relatedFindingIds")
    check_id: str | None = Field(default=None, alias="checkId")
    slot_id: str | None = Field(default=None, alias="slotId")
    action_guide: str | None = Field(default=None, alias="actionGuide")
    detail_checks: list[ConfirmationDetailCheckResponse] = Field(
        default_factory=list, alias="detailChecks"
    )


class InputConfidenceSummaryResponse(ApiModel):
    confirmed: int = 0
    assumed: int = 0
    unknown: int = 0
    total: int = 0
    confirmed_ratio: float = Field(default=0.0, alias="confirmedRatio")
    assumed_ratio: float = Field(default=0.0, alias="assumedRatio")
    unknown_ratio: float = Field(default=0.0, alias="unknownRatio")


class ApplicabilityNoteResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    reason: str
    rule_id: str | None = Field(default=None, alias="ruleId")


class QuestCheckResponse(ApiModel):
    check_id: str = Field(alias="checkId")
    label: str
    recommended: bool = False
    maps_to_check_key: str | None = Field(default=None, alias="mapsToCheckKey")
    checked: bool | None = None


class QuestEvidenceSlotResponse(ApiModel):
    slot_id: str = Field(alias="slotId")
    title: str
    accepts: list[str] = Field(default_factory=list)
    required_for_level: str | None = Field(default=None, alias="requiredForLevel")
    uploaded: bool = False
    file_name: str | None = Field(default=None, alias="fileName")


class PriorityQuestResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    plain_question: str = Field(alias="plainQuestion")
    audience: list[str] = Field(default_factory=list)
    checks: list[QuestCheckResponse] = Field(default_factory=list)
    action_guide: dict[str, str] | None = Field(default=None, alias="actionGuide")
    evidence_slots: list[QuestEvidenceSlotResponse] = Field(default_factory=list, alias="evidenceSlots")
    level: AssessmentLevel
    level_label: str = Field(alias="levelLabel")
    source: str = "thin"
    confidence: InputConfidence = "unknown"


class PreviewCheckImpactRequest(ApiModel):
    assessments: dict[str, AssessmentLevel]
    control_checks: dict[str, dict[str, bool]] | None = Field(default=None, alias="controlChecks")
    control_id: str = Field(alias="controlId")
    check_key: str = Field(alias="checkKey")
    checked: bool = True
    organization_profile: OrganizationProfileRequest | None = Field(default=None, alias="organizationProfile")


class PreviewCheckFindingResponse(ApiModel):
    finding_id: str = Field(alias="findingId")
    control_id: str = Field(alias="controlId")
    checklist_item_id: str = Field(default="", alias="checklistItemId")
    checklist_item: str = Field(default="", alias="checklistItem")
    problem: str = ""
    causal_statement: str = Field(default="", alias="causalStatement")


class PreviewCheckImpactResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    check_key: str = Field(alias="checkKey")
    check_label: str = Field(alias="checkLabel")
    checked: bool
    before_count: int = Field(alias="beforeCount")
    after_count: int = Field(alias="afterCount")
    resolved_findings: list[PreviewCheckFindingResponse] = Field(alias="resolvedFindings")
    remaining_findings: list[PreviewCheckFindingResponse] = Field(alias="remainingFindings")
    introduced_findings: list[PreviewCheckFindingResponse] = Field(alias="introducedFindings")
    summary: str


class BootstrapAssessmentResponse(ApiModel):
    assessments: dict[str, AssessmentLevel]


class ChecklistBreakdownItemResponse(ApiModel):
    item: str
    status_note: str = Field(alias="statusNote")
    operational_risk: str = Field(alias="operationalRisk")
    audit_risk: str = Field(alias="auditRisk")
    audit_question: str | None = Field(default=None, alias="auditQuestion")
    related_controls: list[str] = Field(alias="relatedControls")
    remediation: str
    consequence_if_failed: str | None = Field(default=None, alias="consequenceIfFailed")
    verification_method: str | None = Field(default=None, alias="verificationMethod")
    evidence_hint: str | None = Field(default=None, alias="evidenceHint")
    relationship_note: str | None = Field(default=None, alias="relationshipNote")
    check_key: str | None = Field(default=None, alias="checkKey")
    checklist_item_id: str | None = Field(default=None, alias="checklistItemId")
    unmet: bool | None = None
    grounding_note: str | None = Field(default=None, alias="groundingNote")


class CascadeRiskItemResponse(ApiModel):
    direction: str
    source_control_id: str = Field(alias="sourceControlId")
    target_control_id: str = Field(alias="targetControlId")
    target_title: str = Field(alias="targetTitle")
    target_level: str | None = Field(default=None, alias="targetLevel")
    connection_reason: str = Field(alias="connectionReason")
    impact: str
    severity: str
    evidence_label: str | None = Field(default=None, alias="evidenceLabel")
    grounding_level: str | None = Field(default=None, alias="groundingLevel")
    grounding_note: str | None = Field(default=None, alias="groundingNote")
    logic_steps: list[str] = Field(default_factory=list, alias="logicSteps")
    evidence_to_check: list[str] = Field(default_factory=list, alias="evidenceToCheck")
    operational_impact: str | None = Field(default=None, alias="operationalImpact")
    audit_impact: str | None = Field(default=None, alias="auditImpact")


class OfficialCheckItemResponse(ApiModel):
    """인증기준 안내서 주요 확인사항 (확인 질문 레이어)."""

    check_id: str = Field(alias="checkId")
    label: str
    maps_to_check_key: str | None = Field(default=None, alias="mapsToCheckKey")
    source_doc: str = Field(default="ISMS-P 인증기준 안내서(2023.11.23)", alias="sourceDoc")


class CasebookProblemItemResponse(ApiModel):
    """사례집 기반 문제 문장 (판정/영향 레이어)."""

    problem: str
    checklist_item_id: str | None = Field(default=None, alias="checklistItemId")
    check_key: str | None = Field(default=None, alias="checkKey")
    source_ref: str | None = Field(default=None, alias="sourceRef")
    source_doc: str = Field(default="사례집.md", alias="sourceDoc")


class CascadeChainItemResponse(ApiModel):
    origin_control_id: str = Field(alias="originControlId")
    origin_title: str = Field(alias="originTitle")
    origin_level: AssessmentLevel | None = Field(default=None, alias="originLevel")
    origin_level_label: str | None = Field(default=None, alias="originLevelLabel")
    target_control_id: str = Field(alias="targetControlId")
    target_title: str | None = Field(alias="targetTitle")
    target_level: AssessmentLevel | None = Field(default=None, alias="targetLevel")
    target_level_label: str | None = Field(default=None, alias="targetLevelLabel")
    connection_reason: str = Field(alias="connectionReason")
    impact: str
    logic_steps: list[str] = Field(default_factory=list, alias="logicSteps")
    evidence_to_check: list[str] = Field(default_factory=list, alias="evidenceToCheck")
    operational_impact: str | None = Field(default=None, alias="operationalImpact")
    audit_impact: str | None = Field(default=None, alias="auditImpact")
    evidence_label: str | None = Field(default=None, alias="evidenceLabel")
    grounding_note: str | None = Field(default=None, alias="groundingNote")
    grounding_level: str | None = Field(default=None, alias="groundingLevel")
    relation_evidence: list[dict[str, object]] = Field(default_factory=list, alias="relationEvidence")
    source_defect_examples: list[str] = Field(default_factory=list, alias="sourceDefectExamples")
    target_defect_examples: list[str] = Field(default_factory=list, alias="targetDefectExamples")
    validation_criteria: list[str] = Field(default_factory=list, alias="validationCriteria")
    rejection_criteria: list[str] = Field(default_factory=list, alias="rejectionCriteria")
    source_artifacts: list[str] = Field(default_factory=list, alias="sourceArtifacts")
    target_artifacts: list[str] = Field(default_factory=list, alias="targetArtifacts")
    comparison_rows: list[dict[str, str]] = Field(default_factory=list, alias="comparisonRows")
    decision_rule: str = Field(default="", alias="decisionRule")
    severity: str


class MatchedControlSnapshotResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    level: AssessmentLevel
    level_label: str = Field(alias="levelLabel")


class OverlappingRiskBriefResponse(ApiModel):
    bundle_id: str = Field(alias="bundleId")
    title: str
    theme: str
    match_type: str = Field(alias="matchType")
    co_gap_controls: list[MatchedControlSnapshotResponse] = Field(default_factory=list, alias="coGapControls")
    summary: str
    excerpt: str | None = None


class MultiGapOverlapResponse(ApiModel):
    bundle_id: str = Field(alias="bundleId")
    title: str
    theme: str
    source: str = "curated"
    source_label: str = Field(default="수작업 복합 패턴", alias="sourceLabel")
    basis: str = ""
    evidence: list[str] = Field(default_factory=list)
    match_type: str = Field(alias="matchType")
    matched_count: int = Field(alias="matchedCount")
    required_count: int = Field(alias="requiredCount")
    matched_controls: list[MatchedControlSnapshotResponse] = Field(alias="matchedControls")
    control_ids: list[str] = Field(alias="controlIds")
    severity: GapSeverity
    priority_score: int = Field(alias="priorityScore")
    summary: str
    compound_analysis: str = Field(alias="compoundAnalysis")
    operational_impact: str = Field(alias="operationalImpact")
    audit_impact: str = Field(alias="auditImpact")
    incident_scenarios: list[str] = Field(alias="incidentScenarios")
    remediation_path: list[str] = Field(alias="remediationPath")
    overlap_narrative: str = Field(alias="overlapNarrative")
    related_scenario_ids: list[str] = Field(default_factory=list, alias="relatedScenarioIds")


class GapItemResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    category_name: str = Field(alias="categoryName")
    area_name: str = Field(alias="areaName")
    level: AssessmentLevel
    level_label: str = Field(alias="levelLabel")
    severity: GapSeverity
    priority: int
    risk_if_missing: str = Field(alias="riskIfMissing")
    problem: str
    logical_basis: str = Field(alias="logicalBasis")
    expected_issue: str = Field(alias="expectedIssue")
    recommended_actions: list[str] = Field(alias="recommendedActions")
    audit_evidence_needed: list[str] = Field(alias="auditEvidenceNeeded")
    related_control_ids: list[str] = Field(alias="relatedControlIds")
    project_hint: str | None = Field(alias="projectHint")
    control_focus: str | None = Field(default=None, alias="controlFocus")
    checklist_breakdown: list[ChecklistBreakdownItemResponse] = Field(default_factory=list, alias="checklistBreakdown")
    consequence_scenarios: list[str] = Field(default_factory=list, alias="consequenceScenarios")
    cascade_risks: list[CascadeRiskItemResponse] = Field(default_factory=list, alias="cascadeRisks")
    detailed_summary: str | None = Field(default=None, alias="detailedSummary")
    organic_analysis: str | None = Field(default=None, alias="organicAnalysis")
    immediate_actions: list[str] = Field(default_factory=list, alias="immediateActions")
    narrative_report: str | None = Field(default=None, alias="narrativeReport")
    detail_narrative: str | None = Field(default=None, alias="detailNarrative")
    detail_narrative_tip: str | None = Field(default=None, alias="detailNarrativeTip")
    detail_narrative_sources: list[str] = Field(
        default_factory=list,
        alias="detailNarrativeSources",
    )
    evidence_note: str | None = Field(default=None, alias="evidenceNote")
    scenario_relevant: bool = Field(default=False, alias="scenarioRelevant")
    overlapping_risks: list[OverlappingRiskBriefResponse] = Field(default_factory=list, alias="overlappingRisks")
    profile_relevance: list[str] = Field(default_factory=list, alias="profileRelevance")
    profile_priority: int = Field(default=0, alias="profilePriority")
    causal_basis: list[str] = Field(default_factory=list, alias="causalBasis")
    causal_finding_ids: list[str] = Field(default_factory=list, alias="causalFindingIds")
    official_checks: list[OfficialCheckItemResponse] = Field(default_factory=list, alias="officialChecks")
    casebook_problems: list[CasebookProblemItemResponse] = Field(
        default_factory=list,
        alias="casebookProblems",
    )

class DefectEvidenceResponse(ApiModel):
    defect_count: int = Field(default=0, alias="defectCount")
    case_count: int = Field(default=0, alias="caseCount")
    mapped_sources: list[str] = Field(default_factory=list, alias="mappedSources")
    examples: list[str] = Field(default_factory=list)
    source_doc: str | None = Field(default=None, alias="sourceDoc")
    pages: list[int] = Field(default_factory=list)


class GapClusterControlResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    level: AssessmentLevel
    level_label: str = Field(alias="levelLabel")
    next_action: str = Field(default="", alias="nextAction")
    risk_if_missing: str = Field(default="", alias="riskIfMissing")
    selection_reasons: list[str] = Field(default_factory=list, alias="selectionReasons")
    defect_evidence: DefectEvidenceResponse | None = Field(default=None, alias="defectEvidence")


class GapClusterResponse(ApiModel):
    theme: str
    gap_count: int = Field(alias="gapCount")
    none_count: int = Field(default=0, alias="noneCount")
    partial_count: int = Field(default=0, alias="partialCount")
    control_ids: list[str] = Field(alias="controlIds")
    controls: list[GapClusterControlResponse] = Field(default_factory=list)
    primary_control: GapClusterControlResponse | None = Field(default=None, alias="primaryControl")
    summary: str
    severity: str


class ScenarioFocusResponse(ApiModel):
    scenario_id: str = Field(alias="scenarioId")
    title: str
    description: str
    relevant_gap_count: int = Field(alias="relevantGapCount")
    highlighted_control_ids: list[str] = Field(alias="highlightedControlIds")
    unreviewed_candidate_count: int = Field(default=0, alias="unreviewedCandidateCount")


class CertPhaseHintResponse(ApiModel):
    phase_id: str = Field(alias="phaseId")
    title: str
    summary: str
    related_control_ids: list[str] = Field(alias="relatedControlIds")


class ReportSectionResponse(ApiModel):
    id: str
    title: str
    content: str


class ReportDocumentRequest(ApiModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=200_000)


class AccessPassRegisterRequest(ApiModel):
    token: str = Field(min_length=16, max_length=200)


class AccessPassStatusResponse(ApiModel):
    required: bool
    workspace_required: bool = Field(alias="workspaceRequired")
    active: bool
    remaining_seconds: int | None = Field(default=None, alias="remainingSeconds")
    expires_at: str | None = Field(default=None, alias="expiresAt")
    duration_days: int | None = Field(default=None, alias="durationDays")
    kind: str | None = None


class AdminLoginRequest(ApiModel):
    password: str = Field(min_length=1, max_length=200)


class AdminSessionResponse(ApiModel):
    configured: bool
    authenticated: bool


class AdminPassIssueRequest(ApiModel):
    kind: Literal["timed", "invite"] = "timed"
    duration_days: int | None = Field(default=None, alias="durationDays")
    note: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def normalize_issue_kind(self) -> "AdminPassIssueRequest":
        if self.kind == "invite":
            self.duration_days = None
            return self
        days = 7 if self.duration_days is None else int(self.duration_days)
        if days < 1 or days > 90:
            raise ValueError("기간권은 1일에서 90일까지 발급할 수 있습니다.")
        self.duration_days = days
        return self


class AdminPassNoteRequest(ApiModel):
    note: str = Field(default="", max_length=80)


class AdminPassRecordResponse(ApiModel):
    id: str
    token: str = ""
    note: str = ""
    kind: str = "timed"
    duration_days: int | None = Field(default=None, alias="durationDays")
    created_at: str | None = Field(default=None, alias="createdAt")
    activated_at: str | None = Field(default=None, alias="activatedAt")
    expires_at: str | None = Field(default=None, alias="expiresAt")
    revoked_at: str | None = Field(default=None, alias="revokedAt")
    status: str
    remaining_seconds: int = Field(default=0, alias="remainingSeconds")


class AdminPassListResponse(ApiModel):
    passes: list[AdminPassRecordResponse]


class AdminPassIssueResponse(ApiModel):
    token: str
    record: AdminPassRecordResponse


class AdminPassBulkDeleteRequest(ApiModel):
    ids: list[str] = Field(default_factory=list)
    delete_all: bool = Field(default=False, alias="deleteAll")


class AdminPassBulkDeleteResponse(ApiModel):
    deleted: int


class ReportRewriteRequest(ApiModel):
    text: str = Field(min_length=1, max_length=8_000)
    mode: Literal[
        "diagnostic_intro", "result_interpretation", "improvement_plan", "executive_brief"
    ] = "result_interpretation"


class ReportRewriteResponse(ApiModel):
    original: str
    suggestion: str
    applied: bool
    provider: str
    reason: str


class RecommendationResponse(ApiModel):
    priority: str
    title: str
    detail: str


class EvaluationBandItemResponse(ApiModel):
    category: str
    category_id: str = Field(default="", alias="categoryId")
    area_id: str | None = Field(default=None, alias="areaId")
    area_name: str | None = Field(default=None, alias="areaName")
    band: Literal["strength", "weakness", "deferred"] = "deferred"
    reviewed_count: int = Field(default=0, alias="reviewedCount")
    total_count: int = Field(default=0, alias="totalCount")
    coverage_percent: float = Field(default=0, alias="coveragePercent")
    status_counts: dict[str, int] = Field(default_factory=dict, alias="statusCounts")


class EvaluationBandsResponse(ApiModel):
    strengths: list[EvaluationBandItemResponse] = Field(default_factory=list)
    weaknesses: list[EvaluationBandItemResponse] = Field(default_factory=list)
    deferred: list[EvaluationBandItemResponse] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class WeakCategoryResponse(ApiModel):
    category: str
    category_id: str | None = Field(default=None, alias="categoryId")
    area_id: str | None = Field(default=None, alias="areaId")
    area_name: str | None = Field(default=None, alias="areaName")
    score: float
    qualitative_label: str | None = Field(default=None, alias="qualitativeLabel")
    count: int
    reviewed_count: int | None = Field(default=None, alias="reviewedCount")
    coverage_percent: float | None = Field(default=None, alias="coveragePercent")
    first_control_id: str | None = Field(default=None, alias="firstControlId")
    status_counts: dict[str, int] = Field(default_factory=dict, alias="statusCounts")


class AreaCoverageResponse(ApiModel):
    reviewed_count: int = Field(alias="reviewedCount")
    total_count: int = Field(alias="totalCount")
    coverage_percent: float = Field(alias="coveragePercent")


class CategoryCoverageResponse(ApiModel):
    category: str
    category_id: str = Field(alias="categoryId")
    area_id: str = Field(alias="areaId")
    area_name: str = Field(alias="areaName")
    reviewed_count: int = Field(alias="reviewedCount")
    total_count: int = Field(alias="totalCount")
    coverage_percent: float = Field(alias="coveragePercent")
    status_counts: dict[str, int] = Field(default_factory=dict, alias="statusCounts")


class ReviewStatResponse(ApiModel):
    label: str
    value: int | float | str
    tone: str | None = None
    tooltip: str | None = None


class ReviewActionResponse(ApiModel):
    type: str
    label: str
    control_id: str = Field(default="", alias="controlId")


class ReviewPathNodeResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    role: str
    level: AssessmentLevel | None = None
    level_label: str | None = Field(default=None, alias="levelLabel")


class ReviewControlNodeResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    level: AssessmentLevel | None = None
    level_label: str | None = Field(default=None, alias="levelLabel")


class ReviewItemResponse(ApiModel):
    id: str
    kind: str
    classification: str
    title: str
    headline: str
    metric: int | float | str | None = None
    metric_unit: str | None = Field(default=None, alias="metricUnit")
    metric_label: str | None = Field(default=None, alias="metricLabel")
    coverage_percent: float | None = Field(default=None, alias="coveragePercent")
    stats: list[ReviewStatResponse] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
    path: list[str] = Field(default_factory=list)
    path_nodes: list[ReviewPathNodeResponse] = Field(default_factory=list, alias="pathNodes")
    control_nodes: list[ReviewControlNodeResponse] = Field(
        default_factory=list,
        alias="controlNodes",
    )
    route_label: str | None = Field(default=None, alias="routeLabel")
    relation_label: str | None = Field(default=None, alias="relationLabel")
    question: str
    explanation: str
    next_action: str | None = Field(default=None, alias="nextAction")
    basis: list[str] = Field(default_factory=list)
    confidence_level: str = Field(alias="confidenceLevel")
    confidence_label: str = Field(alias="confidenceLabel")
    action: ReviewActionResponse | None = None


class CausalBecauseResponse(ApiModel):
    kind: str
    control_id: str | None = Field(default=None, alias="controlId")
    checklist_item_id: str | None = Field(default=None, alias="checklistItemId")
    checklist_item: str | None = Field(default=None, alias="checklistItem")
    check_key: str | None = Field(default=None, alias="checkKey")
    level: AssessmentLevel | None = None
    label: str | None = None
    mapping_mode: str | None = Field(default=None, alias="mappingMode")


class CausalImpactResponse(ApiModel):
    type: Literal["operational", "audit"]
    text: str


class CausalMayCauseResponse(ApiModel):
    target_control_id: str = Field(alias="targetControlId")
    reason: str
    relation_source: str = Field(alias="relationSource")
    target_level: AssessmentLevel | None = Field(default=None, alias="targetLevel")


class CasebookSourceRefResponse(ApiModel):
    doc: str = "사례집.md"
    control_id: str = Field(alias="controlId")
    case_no: int = Field(alias="caseNo")
    ref: str


class CausalFindingResponse(ApiModel):
    finding_id: str = Field(alias="findingId")
    control_id: str = Field(alias="controlId")
    title: str
    level: AssessmentLevel
    checklist_item_id: str = Field(default="", alias="checklistItemId")
    checklist_item: str = Field(default="", alias="checklistItem")
    problem: str = ""
    problems: list[str] = Field(default_factory=list)
    remediation: str = ""
    operational_impact: str = Field(default="", alias="operationalImpact")
    audit_impact: str = Field(default="", alias="auditImpact")
    severity: GapSeverity
    source: str
    mapping_mode: str = Field(default="maturity_proxy", alias="mappingMode")
    because: list[CausalBecauseResponse] = Field(default_factory=list)
    impacts: list[CausalImpactResponse] = Field(default_factory=list)
    may_cause: list[CausalMayCauseResponse] = Field(default_factory=list, alias="mayCause")
    risk_alternatives: list[str] = Field(default_factory=list, alias="riskAlternatives")
    causal_statement: str = Field(default="", alias="causalStatement")
    source_refs: list[CasebookSourceRefResponse] = Field(default_factory=list, alias="sourceRefs")


class IndividualProblemResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    title: str
    level: AssessmentLevel
    checklist_item_id: str = Field(alias="checklistItemId")
    checklist_item: str = Field(alias="checklistItem")
    problems: list[str]
    remediation: str
    operational_impact: str = Field(default="", alias="operationalImpact")
    audit_impact: str = Field(default="", alias="auditImpact")
    severity: GapSeverity
    source: str
    finding_id: str | None = Field(default=None, alias="findingId")
    problem: str | None = None
    mapping_mode: str | None = Field(default=None, alias="mappingMode")
    because: list[CausalBecauseResponse] = Field(default_factory=list)
    impacts: list[CausalImpactResponse] = Field(default_factory=list)
    may_cause: list[CausalMayCauseResponse] = Field(default_factory=list, alias="mayCause")
    risk_alternatives: list[str] = Field(default_factory=list, alias="riskAlternatives")
    causal_statement: str | None = Field(default=None, alias="causalStatement")
    source_refs: list[CasebookSourceRefResponse] = Field(default_factory=list, alias="sourceRefs")


class CompoundBecauseChecklistRefResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    checklist_item_id: str = Field(default="", alias="checklistItemId")
    checklist_item: str = Field(default="", alias="checklistItem")


class CompoundSynthesisResponse(ApiModel):
    cluster_id: str = Field(alias="clusterId")
    control_ids: list[str] = Field(alias="controlIds")
    matched_compound_key: str | None = Field(default=None, alias="matchedCompoundKey")
    individual_problem_count: int = Field(alias="individualProblemCount")
    compound_problems: list[str] = Field(alias="compoundProblems")
    compound_scenarios: list[str] = Field(alias="compoundScenarios")
    connection_reasons: list[str] = Field(alias="connectionReasons")
    integrated_remediation: list[str] = Field(alias="integratedRemediation")
    synthesis_narrative: str = Field(alias="synthesisNarrative")
    because: list[CausalBecauseResponse] = Field(default_factory=list)
    because_checklist_refs: list[CompoundBecauseChecklistRefResponse] = Field(
        default_factory=list,
        alias="becauseChecklistRefs",
    )
    causal_statement: str | None = Field(default=None, alias="causalStatement")
    evidence_grade: str | None = Field(default=None, alias="evidenceGrade")
    evidence_refs: list[dict[str, object]] = Field(default_factory=list, alias="evidenceRefs")
    evidence_labels: list[str] = Field(default_factory=list, alias="evidenceLabels")
    grounding_level: str | None = Field(default=None, alias="groundingLevel")
    grounding_note: str | None = Field(default=None, alias="groundingNote")


class IntegratedGuidanceResponse(ApiModel):
    summary: str
    prioritized_actions: list[str] = Field(alias="prioritizedActions")
    executive_narrative: str = Field(alias="executiveNarrative")


class ProblemAnalysisStatsResponse(ApiModel):
    kb_version: int = Field(alias="kbVersion")
    total_controls_in_kb: int = Field(alias="totalControlsInKb")
    total_compound_rules: int = Field(alias="totalCompoundRules")
    weak_control_count: int = Field(alias="weakControlCount")
    individual_problem_count: int = Field(alias="individualProblemCount")
    causal_finding_count: int = Field(default=0, alias="causalFindingCount")
    compound_cluster_count: int = Field(alias="compoundClusterCount")
    checklist_derived_count: int = Field(alias="checklistDerivedCount")


class ProblemAnalysisResponse(ApiModel):
    individual_problems: list[IndividualProblemResponse] = Field(alias="individualProblems")
    causal_findings: list[CausalFindingResponse] = Field(default_factory=list, alias="causalFindings")
    compound_syntheses: list[CompoundSynthesisResponse] = Field(alias="compoundSyntheses")
    integrated_guidance: IntegratedGuidanceResponse = Field(alias="integratedGuidance")
    stats: ProblemAnalysisStatsResponse


class VerbalizeMetaResponse(ApiModel):
    requested: bool
    applied: bool
    provider: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    invented_control_ids: list[str] = Field(default_factory=list, alias="inventedControlIds")
    mode: str = "template"
    model: str | None = None
    latency_ms: int | None = Field(default=None, alias="latencyMs")
    max_gaps: int | None = Field(default=None, alias="maxGaps")
    sample_count: int | None = Field(default=None, alias="sampleCount")
    include_quests: bool | None = Field(default=None, alias="includeQuests")


class DetailNarrativeItemResponse(ApiModel):
    control_id: str = Field(alias="controlId")
    summary_tip: str = Field(default="", alias="summaryTip")
    detail: str = ""
    mode: str = "template"
    sources: list[str] = Field(default_factory=list)


class DetailNarrativeMetaResponse(ApiModel):
    requested: bool = False
    applied: bool = False
    provider: str = "none"
    mode: str = "template"
    control_count: int = Field(default=0, alias="controlCount")
    reasons: list[str] = Field(default_factory=list)
    invented_control_ids: list[str] = Field(default_factory=list, alias="inventedControlIds")
    latency_ms: int | None = Field(default=None, alias="latencyMs")
    model: str | None = None
    confidence: float | None = None


class PipelineMetaResponse(ApiModel):
    stages: list[str] = Field(default_factory=list)
    view: str = "full"
    verbalize_max_gaps: int = Field(default=12, alias="verbalizeMaxGaps")
    verbalize_include_quests: bool = Field(default=True, alias="verbalizeIncludeQuests")


class PriorityQuestMetaResponse(ApiModel):
    shown: int = 0
    candidates: int = 0
    limit: int = 10
    gap_count: int = Field(default=0, alias="gapCount")


class ConfirmationActionMetaResponse(ApiModel):
    shown: int = 0
    candidates: int = 0
    limit: int = 10
    mode: Literal["area", "chain", "theme"] = "chain"
    bundle_title: str = Field(default="", alias="bundleTitle")
    bundle_summary: str = Field(default="", alias="bundleSummary")
    area_label: str | None = Field(default=None, alias="areaLabel")
    theme_id: str | None = Field(default=None, alias="themeId")
    chain_path: list[str] = Field(default_factory=list, alias="chainPath")


class AssessResponse(ApiModel):
    overall_readiness: float = Field(alias="overallReadiness")
    readiness_label: str = Field(alias="readinessLabel")
    score_disclaimer: str | None = Field(default=None, alias="scoreDisclaimer")
    score_weight_summary: str | None = Field(default=None, alias="scoreWeightSummary")
    overall_score_tooltip: str | None = Field(default=None, alias="overallScoreTooltip")
    assessed_score_tooltip: str | None = Field(default=None, alias="assessedScoreTooltip")
    assessed_readiness: float | None = Field(default=None, alias="assessedReadiness")
    assessed_readiness_label: str | None = Field(default=None, alias="assessedReadinessLabel")
    assessment_completion_percent: float = Field(default=0, alias="assessmentCompletionPercent")
    reviewed_control_count: int = Field(default=0, alias="reviewedControlCount")
    unreviewed_control_count: int = Field(default=0, alias="unreviewedControlCount")
    status_counts: dict[str, int] = Field(alias="statusCounts")
    area_readiness: dict[str, float] = Field(alias="areaReadiness")
    area_coverage: dict[str, AreaCoverageResponse] = Field(
        default_factory=dict,
        alias="areaCoverage",
    )
    category_coverage: list[CategoryCoverageResponse] = Field(
        default_factory=list,
        alias="categoryCoverage",
    )
    weak_categories: list[WeakCategoryResponse] = Field(alias="weakCategories")
    evaluation_bands: EvaluationBandsResponse | None = Field(
        default=None,
        alias="evaluationBands",
    )
    gap_count: int = Field(alias="gapCount")
    analysis_candidate_count: int = Field(default=0, alias="analysisCandidateCount")
    critical_gaps: list[GapItemResponse] = Field(alias="criticalGaps")
    top_gaps: list[GapItemResponse] = Field(alias="topGaps")
    confirmed_gaps: list[GapItemResponse] = Field(default_factory=list, alias="confirmedGaps")
    cascade_chains: list[CascadeChainItemResponse] = Field(default_factory=list, alias="cascadeChains")
    recommendations: list[RecommendationResponse]
    portfolio_summary: str = Field(alias="portfolioSummary")
    key_insights: list[str] = Field(default_factory=list, alias="keyInsights")
    review_items: list[ReviewItemResponse] = Field(default_factory=list, alias="reviewItems")
    executive_report: str | None = Field(default=None, alias="executiveReport")
    report_sections: list[ReportSectionResponse] = Field(default_factory=list, alias="reportSections")
    gap_clusters: list[GapClusterResponse] = Field(default_factory=list, alias="gapClusters")
    multi_gap_overlaps: list[MultiGapOverlapResponse] = Field(default_factory=list, alias="multiGapOverlaps")
    scenario_focus: ScenarioFocusResponse | None = Field(default=None, alias="scenarioFocus")
    cert_phase_hint: CertPhaseHintResponse | None = Field(default=None, alias="certPhaseHint")
    problem_analysis: ProblemAnalysisResponse | None = Field(default=None, alias="problemAnalysis")
    profile_context: OrganizationProfileResponse | None = Field(default=None, alias="profileContext")
    scope_draft: ScopeDraftResponse | None = Field(default=None, alias="scopeDraft")
    suggested_scenario_ids: list[str] = Field(default_factory=list, alias="suggestedScenarioIds")
    minimum_evidence_pack: MinimumEvidencePackResponse | None = Field(
        default=None,
        alias="minimumEvidencePack",
    )
    verbalize_meta: VerbalizeMetaResponse | None = Field(default=None, alias="verbalizeMeta")
    detail_narratives: dict[str, DetailNarrativeItemResponse] = Field(
        default_factory=dict,
        alias="detailNarratives",
    )
    detail_narrative_meta: DetailNarrativeMetaResponse | None = Field(
        default=None,
        alias="detailNarrativeMeta",
    )
    pipeline_meta: PipelineMetaResponse | None = Field(default=None, alias="pipelineMeta")
    confirmation_actions: list[ConfirmationActionResponse] = Field(
        default_factory=list,
        alias="confirmationActions",
    )
    confirmation_action_meta: ConfirmationActionMetaResponse | None = Field(
        default=None,
        alias="confirmationActionMeta",
    )
    control_session_details: dict[str, ControlSessionDetailResponse] = Field(
        default_factory=dict,
        alias="controlSessionDetails",
    )
    input_confidence_summary: InputConfidenceSummaryResponse | None = Field(
        default=None,
        alias="inputConfidenceSummary",
    )
    applicability_notes: list[ApplicabilityNoteResponse] = Field(
        default_factory=list,
        alias="applicabilityNotes",
    )
    priority_quests: list[PriorityQuestResponse] = Field(
        default_factory=list,
        alias="priorityQuests",
    )
    priority_quest_meta: PriorityQuestMetaResponse | None = Field(
        default=None,
        alias="priorityQuestMeta",
    )
    applicable_control_count: int | None = Field(default=None, alias="applicableControlCount")
    na_control_count: int | None = Field(default=None, alias="naControlCount")
    institution_hints: InstitutionGuideResponse | None = Field(
        default=None,
        alias="institutionHints",
    )
    simple_cert_hints: SimpleCertHintsResponse | None = Field(
        default=None,
        alias="simpleCertHints",
    )
