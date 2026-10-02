import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { gabungSystem, ringkasPersona } from '../src/index.ts'

/**
 * `ringkasPersona` memotong persona secara diam-diam kalau kepanjangan.
 *
 * Ini pernah benar-benar terjadi: batas 9.000 sementara persona Silver Wolf
 * 9.700 karakter, sehingga bagian terakhir — "Emoji", yang melarang emoji —
 * terbuang. Model lalu bebas menempelkan emoji ke balasannya.
 */
describe('pemotong persona', () => {
  it('membiarkan persona pendek apa adanya', () => {
    const hasil = ringkasPersona('## Satu\n\nisi pendek')
    expect(hasil.terpotong).toBe(false)
    expect(hasil.bagianHilang).toEqual([])
  })

  it('memotong di batas paragraf, bukan di tengah kalimat', () => {
    const paragraf = Array.from({ length: 40 }, (_, i) => `## Bagian ${i}\n\n${'kata '.repeat(200)}`).join('\n\n')
    const hasil = ringkasPersona(paragraf, 2000)
    expect(hasil.terpotong).toBe(true)
    expect(hasil.teks.endsWith(' ')).toBe(false)
    expect(hasil.teks.length).toBeLessThanOrEqual(2000)
  })

  it('melaporkan bagian yang hilang supaya bisa dilog', () => {
    const paragraf = ['## Awal', 'x'.repeat(1500), '## Tengah', 'y'.repeat(1500), '## Akhir', 'z'.repeat(1500)].join('\n\n')
    const hasil = ringkasPersona(paragraf, 2000)
    expect(hasil.bagianHilang).toContain('Akhir')
  })

  it('persona Silver Wolf yang asli TIDAK terpotong', async () => {
    // Menjaga agar batas bawaan selalu di atas panjang berkas aslinya.
    const teks = await readFile(join(process.cwd(), 'silver_wolf_memory', 'persona.md'), 'utf8')
    const hasil = ringkasPersona(teks)
    expect(hasil.terpotong, 'naikkan batas ringkasPersona kalau persona bertambah panjang').toBe(false)
    expect(hasil.bagianHilang).toEqual([])
  })

  it('aturan larangan emoji benar-benar sampai ke prompt akhir', async () => {
    const teks = await readFile(join(process.cwd(), 'silver_wolf_memory', 'persona.md'), 'utf8')
    const prompt = gabungSystem(teks, [], undefined, true)
    expect(prompt.toLowerCase()).toContain('emoji')
  })

  it('aturan keras ada di AWAL berkas, bukan di ekor', async () => {
    // Persona ini panjang. Kalau aturan keras ditaruh di bawah, dia yang
    // pertama terbuang saat dipotong — dan model bebas melanggar kontraknya.
    const teks = await readFile(join(process.cwd(), 'silver_wolf_memory', 'persona.md'), 'utf8')
    const depan = teks.slice(0, 3000).toLowerCase()
    expect(depan, 'daftar tag wajah harus di depan').toContain('[senyum]')
    expect(depan, 'larangan emoji harus di depan').toContain('emoji')
    expect(depan, 'larangan label bocor harus di depan').toContain('silver wolf:')
  })

  it('walaupun kepotong, aturan keras tetap selamat', async () => {
    const teks = await readFile(join(process.cwd(), 'silver_wolf_memory', 'persona.md'), 'utf8')
    // Paksa potong pendek: tiru persona yang jauh lebih panjang dari batas.
    const dipotong = ringkasPersona(teks, 3000)
    expect(dipotong.terpotong).toBe(true)
    const bawah = dipotong.teks.toLowerCase()
    expect(bawah).toContain('[senyum]')
    expect(bawah).toContain('emoji')
  })
})
