export const STORAGE_KEY = "isms-p-portfolio-assessment-v1";
export const CHECK_STORAGE_KEY = "isms-p-portfolio-checks-v2";
export const DOMAIN_STORAGE_KEY = "isms-p-portfolio-domain-checks-v1";
export const QUEST_STORAGE_KEY = "isms-p-quest-checks-v1";
export const EVIDENCE_STORAGE_KEY = "isms-p-control-evidence-v1";
export const CONFIDENCE_STORAGE_KEY = "isms-p-input-confidence-v1";
export const ANALYSIS_HISTORY_KEY = "isms-p-analysis-history-v1";
export const REPORT_REVIEW_STORAGE_KEY = "isms-p-report-review-v1";
export const PROFILE_STORAGE_KEY = "isms-p-organization-profile-v1";
export const DIAGNOSIS_SESSIONS_STORAGE_KEY = "isms-p-diagnosis-sessions-v1";

export const LEVEL_LABEL = {
  unknown: "미점검",
  none: "미이행",
  partial: "부분 이행",
  done: "이행",
  evidenced: "이행", // 레거시 저장값 → 이행으로 표시
  na: "해당 없음",
};

export const CHECK_LABEL = {
  reviewed: "검토",
  policy: "정책",
  implemented: "구현",
  evidence: "증적",
};
export const CHECK_LABEL_FULL = {
  reviewed: "검토",
  policy: "정책/절차",
  implemented: "구현/운영",
  evidence: "증적",
};

export const AREA_SHORT = {
  "1": "관리체계",
  "2": "보호대책",
  "3": "개인정보",
};

export const INPUT_CONF_LABEL = {
  unknown: "모름",
  assumed: "추정",
  confirmed: "확인됨",
};

export const HERO_LEDE = {
  assess: "물리 통제(전산실) 적용 여부만 고르면 됩니다. 인증 맞춤이 아니라 점검 범위 설정입니다.",
  analyze: "왼쪽 통제 항목에서 항목을 고르고, 오른쪽 카드에 진단 상태를 남기세요.",
};
export const PAGE_TITLE = {
  assess: "점검 범위",
  analyze: "자가진단",
};
export const PAGE_KICKER = {
  assess: "1단계 · 범위",
  analyze: "2단계 · 진단",
};

/** UI에 노출하지 않는 기본값. 우선순위/시나리오 내부 힌트용이며 사용자 맞춤 입력이 아님. */
export const SME_DEFAULT_PROFILE = {
  headcountBand: "1-50",
  industry: "technology",
  piiVolume: "low",
  usesCloud: true,
  hasOnPremFacility: false,
  usesOutsourcing: false,
  usesRemoteAccess: false,
  processesRrn: false,
};
