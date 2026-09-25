// Gerbang tag ekspresi: mana yang boleh dipanggil chat, dan bagaimana bentuknya
// di layar. Nama wajah dan nama pose TIDAK ditulis di sini -- keduanya datang
// dari .env (VITE_WAJAH_* dan VITE_POSE_*), lihat setelan.js.
import { setelan } from './setelan.js';

/** Tag yang mengganti raut wajah; satu wajah aktif pada satu waktu. */
export const NAMA_WAJAH = new Set(setelan.wajah.map((w) => w.nama));

/** Tag `[prop:nama]`; pose/aksesoris ini ditumpuk di atas wajah, bukan menggantikannya. */
export const NAMA_POSE = new Set(setelan.pose.map((p) => p.nama));

export const EKSPRESI_DASAR = setelan.ekspresiDasar;

/**
 * Mengupas tag `[...]` dari aliran teks tanpa menampilkannya ke layar.
 * Sisa potongan tag di akhir chunk ditahan sampai chunk berikutnya, supaya
 * penonton tidak pernah melihat `[se` lewat di gelembung chat.
 */
export function kupasTag(picu) {
  // 1..26 karakter: cukup untuk kanal kedua, `[prop:pamer-barang-1=mati]`,
  // tapi masih cukup pendek untuk tidak salah menelan kurung siku biasa.
  const TAG = /\[([^\n[]{1,26})\]/g;
  let simpan = '';

  return {
    tulis(chunk) {
      const teks = simpan + chunk;
      let keluaran = '';
      let batas = 0;
      TAG.lastIndex = 0;

      let m = TAG.exec(teks);
      while (m) {
        keluaran += teks.slice(batas, m.index);
        picu(m[1].trim().toLowerCase());
        batas = TAG.lastIndex;
        m = TAG.exec(teks);
      }

      const ekor = teks.slice(batas);
      const buka = ekor.lastIndexOf('[');
      if (buka === -1) {
        keluaran += ekor;
        simpan = '';
      } else {
        keluaran += ekor.slice(0, buka);
        simpan = ekor.slice(buka);
      }
      return keluaran;
    },

    // Tag yang tidak pernah tertutup berarti model tidak menaati format:
    // tampilkan apa adanya daripada menghilangkannya diam-diam.
    tutup() {
      const sisa = simpan;
      simpan = '';
      return sisa;
    },
  };
}
