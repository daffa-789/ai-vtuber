// HuoHuo Live2D & Companion Controller
let app = null;
let currentModel = null;
let bubbleTimeout = null;

// Konfigurasi posisi avatar sesuai kalibrasi proyek
const CONFIG = {
  zoom: 1.85,
  x: 0.5,
  jangkar: 0.92,
  headY: 0.46,
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

// ── Fungsi yang dipanggil dari Python / Bridge ──────────────────────────────

// Pemetaan tag emosi -> ekspresi/motion HuoHuo (lihat huohuo.model3.json).
const HUOHUO_EXPR = {
  senyum: "senyum", goda: "senyum", sebal: "sebal", kaget: "kaget",
  bingung: "bingung", lelah: "qizi1", semangat: "semangat", sedih: "sedih",
  netral: "qizi1",
};
const HUOHUO_MOTION = {
  kaget: "head", semangat: "greeting", senyum: "greeting",
  goda: "curious", bingung: "curious", lelah: "sleepy",
};

window.setExpression = function(name) {
  if (!currentModel) return;
  try {
    const expr = HUOHUO_EXPR[name] || name;
    if (expr) currentModel.expression(expr);
    const motion = HUOHUO_MOTION[name];
    if (motion && currentModel.motion) currentModel.motion(motion);
  } catch (e) {
    console.log("[Live2D] Expression:", name);
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

window.showBubble = function(text, emotion = "SENYUM") {
  const bubble = document.getElementById("speech-bubble");
  const tag = document.getElementById("emotion-tag");
  const txt = document.getElementById("bubble-text");

  if (!bubble || !txt) return;

  tag.textContent = (emotion || "SENYUM").toUpperCase();
  txt.textContent = text;
  bubble.classList.remove("hidden");

  if (bubbleTimeout) clearTimeout(bubbleTimeout);
  bubbleTimeout = setTimeout(() => {
    bubble.classList.add("hidden");
  }, Math.max(4000, text.length * 90));
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
  // Tampilkan gelembung sementara
  window.showBubble("...", "SEBAL");

  if (window.pywebview?.api?.send_message) {
    window.pywebview.api.send_message(text);
  } else {
    console.log("[Chat] Mengirim pesan ke Python:", text);
  }
}

function sendQuickAction(action) {
  if (action === "headpat") {
    window.showBubble("*dielus kepalanya*", "KAGET");
    window.setExpression("kaget");
    if (window.pywebview?.api?.touch_head) {
      window.pywebview.api.touch_head();
    }
  } else if (action === "puji") {
    const input = document.getElementById("chat-input");
    if (input) {
      input.value = "Kamu manis banget hari ini, HuoHuo.";
      handleSend();
    }
  } else if (action === "mabar") {
    const input = document.getElementById("chat-input");
    if (input) {
      input.value = "Mabar game bareng yuk!";
      handleSend();
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("chat-input");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleSend();
    });
  }
  initLive2D();
});
