import { SME_DEFAULT_PROFILE } from "../../core/constants.js";
import { el, escapeHtml } from "../../core/dom.js";
import { state } from "../../core/state.js";

export function readProfileForm() {
  // usesCloud / hasOnPremFacility만 사용자 입력. 나머지는 dormant 기본값.
  return {
    headcountBand: el("profileHeadcount")?.value || SME_DEFAULT_PROFILE.headcountBand,
    industry: el("profileIndustry")?.value || SME_DEFAULT_PROFILE.industry,
    piiVolume: el("profilePiiVolume")?.value || SME_DEFAULT_PROFILE.piiVolume,
    usesCloud: !!el("profileCloud")?.checked,
    hasOnPremFacility: !!el("profileOnPrem")?.checked,
    usesOutsourcing: false,
    usesRemoteAccess: false,
    processesRrn: false,
  };
}

export function hasSelectedEnvironment(profile = readProfileForm()) {
  return Boolean(profile?.usesCloud || profile?.hasOnPremFacility);
}

export function fillProfileForm(profile) {
  const value = { ...SME_DEFAULT_PROFILE, ...(profile || {}) };
  if (el("profileHeadcount")) el("profileHeadcount").value = value.headcountBand || "1-50";
  if (el("profileIndustry")) el("profileIndustry").value = value.industry || "technology";
  if (el("profilePiiVolume")) el("profilePiiVolume").value = value.piiVolume || "low";
  if (el("profileCloud")) el("profileCloud").checked = Boolean(value.usesCloud);
  if (el("profileOnPrem")) el("profileOnPrem").checked = Boolean(value.hasOnPremFacility);
}

export function profileImpactSummary(profile) {
  const value = profile || readProfileForm();
  if (value.usesCloud && !value.hasOnPremFacility) {
    return [
      "바뀌는 결과: 물리/전산실 통제 6개(2.4.1~2.4.6)만 N/A.",
      "나머지 통제는 그대로 점검 대상입니다.",
    ];
  }
  if (value.usesCloud && value.hasOnPremFacility) {
    return [
      "바뀌는 결과: 물리 통제도 점검 대상(N/A 없음).",
      "클라우드·전산실을 함께 운영하는 범위로 둡니다.",
    ];
  }
  if (!value.usesCloud && value.hasOnPremFacility) {
    return [
      "바뀌는 결과: 자체 전산실 기준으로 물리 통제를 점검.",
      "N/A 규칙은 적용되지 않습니다.",
    ];
  }
  return [
    "운영 환경을 아직 고르지 않았습니다.",
    "클라우드 또는 자체 인프라를 하나 이상 선택하세요.",
  ];
}

export function renderProfileImpact() {
  const box = el("profileImpact");
  if (!box) return;
  const profile = readProfileForm();
  const selected = hasSelectedEnvironment(profile);
  const total = state.checklist?.length || 101;
  const na = selected && profile.usesCloud && !profile.hasOnPremFacility ? 6 : 0;
  const items = profileImpactSummary(profile)
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");
  box.classList.toggle("is-incomplete", !selected);
  box.innerHTML = selected
    ? `
    <div class="profile-impact-head"><span>적용 결과</span><em>${na ? `${na}개 통제 제외` : "전체 통제 적용"}</em></div>
    <strong>${na ? "운영 환경에 맞춰 범위를 조정했습니다" : "전체 통제를 점검합니다"}</strong>
    <dl class="profile-impact-metrics">
      <div><dt>전체 통제</dt><dd>${total}</dd></div>
      <div><dt>적용</dt><dd>${Math.max(total - na, 0)}</dd></div>
      <div><dt>N/A</dt><dd>${na}</dd></div>
    </dl>
    <div class="profile-impact-bar" aria-label="적용 통제 ${Math.max(total - na, 0)}개"><i style="width:${total ? Math.round(((total - na) / total) * 100) : 0}%"></i></div>
    <ul>${items}</ul>`
    : `
    <div class="profile-impact-head"><span>적용 결과</span><em>환경 미선택</em></div>
    <strong>운영 환경을 선택하세요</strong>
    <ul>${items}</ul>`;
  syncProfileSubmit(selected);
}

export function syncProfileSubmit(selected = hasSelectedEnvironment()) {
  const button = el("applyProfileBtn");
  if (!button) return;
  button.disabled = !selected;
}

export function syncAssessLayout() {
  const view = el("view-assess");
  if (!view) return;
  const ready = !!state.organizationProfile;
  view.classList.toggle("is-prestart", !ready);
  view.classList.toggle("is-ready", ready);
}

export function openProfilePanel({ focus = true } = {}) {
  const panel = el("profileInline");
  if (!panel) return;
  panel.classList.add("open");
  fillProfileForm(state.organizationProfile);
  el("profileForm").style.display = "";
  el("profileLede").style.display = "";
  el("profileTitle").textContent = state.organizationProfile ? "진단 환경 수정" : "현재 운영 환경을 선택하세요";
  renderProfileImpact();
  if (focus) {
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => el("profileCloud")?.focus(), 0);
  }
  syncAssessLayout();
}

export function closeProfilePanel() {
  const panel = el("profileInline");
  if (!panel) return;
  if (!state.organizationProfile) {
    panel.classList.add("open");
    syncAssessLayout();
    return;
  }
  panel.classList.remove("open");
  syncAssessLayout();
}

export function renderProfileContext() {
  const panel = el("profileContextPanel");
  if (!panel) return;
  if (!state.organizationProfile) {
    panel.innerHTML = `<strong>아직 점검 범위 설정 전입니다.</strong><div class="profile-context-chips"><span>클라우드만 쓰면 물리 6개가 N/A가 됩니다.</span></div>`;
    return;
  }
  const profile = state.organizationProfile;
  const impact = profileImpactSummary(profile);
  const chips = [
    profile.usesCloud && !profile.hasOnPremFacility ? "물리 6개 N/A" : null,
    profile.usesCloud ? "클라우드" : null,
    profile.hasOnPremFacility ? "자체전산실" : null,
    !profile.usesCloud && !profile.hasOnPremFacility ? "N/A 없음" : null,
  ].filter(Boolean);
  panel.innerHTML = `
    <strong>현재 점검 범위</strong>
    <div class="profile-context-chips">${chips.map((chip) => `<span>${escapeHtml(String(chip))}</span>`).join("")}</div>
    <p class="panel-desc" style="margin:8px 0 0;">${escapeHtml(impact[0] || "")}</p>
  `;
}
