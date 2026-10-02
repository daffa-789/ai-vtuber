import { EMOTION_TAGS, type EmotionTag } from './mood.ts'

const dikenal = new Set<string>(EMOTION_TAGS)
/**
 * Tag wajah di paling awal.
 *
 * `[[` di depan ditoleransi karena model 2B kadang menulis `[[senyum]`. Tanpa
 * toleransi itu tag dikenali sebagai "asing", dibuang dari teks, tapi tag-nya
 * hilang — raut wajah tidak pernah berubah walau model sudah menuliskannya.
 */
const TAG_AWAL = /^[\s`'"]*\[{1,2}([a-zA-Z][^\n[\]{}]{0,25})\]\]*[\s`'"]*/
/**
 * Tag berbentuk kurung siku di paling awal — dikenal atau tidak.
 *
 * Dipakai untuk MEMBUANG tag yang tidak dikenal. Model 2B kadang mengarang
 * tag di luar daftar (`[kosakata]`, `[Kegagalan]`). Kalau tidak dibuang, tag
 * itu tampil di chat DAN dibacakan TTS sebagai kata. Isinya dibatasi: huruf
 * diikuti huruf/angka/`_`/`-`/`:` — jadi `arr[0]` atau `[1, 2, 3]` di awal
 * kalimat tidak ikut kena.
 */
const TAG_ASING = /^[\s`'"]*\[{1,2}([a-zA-Z][\w:-]{0,24})\]\]*[\s`'"]*/

export function bacaTagAwal(teks: string): EmotionTag | undefined {
  const tag = TAG_AWAL.exec(teks)?.[1]?.trim().toLowerCase()
  return tag && dikenal.has(tag) ? tag as EmotionTag : undefined
}

/**
 * Buang tag wajah di awal teks.
 *
 * - Tag yang **dikenal** mengembalikan `tag` supaya mood/raut bisa diperbarui.
 * - Tag yang **tidak dikenal** tetap dibuang dari teks, tapi `tag` tidak diisi —
 *   supaya salah tulis model tidak merusak mood dan tidak ikut diucapkan.
 */
export function bersihkanTagAwal(teks: string): { teks: string; tag?: EmotionTag } {
  const tag = bacaTagAwal(teks)
  if (tag) return { teks: teks.replace(TAG_AWAL, ''), tag }
  const asing = TAG_ASING.test(teks)
  return asing ? { teks: teks.replace(TAG_ASING, '') } : { teks }
}
