export const el = (id) => document.getElementById(id);

export async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

let toastTimer = null;

export function showToast(message, options = {}) {
  const toast = el("toast");
  if (!toast) return;
  const raw = String(message || "").trim();
  if (!raw) return;
  const inferredTone = /실패|오류|불러오지 못/.test(raw)
    ? "error"
    : /찾을 수 없|없습니다|먼저|필요|변경되었습니다/.test(raw) ? "warning" : "success";
  const tone = options.tone || inferredTone;
  const labels = tone === "warning"
    ? { title: "확인 필요", icon: "!" }
    : tone === "error"
      ? { title: "처리 실패", icon: "!" }
      : { title: "", icon: "✓" };
  const title = options.title ?? labels.title;
  const titleEl = toast.querySelector(".toast-copy strong");
  toast.dataset.tone = tone;
  toast.querySelector(".toast-icon").textContent = labels.icon;
  titleEl.textContent = title;
  titleEl.hidden = !title;
  toast.querySelector(".toast-copy p").textContent = raw;
  const duration = options.duration || (tone === "success" ? 2200 : 4000);
  toast.style.setProperty("--toast-duration", `${duration}ms`);
  toast.classList.remove("show");
  void toast.offsetWidth;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), duration);
  toast.querySelector(".toast-close").onclick = () => {
    window.clearTimeout(toastTimer);
    toast.classList.remove("show");
  };
}

export function confirmAction({
  title = "계속 진행할까요?",
  message = "이 작업을 진행하기 전에 내용을 확인해 주세요.",
  confirmLabel = "확인",
  cancelLabel = "취소",
  tone = "default",
} = {}) {
  let dialog = el("appConfirmDialog");
  if (!dialog) {
    dialog = document.createElement("dialog");
    dialog.id = "appConfirmDialog";
    dialog.className = "app-confirm-dialog";
    dialog.setAttribute("aria-labelledby", "appConfirmTitle");
    dialog.setAttribute("aria-describedby", "appConfirmMessage");
    dialog.innerHTML = `
      <form method="dialog" class="app-confirm-shell">
        <div class="app-confirm-icon" aria-hidden="true">!</div>
        <div class="app-confirm-copy">
          <span>확인</span>
          <h2 id="appConfirmTitle"></h2>
          <p id="appConfirmMessage"></p>
        </div>
        <div class="app-confirm-actions">
          <button type="submit" value="cancel" class="app-confirm-cancel"></button>
          <button type="submit" value="confirm" class="app-confirm-submit"></button>
        </div>
      </form>`;
    document.body.append(dialog);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close("cancel");
    });
  }
  dialog.dataset.tone = tone;
  dialog.querySelector(".app-confirm-copy > span").textContent = tone === "danger" ? "삭제 확인" : "확인";
  dialog.querySelector("#appConfirmTitle").textContent = title;
  dialog.querySelector("#appConfirmMessage").textContent = message;
  dialog.querySelector(".app-confirm-cancel").textContent = cancelLabel;
  dialog.querySelector(".app-confirm-submit").textContent = confirmLabel;
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
  });
}


export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
