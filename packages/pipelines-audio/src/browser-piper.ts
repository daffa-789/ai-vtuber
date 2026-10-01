import { TtsSession } from '@mintplex-labs/piper-tts-web'

export interface BrowserPiperOptions { modelUrl?: string; configUrl?: string; voice?: string }
export class BrowserPiper {
  private session?: Promise<TtsSession>
  private readonly modelUrl: string
  private readonly configUrl: string
  private readonly voice: string
  constructor(options: BrowserPiperOptions = {}) {
    this.modelUrl = options.modelUrl ?? '/assets/piper/id_ID-news_tts-medium.onnx'
    this.configUrl = options.configUrl ?? `${this.modelUrl}.json`
    // ID ini hanya menjadi cache key; fetch model diarahkan ke model lokal di bawah.
    this.voice = options.voice ?? 'en_US-hfc_female-medium'
  }
  private create(): Promise<TtsSession> {
    this.session ??= (async () => {
      const original = globalThis.fetch
      globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('huggingface.co/rhasspy/piper-voices/') && url.endsWith('.onnx.json')) return original(this.configUrl, init)
        if (url.includes('huggingface.co/rhasspy/piper-voices/') && url.endsWith('.onnx')) return original(this.modelUrl, init)
        return original(input, init)
      }) as typeof fetch
      try {
        return await TtsSession.create({ voiceId: this.voice, wasmPaths: { onnxWasm: '/onnx/', piperData: '/piper/piper_phonemize.data', piperWasm: '/piper/piper_phonemize.wasm' } })
      } finally { globalThis.fetch = original }
    })()
    return this.session
  }
  async synthesize(text: string): Promise<Blob> { return (await this.create()).predict(text) }
  destroy(): void { this.session = undefined }
}
