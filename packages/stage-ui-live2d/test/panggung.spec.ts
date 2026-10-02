import { describe, expect, it } from 'vitest'
import { bacaPanggung, hitungSkala } from '../src/panggung.ts'

/**
 * Regresi untuk bug "karakter terlalu ke-zoom".
 *
 * Versi lama menghitung `min(screen/model.width, ...)` -- dan `model.width`
 * getter PIXI adalah `scale.x * getLocalBounds().width`, jadi nilainya ikut
 * berubah oleh skala yang sedang dihitung. Fungsi `fit()` jadi tidak idempoten
 * dan karakter berpindah antara "pas" dan ukuran native model setiap kali
 * jendela di-resize.
 */
describe('tata letak panggung', () => {
  it('skala tidak berubah walau dihitung berulang kali (idempoten)', () => {
    const [W, H, w0, h0] = [760, 1000, 1024, 2048]
    const pertama = hitungSkala(W, H, w0, h0, 0.96)
    // Simulasi pemanggilan kedua: ukuran "dasar" yang dipakai rumus lama adalah
    // model.width = skala_sebelumnya * w0. Rumus baru tidak memakainya sama sekali.
    const kedua = hitungSkala(W, H, w0, h0, 0.96)
    expect(pertama).toBeCloseTo(kedua, 12)
    expect(pertama).toBeCloseTo((H / h0) * 0.96, 12)
  })

  it('karakter selalu masuk kotak (contain), tidak pernah terpotong', () => {
    for (const [W, H, w0, h0] of [
      [760, 1000, 1024, 2048], // kotak tinggi, model tinggi
      [1600, 600, 2048, 1024], // kotak lebar, model lebar
      [400, 400, 1000, 3000], // model sangat tinggi
    ]) {
      const s = hitungSkala(W, H, w0, h0, 0.96)
      expect(w0 * s).toBeLessThanOrEqual(W + 1e-9)
      expect(h0 * s).toBeLessThanOrEqual(H + 1e-9)
    }
  })

  it('zoom 1 mengisi sisi terpendek persis; ukuran 0/tak valid jadi 0', () => {
    expect(hitungSkala(800, 800, 400, 400, 1)).toBe(2)
    expect(hitungSkala(0, 800, 400, 400, 1)).toBe(0)
    expect(hitungSkala(800, 800, 0, 400, 1)).toBe(0)
  })

  it('bacaPanggung memakai bawaan .env bila env kosong', () => {
    expect(bacaPanggung({})).toEqual({ zoom: 0.96, x: 0.5, jangkar: 1, skalaMaks: 2 })
    expect(bacaPanggung({ VITE_AVATAR_ZOOM: '0.8', VITE_AVATAR_X: '0.25' })).toMatchObject({
      zoom: 0.8,
      x: 0.25,
      jangkar: 1,
    })
  })
})
