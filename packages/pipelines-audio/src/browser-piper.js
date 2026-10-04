import * as ort from "onnxruntime-web";
import { TtsSession } from "@mintplex-labs/piper-tts-web";

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
      if (typeof crossOriginIsolated !== "undefined" && !crossOriginIsolated) {
        ort.env.wasm.numThreads = 1;
      }
    }
  }

  create() {
    this.session ??= (async () => {
      if (ort.env?.wasm) {
        ort.env.wasm.wasmPaths = "/onnx/";
        if (typeof crossOriginIsolated !== "undefined" && !crossOriginIsolated) {
          ort.env.wasm.numThreads = 1;
        }
      }

      const original = globalThis.fetch;
      globalThis.fetch = ((input, init) => {
        const url = String(input);
        if (url.includes("piper-voices") && (url.endsWith(".onnx.json") || url.endsWith(".json"))) {
          return original(this.configUrl, init);
        }
        if (url.includes("piper-voices") && url.endsWith(".onnx")) {
          return original(this.modelUrl, init);
        }
        return original(input, init);
      });

      try {
        return await TtsSession.create({
          voiceId: this.voice,
          wasmPaths: {
            onnxWasm: "/onnx/",
            piperData: "/piper/piper_phonemize.data",
            piperWasm: "/piper/piper_phonemize.wasm"
          }
        });
      } finally {
        globalThis.fetch = original;
      }
    })();
    return this.session;
  }

  async synthesize(text) {
    const s = await this.create();
    return await s.predict(text);
  }

  destroy() {
    this.session = void 0;
  }
}

export { BrowserPiper };
