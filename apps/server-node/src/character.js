/**
 * Logika karakter, persona, vault memori, dan mood untuk server Node.
 */
import { existsSync } from 'node:fs'
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

export const EMOTION_TAGS = [
  'netral', 'senyum', 'semangat', 'kaget', 'bingung', 'lelah', 'goda', 'sebal', 'sedih',
]

const dikenal = new Set(EMOTION_TAGS)

export const MOOD_AWAL = Object.freeze({
  valensi: 0.2,
  energi: 0.6,
  afinitas: 0.3,
  pertukaran: 0,
})

const NILAI_TAG = {
  senyum: 0.25,
  semangat: 0.35,
  goda: 0.2,
  netral: 0,
  bingung: -0.05,
  kaget: 0,
  lelah: -0.2,
  sedih: -0.3,
  sebal: -0.25,
}

const jepit = (n, min, maks) => Math.min(maks, Math.max(min, n))

export function perbaruiMood(lama, tag) {
  const dasar = lama ?? MOOD_AWAL
  const delta = NILAI_TAG[tag ?? 'netral'] ?? 0
  return {
    valensi: jepit(dasar.valensi * 0.8 + delta * 0.5, -1, 1),
    energi: jepit(dasar.energi * 0.95 + (tag === 'semangat' ? 0.1 : 0) - 0.02, 0, 1),
    afinitas: jepit(dasar.afinitas + 0.03, 0, 1),
    pertukaran: dasar.pertukaran + 1,
    alasan: `tag terakhir: ${tag ?? 'tidak ada'}`,
  }
}

export function suasana(mood) {
  if (!mood) return ''
  if (mood.valensi < -0.25) return 'Kamu lagi agak berat hari ini, jadi jawabanmu lebih pendek dan lebih jujur.'
  if (mood.valensi > 0.3 && mood.energi > 0.5) return 'Kamu lagi ceria, boleh lebih usil sedikit.'
  if (mood.energi < 0.3) return 'Kamu lagi capek, bicaranya lebih pelan dan pendek.'
  return ''
}

const TAG_AWAL = /^[\s`'"]*\[{1,2}([a-zA-Z][^\n[\]{}]{0,25})\]\]*[\s`'"]*/
const TAG_ASING = /^[\s`'"]*\[{1,2}([a-zA-Z][\w:-]{0,24})\]\]*[\s`'"]*/

export function bacaTagAwal(teks) {
  const tag = TAG_AWAL.exec(teks)?.[1]?.trim().toLowerCase()
  return tag && dikenal.has(tag) ? tag : undefined
}

export function bersihkanTagAwal(teks) {
  const tag = bacaTagAwal(teks)
  if (tag) return { teks: teks.replace(TAG_AWAL, ''), tag }
  const asing = TAG_ASING.test(teks)
  return asing ? { teks: teks.replace(TAG_ASING, '') } : { teks }
}

export function ringkasPersona(teks, batas = 18000) {
  if (teks.length <= batas) return { teks, terpotong: false, bagianHilang: [] }
  let hasil = teks.slice(0, batas)
  const paragraf = hasil.lastIndexOf('\n\n')
  if (paragraf > batas / 2) hasil = hasil.slice(0, paragraf)
  const judul = [...teks.matchAll(/^## (.+)$/gm)].map(m => m[1]?.trim()).filter(Boolean)
  return { teks: hasil, terpotong: true, bagianHilang: judul.filter(j => !hasil.includes(`## ${j}`)) }
}

export function gabungSystem(persona, fakta, mood, lokal = true) {
  const bagian = [ringkasPersona(persona).teks]
  if (lokal) {
    bagian.push(
      `WAJIB: Awali setiap balasanmu dengan satu tag emosi di paling depan, persis satu dari ${EMOTION_TAGS.map(t => `[${t}]`).join(', ')}. Contoh: [senyum] Beres, Master. Tinggal bilang bagian mana yang macet.`
    )
  }
  if (fakta && fakta.length) {
    const daftar = lokal ? fakta.slice(-5) : fakta
    bagian.push(
      `${lokal ? 'Fakta tentang Master' : '## Yang aku ingat tentang Master'}:\n${daftar.map(f => `- ${f}`).join('\n')}`
    )
  }
  const kini = suasana(mood)
  if (kini) {
    bagian.push(`${lokal ? 'Suasana hatimu saat ini' : '## Suasana hatiku sekarang'}: ${kini}`)
  }
  return bagian.join('\n\n')
}

export async function bacaPersona(jalur) {
  return await readFile(jalur, 'utf8')
}

const TAUTAN = ['silverwolf-persona']
const tanggal = (d = new Date()) => d.toISOString().slice(0, 10)

export class CharacterVault {
  constructor(root) {
    this.root = root
  }

  available() {
    return existsSync(this.root)
  }

  unavailableReason() {
    return `folder ${this.root} tidak ada`
  }

  async baca(nama) {
    try {
      return await readFile(join(this.root, nama), 'utf8')
    } catch (error) {
      if (error && error.code === 'ENOENT') return undefined
      throw error
    }
  }

  async tulis(nama, isi) {
    const path = join(this.root, nama)
    await mkdir(dirname(path), { recursive: true })
    const temp = `${path}.${process.pid}.${Date.now()}.tmp`
    await writeFile(temp, isi, 'utf8')
    await rename(temp, path)
  }

  kerangka(nama, judul, isi, links = []) {
    const semua = [...new Set([...TAUTAN, ...links])]
    return [
      '---', 'type: memory', 'kind: karakter', 'wilayah: waifu', `name: "${nama}"`,
      `description: "${judul}"`, 'project: "Desktop AI VTUBER"', `updated: "${tanggal()}"`,
      'tags:', '  - "memory/karakter"', '  - "wilayah/waifu"', '  - "project/Desktop AI VTUBER"',
      'links:', ...semua.map(x => `  - "[[${x}]]"`), '---', '', `# ${judul}`, '', isi.trim(), '',
    ].join('\n')
  }

  async bacaFakta() {
    const teks = await this.baca('Fakta.md')
    if (!teks) return []
    return teks
      .split('\n')
      .filter(x => x.startsWith('- '))
      .map(x => x.slice(2).trim())
      .filter(x => x && !x.startsWith('_'))
  }

  async simpanFakta(fakta) {
    const panduan = 'Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.\nHanya simpan yang pernah Master tulis sendiri atau yang terukur dari mesin ini.\n\n'
    const isi = panduan + (fakta.length ? fakta.map(x => `- ${x}`).join('\n') : '_Belum ada fakta tersimpan._')
    await this.tulis('Fakta.md', this.kerangka('fakta-silverwolf', 'Fakta yang Silver Wolf ingat tentang Master', isi, ['Mood', 'Riwayat']))
  }

  async bacaMood() {
    const teks = await this.baca('Mood.md')
    if (!teks) return undefined
    const ambil = k => Number(new RegExp(`${k}: (-?[\\d.]+)`).exec(teks)?.[1])
    const valensi = ambil('Valensi')
    const energi = ambil('Energi')
    const afinitas = ambil('Afinitas')
    if (![valensi, energi, afinitas].every(Number.isFinite)) return undefined
    return {
      valensi,
      energi,
      afinitas,
      pertukaran: Number(/Pertukaran tercatat: (\d+)/.exec(teks)?.[1] ?? 0),
    }
  }

  async simpanMood(mood) {
    const isi = [
      `Valensi: ${mood.valensi.toFixed(2)} (-1 berat .. +1 senang)`,
      `Energi: ${mood.energi.toFixed(2)}`,
      `Afinitas: ${mood.afinitas.toFixed(2)} (0 jauh .. 1 dekat)`,
      `Pertukaran tercatat: ${mood.pertukaran}`,
      `Terakhir diperbarui: ${new Date().toISOString()}`,
      mood.alasan ? `Alasan: ${mood.alasan}` : '',
    ].filter(Boolean).join('\n')
    await this.tulis('Mood.md', this.kerangka('mood-silverwolf', 'Suasana hati Silver Wolf saat ini', isi, ['Fakta', 'Riwayat']))
  }

  async catatHari(baris) {
    const nama = `Riwayat/${tanggal()}.md`
    const lama = await this.baca(nama)
    const badan = lama?.split('\n').filter(x => x.startsWith('- ')) ?? []
    badan.push(`- ${baris}`)
    await this.tulis(nama, this.kerangka(`riwayat-${tanggal()}`, `Riwayat percakapan ${tanggal()}`, badan.join('\n'), ['Fakta', 'Mood', 'Riwayat']))
  }
}
