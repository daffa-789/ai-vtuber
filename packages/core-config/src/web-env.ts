import type { EnvSource } from './coerce.ts'

/**
 * Padanan `env_web()` di `konfig.py`.
 *
 * Sengaja HANYA berprefiks `VITE_`: kunci `VTUBER_*` tidak boleh pernah
 * dibubuhkan ke halaman (ia memuat jalur berkas lokal dan pengaturan mesin).
 * Fungsi ini adalah satu-satunya jembatan konfigurasi ke sisi browser.
 */
export function envWeb(env: EnvSource): Record<string, string> {
  const hasil: Record<string, string> = {}
  for (const [k, v] of Object.entries(env.file)) {
    if (k.startsWith('VITE_'))
      hasil[k] = v
  }
  for (const [k, v] of Object.entries(env.environ)) {
    if (k.startsWith('VITE_') && typeof v === 'string')
      hasil[k] = v
  }
  return hasil
}

/**
 * Bentuk yang disuntikkan ke halaman sebagai `window.__VTUBER_ENV__`.
 * `statis.py` dulu menulis ini ke `<!--VTUBER_ENV-->`; sekarang Vite/Electron
 * yang menyuntik, tapi bentuk objeknya dipertahankan agar `setelan.js` (kini
 * `settings.ts`) tidak perlu berubah.
 */
export interface WebEnv {
  VITE_WAJAH?: Record<string, string>
  VITE_POSE?: Record<string, string>
  VITE_GERAK?: Record<string, string>
  [kunci: string]: unknown
}
