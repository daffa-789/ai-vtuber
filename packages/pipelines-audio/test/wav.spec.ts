import { describe, expect, it } from 'vitest'
import {
  AMBANG_DENGAR,
  WavRusak,
  adaBunyi,
  bacaHeader,
  lajuKanal,
  pcmKeWav,
  puncak,
  sudahWav,
} from '../src/wav.ts'

/** Bangun WAV PCM16 mono dari daftar sampel. */
function buatWav(sampel: number[], laju = 22050, kanal = 1): Uint8Array {
  const pcm = new Uint8Array(sampel.length * 2)
  const dv = new DataView(pcm.buffer)
  sampel.forEach((s, i) => dv.setInt16(i * 2, s, true))
  return pcmKeWav(pcm, laju, kanal)
}

describe('pcmKeWav / sudahWav', () => {
  it('membungkus PCM mentah menjadi WAV yang dikenali', () => {
    const wav = buatWav([100, -200, 300], 40000)
    expect(sudahWav(wav)).toBe(true)
    const h = bacaHeader(wav)
    expect(h.laju).toBe(40000)
    expect(h.kanal).toBe(1)
    expect(h.jumlahFrame).toBe(3)
    expect(h.detik).toBeCloseTo(3 / 40000, 6)
  })

  it('sudahWav menolak berkas yang bukan RIFF/WAVE', () => {
    expect(sudahWav(new Uint8Array([1, 2, 3]))).toBe(false)
    expect(sudahWav(new Uint8Array(0))).toBe(false)
    const mp3Mirip = new Uint8Array(20)
    mp3Mirip.set([0x49, 0x44, 0x33], 0)
    expect(sudahWav(mp3Mirip)).toBe(false)
  })

  it('bacaHeader melempar WavRusak, bukan mengembalikan angka bohong', () => {
    expect(() => bacaHeader(new Uint8Array([1, 2, 3, 4]))).toThrow(WavRusak)
  })
})

describe('puncak — mengukur SELURUH berkas, bukan cuplikan awal', () => {
  it('menemukan puncak yang jauh di belakang ramp hening', () => {
    // Inilah bug yang pernah terjadi: 4096 frame pertama hening (puncak 66),
    // sementara seluruh berkas 28710. Kalau `puncak` jadi "cuplikan saja",
    // setiap kalimat RVC dinyatakan bisu.
    const sampel = [...Array(8192).fill(66), 28710, ...Array(8192).fill(-1000)]
    const wav = buatWav(sampel)
    expect(puncak(wav)).toBe(28710)
    expect(adaBunyi(wav)).toBe(true)
  })

  it('mengembalikan 0 hanya untuk berkas yang benar-benar hening', () => {
    const hening = buatWav(new Array(5000).fill(0))
    expect(puncak(hening)).toBe(0)
    expect(adaBunyi(hening)).toBe(false)
  })

  it('ambang dengar memisahkan "ada byte" dari "bisa didengar"', () => {
    const pelan = buatWav(new Array(1000).fill(AMBANG_DENGAR)) // tepat di ambang
    expect(puncak(pelan)).toBe(AMBANG_DENGAR)
    expect(adaBunyi(pelan)).toBe(false) // harus > ambang, bukan >=
    expect(adaBunyi(buatWav(new Array(1000).fill(AMBANG_DENGAR + 1)))).toBe(true)
  })

  it('berhenti lebih awal pada 32767 (tidak mungkin lebih tinggi)', () => {
    const penuh = buatWav([32767, ...new Array(1000).fill(0)])
    expect(puncak(penuh)).toBe(32767)
  })

  it('mengembalikan 1 (bukan 0) bila kedalaman bit bukan PCM16', () => {
    // Bukan PCM16 => "kita tidak tahu", jadi JANGAN sebut diam.
    const wav = buatWav([0, 0, 0])
    const dv = new DataView(wav.buffer)
    dv.setUint16(34, 8, true) // bit depth 8
    expect(puncak(wav)).toBe(1)
  })
})

describe('lajuKanal', () => {
  it('membaca rate dan channels dari mime', () => {
    expect(lajuKanal('audio/L16;codec=pcm;rate=24000')).toEqual([24000, 1])
    expect(lajuKanal('audio/wav;rate=48000;channels=2')).toEqual([48000, 2])
    expect(lajuKanal('audio/wav')).toEqual([24000, 1])
  })
})
