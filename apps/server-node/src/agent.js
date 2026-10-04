/**
 * Agen percakapan: menyusun prompt, mengalirkan balasan, menyimpan mood & riwayat.
 */
import { bacaTagAwal, gabungSystem, perbaruiMood } from './character.js'

const spasiGanda = /\s+/g

export class Agent {
  constructor(o) {
    this.provider = o.provider
    this.persona = o.persona
    this.vault = o.vault
    this.lokal = o.provider.id === 'ollama' ? false : Boolean(o.localPrompt)
    this.onError = o.onError ?? (error => console.error('memori:', error))
  }

  get localPrompt() {
    return this.lokal
  }

  async memory() {
    if (!this.vault.available()) return { fakta: [] }
    let fakta = []
    try {
      fakta = await this.vault.bacaFakta()
    } catch (error) {
      this.onError(error)
      return { fakta: [] }
    }
    let mood
    try {
      mood = await this.vault.bacaMood()
    } catch (error) {
      this.onError(error)
    }
    return { fakta, mood }
  }

  async *chat(riwayat, opts = {}, signal) {
    const memory = await this.memory()
    const pesan = [
      { role: 'system', content: gabungSystem(this.persona, memory.fakta, memory.mood, this.lokal) },
      ...riwayat.filter(m => m.role !== 'system'),
    ]
    let jawaban = ''
    for await (const potongan of this.provider.stream(pesan, opts, signal)) {
      if (potongan.err) {
        yield potongan
        return
      }
      jawaban += potongan.text ?? ''
      yield potongan
    }
    if (jawaban.length > 0) {
      try {
        await this.persist(riwayat, jawaban, memory)
      } catch (error) {
        this.onError(error)
      }
    }
  }

  async persist(riwayat, jawaban, memory) {
    if (!this.vault.available()) return
    const mood = perbaruiMood(memory.mood, bacaTagAwal(jawaban))
    await this.vault.simpanMood(mood)
    let ucapan = ''
    for (let i = riwayat.length - 1; i >= 0; i--) {
      if (riwayat[i]?.role === 'user') {
        ucapan = riwayat[i].content
        break
      }
    }
    const ringkas = s => {
      const padat = s.replace(spasiGanda, ' ').trim()
      return padat.length > 240 ? padat.slice(0, 240) : padat
    }
    await this.vault.catatHari(`Master: ${ringkas(ucapan)} | Silver Wolf: ${ringkas(jawaban)}`)
  }
}
