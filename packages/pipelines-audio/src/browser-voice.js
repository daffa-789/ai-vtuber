import { BrowserPiper } from "./browser-piper.js";
import { BrowserRvc } from "./browser-rvc.js";
class BrowserVoicePipeline {
  piper;
  rvc;
  constructor(options = {}) {
    this.piper = new BrowserPiper(options.piper);
    this.rvc = new BrowserRvc(options.rvc);
  }
  async synthesize(text) {
    const source = await this.piper.synthesize(text);
    try {
      return await this.rvc.convert(source);
    } catch (error) {
      console.warn("RVC tidak tersedia; memakai keluaran Piper:", error);
      return source;
    }
  }
  destroy() {
    this.piper.destroy();
  }
}
export {
  BrowserVoicePipeline
};
