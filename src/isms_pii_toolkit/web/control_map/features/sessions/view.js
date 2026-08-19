import { el, escapeHtml, showToast } from "../../core/dom.js";
import { diagnosisProgress, SESSION_NAME_MAX_LENGTH } from "../../core/session-model.js";
import { state } from "../../core/state.js";

export const SESSION_PAGE_SIZE = 4;

let sessionListPageIndex = 1;
let pickerHandlers = null;

export function resetDiagnosisSessionPage() {
  sessionListPageIndex = 1;
}

export function paginateDiagnosisSessions(sessions, page, pageSize = SESSION_PAGE_SIZE) {
  const items = Array.isArray(sessions) ? sessions : [];
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize) || 1);
  const current = Math.min(Math.max(1, Number(page) || 1), pageCount);
  const start = (current - 1) * pageSize;
  return {
    current,
    pageCount,
    total: items.length,
    items: items.slice(start, start + pageSize),
  };
}

export function diagnosisSessionPageNumbers(current, pageCount) {
  const total = Math.max(1, pageCount);
  const active = Math.min(Math.max(1, current), total);
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  const pages = new Set([1, total, active - 1, active, active + 1]);
  if (active <= 3) [2, 3, 4].forEach((page) => pages.add(page));
  if (active >= total - 2) [total - 3, total - 2, total - 1].forEach((page) => pages.add(page));
  return [...pages].filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
}

function formatUpdatedAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "수정 시간 없음";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function renderSessionCard(session) {
  const progress = diagnosisProgress(session, state.checklist?.length || 101);
  const status = progress.percent >= 100
    ? { className: "is-complete", label: "완료", action: "결과 보기", icon: '<svg viewBox="0 0 24 24"><path d="m6.5 12.5 3.5 3.5 7.5-8"/></svg>' }
    : progress.percent > 0
      ? { className: "is-active", label: "진행 중", action: "이어하기", icon: '<svg viewBox="0 0 24 24"><path d="m9 7 7 5-7 5V7Z"/></svg>' }
      : { className: "is-new", label: "시작 전", action: "시작하기", icon: '<svg viewBox="0 0 24 24"><path d="M12 7v10M7 12h10"/></svg>' };
  return `
    <article class="diagnosis-session-card ${status.className}" data-session-id="${escapeHtml(session.id)}">
      <span class="diagnosis-session-state" aria-hidden="true">${status.icon}</span>
      <div class="diagnosis-session-copy">
        <div class="diagnosis-session-heading">
          <strong class="diagnosis-session-name">${escapeHtml(session.name)}</strong>
          <button type="button" class="diagnosis-session-rename-btn" data-session-rename aria-label="${escapeHtml(session.name)} 이름 변경">
            <svg aria-hidden="true" viewBox="0 0 20 20"><path d="M12.4 4.1 15.9 7.6 7.5 16H4v-3.5L12.4 4.1Z"/><path d="M11.2 5.3 14.7 8.8"/></svg>
          </button>
          <span class="diagnosis-session-badge">${status.label}</span>
        </div>
        <span>마지막 수정 ${escapeHtml(formatUpdatedAt(session.updatedAt))}</span>
        <code title="진단 ID">진단 ID · ${escapeHtml(session.id.slice(0, 8))}</code>
      </div>
      <div class="diagnosis-session-progress" aria-label="진단 진행률 ${progress.percent}%">
        <div>
          <span>진행률</span>
          <strong>${progress.percent}% · ${progress.reviewed}/${progress.applicable}</strong>
        </div>
        <div class="diagnosis-session-track" role="progressbar" aria-valuenow="${progress.percent}" aria-valuemin="0" aria-valuemax="100">
          <i style="width:${progress.percent}%"></i>
        </div>
      </div>
      <div class="diagnosis-session-actions">
        <button type="button" class="primary" data-session-open>${status.action} <svg aria-hidden="true" viewBox="0 0 20 20"><path d="M4 10h11M11 6l4 4-4 4"/></svg></button>
        <div class="diagnosis-session-secondary">
          <button type="button" data-session-rename>이름 변경</button>
          <button type="button" data-session-duplicate>복제</button>
          <button type="button" data-session-export>내보내기</button>
          <button type="button" class="danger" data-session-delete>삭제</button>
        </div>
      </div>
    </article>
  `;
}

function beginSessionRename(card, onRename) {
  if (!card || card.classList.contains("is-renaming") || typeof onRename !== "function") return;
  const nameNode = card.querySelector(".diagnosis-session-name");
  if (!nameNode) return;

  const currentName = nameNode.textContent || "";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "diagnosis-session-name-input";
  input.value = currentName;
  input.maxLength = SESSION_NAME_MAX_LENGTH;
  input.setAttribute("aria-label", "진단 이름");
  input.autocomplete = "off";
  input.spellcheck = false;

  card.classList.add("is-renaming");
  nameNode.replaceWith(input);
  input.focus();
  input.select();

  let settled = false;
  const restore = () => {
    if (!input.isConnected) return;
    input.replaceWith(nameNode);
    card.classList.remove("is-renaming");
  };
  const finish = (commit) => {
    if (settled) return;
    settled = true;
    const nextName = input.value.replace(/\s+/g, " ").trim();
    if (!commit) {
      restore();
      return;
    }
    if (!nextName) {
      restore();
      showToast("진단 이름을 입력해 주세요.", { tone: "warning" });
      return;
    }
    onRename(card.dataset.sessionId, nextName);
  };

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      input.blur();
      finish(true);
    }
    if (event.key === "Escape") {
      event.preventDefault();
      finish(false);
    }
  });
  input.addEventListener("blur", () => finish(true));
}

function pagerButton(page, label, options = {}) {
  const current = options.current ? ' aria-current="page"' : "";
  const disabled = options.disabled ? " disabled" : "";
  const aria = options.ariaLabel ? ` aria-label="${escapeHtml(options.ariaLabel)}"` : "";
  return `<button type="button" data-session-page="${page}"${current}${disabled}${aria}>${label}</button>`;
}

function renderSessionPager(pager, current, pageCount) {
  if (!pager) return;
  if (pageCount <= 1) {
    pager.hidden = true;
    pager.innerHTML = "";
    return;
  }
  pager.hidden = false;
  const numbers = diagnosisSessionPageNumbers(current, pageCount);
  const parts = [
    pagerButton(current - 1, '<svg aria-hidden="true" viewBox="0 0 20 20"><path d="M12 5 7 10l5 5"/></svg>', {
      disabled: current <= 1,
      ariaLabel: "이전 페이지",
    }),
  ];
  let previous = 0;
  numbers.forEach((page) => {
    if (previous && page > previous + 1) {
      parts.push('<span class="diagnosis-session-pager-gap" aria-hidden="true">...</span>');
    }
    parts.push(pagerButton(page, String(page), { current: page === current, ariaLabel: `${page}페이지` }));
    previous = page;
  });
  parts.push(pagerButton(current + 1, '<svg aria-hidden="true" viewBox="0 0 20 20"><path d="m8 5 5 5-5 5"/></svg>', {
    disabled: current >= pageCount,
    ariaLabel: "다음 페이지",
  }));
  pager.innerHTML = parts.join("");
  pager.querySelectorAll("[data-session-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextPage = Number(button.dataset.sessionPage);
      if (!Number.isInteger(nextPage) || nextPage === sessionListPageIndex) return;
      sessionListPageIndex = nextPage;
      if (pickerHandlers) renderDiagnosisSessionPicker(pickerHandlers);
    });
  });
}

export function renderDiagnosisSessionPicker({
  onOpen,
  onCreate,
  onDuplicate,
  onRename,
  onExport,
  onImport,
  onDelete,
}) {
  const list = el("diagnosisSessionList");
  if (!list) return;
  pickerHandlers = {
    onOpen,
    onCreate,
    onDuplicate,
    onRename,
    onExport,
    onImport,
    onDelete,
  };
  const sessions = [...state.diagnosisSessions].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
  const page = paginateDiagnosisSessions(sessions, sessionListPageIndex);
  sessionListPageIndex = page.current;
  list.innerHTML = page.total
    ? page.items.map(renderSessionCard).join("")
    : `
      <section class="diagnosis-session-empty" role="status">
        <strong>저장된 진단이 없습니다</strong>
        <p>새 진단을 만들면 현재 브라우저에 독립된 진단 프로젝트로 저장됩니다.</p>
      </section>
    `;
  renderSessionPager(el("diagnosisSessionPager"), page.current, page.total ? page.pageCount : 0);

  list.querySelectorAll("[data-session-open]").forEach((button) => {
    button.addEventListener("click", () => {
      onOpen(button.closest("[data-session-id]")?.dataset.sessionId);
    });
  });
  list.querySelectorAll("[data-session-rename]").forEach((button) => {
    button.addEventListener("click", () => {
      beginSessionRename(button.closest("[data-session-id]"), onRename);
    });
  });
  list.querySelectorAll("[data-session-duplicate]").forEach((button) => {
    button.addEventListener("click", () => {
      onDuplicate(button.closest("[data-session-id]")?.dataset.sessionId);
    });
  });
  list.querySelectorAll("[data-session-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      onDelete(button.closest("[data-session-id]")?.dataset.sessionId);
    });
  });
  list.querySelectorAll("[data-session-export]").forEach((button) => {
    button.addEventListener("click", () => {
      onExport(button.closest("[data-session-id]")?.dataset.sessionId);
    });
  });
  const createButton = el("createDiagnosisSessionBtn");
  if (createButton) createButton.onclick = onCreate;
  const importButton = el("importDiagnosisSessionBtn");
  const importInput = el("importDiagnosisSessionInput");
  if (importButton && importInput) {
    importButton.onclick = () => importInput.click();
    importInput.onchange = async () => {
      const file = importInput.files?.[0];
      importInput.value = "";
      if (file) await onImport(file);
    };
  }
}

export function showDiagnosisSessionPicker() {
  const picker = el("sessionPicker");
  const app = el("appMain");
  if (picker) picker.hidden = false;
  if (app) app.hidden = true;
}

export function showDiagnosisApp() {
  const picker = el("sessionPicker");
  const app = el("appMain");
  if (picker) picker.hidden = true;
  if (app) app.hidden = false;
}
