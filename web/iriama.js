// @ts-check
/**
 * Irama render. Dua keadaan yang selama ini tidak dibedakan:
 *
 *   halaman terlihat & jendela fokus  ->  gambar penuh (60 FPS di hardware ini)
 *   halaman terlihat & tidak fokus    ->  dibatasi (bawaan 30 FPS)
 *   halaman tersembunyi / diminimakan ->  ticker berhenti total
 *
 * Yang terakhir itu alasan berkas ini ada. Chromium sendiri sudah memotong tab
 * latar sampai ~1 FPS, jadi "tab latar" bukan borosnya; yang benar-benar boros
 * adalah jendela yang terlihat tapi tidak dilihat -- overlay selalu-di-depan,
 * atau jendela yang tertutup jendela lain sebagian -- dan window.model ini tetap
 * minta 60 frame per detik di sana. Terukur: tanpa modul ini kanvas menggambar
 * terus sampai perangkatnya panas.
 *
 * Dua hal yang sudah diukur sebelum kode ini ditulis (bukan diasumsikan):
 *   - app.ticker bukan Ticker.shared, jadi stop() hanya memengaruhi avatar ini;
 *   - model Live2D ikut ticker itu (registerTicker di main.js), jadi stop()
 *     menghentikan PEMBARUAN parameter sekaligus PENGGAMBARAN, dan _requestId
 *     jadi null: tidak ada requestAnimationFrame yang tertinggal di antrean.
 *   - start() lagi setelah jeda panjang tidak melompat: deltaMS frame pertama
 *     tetap kecil karena Pixi memasang ulang clock-nya sendiri, jadi motion
 *     timeline tidak melompat ke tengah.
 *
 * Suara TIDAK tersentuh: audio diputar elemen <audio>, dan rahang dibaca dari
 * posisi audio (tingkatMulut), jadi saat halaman tersembunyi mulutnya membeku
 * tapi suaranya tetap jalan, dan begitu muncul lagi rahangnya langsung benar --
 * bukan mulai dari nol.
 */

/**
 * @param {{
 *   app: any,
 *   fpsEl: HTMLElement | null,
 *   jedaSaatSembunyi: boolean,
 *   fpsSaatTakFokus: number,
 *   setelahLanjut?: () => void,
 * }} opsi
 * @returns {{ status(): {sembunyi: boolean, fokus: boolean, batasFps: number, jalan: boolean}, copot(): void }}
 */
export function pasangIrama({ app, fpsEl, jedaSaatSembunyi, fpsSaatTakFokus, setelahLanjut }) {
  const ticker = app.ticker;
  let jeda = false;

  const tulis = (/** @type {string} */ teks) => {
    if (fpsEl) fpsEl.textContent = teks;
  };

  function terapkan() {
    const sembunyi = document.hidden;
    if (sembunyi && jedaSaatSembunyi) {
      if (ticker.started) ticker.stop();
      if (!jeda) {
        jeda = true;
        // Angka FPS terakhir akan tetap terbaca selamanya kalau tidak diganti:
        // "60" pada halaman yang tidak menggambar apa pun adalah bohong.
        tulis('jeda');
      }
      return;
    }

    const fokus = document.hasFocus();
    // 0 di Pixi berarti "sebisa rAF", bukan "nol frame".
    const batas = fokus ? 0 : Math.max(0, fpsSaatTakFokus);
    if (ticker.maxFPS !== batas) ticker.maxFPS = batas;

    if (!ticker.started) {
      ticker.start();
      // Meteran FPS memegang waktu frame terakhir; tanpa reset, detik pertama
      // sesudah bangun menampilkan FPS yang sangat kecil.
      setelahLanjut?.();
    }
    jeda = false;
  }

  document.addEventListener('visibilitychange', terapkan);
  window.addEventListener('focus', terapkan);
  window.addEventListener('blur', terapkan);
  terapkan();

  return {
    status: () => ({
      sembunyi: document.hidden,
      fokus: document.hasFocus(),
      batasFps: ticker.maxFPS,
      jalan: !!ticker.started,
      jeda,
    }),
    copot() {
      document.removeEventListener('visibilitychange', terapkan);
      window.removeEventListener('focus', terapkan);
      window.removeEventListener('blur', terapkan);
    },
  };
}
