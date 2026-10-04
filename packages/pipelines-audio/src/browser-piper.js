import * as ort from "onnxruntime-web";
import { TtsSession } from "@mintplex-labs/piper-tts-web";

function lockWasmThreads(env) {
  if (!env?.wasm) return;
  try {
    Object.defineProperty(env.wasm, "numThreads", {
      get: () => 1,
      set: () => {},
      configurable: true,
      enumerable: true
    });
  } catch {}
}

lockWasmThreads(ort.env);

class BrowserPiper {
  session;
  modelUrl;
  configUrl;
  voice;

  constructor(options = {}) {
    this.modelUrl = options.modelUrl ?? "/assets/piper/id_ID-news_tts-medium.onnx";
    this.configUrl = options.configUrl ?? `${this.modelUrl}.json`;
    this.voice = options.voice ?? "en_US-hfc_female-medium";

    if (ort.env?.wasm) {
      ort.env.wasm.wasmPaths = "/onnx/";
      lockWasmThreads(ort.env);
    }
  }

  create() {
    this.session ??= (async () => {
      lockWasmThreads(ort.env);
      if (ort.env?.wasm) {
        ort.env.wasm.wasmPaths = "/onnx/";
      }

      // Pastikan onnxruntime-web/wasm juga terkunci single-thread
      try {
        const ortWasm = await import("onnxruntime-web/wasm");
        const instance = ortWasm.default || ortWasm;
        lockWasmThreads(instance.env);
        if (instance.env?.wasm) {
          instance.env.wasm.wasmPaths = "/onnx/";
        }
      } catch {}

      const original = globalThis.fetch;
      globalThis.fetch = ((input, init) => {
        const url = String(input);
        if (url.includes("piper-voices") && (url.endsWith(".onnx.json") || url.endsWith(".json"))) {
          console.log("[piper] Fetch redirect (config):", url, "->", this.configUrl);
          return original(this.configUrl, init);
        }
        if (url.includes("piper-voices") && url.endsWith(".onnx")) {
          console.log("[piper] Fetch redirect (model):", url, "->", this.modelUrl);
          return original(this.modelUrl, init);
        }
        return original(input, init);
      });

      try {
        console.log("[piper] Menginisialisasi Piper TTS Session dengan voiceId:", this.voice);
        const session = await TtsSession.create({
          voiceId: this.voice,
          wasmPaths: {
            onnxWasm: "/onnx/",
            piperData: "/piper/piper_phonemize.data",
            piperWasm: "/piper/piper_phonemize.wasm"
          }
        });
        console.log("[piper] Piper TTS Session berhasil dibuat dan siap!");
        return session;
      } catch (err) {
        console.error("[piper] Gagal membuat sesi Piper TTS:", err);
        throw err;
      } finally {
        globalThis.fetch = original;
      }
    })();
    return this.session;
  }

  async synthesize(text) {
    if (!text || !text.trim()) return null;
    try {
      console.log("[piper] Memulai sintesis teks:", JSON.stringify(text));
      const s = await this.create();
      const blob = await s.predict(text);
      console.log("[piper] Sintesis sukses! Blob size:", blob?.size, "tipe:", blob?.type);
      return blob;
    } catch (err) {
      console.error("[piper] Gagal sintesis teks:", JSON.stringify(text), "Error:", err);
      throw err;
    }
  }

  destroy() {
    this.session = void 0;
  }
}

export { BrowserPiper };

