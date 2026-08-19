export function formatPassRemaining(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (days > 0) return `${days}일 ${hours}시간 남음`;
  if (hours > 0) return `${hours}시간 ${minutes}분 남음`;
  if (minutes > 0) return `${minutes}분 남음`;
  return "1분 미만 남음";
}

export function remainingFromExpires(expiresAt, now = Date.now()) {
  if (!expiresAt) return 0;
  const expiry = Date.parse(expiresAt);
  if (Number.isNaN(expiry)) return 0;
  return Math.max(0, Math.floor((expiry - now) / 1000));
}

function el(id) {
  return document.getElementById(id);
}

let passStatus = {
  required: true,
  active: false,
  remainingSeconds: 0,
  expiresAt: null,
  durationDays: null,
};
let tickTimer = 0;
let registerResolver = null;

function applyChip() {
  const chip = el("pageHeadPass");
  const label = el("pageHeadPassLabel");
  const meta = el("pageHeadPassMeta");
  if (!chip || !label || !meta) return;
  if (!passStatus.required) {
    chip.hidden = true;
    return;
  }
  chip.hidden = false;
  const remaining = remainingFromExpires(passStatus.expiresAt);
  const active = remaining > 0;
  chip.classList.toggle("is-active", active);
  chip.classList.toggle("is-expired", passStatus.expiresAt && !active);
  chip.classList.toggle("is-empty", !passStatus.expiresAt && !active);
  label.textContent = "AI 사용권";
  if (active) {
    meta.textContent = formatPassRemaining(remaining);
    chip.setAttribute("aria-label", `AI 사용권 ${formatPassRemaining(remaining)}`);
    return;
  }
  if (passStatus.expiresAt) {
    meta.textContent = "만료됨";
    chip.setAttribute("aria-label", "AI 사용권이 만료되었습니다. 다시 등록하세요.");
    return;
  }
  meta.textContent = "미등록";
  chip.setAttribute("aria-label", "AI 사용권을 등록하세요.");
}

function scheduleTick() {
  window.clearInterval(tickTimer);
  if (!passStatus.required || !passStatus.expiresAt) return;
  const remaining = remainingFromExpires(passStatus.expiresAt);
  if (remaining <= 0) {
    passStatus = { ...passStatus, active: false, remainingSeconds: 0 };
    applyChip();
    return;
  }
  const interval = remaining < 3600 ? 1000 : 30000;
  tickTimer = window.setInterval(() => {
    applyChip();
    if (remainingFromExpires(passStatus.expiresAt) <= 0) {
      window.clearInterval(tickTimer);
      refreshAccessPassStatus();
    }
  }, interval);
}

export async function refreshAccessPassStatus() {
  try {
    const response = await fetch("/access/status", { credentials: "same-origin" });
    if (!response.ok) throw new Error("status");
    passStatus = await response.json();
  } catch (_) {
    passStatus = {
      required: true,
      active: false,
      remainingSeconds: 0,
      expiresAt: null,
      durationDays: null,
    };
  }
  applyChip();
  scheduleTick();
  return passStatus;
}

function closeAccessPassDialog(result = false) {
  const dialog = el("accessPassDialog");
  dialog?.close();
  if (registerResolver) {
    const resolve = registerResolver;
    registerResolver = null;
    resolve(result);
  }
}

function bindAccessPassDialog() {
  const dialog = el("accessPassDialog");
  const form = el("accessPassForm");
  const input = el("accessPassInput");
  const errorEl = el("accessPassError");
  if (!dialog || !form || form.dataset.bound === "1") return;
  form.dataset.bound = "1";
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeAccessPassDialog(false);
  });
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeAccessPassDialog(false);
  });
  el("accessPassCancelBtn")?.addEventListener("click", () => closeAccessPassDialog(false));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const token = String(input?.value || "").trim();
    if (errorEl) errorEl.hidden = true;
    if (token.length < 16) {
      if (errorEl) {
        errorEl.hidden = false;
        errorEl.textContent = "사용권 문자열을 그대로 붙여넣으세요.";
      }
      input?.focus();
      return;
    }
    const submit = el("accessPassSubmitBtn");
    if (submit) submit.disabled = true;
    try {
      const response = await fetch("/access/register", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "사용권을 등록하지 못했습니다.");
      }
      passStatus = payload;
      applyChip();
      scheduleTick();
      if (input) input.value = "";
      closeAccessPassDialog(true);
    } catch (error) {
      if (errorEl) {
        errorEl.hidden = false;
        errorEl.textContent = error.message || "사용권을 등록하지 못했습니다.";
      }
    } finally {
      if (submit) submit.disabled = false;
    }
  });
}

export function openAccessPassDialog() {
  bindAccessPassDialog();
  const dialog = el("accessPassDialog");
  const input = el("accessPassInput");
  const errorEl = el("accessPassError");
  if (!dialog) return Promise.resolve(false);
  if (errorEl) errorEl.hidden = true;
  if (dialog.open) return registerResolver ? new Promise((resolve) => {
    const previous = registerResolver;
    registerResolver = (result) => {
      previous(result);
      resolve(result);
    };
  }) : Promise.resolve(false);
  return new Promise((resolve) => {
    registerResolver = resolve;
    dialog.showModal();
    input?.focus();
    input?.select();
  });
}

export async function ensureAccessPass() {
  const status = await refreshAccessPassStatus();
  if (!status.required || status.active) return true;
  return openAccessPassDialog();
}

export function initAccessPass() {
  bindAccessPassDialog();
  el("pageHeadPass")?.addEventListener("click", () => {
    openAccessPassDialog();
  });
  window.addEventListener("access-pass:required", () => {
    openAccessPassDialog();
  });
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const response = await nativeFetch(input, init);
    try {
      const url = String(typeof input === "string" ? input : input?.url || "");
      const path = new URL(url, window.location.origin).pathname;
      if (
        response.status === 403
        && (path === "/controls/report" || path === "/controls/report/rewrite")
      ) {
        window.dispatchEvent(new CustomEvent("access-pass:required"));
      }
    } catch (_) {
      /* ignore URL parse errors */
    }
    return response;
  };
  refreshAccessPassStatus();
}
