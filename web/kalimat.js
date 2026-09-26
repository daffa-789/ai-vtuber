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

export function kalimatSiap(teks) {
  const siap = [];
  let akhir = 0;
  let m;
  BATAS.lastIndex = 0;
  while ((m = BATAS.exec(teks))) {
    const potong = teks.slice(akhir, m.index + m[0].length).trim();
    if (potong) siap.push(potong);
    akhir = m.index + m[0].length;
  }
  const sisa = teks.slice(akhir);
  return { siap, sisa };
}
