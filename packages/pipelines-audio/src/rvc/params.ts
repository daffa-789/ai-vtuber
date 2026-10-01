import type { Konfig } from '@silverwolf/core-config'

/**
 * Padanan `param_aktif()` di `server_py/tts_rvc.py`.
 *
 * Nama kunci di sini adalah nama parameter asli RVC (f0method, f0up_key, ...)
 * yang TIDAK bisa ditebak dari nama konfigurasi kita. Fungsi ini adalah satu-
 * satunya tempat pemetaan itu hidup, dan `fingerprint()` meng-iterasi objek ini
 * (bukan menulis ulang daftar kuncinya) supaya menambah parameter baru tidak
 * bisa membuat cache mengembalikan audio lama tanpa pesan — kelas bug yang
 * pernah terjadi di `tts_rvc.py` (empat kunci terlewat dari daftar cache key).
 */
export interface RvcParams {
  f0method: string
  f0up_key: number
  index_rate: number
  filter_radius: number
  resample_sr: number
  rms_mix_rate: number
  protect: number
}

/** Bangun `RvcParams` dari konfigurasi. */
export function paramAktif(k: Konfig): RvcParams {
  return {
    f0method: k.rvcF0,
    f0up_key: k.rvcTranspose,
    index_rate: k.rvcIndeksLaju,
    filter_radius: k.rvcPencucian,
    resample_sr: k.rvcResample,
    rms_mix_rate: k.rvcCampurRms,
    protect: k.rvcProteksi,
  }
}

/**
 * Sidik jari parameter untuk cache key. Urutan kunci disortir supaya hasilnya
 * stabil, dan `index_rate === 0` menghasilkan penanda `tanpa-index` (padanan
 * `"tanpa-index"` di `tts_rvc.py`) agar audio ber-index dan tanpa-index tidak
 * pernah berbagi entri cache.
 */
export function sidikJariRvc(k: Konfig, tandaCheckpoint: string, tandaIndex: string): string {
  const p = paramAktif(k)
  const bagian = Object.keys(p)
    .sort()
    .map(kunci => `${kunci}=${p[kunci as keyof RvcParams]}`)
  bagian.push(tandaCheckpoint)
  bagian.push(p.index_rate ? tandaIndex : 'tanpa-index')
  return bagian.join('|')
}

/** Laju keluaran RVC menurut checkpoint (dibuktikan spike; 40000 untuk v2 kita). */
export const LAJU_KELUARAN_RVC_DEFAULT = 40000
