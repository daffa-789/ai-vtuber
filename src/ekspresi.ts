// Tag ekspresi dari model -> nama ekspresi pada model Penyihir.
// Nama sengaja dibuat sama dengan tag di persona.md, sehingga berkas
// public/models/penyihir/ekspresi/<nama>.exp3.json bisa dicari dengan mata.
// Peta ini tetap dipakai sebagai gerbang: tag di luar daftar diabaikan chat.ts.
export const TAG_KE_EKSPRESI: Record<string, string> = {
  netral: 'netral', // mata terbuka, senyum tipis
  semangat: 'semangat', // mata bintang, senyum lebar
  kaget: 'kaget', // mata melebar, mulut terbuka
  lelah: 'lelah', // mata setengah terpejam, alis turun
  senyum: 'senyum', // mata menyempit, mulut melengkung jelas
  bingung: 'bingung', // bayangan muram di mata, setetes keringat
  goda: 'goda', // pupil berbentuk hati
  sebal: 'sebal', // alis turun, mulut ditekuk
  sedih: 'sedih', // mata berair, alis naik ke dalam
};

export const EKSPRESI_DASAR = TAG_KE_EKSPRESI.netral;

/**
 * Mengupas tag `[...]` dari aliran teks tanpa menampilkannya ke layar.
 * Sisa potongan tag di akhir chunk ditahan sampai chunk berikutnya, supaya
 * penonton tidak pernah melihat `[se` lewat di gelembung chat.
 */
export function kupasTag(picu: (tag: string) => void) {
  const TAG = /\[([^\n[]{1,20})\]/g;
  let simpan = '';

  return {
    tulis(chunk: string): string {
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
    tutup(): string {
      const sisa = simpan;
      simpan = '';
      return sisa;
    },
  };
}
