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
  }
  create() {
    this.session ??= (async () => {
      const original = globalThis.fetch;
      globalThis.fetch = ((input, init) => {
        const url = String(input);
        if (url.includes("huggingface.co/rhasspy/piper-voices/") && url.endsWith(".onnx.json")) return original(this.configUrl, init);
        if (url.includes("huggingface.co/rhasspy/piper-voices/") && url.endsWith(".onnx")) return original(this.modelUrl, init);
        return original(input, init);
      });
      try {
        return await TtsSession.create({ voiceId: this.voice, wasmPaths: { onnxWasm: "/onnx/", piperData: "/piper/piper_phonemize.data", piperWasm: "/piper/piper_phonemize.wasm" } });
      } finally {
        globalThis.fetch = original;
      }
    })();
    return this.session;
  }
  async synthesize(text) {
    return (await this.create()).predict(text);
  }
  destroy() {
    this.session = void 0;
  }
}
export {
  BrowserPiper
};
