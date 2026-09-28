// @ts-check
/**
 * Mesin keadaan gerak: `diam` -> `bicara` -> `tidur`.
 *
 * Kenapa modul ini ada: model ini hanya punya empat motion (berubah-1, berubah-2,
 * siklus, tidur) dan sebelumnya satu-satunya jalan memanggilnya adalah tombol di
 * mode browser -- yang disembunyikan di mode pet. Tanpa mesin ini karakternya
 * patung yang hanya bergerak kalau Master menekan sesuatu.
 *
 * Kenapa waktu dihitung dari SELISIH FRAME dan bukan jam dinding: saat jendela
 * tersembunyi, ticker-nya dihentikan (web/iriama.js). Diukur dengan jam dinding,
 * waktu di belakang layar ikut terhitung dan dia langsung masuk `tidur` pada
 * frame pertama setelah jendelanya dibuka lagi -- padahal justru itu momen dia
 * seharusnya bangun.
 *
 * Kejujuran pada datanya: tidak ada motion "bicara" di model ini, jadi `bicara`
 * BUKAN animasi ngobrol. Rahang tetap dari amplitudo audio (main.js), dan keadaan
 * ini hanya menambahkan satu isyarat badan di awal balasan -- itu pun bawaannya
 * mati (VITE_KEADAAN_GERAK_BICARA="kosong") karena empat berkas motion yang ada
 * lebih cocok dipakai untuk hal lain.
 */
import { pasangStatusSuara } from './suara.js';

const PRIORITAS = { ambient: 1, bicara: 2 };

/** @param {number} dasar */
function acak(dasar) {
  // 0.5..1.5 x dasar: pengingat ambient yang periodik terbaca seperti metronom.
  return Math.max(0.5, dasar * (0.5 + Math.random()));
}

/**
 * @param {{
 *   konfig: any,
 *   daftar: Map<string, unknown>,
 *   picu: (nama: string, prioritas: number) => boolean,
 *   berhenti: () => void,
 *   peringatan: string[],
 * }} opsi
 */
export function pasangKeadaan({ konfig, daftar, picu, berhenti, peringatan }) {
  const k = konfig.keadaan;

  const pilih = (nama, kunci) => {
    if (!k.hidup || !nama || nama === 'kosong') return '';
    if (!daftar.has(nama)) {
      peringatan.push(`${kunci}: "${nama}" bukan nama gerakan (daftar VITE_GERAK_ ...)`);
      return '';
    }
    return nama;
  };
  const gerakDiam = pilih(k.gerakDiam, 'VITE_KEADAAN_GERAK_DIAM');
  const gerakBicara = pilih(k.gerakBicara, 'VITE_KEADAAN_GERAK_BICARA');
  const gerakTidur = pilih(k.gerakTidur, 'VITE_KEADAAN_GERAK_TIDUR');

  let nama = 'diam';
  let sejak = 0;
  let sejakAktif = 0;
  let sejakGerak = 0;
  let jedaBerikut = acak(k.jedaDetik);
  let terakhir = performance.now();
  /** Balasan yang membawa tag [gerak:] tidak perlu disela isyarat tambahan. */
  let balasanPunyaGerak = false;

  /** Semua yang berarti "Master masih di sini". */
  function aktif() {
    sejakAktif = 0;
    if (nama === 'tidur') {
      berhenti();
      // Bangun dari motion yang melooping: motionFinish tidak akan pernah membakar,
      // jadi bekas parameternya dibersihkan langsung.
      nama = 'diam';
      sejak = 0;
      jedaBerikut = acak(k.jedaDetik);
    }
  }

  const dengar = () => aktif();
  window.addEventListener('pointerdown', dengar);
  window.addEventListener('keydown', dengar);

  const lepasSuara = pasangStatusSuara((keadaan) => {
    if (keadaan === 'berbicara') {
      aktif();
      if (nama !== 'bicara') {
        nama = 'bicara';
        sejak = 0;
        if (gerakBicara && !balasanPunyaGerak) picu(gerakBicara, PRIORITAS.bicara);
      }
    } else if (keadaan === 'diam' && nama === 'bicara') {
      nama = 'diam';
      sejak = 0;
    }
  });

  return {
    /**
     * Dipanggil dari sisi chat: 'kirim' menandai awal balasan, 'gerak' menandai
     * balasan itu sudah membawa gerakannya sendiri.
     * @param {'kirim' | 'gerak'} apa
     */
    catat(apa) {
      if (apa === 'kirim') {
        balasanPunyaGerak = false;
        sejakGerak = 0;
      } else if (apa === 'gerak') {
        balasanPunyaGerak = true;
      }
      aktif();
    },

    /** Satu kali per frame, dari ticker yang sama dengan avatar. */
    perFrame() {
      const dt = Math.min(0.25, (performance.now() - terakhir) / 1000);
      terakhir = performance.now();
      // Jendela tersembunyi tapi ticker masih jalan (VITE_IRAMA_JEDA_SAAT_SEMBUNYI
      // =tidak): jangan hitung waktu dan jangan mulai apa pun di belakang punggung.
      if (document.hidden) return;

      sejak += dt;
      sejakAktif += dt;
      sejakGerak += dt;

      if (nama === 'diam') {
        if (gerakTidur && sejakAktif >= k.detikTidur) {
          // Sekali coba per periode: picu() async, dan IDLE akan ditolak selama
          // ada motion lain berjalan -- menunggu lagi periode berikutnya.
          sejakAktif = 0;
          Promise.resolve(picu(gerakTidur, PRIORITAS.ambient)).then((jadi) => {
            if (jadi) {
              nama = 'tidur';
              sejak = 0;
            }
          });
          return;
        }
        if (gerakDiam && sejakGerak >= jedaBerikut) {
          sejakGerak = 0;
          jedaBerikut = acak(k.jedaDetik);
          picu(gerakDiam, PRIORITAS.ambient);
        }
      } else if (nama === 'bicara' && sejakAktif >= 0.5) {
        // Suara berhenti tanpa panggilan 'diam' (pemutar gugur): kembali normal.
        nama = 'diam';
        sejak = 0;
      }
    },

    status: () => ({
      nama,
      sejakSah: +sejak.toFixed(2),
      sejakAktifSah: +sejakAktif.toFixed(2),
      jedaBerikutSah: +jedaBerikut.toFixed(2),
      hidup: !!k.hidup,
      gerak: { diam: gerakDiam, bicara: gerakBicara, tidur: gerakTidur },
    }),

    copot() {
      window.removeEventListener('pointerdown', dengar);
      window.removeEventListener('keydown', dengar);
      lepasSuara?.();
    },
  };
}
