import { BrowserPiper, type BrowserPiperOptions } from './browser-piper.ts'
import { BrowserRvc, type BrowserRvcOptions } from './browser-rvc.ts'
export class BrowserVoicePipeline {
  private readonly piper: BrowserPiper; private readonly rvc: BrowserRvc
  constructor(options: { piper?: BrowserPiperOptions; rvc?: BrowserRvcOptions } = {}) { this.piper = new BrowserPiper(options.piper); this.rvc = new BrowserRvc(options.rvc) }
  async synthesize(text: string): Promise<Blob> {
    const source = await this.piper.synthesize(text)
    try { return await this.rvc.convert(source) }
    catch (error) { console.warn('RVC tidak tersedia; memakai keluaran Piper:', error); return source }
  }
  destroy(): void { this.piper.destroy() }
}
