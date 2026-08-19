const SYNONYM_GROUPS = [
  ["제거", "삭제", "해지", "말소", "회수", "폐기"],
  ["계정", "아이디", "userid"],
  ["불필요", "미사용", "휴면"],
  ["패치", "업데이트", "보안패치", "핫픽스"],
  ["비밀번호", "패스워드", "password"],
  ["권한", "접근권한"],
  ["관리자", "root", "admin", "특권"],
  ["암호화", "tls", "ssl"],
  ["로그", "접속기록", "감사로그"],
  ["백업", "복구"],
  ["악성코드", "바이러스", "랜섬웨어", "백신"],
  ["퇴직", "퇴사", "이직"],
  ["외주", "수탁", "위탁", "외부자"],
  ["원격", "vpn", "재택"],
  ["인증", "mfa", "otp", "다중인증"],
];

const EXTRA_LEXICON = [
  "불필요",
  "주기적",
  "사용자",
  "보안패치",
  "보안",
  "적용",
  "점검",
  "파일",
  "최소",
  "그룹",
  "방화벽",
  "개인정보",
  "파기",
  "보유기간",
  "화면보호기",
  "취약점",
  "재직",
  "계약종료",
  "계약만료",
  "계약",
  "직무변경",
  "필요성",
  "잔존",
];

const LEXICON = [...new Set([...SYNONYM_GROUPS.flat(), ...EXTRA_LEXICON])]
  .filter((term) => term.length >= 2)
  .sort((a, b) => b.length - a.length);

const SYNONYM_LOOKUP = new Map();
SYNONYM_GROUPS.forEach((group) => {
  group.forEach((term) => {
    SYNONYM_LOOKUP.set(term, group);
  });
});

export function compactSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFC")
    .replace(/[\s\u00a0·.,;:()[\]{}'"'`~!@#$%^&*_+=|\\/<>?-]/g, "");
}

function collectText(value, out) {
  if (value == null) return;
  if (typeof value === "string" || typeof value === "number") {
    const text = String(value).trim();
    if (text) out.push(text);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectText(item, out));
    return;
  }
  if (typeof value === "object") {
    ["item", "label", "title", "text", "problem", "phrase", "concepts"].forEach((key) => {
      if (value[key]) collectText(value[key], out);
    });
  }
}

export function controlSearchHaystack(control) {
  const parts = [];
  collectText(control?.id, parts);
  collectText(control?.title, parts);
  collectText(control?.areaName, parts);
  collectText(control?.categoryName, parts);
  collectText(control?.tags, parts);
  collectText(control?.checklistItems, parts);
  collectText(control?.officialRequirement, parts);
  collectText(control?.officialEvidenceExamples, parts);
  collectText(control?.recommendedActions, parts);
  collectText(control?.riskIfMissing, parts);
  collectText(control?.searchHints, parts);
  collectText(control?.searchEntries, parts);
  collectText(control?.searchIntents, parts);
  collectText(control?.officialChecks, parts);
  return compactSearchText(parts.join(" "));
}

function tokenizeCompact(compact) {
  const found = [];
  let index = 0;
  while (index < compact.length) {
    let matched = "";
    for (const term of LEXICON) {
      if (compact.startsWith(term, index)) {
        matched = term;
        break;
      }
    }
    if (matched) {
      found.push(matched);
      index += matched.length;
    } else {
      index += 1;
    }
  }
  return found;
}

function normalizeQueryPart(part) {
  let value = compactSearchText(part);
  // Lightweight handling for common Korean particles/endings in natural
  // questions. This is intentionally conservative; official content remains
  // the source of truth and this only broadens candidate retrieval.
  const endings = ["해주세요", "인가요", "입니다", "합니다", "했어요", "해요", "되어", "됐다", "있음", "없음"];
  for (const ending of endings) {
    if (value.length > ending.length + 1 && value.endsWith(ending)) {
      value = value.slice(0, -ending.length);
      break;
    }
  }
  for (const particle of ["에서", "으로", "라고", "까지", "부터", "이", "가", "을", "를", "은", "는", "의", "에", "로", "도", "만"]) {
    if (value.length > particle.length + 1 && value.endsWith(particle)) {
      value = value.slice(0, -particle.length);
      break;
    }
  }
  return value;
}

export function queryTokens(query) {
  const raw = String(query || "").trim().toLowerCase().normalize("NFC");
  if (!raw) return [];
  const spaced = raw
    .split(/[\s,./·]+/)
    .map(normalizeQueryPart)
    .filter((part) => part.length >= 2);
  if (spaced.length > 1) {
    // Users often paste a rough list ("불필요한, 불필요한 계정") rather
    // than an official control name. Extract known concepts from every
    // fragment so Korean particles and repeated phrases do not make an AND
    // query impossible to satisfy.
    const concepts = spaced.flatMap((part) => {
      const parsed = tokenizeCompact(part);
      return parsed.length ? parsed : [part];
    });
    return [...new Set(concepts)];
  }
  const compact = compactSearchText(raw);
  const greedy = tokenizeCompact(compact);
  if (greedy.length >= 2) return [...new Set(greedy)];
  return compact ? [compact] : [];
}

function expandToken(token) {
  const compact = compactSearchText(token);
  const group = SYNONYM_LOOKUP.get(compact);
  if (!group) return [compact];
  return [...new Set(group.map((item) => compactSearchText(item)))];
}

function haystackHasToken(haystack, token) {
  return expandToken(token).some((variant) => variant && haystack.includes(variant));
}

function intentMatchScore(control, query) {
  const compactQuery = compactSearchText(query);
  if (!compactQuery) return 0;
  return (control?.searchIntents || []).reduce((best, intent) => {
    const concepts = [...new Set((intent?.concepts || []).map(compactSearchText).filter(Boolean))];
    if (!concepts.length) return best;
    const hits = concepts.filter((concept) => compactQuery.includes(concept)).length;
    const required = concepts.length === 1 ? 1 : Math.min(2, concepts.length);
    if (hits < required) return best;
    const coverage = hits / concepts.length;
    const specificity = Math.min(concepts.reduce((sum, concept) => sum + concept.length, 0), 18) / 18;
    const weight = Math.max(0, Math.min(100, Number(intent?.weight) || 0));
    return Math.max(best, 42 + (coverage * 28) + (specificity * 12) + (weight * 0.18));
  }, 0);
}

const DISTINCTIVE_INTENT_TOKENS = new Set([
  "재직", "계약", "계약종료", "계약만료", "직무변경", "필요성", "잔존", "퇴사", "퇴직", "외주",
]);

function matchesDistinctiveIntent(control, tokens) {
  if (tokens.length < 3) return false;
  const entries = (control?.searchEntries || []).filter(
    (entry) => Number(entry?.weight) >= 90 && entry?.text,
  );
  return entries.some((entry) => {
    const entryText = compactSearchText(entry.text);
    return tokens.some(
      (token) => DISTINCTIVE_INTENT_TOKENS.has(token) && haystackHasToken(entryText, token),
    );
  });
}

function longestCommonSubstringLength(left, right) {
  if (!left || !right) return 0;
  const rows = left.length;
  const cols = right.length;
  let best = 0;
  let prev = new Array(cols + 1).fill(0);
  for (let i = 1; i <= rows; i += 1) {
    const next = new Array(cols + 1).fill(0);
    for (let j = 1; j <= cols; j += 1) {
      if (left[i - 1] === right[j - 1]) {
        next[j] = prev[j - 1] + 1;
        if (next[j] > best) best = next[j];
      }
    }
    prev = next;
  }
  return best;
}

export function matchesControlSearch(control, query) {
  const raw = String(query || "").trim();
  if (!raw) return true;
  const compactQuery = compactSearchText(raw);
  if (!compactQuery) return true;
  const haystack = controlSearchHaystack(control);
  if (haystack.includes(compactQuery)) return true;
  const controlId = String(control?.id || "").toLowerCase();
  if (controlId && controlId.includes(raw.toLowerCase())) return true;
  if (/^\d+(\.\d+)*$/.test(raw) && compactSearchText(controlId) === compactQuery) return true;
  const tokens = queryTokens(raw);
  if (intentMatchScore(control, raw) >= 60) return true;
  if (tokens.length >= 2) {
    const hits = tokens.filter((token) => haystackHasToken(haystack, token)).length;
    if (matchesDistinctiveIntent(control, tokens)) return true;
    // Two-word searches stay strict. Longer natural-language searches may
    // include conversational filler, so two strong concepts and 60% coverage
    // are enough to show a candidate.
    return tokens.length === 2
      ? hits === 2
      : hits >= 2 && hits / tokens.length >= 0.6;
  }
  if (compactQuery.length >= 6) {
    const overlap = longestCommonSubstringLength(compactQuery, haystack);
    return overlap >= Math.min(6, Math.ceil(compactQuery.length * 0.65));
  }
  return haystack.includes(compactQuery);
}

export function controlSearchScore(control, query) {
  const raw = String(query || "").trim();
  if (!raw) return 0;
  const compactQuery = compactSearchText(raw);
  const title = compactSearchText(control?.title);
  const idCompact = compactSearchText(control?.id);
  if (idCompact === compactQuery || String(control?.id || "").toLowerCase() === raw.toLowerCase()) {
    return 100;
  }
  if (title.includes(compactQuery)) return 90;
  const tokens = queryTokens(raw);
  const structuredIntent = intentMatchScore(control, raw);
  const hints = (control?.searchHints || []).map((hint) => compactSearchText(hint));
  const weightedEntries = (control?.searchEntries || [])
    .map((entry) => ({
      text: compactSearchText(entry?.text),
      weight: Math.max(0, Math.min(100, Number(entry?.weight) || 0)),
    }))
    .filter((entry) => entry.text);
  const weightedExact = weightedEntries
    .filter((entry) => entry.text.includes(compactQuery))
    .reduce((best, entry) => Math.max(best, entry.weight), 0);
  if (weightedExact) return Math.max(70 + Math.round(weightedExact * 0.2), Math.round(structuredIntent));
  // A finding can contain both the observed state and the reason for review.
  // Prefer the intent phrase covering the most query concepts so account
  // deletion, employment changes, and contract expiry remain distinguishable.
  const weightedIntent = weightedEntries.reduce((best, entry) => {
    if (!tokens.length) return best;
    const hits = tokens.filter((token) => haystackHasToken(entry.text, token)).length;
    if (!hits) return best;
    const coverage = hits / tokens.length;
    const specificity = Math.min(hits, 3) / 3;
    return Math.max(best, (coverage * 38) + (specificity * 22) + (entry.weight * 0.18));
  }, 0);
  const hintHit = hints.some((hint) => hint.includes(compactQuery));
  if (hintHit) return Math.max(90, Math.round(structuredIntent));
  const titleHits = tokens.filter((token) => haystackHasToken(title, token)).length;
  const hintHits = tokens.filter((token) => hints.some((hint) => haystackHasToken(hint, token))).length;
  const haystack = controlSearchHaystack(control);
  const allHits = tokens.filter((token) => haystackHasToken(haystack, token)).length;
  if (tokens.length && titleHits === tokens.length) return Math.max(82, Math.round(weightedIntent));
  if (tokens.length && hintHits === tokens.length) return Math.max(76, Math.round(weightedIntent));
  if (tokens.length && allHits === tokens.length) return Math.max(64, Math.round(weightedIntent));
  return Math.max(
    Math.round(structuredIntent),
    Math.round(weightedIntent),
    allHits ? 35 + Math.round((allHits / tokens.length) * 20) : 0,
  );
}

export function rankControlsBySearch(controls, query) {
  const items = Array.isArray(controls) ? controls : [];
  if (!String(query || "").trim()) return items;
  return [...items].sort((left, right) => {
    const diff = controlSearchScore(right, query) - controlSearchScore(left, query);
    if (diff) return diff;
    return String(left.id).localeCompare(String(right.id), "en", { numeric: true });
  });
}
