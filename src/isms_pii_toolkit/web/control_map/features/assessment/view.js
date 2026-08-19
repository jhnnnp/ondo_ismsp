import {
  AREA_SHORT,
  CHECK_LABEL,
  CHECK_LABEL_FULL,
  LEVEL_LABEL,
} from "../../core/constants.js";
import { el, escapeHtml, showToast } from "../../core/dom.js";
import { state } from "../../core/state.js";
import {
  areaNameMap,
  assessFiltersActive,
  countByArea,
  countByLevel,
} from "./filter.js";
import { listControlEvidence } from "./evidence.js";
import { categoryProgress, compareDotId, getAssessment } from "./model.js";

export function levelPill(level) {
  return `<span class="status-pill level-${level}">${LEVEL_LABEL[level] || level}</span>`;
}

function officialLawUrl(value) {
  try {
    const url = new URL(value || "");
    if (url.protocol !== "https:" || !["law.go.kr", "www.law.go.kr"].includes(url.hostname)) return "";
    return url.href;
  } catch (_) {
    return "";
  }
}

function cleanCasebookSpacing(value) {
  return String(value || "")
    .replace(/개인 정보/g, "개인정보")
    .replace(/정보 주체/g, "정보주체")
    .replace(/공동 주택/g, "공동주택")
    .replace(/관리 주체/g, "관리주체")
    .replace(/주택 관리/g, "주택관리")
    .replace(/관리 사무소/g, "관리사무소")
    .replace(/입주자대표 회의/g, "입주자대표회의")
    .replace(/개인정보 처리자/g, "개인정보처리자")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeLegalSource(value) {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .replace(/\u00a0/g, " ")
    .replace(/(\d+)\s*[•·]\s*(?:\n|$)/g, "\n")
    .replace(/(\d+\))\s*\1/g, "$1 ")
    .replace(/\s*<\s*([^<>]{2,40})\s*>\s*/g, "\n<$1>\n")
    .replace(/\s+([가나다라마바사아자차카타파하])\.\s+(?=「|[가-힣]|제\d)/g, "\n$1. ")
    .replace(/(?:^|\n)\s*([①-⑳])\s+/g, "\n$1 ")
    .replace(/\s+(※)\s+/g, "\n$1 ")
    .replace(/(?:^|\n)\s*[-–∙·•▪◦]\s+/g, "\n- ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitQuestionClauses(line) {
  if (!/여부와/.test(line)) return [line];
  const parts = line.split(/\s*여부와\s+/);
  if (parts.length !== 2) return [line];
  const left = parts[0].trim();
  const right = parts[1].trim();
  if (!left || !right) return [line];
  if (!/(여부|있는지|할지|인지|「)/.test(left) || !/(여부|「)/.test(right)) return [line];
  return [
    /여부\??$/.test(left) ? left : `${left} 여부`,
    right,
  ];
}

function explodeSentences(line) {
  if (line.length < 160) return [line];
  const parts = line.split(/(?<=(?:합니다|됩니다|있습니다|없습니다|봅니다|판단됩니다|어렵습니다|해당하지 않습니다|요청함)\.)\s+/);
  return parts.length > 1 ? parts.map((part) => part.trim()).filter(Boolean) : [line];
}

function isLegalHeading(line, nextLine) {
  if (/^(행위 주체 내용|관리주체|질의 배경|관계 법령|결론)$/.test(line)) return true;
  if (line.length <= 40 && /(?:결정례|판례|구조도|법적 근거)$/.test(line)) return true;
  return line.length <= 16
    && !/[.!?。?]$/.test(line)
    && !/^[①-⑳가나다라마바사\d]/.test(line)
    && /^[①-⑳]/.test(nextLine || "");
}

export function renderLegalProse(value) {
  const lines = normalizeLegalSource(value)
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !/^\d+\s*[•·]\s*$/.test(line) && !/^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+$/.test(line))
    .flatMap((line) => (
      /^([가나다라마바사아자차카타파하]\.|[①-⑳]|\d{1,2}\.|-|※|<)/.test(line)
        ? [line]
        : explodeSentences(line)
    ));
  if (!lines.length) return "";

  const blocks = [];
  let paragraph = [];
  let listItems = [];
  let listKind = "";
  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(`<p>${escapeHtml(cleanCasebookSpacing(paragraph.join(" ")))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (!listItems.length) return;
    const isHangul = listKind === "hangul";
    const isBullet = listKind === "bullet";
    const tag = isBullet ? "ul" : "ol";
    const cls = isHangul ? "legal-hangul-list" : isBullet ? "legal-bullet-list" : "legal-reasoning-list";
    blocks.push(`<${tag} class="${cls}">${listItems.map((item) => `<li>${escapeHtml(cleanCasebookSpacing(item))}</li>`).join("")}</${tag}>`);
    listItems = [];
    listKind = "";
  };
  const pushListItem = (kind, text) => {
    if (listKind && listKind !== kind) flushList();
    listKind = kind;
    listItems.push(text);
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.replace(/^<\s*([^>]+)\s*>$/, "$1").trim();
    const markerHeading = /^<\s*([^>]+)\s*>$/.test(rawLine);
    const hangulItem = line.match(/^([가나다라마바사아자차카타파하])\.\s*(.+)$/);
    const numbered = line.match(/^(\d{1,2})\.\s+(.+)$/);
    const circled = line.match(/^([①-⑳])\s*(.+)$/);
    const bullet = line.match(/^-\s*(.+)$/);
    const note = line.match(/^※\s*(.+)$/);
    const omission = /^(?:[①-⑳]|\d{1,2}\.)\s*[∼~～]/.test(line);
    const nextLine = lines[index + 1] || "";

    if (omission) {
      flushParagraph();
      flushList();
      blocks.push(`<p class="legal-note">${escapeHtml(cleanCasebookSpacing(line))}</p>`);
      return;
    }

    if (markerHeading || isLegalHeading(line, nextLine)) {
      flushParagraph();
      flushList();
      blocks.push(`<h5>${escapeHtml(cleanCasebookSpacing(line))}</h5>`);
      return;
    }
    if (note) {
      flushParagraph();
      flushList();
      blocks.push(`<p class="legal-note">${escapeHtml(cleanCasebookSpacing(note[1]))}</p>`);
      return;
    }
    if (hangulItem) {
      flushParagraph();
      pushListItem("hangul", hangulItem[2]);
      return;
    }
    if (numbered || circled || bullet) {
      flushParagraph();
      const kind = bullet ? "bullet" : "decimal";
      pushListItem(kind, (numbered || circled || bullet)[numbered || circled ? 2 : 1]);
      return;
    }

    const clauses = splitQuestionClauses(line);
    if (clauses.length > 1) {
      flushParagraph();
      clauses.forEach((clause) => pushListItem("decimal", clause));
      return;
    }

    if (listItems.length) {
      const previous = listItems[listItems.length - 1];
      const startsNewParagraph = /[.)”’]$/.test(previous)
        && /^(이 |그 |따라서|그러므로|한편|반면|결론적으로|대법원|헌법재판소)/.test(line);
      if (!startsNewParagraph) {
        listItems[listItems.length - 1] = `${previous} ${line}`;
        return;
      }
    }
    flushList();
    paragraph.push(line);
    if (/[.!?。?][”’)]?$/.test(line) || /(?:합니다|됩니다|있습니다|없습니다|봅니다|판단됩니다|요청함)[.]?$/.test(line)) {
      flushParagraph();
    }
  });
  flushParagraph();
  flushList();
  return `<div class="legal-prose legal-reasoning-content">${blocks.join("")}</div>`;
}

export function renderCasebookReasoning(value) {
  return renderLegalProse(value);
}

function renderReadingSection(title, value, kind) {
  const body = renderLegalProse(value);
  if (!body) return "";
  return `<section class="legal-reading-section is-${kind}"><h4>${escapeHtml(title)}</h4>${body}</section>`;
}

export function renderLegalBasisContent(controlId, entry = state.legalBasisCache?.[controlId]) {
  if (!entry || entry.status === "idle") {
    return `<p class="today-detail-note">관련 법령과 법령해석을 불러오는 중입니다.</p>`;
  }
  if (entry.status === "loading") {
    return `<p class="today-detail-note" role="status">법적 근거를 불러오는 중...</p>`;
  }
  if (entry.status === "error") {
    return `
      <p class="legal-error">법적 근거를 불러오지 못했습니다.</p>
      <button type="button" class="legal-retry" data-retry-legal="${escapeHtml(controlId)}">다시 시도</button>
    `;
  }

  const data = entry.data || {};
  const laws = (data.laws || []).map((law, lawIndex) => {
    const sourceUrl = officialLawUrl(law.sourceUrl);
    return `
      <li class="legal-law-item">
        <div>
          <strong>${escapeHtml(law.lawName || "관련 법령")}</strong>
          ${law.article ? `<span>${escapeHtml(law.article)}</span>` : ""}
          ${law.articleTitle ? `<small>${escapeHtml(law.articleTitle)}</small>` : ""}
          ${law.basisType === "COMMON_CERTIFICATION_BASIS" ? '<em class="legal-basis-kind">제도 공통 근거</em>' : ""}
        </div>
        <div class="legal-law-actions">
          ${sourceUrl ? `<a class="legal-source-link" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">법령 원문</a>` : ""}
          ${law.articleText ? `<button type="button" class="legal-article-open" data-open-law-article="${lawIndex}" data-law-control="${escapeHtml(controlId)}">조문 내용 보기</button>` : `<span class="legal-article-unavailable">본문 없음</span>`}
        </div>
      </li>
    `;
  }).join("");
  const interpretations = (data.interpretations || []).map((item) => {
    const sourceUrl = officialLawUrl(item.source?.originalUrl);
    const warning = item.warning || (item.temporalStatus === "REVIEW_REQUIRED"
      ? "해석 이후 관련 법령이 개정되었을 수 있어 현재 적용 여부를 검토해야 합니다."
      : "");
    return `
      <details class="legal-interpretation-card">
        <summary>
          <span>
            <strong>${escapeHtml(item.title || "법령해석례")}</strong>
            <small>${escapeHtml(item.caseNumber || item.interpretationId || "")} · ${escapeHtml(item.responseDate || "회신일 미상")}</small>
          </span>
          ${Number.isFinite(item.matchScore) ? `<em>관련도 ${escapeHtml(item.matchScore)}점</em>` : ""}
        </summary>
        <div class="legal-interpretation-body">
          ${warning ? `<p class="legal-warning">${escapeHtml(warning)}</p>` : ""}
          ${(item.matchReasons || []).length ? `<div class="legal-interpretation-meta"><b>이 통제와 연결된 이유</b><span>${item.matchReasons.map(escapeHtml).join(" · ")}</span></div>` : ""}
          <div class="legal-interpretation-reading">
            ${renderReadingSection("질의 요지", item.question, "question")}
            ${renderReadingSection("공식 회답", item.answer, "answer")}
            ${renderReadingSection("판단 이유", item.reasoning, "reason")}
          </div>
          ${sourceUrl ? `<div class="legal-interpretation-footer"><span>법령해석은 참고자료이며 현재 사실관계에 대한 적합 판정을 대신하지 않습니다.</span><a class="legal-source-link" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">국가법령정보센터 원문 보기</a></div>` : ""}
        </div>
      </details>
    `;
  }).join("");
  const interpretationEmpty = data.interpretationDataStatus === "NOT_CONFIGURED"
    ? "법령해석 Open API 동기화가 아직 설정되지 않았습니다. 인증키 설정 후 수집하면 질의요지·회답·이유가 표시됩니다."
    : `현재 수집된 법령해석 ${Number(data.interpretationCorpusSize || 0)}건 중 관련 조문이 정확히 일치하는 해석례가 없습니다.`;
  const casebookExamples = (data.casebookExamples || []).map((item) => {
    const source = item.source || {};
    return `
      <details class="legal-interpretation-card legal-casebook-card">
        <summary>
          <span>
            <strong>${escapeHtml(item.title || "개인정보 법령해석 사례")}</strong>
            <small>${escapeHtml(source.document || "2023 개인정보 법령해석 사례 30선")} · ${escapeHtml(item.sourcePage ? `${item.sourcePage}쪽` : "페이지 미상")}</small>
          </span>
          <em>내용 보기</em>
        </summary>
        <div class="legal-interpretation-body">
          ${item.warning ? `<p class="legal-warning">${escapeHtml(item.warning)}</p>` : ""}
          ${renderReadingSection("질의 요지", item.question, "question")}
          ${renderReadingSection("사례집 답변", item.answer, "answer")}
          ${item.reasoning ? `<details class="legal-reasoning-more"><summary>판단 이유 자세히 보기</summary>${renderLegalProse(item.reasoning)}</details>` : ""}
          <p class="legal-casebook-source">출처: ${escapeHtml(source.provider || "개인정보보호위원회·한국인터넷진흥원")} · ${escapeHtml(source.publishedAt || "2023-12")}</p>
        </div>
      </details>
    `;
  }).join("");
  const officialGuidance = (data.officialGuidance || []).map((item) => `
    <details class="legal-interpretation-card legal-casebook-card official-guidance-card">
      <summary>
        <span>
          <span class="legal-source-badge">개인정보보호위원회 공식 안내서</span>
          <strong>${escapeHtml(item.section || item.title || "관련 안내")}</strong>
          <small>${escapeHtml(item.title || "")} · ${escapeHtml(item.publishedAt || "")} · ${escapeHtml((item.pages || []).length ? `${item.pages.join("–")}쪽` : "페이지 미상")}</small>
        </span>
        <em>내용 보기</em>
      </summary>
      <div class="legal-interpretation-body official-guidance-body">
        <p class="official-guidance-applicability">${escapeHtml(item.applicability || "일반 개인정보처리자")}</p>
        ${renderLegalProse(item.summary || "")}
        ${(item.checkpoints || []).length ? `
          <section>
            <h4>이 통제에서 확인할 사항</h4>
            <ul>${item.checkpoints.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>
          </section>
        ` : ""}
      </div>
    </details>
  `).join("");
  const interpretationCount = (data.interpretations || []).length;
  const casebookCount = (data.casebookExamples || []).length;
  const guidanceCount = (data.officialGuidance || []).length;
  const lawCount = (data.laws || []).length;

  return `
    <div class="legal-resource-counts" aria-label="관련 자료 수">
      <span><b>법령</b> ${lawCount}건</span>
      <span><b>법령해석</b> ${interpretationCount}건</span>
      <span><b>공식 사례</b> ${casebookCount}건</span>
      <span><b>공식 안내서</b> ${guidanceCount}건</span>
    </div>
    <section class="legal-law-section">
      <h4>관련 법령 <span>${lawCount}건</span></h4>
      <ul class="legal-law-list">${laws || "<li>구조화된 관련 조문이 없습니다.</li>"}</ul>
    </section>
    <section class="legal-interpretation-section">
      <h4>관련 법령해석 <span>${interpretationCount}건</span></h4>
      ${interpretations || `<p class="legal-empty-state">${escapeHtml(interpretationEmpty)}</p>`}
      <p class="legal-disclaimer">${escapeHtml(data.disclaimer || "법령해석례는 진단 결과를 직접 확정하지 않습니다.")}</p>
    </section>
    ${(casebookExamples || officialGuidance) ? `
      <section class="legal-reference-section">
        <h4>공식 참고자료 <span>${casebookCount + guidanceCount}건</span></h4>
        ${casebookExamples ? `
          <details class="legal-resource-disclosure legal-casebook-section">
            <summary>
              <span><b>관련 공식 사례집</b><small>개인정보위·KISA의 공식 학습·참고 사례</small></span>
              <em>${casebookCount}건 보기</em>
            </summary>
            <div class="legal-resource-disclosure-body legal-reference-list">${casebookExamples}</div>
          </details>
        ` : ""}
        ${officialGuidance ? `
          <details class="legal-resource-disclosure official-guidance-section">
            <summary>
              <span><b>관련 공식 안내서</b><small>일반 개인정보처리자용 실무 해설</small></span>
              <em>${guidanceCount}건 보기</em>
            </summary>
            <div class="legal-resource-disclosure-body legal-reference-list">${officialGuidance}</div>
          </details>
        ` : ""}
      </section>
    ` : ""}
    ${data.lastUpdatedAt ? `<p class="legal-updated">법령 데이터 동기화: ${escapeHtml(data.lastUpdatedAt)}</p>` : ""}
  `;
}

export function renderAssessToolbar() {
  const areaCounts = countByArea();
  const areaNames = areaNameMap();
  const areaGroup = el("areaFilterGroup");
  if (areaGroup) {
    const areaFilters = [
      { id: "all", label: "전체" },
      { id: "1", label: AREA_SHORT["1"] },
      { id: "2", label: AREA_SHORT["2"] },
      { id: "3", label: AREA_SHORT["3"] },
    ];
    areaGroup.innerHTML = areaFilters.map((filter) => {
      const count = filter.id === "all" ? areaCounts.all : (areaCounts[filter.id] || 0);
      const title = filter.id === "all"
        ? `전체 ${count}개 통제`
        : `${areaNames[filter.id] || filter.label} (${count}개)`;
      return `
        <button type="button" class="filter-btn${state.areaFilter === filter.id ? " active" : ""}" data-area-filter="${filter.id}" title="${title}">
          ${filter.label}<span class="filter-count">${count}</span>
        </button>
      `;
    }).join("");
  }

  const levelCounts = countByLevel();
  const levelGroup = el("levelFilterGroup");
  if (levelGroup) {
    const levelFilters = [
      { id: "all", label: "전체" },
      { id: "unknown", label: "미점검" },
      { id: "none", label: "미이행" },
      { id: "partial", label: "부분 이행" },
      { id: "done", label: "이행" },
      { id: "na", label: "해당 없음" },
    ];
    levelGroup.innerHTML = levelFilters.map((filter) => `
      <button type="button" class="filter-btn${state.levelFilter === filter.id ? " active" : ""}" data-level-filter="${filter.id}">
        ${filter.label}<span class="filter-count">${levelCounts[filter.id] || 0}</span>
      </button>
    `).join("");
  }
}

export function renderControlAssessRow(control, { ensureChecks, ensureDomainChecks }) {
    const level = getAssessment(control.id);
    const checks = ensureChecks(control.id);
    const conf = state.inputConfidence?.[control.id] || "unknown";
    const expanded = state.expandedRows.has(control.id);
    const checklistItems = control.checklistItems || [];
    const domain = expanded
      ? ensureDomainChecks(control.id, checklistItems)
      : (state.domainChecks[control.id] || {});
    const checklistHtml = checklistItems.map((item, index) => {
      const itemId = String(index + 1);
      const checked = !!domain[itemId];
      if (!expanded) {
        return `<li><strong>${itemId}.</strong> ${escapeHtml(item)}</li>`;
      }
      return `
        <li class="domain-check-item">
          <label>
            <input type="checkbox" data-domain-control="${control.id}" data-domain-item="${itemId}"${checked ? " checked" : ""}>
            <span><strong>${itemId}.</strong> ${escapeHtml(item)}</span>
          </label>
        </li>
      `;
    }).join("");
    const actionsHtml = (control.recommendedActions || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("");
    const evidenceHtml = (control.officialEvidenceExamples || []).slice(0, 6).map((e) => `<li>${escapeHtml(e)}</li>`).join("");
    const registered = listControlEvidence(control.id);
    const registeredHtml = registered.length
      ? registered.map((item) => `<li><strong>${escapeHtml(item.title)}</strong>${item.url ? ` · ${escapeHtml(item.url)}` : ""}${item.note ? ` · ${escapeHtml(item.note)}` : ""}</li>`).join("")
      : "<li>등록된 증적 없음 (이행 판정에 필요)</li>";
    const displayLevel = level === "evidenced" ? "done" : level;
    const requirementHtml = control.officialRequirement
      ? `<div class="detail-block"><h3>인증기준 (안내서)</h3><p>${escapeHtml(control.officialRequirement)}</p></div>`
      : "";
    const legalBasisHtml = expanded
      ? `<div class="detail-block legal-basis-block">
          <h3>법적 근거 및 참고자료</h3>
          <p class="today-detail-note">공식 자료와 프로젝트의 통제 연결 결과를 구분하여 표시합니다.</p>
          <div data-legal-basis="${escapeHtml(control.id)}">${renderLegalBasisContent(control.id)}</div>
        </div>`
      : "";
    return `
      <div class="assess-row${expanded ? " expanded" : ""}${displayLevel !== "unknown" && displayLevel !== "na" ? " is-reviewed" : ""}${displayLevel === "none" ? " is-risk" : ""}" data-control="${control.id}">
        <div class="assess-row-head">
        <span class="assess-expand-icon" aria-hidden="true">▾</span>
          <div class="assess-row-text">
            <div class="assess-row-meta-line">
              <span class="assess-id">${control.id}</span>
              ${levelPill(displayLevel)}
              <label class="assess-confidence" title="이 통제 입력의 신뢰도 (모름/추정/확인됨)">
                신뢰도
                <select data-row-confidence="${escapeHtml(control.id)}" aria-label="${escapeHtml(control.id)} 입력 신뢰도">
                  <option value="unknown"${conf === "unknown" ? " selected" : ""}>모름</option>
                  <option value="assumed"${conf === "assumed" ? " selected" : ""}>추정</option>
                  <option value="confirmed"${conf === "confirmed" ? " selected" : ""}>확인됨</option>
                </select>
              </label>
            </div>
          <span class="assess-title" title="${control.areaName} / ${control.categoryName}">${control.title}</span>
          </div>
          <div class="audit-checks" aria-label="${control.id} 자체진단 체크 항목">
            ${Object.keys(CHECK_LABEL).map((key) => `
            <label class="audit-check" title="${control.id} ${CHECK_LABEL_FULL[key]}">
                <input type="checkbox" data-check-control="${control.id}" data-check-key="${key}"${checks[key] ? " checked" : ""}>
                <span>${CHECK_LABEL[key]}</span>
              </label>
            `).join("")}
          </div>
        </div>
        <div class="assess-row-body">
          <div class="assess-detail-grid">
            <div class="detail-block">
              <h3>주요 확인사항 (안내서)</h3>
              <p style="font-size:12px;color:var(--muted);margin:0 0 8px;">인증기준 안내서 주요 확인사항. 체크하면 해당 문항은 문제 근거에서 제외됩니다. 이행은 등록 증적이 있을 때만 가능합니다.</p>
              <ul class="domain-check-list">${checklistHtml || "<li>항목 없음</li>"}</ul>
            </div>
            ${requirementHtml}
            ${legalBasisHtml}
            <div class="detail-block">
            <h3>미이행 시 취약점/심사 리스크</h3>
              <p>${escapeHtml(control.riskIfMissing || "-")}</p>
            </div>
            <div class="detail-block">
              <h3>등록된 증적</h3>
              <p style="font-size:12px;color:var(--muted);margin:0 0 8px;">자가진단 상세 카드에서 링크/메모를 등록하세요.</p>
              <ul>${registeredHtml}</ul>
            </div>
            ${evidenceHtml ? `
              <div class="detail-block">
                <h3>증거자료 예시 (안내서)</h3>
                <ul>${evidenceHtml}</ul>
              </div>
            ` : ""}
            ${actionsHtml ? `
              <div class="detail-block">
                <h3>권장 조치</h3>
                <ul>${actionsHtml}</ul>
              </div>
            ` : ""}
          </div>
        </div>
      </div>
  `;
}

export function renderAssessRailFilterHint(visibleCount, navTotal, onReset) {
  const hint = el("assessRailFilterHint");
  if (!hint) return;
  if (!assessFiltersActive()) {
    hint.hidden = true;
    hint.innerHTML = "";
    return;
  }
  hint.hidden = false;
  hint.innerHTML = `
    필터 적용 중 — 목록 <strong>${visibleCount}개</strong> /
    분류 트리 ${navTotal}개 기준.
    <button type="button" id="resetAssessFiltersBtn">필터 초기화</button>
  `;
  hint.querySelector("#resetAssessFiltersBtn")?.addEventListener("click", () => {
    onReset();
  });
}

export function renderAssessCategoryNav(groups, visibleIds) {
  const nav = el("assessCategoryNav");
  if (!nav) return;
  const filtersOn = assessFiltersActive();
  if (!groups.length) {
    nav.innerHTML = `<p class="detail-empty">표시할 분류가 없습니다.</p>`;
    return;
  }
  const byArea = new Map();
  groups.forEach((group) => {
    const areaKey = group.areaId || "0";
    if (!byArea.has(areaKey)) {
      byArea.set(areaKey, {
        areaId: areaKey,
        areaName: group.areaName || AREA_SHORT[areaKey] || "기타",
        groups: [],
      });
    }
    byArea.get(areaKey).groups.push(group);
  });
  const areas = Array.from(byArea.values()).sort((a, b) => compareDotId(a.areaId, b.areaId));
  nav.innerHTML = areas.map((area) => {
    const areaVisible = area.groups.reduce(
      (sum, g) => sum + g.controls.filter((c) => visibleIds.has(c.id)).length,
      0
    );
    const areaTotal = area.groups.reduce((sum, g) => sum + g.controls.length, 0);
    const areaCountLabel = filtersOn ? `${areaVisible}/${areaTotal}` : String(areaTotal);
    return `
    <div class="assess-area-block">
      <div class="assess-area-label">
        <span>${AREA_SHORT[area.areaId] || area.areaName}</span>
        <span>${areaCountLabel}</span>
      </div>
      ${area.groups.map((group) => {
        const visibleCount = group.controls.filter((c) => visibleIds.has(c.id)).length;
        const progress = categoryProgress(group.controls);
        const dimmed = filtersOn && visibleCount === 0;
        const active = state.activeCategoryId === group.categoryId ? " active" : "";
        const meta = filtersOn
          ? `${visibleCount}/${group.controls.length}`
          : `${progress.reviewed}/${progress.total} (${progress.pct}%)`;
        return `
          <button type="button" class="assess-nav-item${active}${dimmed ? " is-dimmed" : ""}" data-jump-category="${group.categoryId}" title="${escapeHtml(group.categoryName)}${filtersOn ? ` — 필터 ${visibleCount}개` : ` (${progress.pct}%)`}">
            <strong>${group.categoryId} ${group.categoryName}</strong>
            <span class="assess-nav-meta">${meta}</span>
          </button>
        `;
      }).join("")}
    </div>
  `;
  }).join("");

  nav.querySelectorAll("[data-jump-category]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const categoryId = btn.dataset.jumpCategory;
      const group = groups.find((g) => g.categoryId === categoryId);
      const visibleInGroup = (group?.controls || []).filter((c) => visibleIds.has(c.id));
      if (filtersOn && !visibleInGroup.length) {
        showToast("이 분류에는 현재 필터 조건에 맞는 통제가 없습니다.");
        return;
      }
      state.activeCategoryId = categoryId;
      state.collapsedCategories.delete(categoryId);
      const target = document.querySelector(`[data-category-group="${categoryId}"]`);
      if (target) {
        target.classList.remove("collapsed");
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      renderAssessCategoryNav(groups, visibleIds);
    });
  });
}
