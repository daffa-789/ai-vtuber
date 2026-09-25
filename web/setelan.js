// Konfigurasi avatar yang SEDANG dipakai browser.
//
// Dulu bacaannya `import.meta.env` (punya Vite). Sekarang halaman ini disajikan
// Python tanpa bundler, jadi .env disuntikkan ke `window.__VTUBER_ENV__` lewat
// index.html -- isinya tetap kunci VITE_* yang sama, parser-nya tetap
// konfigurasi.mjs yang sama dengan yang dipakai `node scripts/pasang-model.mjs`.
import { bacaKonfigurasi } from './konfigurasi.mjs';

export const setelan = bacaKonfigurasi(window.__VTUBER_ENV__ || {});

/** `auto` = ikuti devicePixelRatio (dibatasi VITE_RENDER_SKALA_MAKS); angka = paksa. */
export function skalaRender(dpr = window.devicePixelRatio || 1) {
  const paksa = setelan.render.skala;
  if (paksa !== null) return paksa;
  return Math.min(dpr, setelan.render.skalaMaks);
}

/** Nilai CSS untuk lebar/tinggi kotak avatar; kosong berarti ikut VITE_PANGGUNG_UKURAN. */
export function ukuranPanggung() {
  const { ukuran, lebar, tinggi } = setelan.panggung;
  return { lebar: lebar || ukuran, tinggi: tinggi || ukuran };
}
