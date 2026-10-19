// Silver Wolf Live2D & Companion Controller
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
    // Model Live2D Silver Wolf dimuat dari API local static server
    const modelUrl = "/api/model3.json";
    currentModel = await Live2DModel.from(modelUrl, { autoInteract: false });
    app.stage.addChild(currentModel);

    fitModel();
    window.addEventListener("resize", fitModel);
    setupPointerTracking();

    console.log("[Live2D] Model Silver Wolf berhasil dimuat!");
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

window.setExpression = function(name) {
  if (!currentModel) return;
  try {
    currentModel.expression(name);
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
      input.value = "Kamu manis banget hari ini, Silver Wolf.";
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
