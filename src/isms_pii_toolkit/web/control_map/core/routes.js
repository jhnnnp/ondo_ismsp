export const APP_BASE = "/workspace";
export const LEGACY_APP_BASE = "/controls/map";

export const ROUTES = {
  sessions: {
    id: "sessions",
    path: APP_BASE,
    title: "진단 관리",
  },
  scope: {
    id: "scope",
    path: `${APP_BASE}/scope`,
    title: "점검 범위",
  },
  assessment: {
    id: "assessment",
    path: `${APP_BASE}/assessment`,
    title: "자가진단",
    workspace: "assessment",
  },
  results: {
    id: "results",
    path: `${APP_BASE}/results`,
    title: "진단 결과",
    workspace: "results",
  },
  evidence: {
    id: "evidence",
    path: `${APP_BASE}/evidence`,
    title: "증적 관리",
    workspace: "evidence",
  },
  report: {
    id: "report",
    path: `${APP_BASE}/report`,
    title: "보고서",
    workspace: "report",
  },
};

export const CONTROL_MAP_PAGES = Object.keys(ROUTES);

let applyRouteHandler = null;

export function setRouteHandler(handler) {
  applyRouteHandler = handler;
}

export function normalizePath(pathname) {
  const path = String(pathname || "").replace(/\/+$/, "");
  return path || "/";
}

function canonicalPath(pathname) {
  const path = normalizePath(pathname);
  if (path === LEGACY_APP_BASE || path.startsWith(`${LEGACY_APP_BASE}/`)) {
    return APP_BASE + path.slice(LEGACY_APP_BASE.length);
  }
  return path;
}

export function parsePath(pathname = globalThis.location?.pathname) {
  const path = canonicalPath(pathname);
  if (path === `${APP_BASE}/sessions`) return ROUTES.sessions;
  if (path === `${APP_BASE}/dashboard`) return ROUTES.assessment;
  return Object.values(ROUTES).find((route) => normalizePath(route.path) === path) || null;
}

export function navigateTo(routeId, options = {}) {
  applyRouteHandler?.(routeId, options);
}
