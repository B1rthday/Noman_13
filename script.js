/* Chapter 13 — The Birthday Mission. Vanilla JS, no dependencies, no network calls. */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduceMQ = window.matchMedia("(prefers-reduced-motion: reduce)");
  const reduced = () => reduceMQ.matches;

  const STEPS = ["intro", "goat", "emblem", "gallery", "chapter", "premiere"];
  const LABELS = { intro: "TRANSMISSION", goat: "MISSION 1 / 4", emblem: "MISSION 2 / 4", gallery: "MISSION 3 / 4", chapter: "MISSION 4 / 4", premiere: "THE PREMIERE" };
  const PHOTOS = [
    { src: "assets/photos/cousin-car.png", alt: "The birthday boy taking a mirror selfie in a showroom, a black sports car behind him", cap: "01 · Showroom mode" },
    { src: "assets/photos/cousin-drink.png", alt: "The birthday boy in a red jacket sipping a green bottle at a busy restaurant", cap: "02 · Caught mid-sip" },
  ];

  const state = { scene: "intro", busy: false, goatRevealed: false, charge: 0, unlocked: false, noteOpen: false, wishes: new Set(), musicOn: true, photoIndex: 0, lastFocus: null };
  const el = {
    scenes: $$("[data-scene]"), fill: $("[data-progress-fill]"), ptext: $("[data-progress-text]"), plabel: $("[data-progress-label]"),
    music: $("#music"), musicBtn: $('[data-action="toggle-music"]'), soundLabel: $("[data-sound-label]"),
    film: $("#film"), missing: $("[data-missing]"), ending: $("[data-ending]"), toast: $("[data-toast]"),
    lb: $("[data-lightbox]"), lbImg: $("[data-lb-img]"), lbCap: $("[data-lb-cap]"),
  };
  let toastTimer = 0, busyTimer = 0, shakeTimer = 0;

  /* ---------- helpers ---------- */
  function toast(msg) {
    clearTimeout(toastTimer); el.toast.textContent = msg; el.toast.hidden = false;
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, 3200);
  }
  function lockBriefly(ms) { state.busy = true; clearTimeout(busyTimer); busyTimer = setTimeout(() => { state.busy = false; }, ms); }
  function focusHeading(scene) {
    const h = $("[tabindex='-1']", scene); if (!h) return;
    try { h.focus({ preventScroll: true }); } catch { h.focus(); }
  }

  /* ---------- scene navigation ---------- */
  function go(to, { instant = false } = {}) {
    if (state.busy || to === state.scene) return;
    // Any real tap on navigation counts as the user gesture browsers need for audio.
    if (state.musicOn && to !== "premiere" && el.music.paused) playMusic();
    if (state.scene === "intro") el.musicBtn.classList.remove("attention");
    const next = el.scenes.find((s) => s.dataset.scene === to), prev = el.scenes.find((s) => s.dataset.scene === state.scene);
    if (!next) return;
    if (to === "premiere" && !(state.unlocked && state.noteOpen && state.wishes.size === 5)) { /* can't skip ahead */ if (!state.goatRevealed) return; }
    const dur = instant || reduced() ? 0 : 300;
    lockBriefly(dur + 420);
    const finish = () => {
      el.scenes.forEach((s) => { s.hidden = s !== next; s.classList.remove("is-leaving"); s.classList.toggle("is-active", s === next); });
      state.scene = to; document.body.dataset.step = to;
      const i = STEPS.indexOf(to);
      el.fill.style.width = (i / (STEPS.length - 1)) * 100 + "%";
      el.ptext.textContent = LABELS[to]; el.plabel.setAttribute("aria-label", "Progress: " + LABELS[to]);
      window.scrollTo({ top: 0, behavior: "auto" });
      focusHeading(next);
      if (to === "premiere") onEnterPremiere(); else if (prev && prev.dataset.scene === "premiere") onLeavePremiere();
    };
    if (dur && prev) { prev.classList.remove("is-active"); prev.classList.add("is-leaving"); setTimeout(finish, dur); } else finish();
  }

  /* ---------- goat mission ---------- */
  function revealGoat() {
    if (state.goatRevealed) return; state.goatRevealed = true;
    const fig = $("[data-evidence]"), img = $("[data-goat-img]");
    $("[data-goat-pre]").hidden = true; $("[data-goat-locked]").hidden = true; img.hidden = false;
    fig.classList.add("is-revealed");
    if (!reduced()) { fig.classList.add("is-freeze"); setTimeout(() => fig.classList.remove("is-freeze"), 1500); } else fig.classList.add("is-freeze");
    $("[data-goat-post]").hidden = false;
    setTimeout(() => $('[data-action="react-goat"]').focus({ preventScroll: true }), 80);
  }
  function reactGoat() {
    const sc = $("#goat"), reply = $("[data-goat-reply]");
    reply.textContent = "CASE CLOSED. NO FURTHER QUESTIONS. 🐐";
    if (!reduced()) { sc.classList.remove("shake"); void sc.offsetWidth; sc.classList.add("shake"); clearTimeout(shakeTimer); shakeTimer = setTimeout(() => sc.classList.remove("shake"), 650); }
    if (navigator.vibrate && !reduced()) { try { navigator.vibrate(40); } catch { /* ignore */ } }
  }

  /* ---------- emblem ---------- */
  function charge() {
    if (state.unlocked) return;
    state.charge = Math.min(3, state.charge + 1);
    const btn = $(".emblem"), ring = $("[data-ring]");
    btn.style.setProperty("--charge", String(state.charge / 3));
    ring.style.strokeDashoffset = String(565.5 * (1 - state.charge / 3));
    btn.setAttribute("aria-label", `Charge the birthday emblem. Charge ${state.charge} of 3.`);
    $("[data-charge-status]").textContent = `Charge ${state.charge} of 3`;
    if (!reduced()) { btn.classList.remove("pulse"); void btn.offsetWidth; btn.classList.add("pulse"); }
    const hint = $("[data-emblem-hint]");
    hint.textContent = state.charge === 1 ? "Good. Two more." : state.charge === 2 ? "One more tap…" : hint.textContent;
    if (state.charge === 3) unlock();
  }
  function unlock() {
    state.unlocked = true;
    const btn = $(".emblem"); btn.classList.add("is-open"); btn.setAttribute("aria-label", "Birthday emblem unlocked");
    $("[data-lock]").textContent = "UNLOCKED"; $("[data-emblem-hint]").hidden = true; $("#emblem-title").innerHTML = "Emblem <em>unlocked.</em>";
    const box = $("[data-unlock]"); box.hidden = false;
    $("[data-charge-status]").textContent = "Level 13 unlocked. Achievement unlocked: Survived another year of being annoying.";
    fx.burst(btn.getBoundingClientRect());
    setTimeout(() => $("button", box).focus({ preventScroll: true }), 120);
  }

  /* ---------- gallery ---------- */
  function openNote() {
    if (state.noteOpen) return; state.noteOpen = true;
    const b = $("[data-note-btn]"); b.setAttribute("aria-expanded", "true"); b.hidden = true;
    $("[data-note]").hidden = false; const n = $("[data-after-note]"); n.hidden = false;
    setTimeout(() => n.focus({ preventScroll: true }), 80);
  }
  function showPhoto(i) {
    state.photoIndex = (i + PHOTOS.length) % PHOTOS.length; const p = PHOTOS[state.photoIndex];
    el.lbImg.src = p.src; el.lbImg.alt = p.alt; el.lbCap.textContent = p.cap;
  }
  function openPhoto(i, trigger) {
    state.lastFocus = trigger || document.activeElement; showPhoto(i);
    if (typeof el.lb.showModal === "function") { if (!el.lb.open) el.lb.showModal(); } else el.lb.setAttribute("open", "");
    $(".lb-close", el.lb).focus();
  }
  function closePhoto() {
    if (el.lb.open && typeof el.lb.close === "function") el.lb.close(); else el.lb.removeAttribute("open");
  }
  el.lb.addEventListener("close", () => { if (state.lastFocus && document.contains(state.lastFocus)) state.lastFocus.focus({ preventScroll: true }); });
  el.lb.addEventListener("click", (e) => { if (e.target === el.lb) closePhoto(); });
  el.lb.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") showPhoto(state.photoIndex - 1); else if (e.key === "ArrowRight") showPhoto(state.photoIndex + 1); });
  let sx = 0, sy = 0;
  el.lb.addEventListener("touchstart", (e) => { sx = e.changedTouches[0].clientX; sy = e.changedTouches[0].clientY; }, { passive: true });
  el.lb.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy; if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) showPhoto(state.photoIndex + (dx < 0 ? 1 : -1)); }, { passive: true });

  /* ---------- wishes ---------- */
  function revealWish(btn) {
    if (btn.getAttribute("aria-expanded") === "true") return;
    btn.setAttribute("aria-expanded", "true"); $(".wish-x", btn).hidden = false;
    state.wishes.add($$(".wish").indexOf(btn)); updateWishes();
  }
  function updateWishes() {
    const n = state.wishes.size; $("[data-wish-count]").textContent = `${n} of 5 revealed`;
    if (n === 5) { $("[data-reveal-all]").hidden = true; const b = $("[data-after-wishes]"); const was = b.hidden; b.hidden = false; if (was) setTimeout(() => b.focus({ preventScroll: true }), 80); }
  }

  /* ---------- premiere & video ---------- */
  let videoOk = true, wasEnded = false;
  function onEnterPremiere() { el.film.load(); }
  function onLeavePremiere() { el.film.pause(); }
  el.film.addEventListener("error", () => showMissing(), true);
  $("source", el.film).addEventListener("error", () => showMissing());
  function showMissing() { videoOk = false; el.missing.hidden = false; el.film.hidden = true; }
  el.film.addEventListener("loadeddata", () => { videoOk = true; el.missing.hidden = true; el.film.hidden = false; });
  el.film.addEventListener("play", () => { pauseMusic(); });
  el.film.addEventListener("ended", () => {
    wasEnded = true; el.ending.hidden = false; resumeMusic();
    requestAnimationFrame(() => { el.ending.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "center" }); try { el.ending.focus({ preventScroll: true }); } catch { /* ignore */ } });
    fx.burst({ left: innerWidth * .3, top: innerHeight * .5, width: innerWidth * .4, height: 10 }, true);
  });

  /* ---------- music ---------- */
  function setMusicUI() {
    el.musicBtn.setAttribute("aria-pressed", String(state.musicOn));
    el.musicBtn.setAttribute("aria-label", state.musicOn ? "Turn background music off" : "Turn background music on");
    el.soundLabel.textContent = state.musicOn ? "Music on" : "Music off";
  }
  function pauseMusic() { el.music.pause(); }
  function resumeMusic() { if (state.musicOn && el.film.paused) playMusic(); }
  async function playMusic() {
    try { el.music.volume = 0.35; await el.music.play(); }
    catch { state.musicOn = false; setMusicUI(); toast("Couldn't start the music. Tap the music button to try again."); }
  }
  function toggleMusic() {
    state.musicOn = !state.musicOn; setMusicUI();
    if (!state.musicOn) pauseMusic(); else if (el.film.paused || el.film.ended) playMusic(); else toast("Music will return when the video ends.");
  }
  el.music.addEventListener("error", () => { if (state.musicOn) { state.musicOn = false; setMusicUI(); toast("Background music isn't available. Everything else still works."); } });

  /* ---------- replay ---------- */
  function replay() {
    if (state.busy) return;
    closePhoto();
    el.film.pause(); try { el.film.currentTime = 0; } catch { /* metadata not ready */ } el.film.load();
    el.ending.hidden = true; wasEnded = false;
    // goat
    state.goatRevealed = false; const fig = $("[data-evidence]"); fig.classList.remove("is-revealed", "is-freeze");
    $("[data-goat-img]").hidden = true; $("[data-goat-locked]").hidden = false; $("[data-goat-pre]").hidden = false; $("[data-goat-post]").hidden = true; $("[data-goat-reply]").textContent = ""; $("#goat").classList.remove("shake");
    // emblem
    state.charge = 0; state.unlocked = false; const em = $(".emblem"); em.classList.remove("is-open", "pulse"); em.style.setProperty("--charge", "0"); $("[data-ring]").style.strokeDashoffset = "565.5";
    em.setAttribute("aria-label", "Charge the birthday emblem. Charge 0 of 3."); $("[data-lock]").textContent = "LOCKED"; const hint = $("[data-emblem-hint]"); hint.hidden = false; hint.textContent = "Tap the 13 to charge it. Three taps should do it.";
    $("#emblem-title").innerHTML = "The emblem is <em>sealed.</em>"; $("[data-unlock]").hidden = true; $("[data-charge-status]").textContent = "";
    // gallery
    state.noteOpen = false; const nb = $("[data-note-btn]"); nb.hidden = false; nb.setAttribute("aria-expanded", "false"); $("[data-note]").hidden = true; $("[data-after-note]").hidden = true;
    // wishes
    state.wishes.clear(); $$(".wish").forEach((w) => { w.setAttribute("aria-expanded", "false"); $(".wish-x", w).hidden = true; });
    $("[data-reveal-all]").hidden = false; $("[data-after-wishes]").hidden = true; $("[data-wish-count]").textContent = "0 of 5 revealed";
    state.busy = false; go("intro", { instant: true });
    if (state.musicOn) playMusic();
  }

  /* ---------- delegated actions (one listener, no duplicates) ---------- */
  const actions = {
    go: (t) => go(t.dataset.to),
    "reveal-goat": revealGoat, "react-goat": reactGoat, charge,
    "open-photo": (t) => openPhoto(Number(t.dataset.index), t), "close-photo": closePhoto,
    "prev-photo": () => showPhoto(state.photoIndex - 1), "next-photo": () => showPhoto(state.photoIndex + 1),
    "open-note": openNote, wish: revealWish,
    "reveal-all-wishes": () => $$(".wish").forEach(revealWish),
    "toggle-music": toggleMusic, replay,
  };
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-action]"); if (!t || t.disabled) return;
    const fn = actions[t.dataset.action]; if (fn) fn(t.dataset.action === "go" || t.dataset.action === "open-photo" || t.dataset.action === "wish" ? t : undefined);
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) { if (!el.music.paused) { el.music.pause(); el.music.dataset.autoPaused = "1"; } } else if (el.music.dataset.autoPaused) { delete el.music.dataset.autoPaused; resumeMusic(); } });

  /* ---------- particles: ambient dust + celebration bursts ---------- */
  const fx = (() => {
    const cv = $("#fx"), ctx = cv.getContext("2d"); let W = 0, H = 0, dpr = 1, dust = [], bits = [], raf = 0, last = 0;
    const COLORS = ["#e8be6a", "#ffe4a0", "#faf3e6", "#ff9a6b", "#c9963e"];
    const slow = (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) || (navigator.deviceMemory && navigator.deviceMemory <= 4);
    function size() { dpr = Math.min(window.devicePixelRatio || 1, slow ? 1 : 1.5); W = innerWidth; H = innerHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    function seed() { const n = reduced() ? 0 : Math.round(Math.min(56, Math.max(18, W / 22)) * (slow ? 0.6 : 1)); dust = Array.from({ length: n }, () => ({ x: Math.random() * W, y: Math.random() * H, r: 0.6 + Math.random() * 1.9, v: 5 + Math.random() * 16, ph: Math.random() * 6.28, w: 0.4 + Math.random() })); }
    function frame(ts) {
      raf = 0; const dt = Math.min(0.05, (ts - last) / 1000 || 0.016); last = ts;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const p of dust) { p.y -= p.v * dt; p.x += Math.sin(ts / 1000 * p.w + p.ph) * 0.25; if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W; } ctx.globalAlpha = 0.25 + 0.4 * (0.5 + 0.5 * Math.sin(ts / 700 * p.w + p.ph)); ctx.fillStyle = "#e8be6a"; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill(); }
      ctx.globalCompositeOperation = "source-over";
      for (let i = bits.length - 1; i >= 0; i--) {
        const b = bits[i]; b.vy += 900 * dt; b.vx *= 0.992; b.x += b.vx * dt; b.y += b.vy * dt; b.rot += b.vr * dt; b.life -= dt;
        if (b.life <= 0 || b.y > H + 30) { bits.splice(i, 1); continue; }
        ctx.save(); ctx.globalAlpha = Math.min(1, b.life * 1.4); ctx.translate(b.x, b.y); ctx.rotate(b.rot); ctx.scale(1, Math.abs(Math.cos(b.rot * 1.7)) * 0.8 + 0.2); ctx.fillStyle = b.c; ctx.fillRect(-b.w / 2, -b.h / 2, b.w, b.h); ctx.restore();
      }
      ctx.globalAlpha = 1; schedule();
    }
    function schedule() { if (!raf && !document.hidden && (dust.length || bits.length)) raf = requestAnimationFrame(frame); }
    function burst(rect, big) {
      if (reduced()) return;
      const n = Math.min(big ? 90 : 70, slow ? 50 : 110), cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
      for (let i = 0; i < n; i++) { const a = Math.random() * 6.283, v = 220 + Math.random() * 520; bits.push({ x: cx, y: cy, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 320, w: 6 + Math.random() * 7, h: 3 + Math.random() * 5, rot: Math.random() * 6, vr: (Math.random() - 0.5) * 14, life: 1.6 + Math.random() * 1.4, c: COLORS[(Math.random() * COLORS.length) | 0] }); }
      if (bits.length > 220) bits.splice(0, bits.length - 220);
      schedule();
    }
    addEventListener("resize", () => { size(); seed(); schedule(); });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) schedule(); });
    reduceMQ.addEventListener?.("change", () => { seed(); if (reduced()) { ctx.clearRect(0, 0, W, H); bits.length = 0; } schedule(); });
    size(); seed(); schedule();
    return { burst };
  })();

  /* ---------- init ---------- */
  setMusicUI(); el.ptext.textContent = LABELS.intro;
  el.musicBtn.classList.add("attention");
  if (reduced()) document.documentElement.classList.add("reduce-motion");
})();
