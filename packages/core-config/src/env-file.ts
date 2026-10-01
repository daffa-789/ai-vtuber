/**
 * Port 1:1 dari parser `.env` di `server_py/konfig.py`.
 *
 * Parser ini TIDAK memakai `dotenv` dengan sengaja: perilaku `_potong_komentar`
 * di bawah adalah hasil perbaikan bug nyata di proyek lama (nilai seperti
 * `99  # semua lapis` dulu terbaca utuh lalu diam-diam jatuh ke bawaan). Aturan
 * yang dipertahankan:
 *   - nilai yang dikutip dipotong sampai kutip penutupnya saja;
 *   - `#` hanya jadi komentar kalau didahului spasi/tab (jadi `#fff` dan resep
 *     param tetap utuh);
 *   - nilai dari `process.env` TIDAK dipotong komentar.
 */

/** Buang kutip pembungkus bila ada (padanan `_bersih`). */
export function bersih(nilai: string): string {
  const v = nilai.trim()
  if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === '"' || v[0] === "'"))
    return v.slice(1, -1)
  return v
}

/** Padanan `_potong_komentar`. */
export function potongKomentar(nilai: string): string {
  const mentah = nilai.trim()
  if (mentah.length >= 2 && (mentah[0] === '"' || mentah[0] === "'")) {
    const kutip = mentah[0]
    const akhir = mentah.indexOf(kutip, 1)
    return akhir > 0 ? mentah.slice(1, akhir) : mentah.slice(1)
  }
  for (let i = 0; i < mentah.length; i++) {
    if (mentah[i] === '#' && i > 0 && (mentah[i - 1] === ' ' || mentah[i - 1] === '\t'))
      return mentah.slice(0, i).replace(/\s+$/, '')
  }
  return mentah
}

/** Padanan `baca_env`: `KUNCI=nilai`, `#` komentar, spasi di sekitar `=`. */
export function bacaEnv(isi: string): Record<string, string> {
  const hasil: Record<string, string> = {}
  for (const barisMentah of isi.split(/\r?\n/)) {
    const baris = barisMentah.trim()
    if (!baris || baris.startsWith('#') || !baris.includes('='))
      continue
    const idx = baris.indexOf('=')
    const kunci = baris.slice(0, idx).trim()
    const nilai = baris.slice(idx + 1)
    if (kunci)
      hasil[kunci] = potongKomentar(nilai)
  }
  return hasil
}
