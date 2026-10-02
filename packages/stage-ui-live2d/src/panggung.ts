/**
 * Tata letak karakter — sengaja terpisah dari `index.ts` agar tidak menarik
 * PIXI/Cubism dan bisa diuji di lingkungan Node biasa.
 */

/** Padanan blok `VITE_AVATAR_*` / `VITE_RENDER_*` di `.env`. */
export interface PanggungOptions {
  /** Bagian kotak yang boleh diisi karakter. 1 = pas penuh, <1 = lebih menjauh. */
  zoom: number
  /** Posisi mendatar: 0 = tepi kiri, 0.5 = tengah, 1 = tepi kanan. */
  x: number
  /** Jangkar vertikal: 1 = kaki menempel dasar, 0 = kepala di dasar. */
  jangkar: number
  /** Batas atas devicePixelRatio; 1 = hemat, 2 = tajam. */
  skalaMaks: number
}

function angka(value: string | undefined, bawaan: number): number {
  if (value === undefined || value.trim() === '') return bawaan
  const n = Number(value)
  return Number.isFinite(n) ? n : bawaan
}

/**
 * Baca `VITE_*` dari lingkungan build (Vite mengganti `import.meta.env` saat
 * bundling). Hanya kunci berawalan `VITE_` yang disuntikkan Vite, jadi jalur
 * berkas lokal (`VTUBER_*`) tidak pernah ikut ke halaman.
 */
export function bacaPanggung(
  env: Record<string, string | undefined> = import.meta.env,
): PanggungOptions {
  return {
    zoom: angka(env.VITE_AVATAR_ZOOM, 0.96),
    x: angka(env.VITE_AVATAR_X, 0.5),
    jangkar: angka(env.VITE_AVATAR_JANGKAR, 1),
    skalaMaks: angka(env.VITE_RENDER_SKALA_MAKS, 2),
  }
}

/**
 * Rumus skala karakter — sengaja dipisah jadi fungsi murni supaya bisa diuji.
 *
 * Memakai `min()` (contain): seluruh karakter terlihat, tidak pernah terpotong.
 * Argumen `dasar*` HARUS ukuran yang tidak berubah oleh skala
 * (`internalModel.width/height`), kalau tidak hasilnya tidak idempoten.
 */
export function hitungSkala(
  lebar: number,
  tinggi: number,
  dasarLebar: number,
  dasarTinggi: number,
  zoom: number,
): number {
  if (!lebar || !tinggi || !dasarLebar || !dasarTinggi) return 0
  return Math.min(lebar / dasarLebar, tinggi / dasarTinggi) * zoom
}
