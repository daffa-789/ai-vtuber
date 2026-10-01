/**
 * Koerser bertipe dengan semantik identik `nilai()/angka()/angka_float()/bool_()`
 * di `server_py/konfig.py`.
 *
 * Satu perbaikan sadar atas Python: nilai yang GAGAL di-parse dicatat di
 * `warnings` alih-alih hilang tanpa jejak. Kode lama berulang kali kena bug
 * "resep diabaikan tanpa pesan" (lihat komentar `_potong_komentar` dan
 * `angka_float` di konfig.py); di sini pemanggil bisa mencetaknya.
 */

export interface EnvSource {
  /** Nilai dari `.env` (sudah dipotong komentarnya). */
  readonly file: Record<string, string>
  /** Nilai dari `process.env`; menang atas berkas bila tidak kosong. */
  readonly environ: Record<string, string | undefined>
  /** Kumpulan peringatan parse; diisi oleh koerser di bawah. */
  readonly warnings: string[]
}

/** Padanan `nilai(kunci, bawaan)`. */
export function nilai(env: EnvSource, kunci: string, bawaan = ''): string {
  const dariEnv = env.environ[kunci]
  if (dariEnv !== undefined && dariEnv.trim() !== '')
    return bersihLocal(dariEnv)
  return env.file[kunci] ?? bawaan
}

function bersihLocal(nilai: string): string {
  const v = nilai.trim()
  if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === '"' || v[0] === "'"))
    return v.slice(1, -1)
  return v
}

/** Padanan `angka(kunci, bawaan)` — gagal parse => bawaan + peringatan. */
export function angka(env: EnvSource, kunci: string, bawaan: number): number {
  const mentah = String(nilai(env, kunci, String(bawaan))).trim()
  if (mentah === '')
    return bawaan
  const n = Number(mentah)
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    env.warnings.push(`${kunci}="${mentah}" bukan bilangan bulat; dipakai bawaan ${bawaan}`)
    return bawaan
  }
  return n
}

/** Padanan `angka_float(kunci, bawaan)` untuk rasio (protect 0.33, length_scale 1.0). */
export function angkaFloat(env: EnvSource, kunci: string, bawaan: number): number {
  const mentah = String(nilai(env, kunci, String(bawaan))).trim()
  if (mentah === '')
    return bawaan
  const n = Number(mentah)
  if (!Number.isFinite(n)) {
    env.warnings.push(`${kunci}="${mentah}" bukan bilangan; dipakai bawaan ${bawaan}`)
    return bawaan
  }
  return n
}

const BENAR = new Set(['true', '1', 'ya', 'on'])
const SALAH = new Set(['false', '0', 'tidak', 'off'])

/** Padanan `bool_()`: true|1|ya|on dan false|0|tidak|off, selain itu bawaan. */
export function bool_(env: EnvSource, kunci: string, bawaan: boolean): boolean {
  const mentah = nilai(env, kunci, bawaan ? 'true' : 'false').trim().toLowerCase()
  if (BENAR.has(mentah))
    return true
  if (SALAH.has(mentah))
    return false
  env.warnings.push(`${kunci}="${mentah}" bukan boolean; dipakai bawaan ${bawaan}`)
  return bawaan
}

/** Padanan `daftar()`: pisah koma, buang yang kosong. */
export function daftar(env: EnvSource, kunci: string, bawaan: string): string[] {
  return nilai(env, kunci, bawaan)
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
}
