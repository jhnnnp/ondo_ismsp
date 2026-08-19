(function () {
  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  const label = toggle ? toggle.querySelector(".visually-hidden") : null;
  const header = document.getElementById("header");
  const navLinks = document.querySelectorAll("[data-nav-link]");
  const sections = ["workflow", "product", "results", "report"]
    .map(function (id) { return document.getElementById(id); })
    .filter(Boolean);

  function setNavOpen(open) {
    if (!toggle || !nav) return;
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (label) label.textContent = open ? "메뉴 닫기" : "메뉴 열기";
    if (open) nav.querySelector("a")?.focus();
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      setNavOpen(!nav.classList.contains("is-open"));
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setNavOpen(false);
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("is-open")) {
        setNavOpen(false);
        toggle.focus();
      }
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) setNavOpen(false);
    });
  }

  document.querySelectorAll("[data-dialog]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      const dialog = document.getElementById(trigger.getAttribute("data-dialog") || "");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    });
  });

  function syncHeader() {
    if (header) header.classList.toggle("is-scrolled", window.scrollY > 12);
  }

  function syncNavActive() {
    if (!navLinks.length || !sections.length) return;
    const offset = (header ? header.offsetHeight : 76) + 48;
    let current = sections[0].id;
    sections.forEach(function (section) {
      const top = section.getBoundingClientRect().top;
      if (top - offset <= 0) current = section.id;
    });
    navLinks.forEach(function (link) {
      const href = link.getAttribute("href") || "";
      link.classList.toggle("is-active", href === "#" + current);
    });
  }

  syncHeader();
  syncNavActive();
  window.addEventListener("scroll", function () {
    syncHeader();
    syncNavActive();
  }, { passive: true });

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealNodes = document.querySelectorAll("[data-reveal]");

  function markVisible(node) {
    node.classList.add("is-visible");
  }

  function animateBars(list) {
    list.classList.add("is-animated");
    const tracks = list.hasAttribute("data-bar")
      ? [list]
      : Array.prototype.slice.call(list.querySelectorAll("[data-bar]"));
    tracks.forEach(function (track, index) {
      const bar = track.matches("b") ? track : track.querySelector("b");
      const value = track.getAttribute("data-bar") || "0";
      if (!bar) return;
      bar.style.setProperty("--bar-width", value + "%");
      bar.style.transitionDelay = (index * 180) + "ms";
    });
  }

  function setCountValue(el, value) {
    const suffix = el.getAttribute("data-suffix") || "";
    el.textContent = String(value) + suffix;
  }

  function animateCounters(root) {
    const nodes = root.hasAttribute("data-count")
      ? [root]
      : Array.prototype.slice.call(root.querySelectorAll("[data-count]"));
    nodes.forEach(function (el) {
      if (el.dataset.animated === "true") return;
      el.dataset.animated = "true";
      const target = Number(el.getAttribute("data-count") || "0");
      const duration = 900;
      const start = performance.now();
      setCountValue(el, 0);
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setCountValue(el, Math.round(target * eased));
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  if (reduceMotion || typeof IntersectionObserver !== "function") {
    revealNodes.forEach(markVisible);
    document.querySelectorAll(".process-track").forEach(markVisible);
    document.querySelectorAll(".temperature-list, .report-temp-bar").forEach(animateBars);
    document.querySelectorAll("[data-count]").forEach(function (el) {
      setCountValue(el, Number(el.getAttribute("data-count") || "0"));
    });
  } else {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
        if (entry.target.hasAttribute("data-count") || entry.target.querySelector("[data-count]")) {
          animateCounters(entry.target);
        }
        entry.target.querySelectorAll(".temperature-list, .report-temp-bar").forEach(animateBars);
        if (entry.target.classList.contains("temperature-list")) animateBars(entry.target);
        if (entry.target.hasAttribute("data-priority-cycle")) cyclePriority(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });

    revealNodes.forEach(function (node) {
      observer.observe(node);
    });

    document.querySelectorAll(".temperature-list").forEach(function (list) {
      if (list.closest("[data-reveal]")) return;
      observer.observe(list);
    });
  }

  if (!reduceMotion) {
    document.querySelectorAll("[data-tilt]").forEach(function (card) {
      card.addEventListener("mousemove", function (event) {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = "perspective(900px) rotateX(" + (-y * 2) + "deg) rotateY(" + (x * 2) + "deg)";
      });
      card.addEventListener("mouseleave", function () {
        card.style.transform = "";
      });
    });
    bindHeroSpot();
    bindHeroDemo();
  }

  bindProductDemo(reduceMotion);

  function bindHeroSpot() {
    const hero = document.getElementById("hero");
    const spot = hero ? hero.querySelector(".hero-spot") : null;
    if (!hero || !spot) return;
    hero.addEventListener("pointermove", function (event) {
      const rect = hero.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;
      spot.style.setProperty("--spot-x", x + "%");
      spot.style.setProperty("--spot-y", y + "%");
    });
  }

  function bindHeroDemo() {
    const stage = document.querySelector("[data-hero-demo]");
    if (!stage) return;
    const scenes = [
      {
        row: "0",
        question: "경영진의 정보보호 관리체계 참여 및 의사결정 여부",
        note: "경영진 보고 주기, 의사결정 기록, 자원 배정 근거가 남아 있는지 확인합니다.",
        status: "unknown",
        statusLabel: "미확인",
        statusBar: "8%",
        temp: 7,
        kpis: { open: 91, partial: 6, done: 4 },
        next: "1.1.2 최고책임자 지정"
      },
      {
        row: "1",
        question: "정보보호 최고책임자의 공식 지정 여부",
        note: "임명 문서, 역할과 책임, 자격요건이 남아 있는지 확인합니다.",
        status: "unknown",
        statusLabel: "미확인",
        statusBar: "18%",
        temp: 25,
        kpis: { open: 72, partial: 8, done: 21 },
        next: "1.2.4 보호대책 선정"
      },
      {
        row: "2",
        question: "위험평가 결과를 반영한 보호대책 선정 여부",
        note: "선정 기준, 책임자, 일정과 이행 현황이 문서에 남아 있는지 확인합니다.",
        status: "partial",
        statusLabel: "부분 이행",
        statusBar: "46%",
        temp: 55,
        kpis: { open: 41, partial: 9, done: 51 },
        next: "1.2.5 보호대책 구현"
      },
      {
        row: "3",
        question: "선정 보호대책의 계획 대비 구현 여부",
        note: "구현 일정, 담당 부서, 완료 증적이 통제와 연결되어 있는지 확인합니다.",
        status: "done",
        statusLabel: "이행",
        statusBar: "88%",
        temp: 80,
        kpis: { open: 16, partial: 9, done: 76 },
        next: "1.3.1 자원 할당"
      }
    ];

    const rows = stage.querySelectorAll("[data-demo-row]");
    const question = stage.querySelector("[data-demo-question]");
    const note = stage.querySelector("[data-demo-note]");
    const statuses = stage.querySelectorAll("[data-demo-status]");
    const temps = stage.querySelectorAll("[data-demo-temp]");
    const gauge = stage.querySelector("[data-demo-gauge]");
    const tempBar = stage.querySelector("[data-demo-temp-bar]");
    const tempChip = stage.querySelector(".preview-fact-top");
    const bandLabels = stage.querySelectorAll("[data-demo-temp-band-label]");
    const statusLabel = stage.querySelector("[data-demo-status-label]");
    const statusBar = stage.querySelector("[data-demo-status-bar]");
    const statusChip = stage.querySelector("[data-demo-status-chip]");
    const next = stage.querySelector("[data-demo-next]");
    const cursor = stage.querySelector("[data-demo-cursor]");
    const mockApp = stage.querySelector(".mock-app");
    const kpis = {
      open: stage.querySelector('[data-demo-kpi="open"]'),
      partial: stage.querySelector('[data-demo-kpi="partial"]'),
      done: stage.querySelector('[data-demo-kpi="done"]')
    };

    let index = 0;
    let stepTimer = 0;
    let loopTimer = 0;
    let playing = false;

    function temperatureBand(value) {
      const n = Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
      if (n >= 80) return { key: "ready", label: "준비" };
      if (n >= 55) return { key: "rising", label: "상승" };
      if (n >= 25) return { key: "warming", label: "예열" };
      return { key: "cold", label: "냉랭" };
    }

    function setTemp(value) {
      const band = temperatureBand(value);
      temps.forEach(function (el) { el.textContent = String(value); });
      bandLabels.forEach(function (el) { el.textContent = band.label; });
      if (gauge) {
        gauge.style.setProperty("--temp", String(value));
        gauge.setAttribute("data-temp-band", band.key);
      }
      if (tempChip) tempChip.setAttribute("data-temp-band", band.key);
      if (tempBar) tempBar.style.width = value + "%";
    }

    function placeCursor(row) {
      if (!cursor || !row || !mockApp) return;
      const appRect = mockApp.getBoundingClientRect();
      const rowRect = row.getBoundingClientRect();
      cursor.style.left = (rowRect.left - appRect.left + 16) + "px";
      cursor.style.top = (rowRect.top - appRect.top + rowRect.height / 2) + "px";
    }

    function applySelect(scene) {
      let selected = null;
      rows.forEach(function (row) {
        const on = row.getAttribute("data-demo-row") === scene.row;
        row.classList.toggle("is-selected", on);
        if (on) selected = row;
      });
      requestAnimationFrame(function () {
        placeCursor(selected);
      });
      if (question) {
        question.classList.remove("is-swapping");
        void question.offsetWidth;
        question.textContent = scene.question;
        question.classList.add("is-swapping");
      }
      if (note) note.textContent = scene.note;
      if (next) next.textContent = scene.next;
    }

    function applyResult(scene) {
      statuses.forEach(function (el) {
        el.classList.toggle("is-on", el.getAttribute("data-demo-status") === scene.status);
      });
      if (statusLabel) statusLabel.textContent = scene.statusLabel;
      if (statusBar) statusBar.style.width = scene.statusBar;
      if (statusChip) statusChip.setAttribute("data-state", scene.status);
      setTemp(scene.temp);
      Object.keys(kpis).forEach(function (key) {
        if (kpis[key]) kpis[key].textContent = String(scene.kpis[key]);
      });
    }

    function playScene() {
      if (!playing) return;
      const scene = scenes[index];
      applySelect(scene);
      window.clearTimeout(stepTimer);
      stepTimer = window.setTimeout(function () {
        if (!playing) return;
        applyResult(scene);
        index = (index + 1) % scenes.length;
        loopTimer = window.setTimeout(playScene, 2200);
      }, 900);
    }

    function start() {
      if (playing) return;
      playing = true;
      playScene();
    }

    function stop() {
      playing = false;
      window.clearTimeout(stepTimer);
      window.clearTimeout(loopTimer);
    }

    if (typeof IntersectionObserver === "function") {
      const watcher = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) start();
          else stop();
        });
      }, { threshold: 0.35 });
      watcher.observe(stage);
    } else {
      start();
    }

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop();
      else if (stage.getBoundingClientRect().top < window.innerHeight) start();
    });
    window.addEventListener("resize", function () {
      placeCursor(stage.querySelector("[data-demo-row].is-selected"));
    });
  }

  function bindProductDemo(reduceMotion) {
    const stage = document.querySelector("[data-product-demo]");
    if (!stage) return;
    const controlName = stage.querySelector("[data-demo-control-name]");
    const controlId = stage.querySelector("[data-demo-control-id]");
    const controlNote = stage.querySelector("[data-demo-control-note]");
    const status = stage.querySelector("[data-demo-card-status]");
    const question = stage.querySelector("[data-demo-product-question]");
    const note = stage.querySelector("[data-demo-product-note]");
    const criteria = Array.prototype.slice.call(stage.querySelectorAll("[data-demo-criterion]"));
    const criterionTexts = Array.prototype.slice.call(stage.querySelectorAll("[data-demo-criterion-text]"));
    const evidences = Array.prototype.slice.call(stage.querySelectorAll("[data-demo-evidence]"));
    const lawTitle = stage.querySelector("[data-demo-law-title]");
    const lawNote = stage.querySelector("[data-demo-law-note]");
    const dots = Array.prototype.slice.call(stage.querySelectorAll("[data-product-dot]"));
    const scenes = [
      {
        controlId: "통제항목 2.5.1",
        controlName: "2.5.1 사용자 계정 관리",
        controlNote: "인증 및 권한관리 · 사용자 계정 관리",
        status: "부분 이행",
        state: "partial",
        question: "계정 발급·변경·삭제 절차 수립 및 승인 기록 보존 여부",
        note: "권한 매트릭스와 발급·회수 이력이 통제 기준과 맞는지 확인합니다.",
        criteria: [
          "계정 발급/변경/삭제 절차가 있다",
          "관리자/특권 계정은 별도 승인 후 발급한다",
          "주기적으로 계정/권한을 점검한다"
        ],
        evidence: ["계정 발급 대장", "권한 매트릭스", "승인 기록"],
        lawTitle: "개인정보 보호법 제29조",
        lawNote: "안전조치의무 · 고시 제5조 접근 권한의 관리",
        focus: 0
      },
      {
        controlId: "통제항목 2.6.4",
        controlName: "2.6.4 데이터베이스 접근",
        controlNote: "접근통제 · 데이터베이스 접근",
        status: "미점검",
        state: "unknown",
        question: "운영 DB 직접 접근 최소화 및 접속 기록 보존 여부",
        note: "업무별 DB 계정 분리와 쿼리 기록이 통제와 연결되어 있는지 검토합니다.",
        criteria: [
          "DB 직접 접근이 최소화되어 있다",
          "DB 접근 계정이 업무별로 분리되어 있다",
          "DB 접속/쿼리 기록이 남는다"
        ],
        evidence: ["DB 접근 권한 목록", "접속/쿼리 로그", "방화벽 규칙"],
        lawTitle: "개인정보 보호법 제29조",
        lawNote: "안전조치의무 · 고시 제6조 접근통제",
        focus: 2
      },
      {
        controlId: "통제항목 3.1.1",
        controlName: "3.1.1 개인정보 수집/이용",
        status: "이행",
        state: "done",
        controlNote: "수집 시 보호조치 · 개인정보 수집/이용",
        question: "수집·이용 목적·동의와 실제 수집 항목의 일치 여부",
        note: "처리 목적별 법적 근거와 동의 고지사항이 현재 수집 항목과 일치하는지 확인합니다.",
        criteria: [
          "수집/이용 목적과 동의가 화면/문서에 맞다",
          "수집 항목과 실제 DB 컬럼이 일치한다",
          "목적 변경 시 재동의/고지 절차가 있다"
        ],
        evidence: ["동의 화면", "수집 항목 목록", "처리방침"],
        lawTitle: "개인정보 보호법 제15조",
        lawNote: "개인정보의 수집·이용 · 동의 또는 법령 근거",
        focus: 0
      }
    ];

    let index = 0;

    function swapText(el, value) {
      if (!el || el.textContent === value) return;
      el.textContent = value;
      if (reduceMotion) return;
      el.classList.remove("is-swapping");
      void el.offsetWidth;
      el.classList.add("is-swapping");
    }

    function applyScene(nextIndex) {
      index = (nextIndex + scenes.length) % scenes.length;
      const scene = scenes[index];
      swapText(controlId, scene.controlId);
      swapText(controlNote, scene.controlNote);
      swapText(controlName, scene.controlName);
      swapText(question, scene.question);
      if (note) note.textContent = scene.note;
      if (status) {
        status.textContent = scene.status;
        status.setAttribute("data-state", scene.state);
      }
      swapText(lawTitle, scene.lawTitle);
      swapText(lawNote, scene.lawNote);
      criterionTexts.forEach(function (el, i) {
        if (scene.criteria[i]) el.textContent = scene.criteria[i];
      });
      evidences.forEach(function (el, i) {
        if (scene.evidence[i]) el.textContent = scene.evidence[i];
      });
      criteria.forEach(function (el, i) {
        el.classList.toggle("is-linked", i === scene.focus);
      });
      dots.forEach(function (dot, i) {
        const on = i === index;
        dot.classList.toggle("is-on", on);
        dot.setAttribute("aria-selected", on ? "true" : "false");
        dot.tabIndex = on ? 0 : -1;
      });
    }

    dots.forEach(function (dot, i) {
      dot.addEventListener("click", function () {
        applyScene(i);
      });
    });

    const dotsWrap = stage.querySelector(".product-dots");
    if (dotsWrap) {
      dotsWrap.addEventListener("keydown", function (event) {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        applyScene(index + (event.key === "ArrowRight" ? 1 : -1));
        if (dots[index]) dots[index].focus();
      });
    }

    applyScene(0);
  }

  function cyclePriority(card) {
    const items = Array.prototype.slice.call(card.querySelectorAll("li"));
    if (items.length < 2) return;
    let index = 0;
    window.setInterval(function () {
      items.forEach(function (item, i) {
        item.classList.toggle("is-hot", i === index);
      });
      index = (index + 1) % items.length;
    }, 2200);
  }
})();
