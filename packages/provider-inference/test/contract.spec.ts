import { describe, expect, it } from 'vitest'
import type { AudioStage, LlmProvider, StageRenderer, TtsProvider } from '../src/index.ts'

/**
 * Uji kontrak: paket ini hanya berisi tipe, jadi yang diuji adalah bahwa
 * implementasi tiruan benar-benar memenuhi antarmuka. Ini menjaga tanda tangan
 * antarmuka tetap dapat dipakai sebelum implementasi asli ada (Fase 1+).
 */
describe('kontrak provider', () => {
  it('LlmProvider tiruan memenuhi antarmuka dan men-stream potongan', async () => {
    const fake: LlmProvider = {
      id: 'llama-server',
      available: async () => ({ ok: true, reason: 'uji' }),
      async *stream() {
        yield '[senyum] '
        yield 'hai bos'
      },
      dispose: async () => {},
    }

    const potongan: string[] = []
    for await (const p of fake.stream([{ role: 'user', content: 'hai' }]))
      potongan.push(p)

    expect(potongan.join('')).toBe('[senyum] hai bos')
    expect((await fake.available()).ok).toBe(true)
  })

  it('TtsProvider dan AudioStage memisahkan teks→wav dan wav→wav', async () => {
    const tts: TtsProvider = {
      id: 'piper',
      available: async () => ({ ok: true, reason: 'uji' }),
      fingerprint: async () => 'piper|id_ID-news_tts-medium|panjang=0.9',
      synthesize: async () => ({ bytes: new Uint8Array(44), sampleRate: 22050, channels: 1 }),
      dispose: async () => {},
    }
    const rvc: AudioStage = {
      id: 'rvc',
      input: 'wav',
      output: 'wav',
      available: async () => ({ ok: true, reason: 'uji' }),
      fingerprint: async () => 'rvc|SilverWolfJP|f0=rmvpe|transpose=10|index=0',
      run: async (wav) => ({ ...wav, sampleRate: 40000 }),
      dispose: async () => {},
    }

    expect(tts.id).toBe('piper')
    expect(rvc.input).toBe('wav')
    const keluar = await rvc.run(await tts.synthesize('hai', Date.now() + 1000), 1000)
    expect(keluar.sampleRate).toBe(40000)
    expect(await rvc.fingerprint()).toContain('index=0')
  })

  it('StageRenderer menyediakan permukaan Body yang dipakai stage-ui', () => {
    const dipanggil: string[] = []
    const renderer: StageRenderer = {
      load: async (url) => void dipanggil.push(`load:${url}`),
      setExpression: (n) => void dipanggil.push(`ekspresi:${n}`),
      setPose: (n, on) => void dipanggil.push(`pose:${n}:${on}`),
      startMotion: async (g, i) => {
        dipanggil.push(`gerak:${g}:${i}`)
        return true
      },
      setMouth: (l) => void dipanggil.push(`mulut:${l}`),
      destroy: () => void dipanggil.push('destroy'),
    }

    renderer.setExpression('senyum')
    renderer.setMouth(0.5)
    expect(dipanggil).toEqual(['ekspresi:senyum', 'mulut:0.5'])
  })
})
