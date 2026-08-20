import { bootstrap } from "./core/router.js";
import { initDesktopWorkspaceGate } from "./core/desktop-gate.js";

function start() {
  initDesktopWorkspaceGate();
  bootstrap();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
