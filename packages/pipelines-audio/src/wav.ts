/**
 * Port `server_py/wav.py`.
 *
 * `sudahWav` dan `puncak` dipertahankan apa adanya karena keduanya menutup dua
 * bug nyata yang pernah terjadi di proyek lama:
 *   - membungkus ulang WAV yang sudah lengkap menghasilkan berkas rusak
 *     ("suara hilang diam-diam saat model TTS diganti");
 *   - mengukur puncak dari CUPLIKAN AWAL (4096 frame) menyatakan keluaran RVC
 *     sebagai bisu, karena RVC membuka dengan ramp hening. Puncak WAJIB diukur
 *     dari seluruh berkas.
 */

export class WavRusak extends Error {
  override name = 'WavRusak'
}

/**
 * Ambang "berkas ini benar-benar ada isinya", dalam amplitudo PCM16 (0..32767).
 * 400 dipilih karena `suara.js` memakai LANTAI_NOISE 0,012 (~393 dari 32767):
 * di bawah angka ini rahang tidak bergerak sama sekali.
 */
export const AMBANG_DENGAR = 400

/** Padanan `pcm_ke_wav`: bungkus PCM mentah jadi WAV PCM16. */
export function pcmKeWav(pcm: Uint8Array, laju: number, kanal = 1): Uint8Array {
  const header = new ArrayBuffer(44)
  const dv = new DataView(header)
  const tulisStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++)
      dv.setUint8(offset + i, s.charCodeAt(i))
  }
  tulisStr(0, 'RIFF')
  dv.setUint32(4, 36 + pcm.length, true)
  tulisStr(8, 'WAVE')
  tulisStr(12, 'fmt ')
  dv.setUint32(16, 16, true)
  dv.setUint16(20, 1, true) // PCM
  dv.setUint16(22, kanal, true)
  dv.setUint32(24, laju, true)
  dv.setUint32(28, laju * kanal * 2, true) // byte rate
  dv.setUint16(32, kanal * 2, true) // block align
  dv.setUint16(34, 16, true) // bit depth
  tulisStr(36, 'data')
  dv.setUint32(40, pcm.length, true)

  const keluar = new Uint8Array(44 + pcm.length)
  keluar.set(new Uint8Array(header), 0)
  keluar.set(pcm, 44)
  return keluar
}

/** Padanan `sudah_wav`. */
export function sudahWav(bin: Uint8Array): boolean {
  return (
    bin.length > 12
    && bin[0] === 0x52 && bin[1] === 0x49 && bin[2] === 0x46 && bin[3] === 0x46 // RIFF
    && bin[8] === 0x57 && bin[9] === 0x41 && bin[10] === 0x56 && bin[11] === 0x45 // WAVE
  )
}

/** Padanan `laju_kanal`. Contoh: 'audio/L16;codec=pcm;rate=24000'. */
export function lajuKanal(mime: string): [number, number] {
  const angka = [...mime.matchAll(/(?:rate|channels)=(\d+)/g)].map(m => Number(m[1]))
  return [angka[0] ?? 24000, angka[1] ?? 1]
}

export interface HeaderWav {
  laju: number
  kanal: number
  detik: number
  bitDepth: number
  jumlahFrame: number
  /** Offset byte awal blok `data`. */
  offsetData: number
  /** Panjang byte blok `data`. */
  panjangData: number
}

/**
 * Padanan `baca_header`: (laju, kanal, detik) + metadata yang dibutuhkan
 * pembaca PCM. Menelusuri chunk RIFF (bukan mengasumsikan offset 44) supaya
 * WAV dengan chunk `LIST`/`fact` tetap terbaca — inilah sebabnya modul Python
 * memakai modul `wave` alih-alih aritmetika offset tetap.
 */
export function bacaHeader(bin: Uint8Array): HeaderWav {
  if (!sudahWav(bin))
    throw new WavRusak('bukan WAV: header RIFF/WAVE tidak ada')

  const dv = new DataView(bin.buffer, bin.byteOffset, bin.byteLength)
  let pos = 12
  let laju = 0
  let kanal = 0
  let bitDepth = 16
  let offsetData = -1
  let panjangData = 0

  while (pos + 8 <= bin.length) {
    const id = String.fromCharCode(bin[pos]!, bin[pos + 1]!, bin[pos + 2]!, bin[pos + 3]!)
    const ukuran = dv.getUint32(pos + 4, true)
    const isi = pos + 8
    if (id === 'fmt ' && isi + 16 <= bin.length) {
      kanal = dv.getUint16(isi + 2, true)
      laju = dv.getUint32(isi + 4, true)
      bitDepth = dv.getUint16(isi + 14, true)
    }
    else if (id === 'data') {
      offsetData = isi
      panjangData = Math.min(ukuran, bin.length - isi)
    }
    pos = isi + ukuran + (ukuran % 2) // chunk ganjil dipad satu byte
  }

  if (!laju)
    throw new WavRusak('laju sampel nol atau header fmt tidak ditemukan')
  if (offsetData < 0)
    throw new WavRusak('blok data tidak ditemukan')

  const bytePerFrame = Math.max(kanal, 1) * Math.max(bitDepth / 8, 1)
  const jumlahFrame = Math.floor(panjangData / bytePerFrame)
  return {
    laju,
    kanal,
    detik: jumlahFrame / laju,
    bitDepth,
    jumlahFrame,
    offsetData,
    panjangData,
  }
}

/**
 * Padanan `puncak`: amplitudo absolut terbesar di SELURUH berkas.
 *
 * `batasFrame` adalah PLAFON KEAMANAN (~100 detik @40 kHz), bukan jendela
 * sampling. Jangan pernah mengubahnya menjadi "cuplikan awal" — itu bug yang
 * membuat seluruh kalimat RVC dinyatakan bisu (lihat docstring `wav.py`).
 */
export function puncak(bin: Uint8Array, batasFrame = 4_000_000): number {
  let h: HeaderWav
  try {
    h = bacaHeader(bin)
  }
  catch (err) {
    throw new WavRusak(`isi WAV tidak terbaca: ${(err as Error).message}`)
  }
  if (h.bitDepth !== 16)
    return 1 // bukan PCM16; jangan sebut diam, kita tidak tahu

  const dv = new DataView(bin.buffer, bin.byteOffset, bin.byteLength)
  const kanal = Math.max(h.kanal, 1)
  const frameTerbaca = Math.min(h.jumlahFrame, batasFrame)
  const bytePerFrame = kanal * 2
  let tertinggi = 0

  for (let f = 0; f < frameTerbaca; f++) {
    const dasar = h.offsetData + f * bytePerFrame
    for (let c = 0; c < kanal; c++) {
      const s = dv.getInt16(dasar + c * 2, true)
      const a = Math.abs(s)
      if (a > tertinggi)
        tertinggi = a
      if (tertinggi >= 32767)
        return 32767 // tidak mungkin lebih tinggi
    }
  }
  return tertinggi
}

/** True bila berkas lolos ambang dengar (padanan pemeriksaan di jalur_suara). */
export function adaBunyi(bin: Uint8Array): boolean {
  return puncak(bin) > AMBANG_DENGAR
}
