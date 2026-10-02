import { describe, expect, it } from 'vitest'
import { buangTag, potongKalimat } from '../src/kalimat.ts'

/**
 * Pemotong kalimat menentukan KAPAN suara pertama terdengar. Kalau dia
 * memotong terlalu cepat, kalimat terdengar terputus-putus; kalau terlalu
 * lambat, kita kembali ke masalah semula (menunggu seluruh balasan).
 */
describe('pemotong kalimat', () => {
  it('melepaskan kalimat yang sudah punya penutup, sisanya ditahan', () => {
    const { kalimat, sisa } = potongKalimat('Beres, Master. Ini masih')
    expect(kalimat).toEqual(['Beres, Master.'])
    expect(sisa).toBe('Ini masih')
  })

  it('menahan kalimat sampai titiknya muncul', () => {
    expect(potongKalimat('Beres, Master')).toEqual({ kalimat: [], sisa: 'Beres, Master' })
    expect(potongKalimat('Beres, Master.').kalimat).toEqual(['Beres, Master.'])
  })

  it('memotong beberapa kalimat sekaligus', () => {
    const { kalimat, sisa } = potongKalimat('Satu hal. Dua hal! Tiga hal? Sisa')
    expect(kalimat).toEqual(['Satu hal.', 'Dua hal!', 'Tiga hal?'])
    expect(sisa).toBe('Sisa')
  })

  it('tidak memotong daftar bernomor atau angka desimal', () => {
    expect(potongKalimat('Ambil 3.14 dulu.').kalimat).toEqual(['Ambil 3.14 dulu.'])
    expect(potongKalimat('1. Pertama. 2. Kedua.').kalimat).toEqual(['1. Pertama.', '2. Kedua.'])
  })

  it('kalimat pendek menyatu dengan berikutnya, bukan diucapkan sendiri', () => {
    // "Oke." hanya 4 karakter -- akan terdengar aneh kalau berdiri sendiri.
    const { kalimat } = potongKalimat('Oke. Ini penjelasan panjang sekali.')
    expect(kalimat).toEqual(['Oke. Ini penjelasan panjang sekali.'])
  })

  it('tanda kutip/kurung penutup ikut ke kalimat', () => {
    expect(potongKalimat('Dia bilang "halo". Lalu pergi.').kalimat).toEqual([
      'Dia bilang "halo".',
      'Lalu pergi.',
    ])
  })

  it('baris baru juga jadi batas kalimat', () => {
    expect(potongKalimat('Baris satu\nBaris dua.').kalimat).toEqual(['Baris satu\nBaris dua.'])
  })

  it('teks kosong tidak menghasilkan apa pun', () => {
    expect(potongKalimat('')).toEqual({ kalimat: [], sisa: '' })
  })
})

/**
 * Tag kendali TIDAK BOLEH diucapkan. Piper akan membacanya sebagai kata
 * ("senyum") kalau lolos. Terukur pada MiniCPM5-2B: dengan persona cadangan
 * pendek, tag keluar di TENGAH kalimat ("Wajib [senyum]."), bukan di awal.
 */
describe('tag kendali tidak diucapkan', () => {
  it('membuang tag di awal kalimat', () => {
    expect(buangTag('[senyum] Halo Master.')).toBe(' Halo Master.')
  })

  it('membuang tag di tengah kalimat', () => {
    const { kalimat } = potongKalimat('Wajib [senyum]. Cari di kecil.')
    expect(kalimat.join(' ')).not.toContain('senyum')
    expect(kalimat[0]).toBe('Wajib .')
  })

  it('membuang tag yang muncul di setiap kalimat', () => {
    const { kalimat } = potongKalimat('Satu [netral]. Dua [senyum]. Tiga [lelah].')
    for (const k of kalimat) expect(k).not.toMatch(/\[|\]/)
  })

  it('membuang tag ber-kanal seperti [prop:kacamata]', () => {
    expect(buangTag('Pakai ini [prop:kacamata] ya.')).not.toContain('prop')
  })

  it('tidak merusak tanda kurung siku biasa di dalam kalimat', () => {
    expect(buangTag('Lihat array[0] dan item[1].')).toBe('Lihat array[0] dan item[1].')
  })
})
