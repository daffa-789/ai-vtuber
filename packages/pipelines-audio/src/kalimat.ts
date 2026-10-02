/**
 * Pemotong kalimat untuk TTS per-kalimat (`VTUBER_TTS_PER_KALIMAT`).
 *
 * Tujuannya supaya suara pertama terdengar setelah kalimat PERTAMA selesai
 * ditulis model, bukan setelah seluruh balasan rampung. Di mesin ini itu
 * menghemat 6-10 detik per balasan (LLM ~10 token/detik).
 *
 * Dipisah jadi fungsi murni agar bisa diuji tanpa browser.
 */

/** Karakter yang menutup sebuah kalimat. */
const PENUTUP = '.!?…。！？'
/** Tanda kutip/kurung penutup yang boleh mengikuti penutup kalimat. */
const EKOR = '"\'”’)]}»'
/**
 * Tag kendali dalam kurung siku: `[senyum]`, `[prop:kacamata]`. Tidak pernah
 * diucapkan — kalau lolos ke TTS, Piper membacanya sebagai kata.
 */
const TAG = /\[[a-zA-Z][^\]\n]{0,40}\]/g

/**
 * Potong teks jadi kalimat-kalimat utuh.
 *
 * - `sisa` adalah potongan terakhir yang belum punya penutup — jangan diucapkan
 *   dulu, karena model masih menulisnya.
 * - Fragmen satu kata yang pendek ("Oke.", "Ya.") digabung ke kalimat
 *   berikutnya, karena terdengar aneh kalau diucapkan berdiri sendiri. Kalimat
 *   pendek TAPI lebih dari satu kata tetap dilepas — menahannya justru
 *   mengembalikan latency yang ingin kita hilangkan.
 */
export function potongKalimat(teks: string, minimal = 12): { kalimat: string[]; sisa: string } {
  return potongBersih(buangTag(teks), minimal)
}

/**
 * Buang tag kendali `[...]` sebelum disuarakan.
 *
 * Persona meminta tag di awal balasan, tapi model 2B kadang menyelipkannya di
 * tengah ("Wajib [senyum].") atau mengulangnya tiap kalimat. Menyaring di sini
 * membuat tulisan model tidak pernah terdengar, apa pun yang dilakukannya.
 */
export function buangTag(teks: string): string {
  return teks.replace(TAG, ' ').replace(/[ \t]{2,}/g, ' ')
}

function potongBersih(teks: string, minimal: number): { kalimat: string[]; sisa: string } {
  const kalimat: string[] = []
  let awal = 0

  for (let i = 0; i < teks.length; i++) {
    const c = teks[i]!
    if (!PENUTUP.includes(c)) continue
    // Bukan akhir kalimat: "1." pada daftar bernomor, atau titik desimal "3.14".
    if (bukanAkhirKalimat(teks, i)) continue
    // Penutup harus diikuti spasi/baris/akhir teks, atau tanda kutip penutup.
    let j = i + 1
    while (j < teks.length && EKOR.includes(teks[j]!)) j++
    const berikut = teks[j]
    if (berikut !== undefined && !/[\s\n]/.test(berikut)) continue

    const potongan = teks.slice(awal, j).trim()
    // Tahan hanya kalau pendek DAN cuma satu kata.
    if (potongan.length >= minimal || /\s/.test(potongan)) {
      kalimat.push(potongan)
      awal = j
    }
  }

  return { kalimat, sisa: teks.slice(awal).replace(/^\s+/, '') }
}

/**
 * Titik setelah angka yang BUKAN penutup kalimat.
 *
 * - desimal: "3.14"          -> angka setelah titik
 * - daftar bernomor: "1. "   -> titik di awal baris/setelah spasi
 * - BUKAN: "Nilainya 100."   -> angka utuh di akhir kalimat, tetap dipotong
 */
function bukanAkhirKalimat(teks: string, i: number): boolean {
  const sebelum = teks[i - 1]
  if (sebelum === undefined || sebelum < '0' || sebelum > '9') return false
  const sesudah = teks[i + 1]
  if (sesudah !== undefined && sesudah >= '0' && sesudah <= '9') return true
  const duaSebelum = teks[i - 2]
  return duaSebelum === undefined || /[\s\n(]/.test(duaSebelum)
}

/**
 * Potong sisa teks yang tersisa saat aliran selesai (tanpa penutup kalimat).
 * Dipakai agar kalimat terakhir yang tidak diakhiri titik tetap diucapkan.
 */
export function sisaKalimat(teks: string): string {
  return teks.trim()
}
