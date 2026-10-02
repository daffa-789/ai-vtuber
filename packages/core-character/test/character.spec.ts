import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { CharacterVault, bersihkanTagAwal, gabungSystem, perbaruiMood } from '../src/index.ts'

describe('karakter', () => {
  it('membaca tag hanya di awal dan menggeser mood', () => {
    expect(bersihkanTagAwal('`[senyum]` Halo')).toEqual({ teks: 'Halo', tag: 'senyum' })
    expect(bersihkanTagAwal('pakai arr[0]')).toEqual({ teks: 'pakai arr[0]' })
    const mood = perbaruiMood(undefined, 'semangat')
    expect(mood.valensi).toBeCloseTo(0.335)
    expect(mood.energi).toBeCloseTo(0.65)
    expect(mood.pertukaran).toBe(1)
  })
  it('merakit prompt dengan fakta terbaru dan daftar tag tertutup', () => {
    const hasil = gabungSystem('persona', ['satu', 'dua', 'tiga', 'empat', 'lima', 'enam'], undefined, true)
    expect(hasil).not.toContain('- satu')
    expect(hasil).toContain('- enam')
    expect(hasil).toContain('[netral]')
  })
  it('menulis vault secara atomik dan dapat membacanya lagi', async () => {
    const root = await mkdtemp(join(tmpdir(), 'sw-vault-'))
    const vault = new CharacterVault(root)
    await vault.simpanFakta(['Master suka gim'])
    await vault.simpanMood(perbaruiMood(undefined, 'senyum'))
    expect(await vault.bacaFakta()).toEqual(['Master suka gim'])
    expect(await vault.bacaMood()).toMatchObject({ pertukaran: 1 })
    expect(await readFile(join(root, 'Fakta.md'), 'utf8')).toContain('[[Mood]]')
  })
})

/**
 * Model 2B kadang mengarang tag wajah di luar daftar tertutup, atau membalik
 * kurungnya. Kalau tag asing itu tidak dibuang, dia tampil di chat DAN
 * dibacakan mesin suara sebagai kata.
 *
 * Contoh nyata dari `silver_wolf_memory/Riwayat/2026-10-01.md`: `[kosakata]`,
 * `[Kegagalan]`, dan `[semangat]` yang muncul di AKHIR kalimat.
 */
describe('tag asing', () => {
  it('membuang tag di luar daftar tanpa mengubah mood', () => {
    expect(bersihkanTagAwal('[kosakata] Halo, Master.')).toEqual({ teks: 'Halo, Master.' })
    expect(bersihkanTagAwal('[Kegagalan] Tidak ada info.')).toEqual({ teks: 'Tidak ada info.' })
  })

  it('membetulkan tag yang kurung siku-nya dobel', () => {
    expect(bersihkanTagAwal('[[senyum] Halo')).toEqual({ teks: 'Halo', tag: 'senyum' })
    expect(bersihkanTagAwal('[[kaget]] Halo')).toEqual({ teks: 'Halo', tag: 'kaget' })
  })

  it('tetap menerima tag dikenal dan mengembalikan tag-nya', () => {
    expect(bersihkanTagAwal('[Bingung] Siapa kamu?')).toEqual({ teks: 'Siapa kamu?', tag: 'bingung' })
  })

  it('tidak menyentuh kode di awal kalimat', () => {
    expect(bersihkanTagAwal('arr[0] itu elemen pertama')).toEqual({ teks: 'arr[0] itu elemen pertama' })
    expect(bersihkanTagAwal('[1, 2, 3] itu array')).toEqual({ teks: '[1, 2, 3] itu array' })
  })

  it('tidak menyentuh tag di tengah kalimat', () => {
    expect(bersihkanTagAwal('Halo Master. [kosakata]')).toEqual({ teks: 'Halo Master. [kosakata]' })
  })
})
