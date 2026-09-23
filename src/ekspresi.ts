// Tag ekspresi dari model -> nama ekspresi pada model Haru.
// Nama f00..f07 diambil dari FileReferences.Expressions di haru_greeter_t03.model3.json.
// Maknanya dibaca dari kontak sheet wajah (.shots/kontak-besar.png), bukan dari
// nama parameter — tebakan awal dari parameter ternyata salah di f02/f05.
export const TAG_KE_EKSPRESI: Record<string, string> = {
  netral: 'f00', // mata terbuka, senyum tipis
  semangat: 'f01', // mulut terbuka lebar
  kaget: 'f02', // alis berkerut, mulut "o"
  lelah: 'f03', // mata setengah terpejam, mulut datar
  senyum: 'f04', // mata terpejam, pipi merah, senyum lebar
  bingung: 'f05', // mata melebar, mulut datar
  goda: 'f06', // mata setengah, pipi merah, senyum kecil
  sebal: 'f07', // mata turun, mulut datar
  sedih: 'f03', // model ini tidak punya wajah sedih; ini kedekatan terbaik
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
