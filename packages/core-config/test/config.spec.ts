import { describe, expect, it } from 'vitest'
import { angka, angkaFloat, bool_, daftar, nilai } from '../src/coerce.ts'
import type { EnvSource } from '../src/coerce.ts'
import { bacaEnv, potongKomentar } from '../src/env-file.ts'
import { bacaKonfig, parseAvatar } from '../src/index.ts'

function env(file: Record<string, string> = {}, environ: Record<string, string> = {}): EnvSource {
  return { file, environ, warnings: [] }
}

describe('parser .env (padanan baca_env / _potong_komentar)', () => {
  it('memotong komentar sebaris hanya bila didahului spasi', () => {
    // Nilai nyata dari .env.example: `VTUBER_VULKAN_NGL=99  # semua lapis`.
    expect(potongKomentar('99  # semua lapis')).toBe('99')
    // Warna dan resep tidak boleh dipotong: `#` tanpa spasi di depan.
    expect(potongKomentar('#fff')).toBe('#fff')
    expect(potongKomentar('grup=isyarat berkas=siklus.motion3.json')).toBe(
      'grup=isyarat berkas=siklus.motion3.json',
    )
  })

  it('nilai yang dikutip dipotong sampai kutip penutup saja', () => {
    expect(potongKomentar('"halo # bukan komentar"')).toBe('halo # bukan komentar')
    expect(potongKomentar("'a b c'")).toBe('a b c')
  })

  it('bacaEnv mengabaikan komentar penuh, baris kosong, dan baris tanpa =', () => {
    const isi = [
      '# komentar',
      '',
      'VTUBER_PORT=8787',
      'VTUBER_TAMPAK=pet   # wujud',
      'bukan-pasangan',
      'VITE_WAJAH_SENYUM=1',
    ].join('\n')
    expect(bacaEnv(isi)).toEqual({
      VTUBER_PORT: '8787',
      VTUBER_TAMPAK: 'pet',
      VITE_WAJAH_SENYUM: '1',
    })
  })
})

describe('koerser (padanan nilai/angka/angka_float/bool_/daftar)', () => {
  it('environment menang atas berkas, tapi yang kosong diabaikan', () => {
    const e = env({ VTUBER_PORT: '8787' }, { VTUBER_PORT: '9999' })
    expect(nilai(e, 'VTUBER_PORT')).toBe('9999')
    expect(nilai(env({ VTUBER_PORT: '8787' }, { VTUBER_PORT: '   ' }), 'VTUBER_PORT')).toBe('8787')
  })

  it('bool_ mengenal ya/tidak seperti Python, dan mencatat nilai tak dikenal', () => {
    expect(bool_(env({ A: 'ya' }), 'A', false)).toBe(true)
    expect(bool_(env({ A: 'tidak' }), 'A', true)).toBe(false)
    expect(bool_(env({ A: 'ON' }), 'A', false)).toBe(true)
    const e = env({ A: 'mungkin' })
    expect(bool_(e, 'A', true)).toBe(true)
    expect(e.warnings[0]).toContain('mungkin')
  })

  it('angka menolak desimal (itu tugas angka_float) dan jatuh ke bawaan', () => {
    const e = env({ A: '0.33' })
    expect(angka(e, 'A', 7)).toBe(7)
    expect(e.warnings).toHaveLength(1)
    expect(angkaFloat(env({ A: '0.33' }), 'A', 1)).toBe(0.33)
  })

  it('daftar memisah koma dan membuang yang kosong', () => {
    expect(daftar(env({ A: 'piper+rvc, piper ,' }), 'A', '')).toEqual(['piper+rvc', 'piper'])
  })
})

describe('bacaKonfig', () => {
  it('memakai seluruh nilai bawaan konfig.py saat .env kosong', () => {
    const k = bacaKonfig(env(), '/akar')
    expect(k.port).toBe(8787)
    expect(k.tampak).toBe('pet')
    expect(k.petSembunyi).toBe('layar-penuh')
    expect(k.petHotkey).toBe('ctrl+shift+s')
    expect(k.llmProvider).toBe('local')
    expect(k.ttsRantai).toEqual(['piper+rvc', 'piper'])
    expect(k.ttsBatasaDetik).toBe(20)
    // Default KODE (bukan .env.example): index tidak dibaca sama sekali.
    expect(k.rvcIndeksLaju).toBe(0)
    expect(k.rvcTranspose).toBe(0)
    expect(k.rvcF0).toBe('pm')
    expect(k.rvcModel).toBe('furina')
    expect(k.rvcCampurRms).toBe(1)
    expect(k.rvcProteksi).toBe(0.33)
    expect(k.sttBahasa).toBe('id')
    expect(k.maksPesan).toBe(24)
    expect(k.maksBody).toBe(65536)
  })

  it('vulkanCtx=0 berarti ikut konteks model lokal (padanan `or`)', () => {
    const k = bacaKonfig(env({ VTUBER_VULKAN_CTX: '0', VTUBER_LOCAL_MODEL_CTX: '4096' }), '/akar')
    expect(k.vulkanCtx).toBe(4096)
  })

  it('nilai .env.example yang menyimpang dari default kode terbaca apa adanya', () => {
    // Inilah konflik yang ditemukan saat perencanaan: .env.example memakai 0.6/10/rmvpe.
    const k = bacaKonfig(
      env({
        VTUBER_RVC_INDEKS_LAJU: '0.6',
        VTUBER_RVC_TRANSPOSE: '10',
        VTUBER_RVC_F0: 'rmvpe',
        VTUBER_RVC_CAMPUR_RMS: '0.8',
        VTUBER_TTS_BATAS_DETIK: '40',
        VTUBER_TTS_PIPER_PANJANG: '0.9',
      }),
      '/akar',
    )
    expect(k.rvcIndeksLaju).toBe(0.6)
    expect(k.rvcTranspose).toBe(10)
    expect(k.rvcF0).toBe('rmvpe')
    expect(k.rvcCampurRms).toBe(0.8)
    expect(k.ttsBatasaDetik).toBe(40)
    expect(k.piperPanjang).toBe(0.9)
  })

  it('tampak tidak dikenal jatuh ke pet; sembunyi tidak dikenal ke layar-penuh', () => {
    const k = bacaKonfig(env({ VTUBER_TAMPAK: 'ngawur', VTUBER_PET_SEMBUNYI: 'ngawur' }), '/akar')
    expect(k.tampak).toBe('pet')
    expect(k.petSembunyi).toBe('layar-penuh')
  })
})

describe('parseAvatar', () => {
  it('menurunkan nama wajah/pose dari kunci, dan gerak dari isinya', () => {
    const hasil = parseAvatar(
      env({
        VITE_WAJAH_SENYUM: '1',
        VITE_POSE_TANGAN_1: '1',
        VITE_GERAK_SIKLUS: 'grup=isyarat berkas=siklus.motion3.json ulang=true',
      }),
      '/akar',
      berkas => (berkas === 'siklus.motion3.json' ? 3 : 0),
    )
    expect(hasil.wajah).toEqual([{ nama: 'senyum' }])
    expect(hasil.pose).toEqual([{ nama: 'tangan-1' }])
    expect(hasil.gerak).toEqual([
      { nama: 'siklus', grup: 'isyarat', indeks: 3, ulang: true },
    ])
  })
})
