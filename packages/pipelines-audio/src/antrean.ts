/**
 * Pemain antrean suara per-kalimat + lip-sync.
 *
 * Masalah yang diselesaikan:
 *  1. Dulu TTS baru mulai SETELAH seluruh balasan LLM rampung. Dengan
 *     ~10 token/detik itu berarti 6-10 detik diam sebelum apa pun terdengar,
 *     ditambah 8-20 detik Piper+RVC. Sekarang kalimat pertama langsung
 *     disintesis begitu model selesai menulisnya.
 *  2. `setMouth()` sudah ada di renderer tapi tidak pernah dipanggil, jadi
 *     karakter bicara dengan mulut tertutup. Di sini RMS audio diukur lewat
 *     AnalyserNode dan dikirim ke `onMulut` setiap frame.
 */

import { potongKalimat } from './kalimat.ts'

export interface AntreanSuaraOptions {
  /** Sintesis satu kalimat jadi berkas audio. */
  synthesize: (teks: string) => Promise<Blob>
  /** Dipanggil dengan 0..1 tiap frame selama pemutaran (gerakan mulut). */
  onMulut?: (level: number) => void
  onKalimatMulai?: (teks: string) => void
  onKalimatSelesai?: (teks: string) => void
  onGalat?: (error: unknown) => void
}

export class AntreanSuara {
  private readonly opsi: AntreanSuaraOptions
  private readonly antrean: string[] = []
  private sisa = ''
  private ditutup = false
  private berjalan = false
  private berhentiTotal = false
  private tunggu: Array<() => void> = []
  private audio?: HTMLAudioElement
  private konteks?: AudioContext
  private bingkai?: number

  constructor(opsi: AntreanSuaraOptions) { this.opsi = opsi }

  /** Tambah potongan teks dari aliran; kalimat utuh langsung masuk antrean. */
  tambah(potongan: string): void {
    if (this.berhentiTotal || !potongan) return
    this.sisa += potongan
    const { kalimat, sisa } = potongKalimat(this.sisa)
    this.sisa = sisa
    for (const k of kalimat) this.antrean.push(k)
    void this.jalankan()
  }

  /** Aliran selesai: sisa tanpa penutup kalimat tetap diucapkan. */
  tutup(): void {
    if (this.berhentiTotal) return
    const sisa = this.sisa.trim()
    if (sisa) { this.antrean.push(sisa); this.sisa = '' }
    this.ditutup = true
    void this.jalankan()
  }

  /** Tunggu sampai seluruh antrean habis diputar. */
  async tungguSelesai(): Promise<void> {
    if (this.berhentiTotal) return
    if (this.ditutup && !this.antrean.length && !this.berjalan) return
    await new Promise<void>(resolve => this.tunggu.push(resolve))
  }

  /** Hentikan semua: audio sekarang, antrean, dan gerakan mulut. */
  berhenti(): void {
    this.berhentiTotal = true
    this.antrean.length = 0
    this.sisa = ''
    if (this.bingkai !== undefined) cancelAnimationFrame(this.bingkai)
    this.bingkai = undefined
    this.opsi.onMulut?.(0)
    if (this.audio) { this.audio.pause(); this.audio = undefined }
    this.selesaikanSemua()
  }

  private selesaikanSemua(): void {
    const daftar = this.tunggu
    this.tunggu = []
    for (const r of daftar) r()
  }

  private async jalankan(): Promise<void> {
    if (this.berjalan || this.berhentiTotal) return
    this.berjalan = true
    try {
      while (this.antrean.length && !this.berhentiTotal) {
        const teks = this.antrean.shift()!
        this.opsi.onKalimatMulai?.(teks)
        try {
          const blob = await this.opsi.synthesize(teks)
          if (this.berhentiTotal) break
          await this.putar(blob)
        }
        catch (error) { this.opsi.onGalat?.(error) }
        this.opsi.onKalimatSelesai?.(teks)
      }
    } finally {
      this.berjalan = false
      if (this.ditutup && !this.antrean.length) this.selesaikanSemua()
    }
  }

  private async putar(blob: Blob): Promise<void> {
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    this.audio = audio
    const konteks = this.konteksAudio()
    let sumber: MediaElementAudioSourceNode | undefined
    let analyser: AnalyserNode | undefined
    if (konteks) {
      try {
        sumber = konteks.createMediaElementSource(audio)
        analyser = konteks.createAnalyser()
        analyser.fftSize = 1024
        analyser.smoothingTimeConstant = 0.2
        sumber.connect(analyser)
        analyser.connect(konteks.destination)
      } catch { sumber = undefined; analyser = undefined }
    }
    try {
      await audio.play()
      if (analyser) this.gerakkanMulut(analyser)
      await new Promise<void>(resolve => {
        audio.onended = () => resolve()
        audio.onerror = () => resolve()
      })
    } finally {
      if (this.bingkai !== undefined) cancelAnimationFrame(this.bingkai)
      this.bingkai = undefined
      this.opsi.onMulut?.(0)
      sumber?.disconnect()
      analyser?.disconnect()
      URL.revokeObjectURL(url)
      if (this.audio === audio) this.audio = undefined
    }
  }

  private konteksAudio(): AudioContext | undefined {
    try {
      this.konteks ??= new AudioContext()
      if (this.konteks.state === 'suspended') void this.konteks.resume()
      return this.konteks
    } catch { return undefined }
  }

  /**
   * Ukur RMS dan kirim ke `onMulut`. Serangan cepat, pelepasan lambat —
   * supaya mulut tidak berkedut di setiap jeda antar-kata.
   */
  private gerakkanMulut(analyser: AnalyserNode): void {
    const data = new Uint8Array(analyser.fftSize)
    let halus = 0
    const langkah = () => {
      if (this.berhentiTotal) return
      analyser.getByteTimeDomainData(data)
      let jumlah = 0
      for (let i = 0; i < data.length; i++) { const s = (data[i]! - 128) / 128; jumlah += s * s }
      const rms = Math.sqrt(jumlah / data.length)
      const target = Math.min(1, rms * 5)
      halus = target > halus ? target : halus * 0.82 + target * 0.18
      this.opsi.onMulut?.(halus)
      this.bingkai = requestAnimationFrame(langkah)
    }
    this.bingkai = requestAnimationFrame(langkah)
  }
}
