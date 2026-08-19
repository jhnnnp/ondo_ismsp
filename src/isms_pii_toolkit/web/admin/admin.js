const STATUS_LABEL = {
  unused: "미등록",
  active: "사용 중",
  expired: "만료",
  revoked: "회수",
};

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatRemaining(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  if (!total) return "-";
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  if (days > 0) return `${days}일 ${hours}시간`;
  const minutes = Math.floor((total % 3600) / 60);
  if (hours > 0) return `${hours}시간 ${minutes}분`;
  return minutes > 0 ? `${minutes}분` : "1분 미만";
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  const parts = new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type)?.value || "";
  return `${get("month")}.${get("day")} ${get("hour")}:${get("minute")}`;
}

const ADMIN_BASE = String(window.ADMIN_BASE || "").replace(/\/$/, "");

function adminUrl(suffix) {
  const path = suffix.startsWith("/") ? suffix : `/${suffix}`;
  return `${ADMIN_BASE}${path}`;
}

async function api(path, options = {}) {
  const response = await fetch(adminUrl(path), {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "요청을 처리하지 못했습니다.");
  }
  return payload;
}

function show(id, visible) {
  const node = el(id);
  if (node) node.hidden = !visible;
}

function setMode(mode) {
  document.body.classList.toggle("is-login", mode === "login");
}

function tokenCell(token) {
  const value = String(token || "").trim();
  if (!value) return '<span class="token-missing">이전 발급분</span>';
  return `
    <div class="token-row">
      <code title="${escapeHtml(value)}">${escapeHtml(value)}</code>
      <button type="button" data-copy-token="${escapeHtml(value)}">복사</button>
    </div>
  `;
}

function renderPasses(passes) {
  const body = el("passTableBody");
  const count = el("passCount");
  if (count) count.textContent = `${passes.length}건`;
  if (!body) return;
  if (!passes.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8">발급된 사용권이 없습니다.</td></tr>';
    return;
  }
  body.innerHTML = passes.map((item) => {
    const revoked = item.status === "revoked";
    const note = escapeHtml(item.note);
    return `
      <tr data-pass-id="${item.id}">
        <td class="col-note"><input class="note-input" data-note-input value="${note}" maxlength="80" placeholder="메모 없음" aria-label="메모"></td>
        <td class="col-token token-cell">${tokenCell(item.token)}</td>
        <td class="col-status"><span class="status status-${item.status}">${STATUS_LABEL[item.status] || item.status}</span></td>
        <td class="col-remain">${formatRemaining(item.remainingSeconds)}</td>
        <td class="col-days">${item.durationDays || "-"}일</td>
        <td class="col-date">${formatDate(item.createdAt)}</td>
        <td class="col-date">${formatDate(item.activatedAt)}</td>
        <td class="col-action row-actions"><button type="button" class="revoke-btn" data-revoke ${revoked ? "disabled" : ""}>${revoked ? "회수됨" : "회수"}</button></td>
      </tr>
    `;
  }).join("");
}

async function copyText(value, button) {
  const token = String(value || "").trim();
  if (!token) return;
  await navigator.clipboard.writeText(token);
  if (!button) return;
  const previous = button.textContent;
  button.textContent = "복사됨";
  window.setTimeout(() => {
    button.textContent = previous;
  }, 1200);
}

async function refreshPasses() {
  const payload = await api("/passes");
  renderPasses(payload.passes || []);
}

async function showDesk() {
  setMode("desk");
  show("setupPanel", false);
  show("loginPanel", false);
  show("deskPanel", true);
  el("logoutBtn").hidden = false;
  await refreshPasses();
}

function showLogin() {
  setMode("login");
  show("setupPanel", false);
  show("loginPanel", true);
  show("deskPanel", false);
  el("logoutBtn").hidden = true;
}

function showSetup() {
  setMode("setup");
  show("setupPanel", true);
  show("loginPanel", false);
  show("deskPanel", false);
  el("logoutBtn").hidden = true;
}

async function boot() {
  const session = await api("/session");
  if (!session.configured) {
    showSetup();
    return;
  }
  if (session.authenticated) {
    await showDesk();
    return;
  }
  showLogin();
}

el("loginForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = el("loginError");
  errorEl.hidden = true;
  try {
    await api("/login", {
      method: "POST",
      body: JSON.stringify({ password: el("adminPassword").value }),
    });
    el("adminPassword").value = "";
    await showDesk();
  } catch (error) {
    errorEl.hidden = false;
    errorEl.textContent = error.message;
  }
});

el("togglePasswordBtn")?.addEventListener("click", () => {
  const input = el("adminPassword");
  const button = el("togglePasswordBtn");
  if (!input || !button) return;
  const hidden = input.type === "password";
  input.type = hidden ? "text" : "password";
  button.textContent = hidden ? "숨김" : "표시";
  button.setAttribute("aria-pressed", hidden ? "true" : "false");
});

el("logoutBtn")?.addEventListener("click", async () => {
  await api("/logout", { method: "POST", body: "{}" });
  showLogin();
});

el("issueForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = el("issueError");
  const banner = el("issuedBanner");
  errorEl.hidden = true;
  banner.hidden = true;
  try {
    const payload = await api("/passes", {
      method: "POST",
      body: JSON.stringify({
        durationDays: Number(el("issueDays").value),
        note: el("issueNote").value,
      }),
    });
    el("issuedToken").textContent = payload.token;
    el("issuedToken").title = payload.token;
    banner.hidden = false;
    el("issueNote").value = "";
    await refreshPasses();
  } catch (error) {
    errorEl.hidden = false;
    errorEl.textContent = error.message;
  }
});

el("copyTokenBtn")?.addEventListener("click", async () => {
  await copyText(el("issuedToken")?.textContent || "", el("copyTokenBtn"));
});

el("passTableBody")?.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-token]");
  if (copyButton) {
    await copyText(copyButton.dataset.copyToken, copyButton);
    return;
  }
  const button = event.target.closest("[data-revoke]");
  if (!button || button.disabled) return;
  const row = button.closest("tr");
  const passId = row?.dataset.passId;
  if (!passId) return;
  if (!window.confirm("이 사용권을 회수할까요? 등록된 브라우저에서도 즉시 막을 수 있습니다.")) return;
  await api(`/passes/${passId}/revoke`, { method: "POST", body: "{}" });
  await refreshPasses();
});

el("passTableBody")?.addEventListener("change", async (event) => {
  const input = event.target.closest("[data-note-input]");
  if (!input) return;
  const passId = input.closest("tr")?.dataset.passId;
  if (!passId) return;
  await api(`/passes/${passId}`, {
    method: "PATCH",
    body: JSON.stringify({ note: input.value }),
  });
});

boot().catch(() => showSetup());
