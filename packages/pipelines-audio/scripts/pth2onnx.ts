/**
 * `pnpm voice:convert` — konversi checkpoint RVC `.pth` → `.onnx` memakai
 * `rvc-onnx-web` (murni TypeScript, tanpa Python).
 *
 * Peringatan yang WAJIB disampaikan ke pengguna (dan dicetak di sini):
 *   - hanya RVC v2;
 *   - korelasi audio akhir ~78% karena ada operator RandomNormalLike yang
 *     sengaja acak — timbre yang sedikit berbeda itu normal, bukan kerusakan;
 *   - berkas `.index` FAISS 178 MB TIDAK ditangani di sini.
 *
 * Pemakaian:
 *   pnpm voice:convert                       # model dari .env
 *   pnpm voice:convert -- masuk.pth keluar.onnx
 */
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import process from 'node:process'
import { pthToOnnx } from 'rvc-onnx-web'
import { cariAkarRepo } from '@silverwolf/core-config/paths'

export interface HasilKonversi {
  jalurMasuk: string
  jalurKeluar: string
  sampleRate: number
  jumlahBobot: number
  versi: string
  useF0: boolean
  byte: number
}

/** Konversi satu berkas `.pth` menjadi `.onnx`. */
export async function konversiPthKeOnnx(
  jalurMasuk: string,
  jalurKeluar: string,
  opsi: { opsetVersion?: number; phoneLen?: number } = {},
): Promise<HasilKonversi> {
  const mentah = readFileSync(jalurMasuk)
  const { onnxBuffer, sampleRate, checkpoint } = await pthToOnnx(new Uint8Array(mentah), {
    opsetVersion: opsi.opsetVersion ?? 17,
    phoneLen: opsi.phoneLen ?? 100,
  })

  mkdirSync(dirname(jalurKeluar), { recursive: true })
  writeFileSync(jalurKeluar, onnxBuffer)

  return {
    jalurMasuk,
    jalurKeluar,
    sampleRate,
    jumlahBobot: checkpoint.weights.size,
    versi: String(checkpoint.version),
    useF0: Boolean(checkpoint.useF0),
    byte: onnxBuffer.byteLength,
  }
}

/** Jalur `.pth` bawaan dari konfigurasi (`VTUBER_RVC_FOLDER` + `VTUBER_RVC_MODEL`). */
export function jalurPthBawaan(): string {
  const akar = cariAkarRepo()
  // Sengaja tidak lewat `konfig()` supaya skrip ini tetap jalan walau .env belum ada.
  return join(akar, 'aset', 'suara', 'rvc', 'SilverWolfJP', 'SilverWolfJP.pth')
}

async function utama(): Promise<void> {
  const akar = cariAkarRepo()
  const arg = process.argv.slice(2).filter(a => !a.startsWith('--'))
  const masuk = resolve(arg[0] ?? jalurPthBawaan())
  const keluar = resolve(arg[1] ?? join(akar, 'assets', 'voices', 'silverwolf', 'model.onnx'))

  console.log('[voice:convert] masuk :', masuk)
  console.log('[voice:convert] keluar:', keluar)
  console.log('[voice:convert] catatan: hanya RVC v2; korelasi audio ~78% itu normal.')

  const hasil = await konversiPthKeOnnx(masuk, keluar)
  console.log('[voice:convert] selesai:', JSON.stringify(hasil, null, 2))
}

// Hanya jalankan CLI bila dipanggil langsung (bukan saat di-impor uji).
if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}` || process.argv[1]?.endsWith('pth2onnx.ts'))
  await utama()
