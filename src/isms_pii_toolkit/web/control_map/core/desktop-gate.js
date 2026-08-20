const STORAGE_KEY = "ondo.narrowWorkspaceContinue";
const UNLOCK_CLASS = "is-narrow-workspace-ok";
const NARROW_QUERY = "(max-width: 860px), (max-height: 520px) and (pointer: coarse)";

function readContinueFlag() {
  try {
    return sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeContinueFlag() {
  try {
    sessionStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* ignore quota / private mode */
  }
}

function syncInert(locked) {
  const gate = document.getElementById("desktopWorkspaceGate");
  Array.from(document.body.children).forEach((node) => {
    if (node === gate) return;
    if (locked) node.setAttribute("inert", "");
    else node.removeAttribute("inert");
  });
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const field = document.createElement("textarea");
  field.value = value;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.left = "-9999px";
  document.body.appendChild(field);
  field.select();
  document.execCommand("copy");
  field.remove();
}

export function initDesktopWorkspaceGate() {
  const gate = document.getElementById("desktopWorkspaceGate");
  if (!gate) return;

  const mq = window.matchMedia(NARROW_QUERY);
  const urlEl = document.getElementById("desktopWorkspaceGateUrl");
  const copyBtn = document.getElementById("desktopWorkspaceGateCopy");
  const continueBtn = document.getElementById("desktopWorkspaceGateContinue");
  const title = document.getElementById("desktopWorkspaceGateTitle");

  function apply() {
    if (readContinueFlag()) {
      document.documentElement.classList.add(UNLOCK_CLASS);
    }
    const locked = mq.matches && !document.documentElement.classList.contains(UNLOCK_CLASS);
    gate.setAttribute("aria-hidden", locked ? "false" : "true");
    if (urlEl) urlEl.textContent = window.location.href;
    syncInert(locked);
    if (locked && title && document.activeElement === document.body) {
      title.focus();
    }
  }

  copyBtn?.addEventListener("click", async () => {
    const url = window.location.href;
    try {
      await copyText(url);
      const prev = copyBtn.textContent;
      copyBtn.textContent = "복사됨";
      window.setTimeout(() => {
        copyBtn.textContent = prev;
      }, 1600);
    } catch {
      copyBtn.textContent = "아래 주소를 길게 누르세요";
    }
  });

  continueBtn?.addEventListener("click", () => {
    writeContinueFlag();
    document.documentElement.classList.add(UNLOCK_CLASS);
    apply();
  });

  if (typeof mq.addEventListener === "function") mq.addEventListener("change", apply);
  else if (typeof mq.addListener === "function") mq.addListener(apply);
  window.addEventListener("popstate", apply);

  apply();
}
