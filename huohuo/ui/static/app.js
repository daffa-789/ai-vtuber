// HuoHuo Live2D & Companion Controller
let app = null;
let currentModel = null;
let bubbleTimeout = null;

// Konfigurasi posisi avatar sesuai kalibrasi proyek
const CONFIG = {
  zoom: 0.95,
  x: 0.5,
  jangkar: 0.5,
  headY: 0.22,
};

async function initLive2D() {
  const canvas = document.getElementById("live2d-canvas");
  if (!canvas) return;

  const { Application, Ticker } = PIXI;
  const { Live2DModel } = PIXI.live2d;

  Live2DModel.registerTicker(Ticker);

  app = new Application({
    view: canvas,
    resizeTo: window,
    backgroundAlpha: 0,
    antialias: true,
    autoDensity: true,
    resolution: Math.min(window.devicePixelRatio || 1, 2),
  });

  try {
    // Model Live2D HuoHuo dimuat dari API local static server
    const modelUrl = "/api/model3.json";
    currentModel = await Live2DModel.from(modelUrl, { autoInteract: false });
    app.stage.addChild(currentModel);

    fitModel();
    window.addEventListener("resize", fitModel);
    setupPointerTracking();

    console.log("[Live2D] Model HuoHuo berhasil dimuat!");
  } catch (err) {
    console.warn("[Live2D] Menjalankan dalam mode avatar visual fallback:", err);
    // Jika model file belum dimuat WebGL, tampilkan indikator interaksi
  }
}

function fitModel() {
  if (!currentModel || !app) return;
  const { width: W, height: H } = app.screen;
  const dasar = currentModel.internalModel;
  if (!dasar?.width || !dasar?.height) return;

  const skalaW = W / dasar.width;
  const skalaH = H / dasar.height;
  const skala = Math.min(skalaW, skalaH) * CONFIG.zoom;

  currentModel.scale.set(skala);
  currentModel.anchor.set(CONFIG.x, CONFIG.jangkar);
  currentModel.x = W * CONFIG.x;
  currentModel.y = H * CONFIG.jangkar;
}

function setupPointerTracking() {
  window.addEventListener("pointermove", (e) => {
    if (!currentModel?.internalModel?.focusController || !app) return;
    const canvas = app.view;
    const rect = canvas.getBoundingClientRect();

    const faceX = rect.left + rect.width * CONFIG.x;
    const faceY = rect.top + rect.height * CONFIG.headY;

    const dx = e.clientX - faceX;
    const dy = e.clientY - faceY;

    const spanLeft = Math.max(160, faceX * 0.85);
    const spanRight = Math.max(250, (window.innerWidth - faceX) * 0.7);
    const spanUp = Math.max(140, (faceY - rect.top) * 0.85);
    const spanDown = Math.max(160, (rect.bottom - faceY) * 0.85);

    let targetX = dx >= 0 ? dx / spanRight : dx / spanLeft;
    let targetY = dy <= 0 ? -dy / spanUp : -dy / spanDown;

    targetX = Math.max(-1, Math.min(1, targetX));
    targetY = Math.max(-1, Math.min(1, targetY));

    currentModel.internalModel.focusController.focus(targetX, targetY);
  });
}

// ── Elus kepala pakai pointer (head-pat via kursor) ─────────────────────────
const PAT = {
  cooldownMs: 6000, // jeda antar-respons ke otak biar nggak spam TTS/LLM
  strokePx: 44,     // jarak geser vertikal = satu "elus"
  active: false,
  lastY: 0,
  accum: 0,
  moved: 0,
  downX: 0,
  downY: 0,
  lastFire: 0,
};

// Area kepala dihitung dari posisi model (tengah horizontal, CONFIG.headY vertikal).
function headRegion() {
  const canvas = document.getElementById("live2d-canvas");
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  return {
    cx: rect.left + rect.width * CONFIG.x,
    cy: rect.top + rect.height * CONFIG.headY,
    rx: Math.max(70, rect.width * 0.16),
    ry: Math.max(58, rect.height * 0.12),
  };
}

function isOverHead(x, y) {
  const h = headRegion();
  if (!h) return false;
  const dx = (x - h.cx) / h.rx;
  const dy = (y - h.cy) / h.ry;
  return dx * dx + dy * dy <= 1;
}

function spawnHeart(x, y) {
  const host = document.getElementById("app");
  if (!host) return;
  const el = document.createElement("div");
  el.className = "pat-heart";
  el.textContent = "💗";
  el.style.left = x + "px";
  el.style.top = y + "px";
  host.appendChild(el);
  setTimeout(() => el.remove(), 900);
}

// Picu satu reaksi elus kepala (dipakai tombol & pointer). Cooldown mencegah
// banjir panggilan saat pointer digerak-gerakkan di atas kepala.
function triggerHeadpat() {
  const now = Date.now();
  if (now - PAT.lastFire < PAT.cooldownMs) return;
  PAT.lastFire = now;
  window.showBubble("...", "KAGET", 60000);
  window.setExpression("kaget");
  if (window.pywebview?.api?.touch_head) {
    window.pywebview.api.touch_head();
  }
}

function setupHeadPat() {
  const canvas = document.getElementById("live2d-canvas");
  if (!canvas) return;

  canvas.addEventListener("pointerdown", (e) => {
    if (!isOverHead(e.clientX, e.clientY)) return;
    PAT.active = true;
    PAT.lastY = e.clientY;
    PAT.accum = 0;
    PAT.moved = 0;
    PAT.downX = e.clientX;
    PAT.downY = e.clientY;
    canvas.style.cursor = "grabbing";
    e.preventDefault();
  });

  window.addEventListener("pointermove", (e) => {
    if (!PAT.active) {
      canvas.style.cursor = isOverHead(e.clientX, e.clientY) ? "grab" : "default";
      return;
    }
    PAT.moved = Math.max(
      PAT.moved,
      Math.hypot(e.clientX - PAT.downX, e.clientY - PAT.downY)
    );
    const step = Math.abs(e.clientY - PAT.lastY);
    PAT.lastY = e.clientY;
    if (isOverHead(e.clientX, e.clientY)) {
      PAT.accum += step;
      if (PAT.accum >= PAT.strokePx) {
        PAT.accum = 0;
        spawnHeart(e.clientX, e.clientY - 18);
        triggerHeadpat();
      }
    }
  });

  const endPat = () => {
    if (!PAT.active) return;
    PAT.active = false;
    canvas.style.cursor = "grab";
    // Klik/tap singkat di kepala (tanpa banyak gerak) = satu elusan.
    if (PAT.moved < 12 && isOverHead(PAT.downX, PAT.downY)) {
      spawnHeart(PAT.downX, PAT.downY - 18);
      triggerHeadpat();
    }
  };
  window.addEventListener("pointerup", endPat);
  window.addEventListener("pointercancel", endPat);
}

// ── Fungsi yang dipanggil dari Python / Bridge ──────────────────────────────

// Pemetaan tag emosi -> ekspresi HuoHuo. Model hanya punya beberapa wajah/efek
// (angry, cry, white_eyes, baozhen, qizi1=roh, qizi2=panji). Emosi tanpa wajah
// khusus memakai wajah dasar (reset) supaya tidak salah tempel efek aneh.
const HUOHUO_EXPR = {
  sebal: "angry", sedih: "cry", kaget: "white_eyes", bingung: "baozhen",
  semangat: "qizi2",
  senyum: "wajah", goda: "wajah", lelah: "wajah", netral: "wajah",
};
const HUOHUO_MOTION = {
  kaget: "head", semangat: "greeting", senyum: "greeting",
  goda: "curious", bingung: "curious", lelah: "sleepy", sedih: "spirit",
};

window.setExpression = function(name) {
  if (!currentModel) return;
  try {
    const expr = (name in HUOHUO_EXPR) ? HUOHUO_EXPR[name] : name;
    if (expr) {
      currentModel.expression(expr);
    } else {
      const em = currentModel.internalModel?.motionManager?.expressionManager;
      if (em && typeof em.resetExpression === "function") em.resetExpression(0);
    }
    const motion = HUOHUO_MOTION[name];
    if (motion && currentModel.motion) currentModel.motion(motion);
  } catch (e) {
    console.log("[Live2D] Expression:", name);
  }
};

// Memutar group motion Live2D dengan aman (abaikan group/index tak valid).
window.setMotion = function(group, index) {
  if (!currentModel || !currentModel.motion) return;
  try {
    if (typeof group !== "string" || group.length === 0) return;
    const opts = typeof index === "number" && index >= 0 ? { index: index } : undefined;
    currentModel.motion(group, opts);
  } catch (e) {
    console.log("[Live2D] Motion:", group, index);
  }
};

window.setMouthOpen = function(level) {
  if (!currentModel?.internalModel?.coreModel) return;
  try {
    currentModel.internalModel.coreModel.setParameterValueById(
      "ParamMouthOpenY",
      Math.max(0, Math.min(1, level))
    );
  } catch (e) {}
};

window.showBubble = function(text, emotion = "SENYUM", ms = null) {
  const bubble = document.getElementById("speech-bubble");
  const tag = document.getElementById("emotion-tag");
  const txt = document.getElementById("bubble-text");

  if (!bubble || !txt) return;

  tag.textContent = (emotion || "SENYUM").toUpperCase();
  txt.textContent = text;
  bubble.classList.remove("hidden");

  if (bubbleTimeout) clearTimeout(bubbleTimeout);
  const hold = (ms != null) ? ms : Math.max(4000, text.length * 90);
  bubbleTimeout = setTimeout(() => {
    bubble.classList.add("hidden");
  }, hold);
};

window.setKizunaStatus = function(statusText) {
  const badge = document.getElementById("status-badge");
  if (badge) badge.textContent = statusText;
};

// ── Voice-to-Voice (F2): kontrol mikrofon ───────────────────────────────────

window.setVoiceListening = function(active) {
  const btn = document.getElementById("mic-btn");
  if (!btn) return;
  if (active) {
    btn.classList.add("active");
    btn.setAttribute("aria-pressed", "true");
  } else {
    btn.classList.remove("active");
    btn.setAttribute("aria-pressed", "false");
  }
};

window.setVoiceStatus = function(statusText) {
  // textContent (bukan innerHTML) => bebas XSS, dirender sebagai teks literal.
  const badge = document.getElementById("status-badge");
  if (badge) badge.textContent = statusText;
};

window.onSpeechRecognized = function(text) {
  if (!text) return;
  const input = document.getElementById("chat-input");
  if (input) input.value = text;
  if (window.pywebview && window.pywebview.api && window.pywebview.api.send_message) {
    try {
      window.pywebview.api.send_message(text);
    } catch (e) {}
  }
};

function toggleMicrophone() {
  try {
    const api = window.pywebview && window.pywebview.api;
    if (api && typeof api.toggle_voice_input === "function") {
      const result = api.toggle_voice_input();
      if (result && typeof result.then === "function") {
        result.then(function (res) {
          if (res && typeof res.active === "boolean") window.setVoiceListening(res.active);
        }).catch(function () {});
      } else if (result && typeof result.active === "boolean") {
        window.setVoiceListening(result.active);
      }
    }
  } catch (e) {
    console.warn("[Voice] Gagal mengaktifkan mikrofon:", e);
  }
}

// ── Interaksi UI ke Python ──────────────────────────────────────────────────

function handleSend() {
  const input = document.getElementById("chat-input");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  // Tampilkan gelembung "sedang mengetik" yang bertahan sampai balasan datang
  // (balasan dari Python akan menimpanya + mengatur ulang timeout normal).
  window.showBubble("...", "SEBAL", 60000);

  if (window.pywebview?.api?.send_message) {
    window.pywebview.api.send_message(text);
  } else {
    console.log("[Chat] Mengirim pesan ke Python:", text);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("chat-input");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleSend();
    });
  }
  setupHeadPat();
  initLive2D();
});
