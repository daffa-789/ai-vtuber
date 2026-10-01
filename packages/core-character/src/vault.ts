import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type { Mood } from './mood.ts'

const TAUTAN = ['silverwolf-persona']
const tanggal = (d = new Date()) => d.toISOString().slice(0, 10)

export class CharacterVault {
  readonly root: string
  constructor(root: string) { this.root = root }
  available(): boolean { return existsSync(this.root) }
  unavailableReason(): string { return `folder ${this.root} tidak ada` }

  private async baca(nama: string): Promise<string | undefined> {
    try { return await readFile(join(this.root, nama), 'utf8') }
    catch (error) { if ((error as NodeJS.ErrnoException).code === 'ENOENT') return undefined; throw error }
  }
  private async tulis(nama: string, isi: string): Promise<void> {
    const path = join(this.root, nama)
    await mkdir(dirname(path), { recursive: true })
    const temp = `${path}.${process.pid}.${Date.now()}.tmp`
    await writeFile(temp, isi, 'utf8')
    await rename(temp, path)
  }
  private kerangka(nama: string, judul: string, isi: string, links: string[] = []): string {
    const semua = [...new Set([...TAUTAN, ...links])]
    return ['---', 'type: memory', 'kind: karakter', 'wilayah: waifu', `name: "${nama}"`,
      `description: "${judul}"`, 'project: "Desktop AI VTUBER"', `updated: "${tanggal()}"`,
      'tags:', '  - "memory/karakter"', '  - "wilayah/waifu"', '  - "project/Desktop AI VTUBER"',
      'links:', ...semua.map(x => `  - "[[${x}]]"`), '---', '', `# ${judul}`, '', isi.trim(), ''].join('\n')
  }
  async bacaFakta(): Promise<string[]> {
    const teks = await this.baca('Fakta.md')
    if (!teks) return []
    return teks.split('\n').filter(x => x.startsWith('- ')).map(x => x.slice(2).trim()).filter(x => x && !x.startsWith('_'))
  }
  async simpanFakta(fakta: string[]): Promise<void> {
    const panduan = 'Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.\nHanya simpan yang pernah Master tulis sendiri atau yang terukur dari mesin ini.\n\n'
    const isi = panduan + (fakta.length ? fakta.map(x => `- ${x}`).join('\n') : '_Belum ada fakta tersimpan._')
    await this.tulis('Fakta.md', this.kerangka('fakta-silverwolf', 'Fakta yang Silver Wolf ingat tentang Master', isi, ['Mood', 'Riwayat']))
  }
  async bacaMood(): Promise<Mood | undefined> {
    const teks = await this.baca('Mood.md'); if (!teks) return undefined
    const ambil = (k: string) => Number(new RegExp(`${k}: (-?[\\d.]+)`).exec(teks)?.[1])
    const valensi = ambil('Valensi'), energi = ambil('Energi'), afinitas = ambil('Afinitas')
    if (![valensi, energi, afinitas].every(Number.isFinite)) return undefined
    return { valensi, energi, afinitas, pertukaran: Number(/Pertukaran tercatat: (\d+)/.exec(teks)?.[1] ?? 0) }
  }
  async simpanMood(mood: Mood): Promise<void> {
    const isi = [`Valensi: ${mood.valensi.toFixed(2)} (-1 berat .. +1 senang)`, `Energi: ${mood.energi.toFixed(2)}`,
      `Afinitas: ${mood.afinitas.toFixed(2)} (0 jauh .. 1 dekat)`, `Pertukaran tercatat: ${mood.pertukaran}`,
      `Terakhir diperbarui: ${new Date().toISOString()}`, mood.alasan ? `Alasan: ${mood.alasan}` : ''].filter(Boolean).join('\n')
    await this.tulis('Mood.md', this.kerangka('mood-silverwolf', 'Suasana hati Silver Wolf saat ini', isi, ['Fakta', 'Riwayat']))
  }
  async catatHari(baris: string): Promise<void> {
    const nama = `Riwayat/${tanggal()}.md`, lama = await this.baca(nama)
    const badan = lama?.split('\n').filter(x => x.startsWith('- ')) ?? []
    badan.push(`- ${baris}`)
    await this.tulis(nama, this.kerangka(`riwayat-${tanggal()}`, `Riwayat percakapan ${tanggal()}`, badan.join('\n'), ['Fakta', 'Mood', 'Riwayat']))
  }
}
