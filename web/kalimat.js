/**
 * Pemotong jawaban menjadi potongan yang siap diucapkan.
 *
 * Berdiri sendiri (tanpa import apa pun) supaya bisa diuji langsung dari Node --
 * fungsi ini murni teks-ke-teks, dan mengujinya lewat browser yang memanggil API
 * sungguhan hanya akan memberi angka yang bergoyang.
 */

// Kalimat dianggap selesai kalau tanda bacanya diikuti spasi/baris, atau ada
// baris baru. Sisa yang belum bertanda selesai dikembalikan untuk chunk berikut.
const BATAS = /[^.!?…\n]*[.!?…]+(?=[\s\n])|[^\n]*\n/g;

// Potongan awal: minimal 8 karakter sebelum koma/titik-koma/titik-dua, supaya
// "[senyum] Ya," tidak dikirim sendirian sebagai suara satu kata.
const COMMA = /^[^,;:]{8,}?[,;:]/;

export function kalimatSiap(teks, potongAwal = false) {
  const siap = [];
  let akhir = 0;
  let m;
  BATAS.lastIndex = 0;
  while ((m = BATAS.exec(teks))) {
    const potong = teks.slice(akhir, m.index + m[0].length).trim();
    if (potong) siap.push(potong);
    akhir = m.index + m[0].length;
  }
  let sisa = teks.slice(akhir);

  if (potongAwal && !siap.length) {
    const awal = COMMA.exec(sisa);
    if (awal) {
      siap.push(awal[0].trim());
      sisa = sisa.slice(awal[0].length);
    }
  }
  return { siap, sisa };
}
