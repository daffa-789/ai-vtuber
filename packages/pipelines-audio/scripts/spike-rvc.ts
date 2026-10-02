/**
 * SPIKE sekali pakai — men-de-risk Fase 4 sebelum monorepo dibangun penuh.
 *
 * Tujuan: mengubah setiap "asumsi untuk divalidasi" di rencana §5 menjadi FAKTA:
 *   1. `pthToOnnx` benar-benar bisa mengubah SilverWolfJP.pth → ONNX;
 *   2. nama + dimensi tensor masuk/keluar setiap model ONNX yang kita punya;
 *   3. laju sampel yang dinyatakan checkpoint.
 *
 * Jalankan: npm run spike:rvc
 */
import { existsSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import * as ort from 'onnxruntime-node'
import { cariAkarRepo } from '@silverwolf/core-config/paths'
import { konversiPthKeOnnx, jalurPthBawaan } from './pth2onnx.ts'

const akar = cariAkarRepo()

function mb(byte: number): string {
  return `${(byte / 1024 / 1024).toFixed(1)} MB`
}

/** Baca nama + bentuk tensor masuk/keluar sebuah model ONNX. */
async function periksaOnnx(label: string, jalur: string): Promise<void> {
  if (!existsSync(jalur)) {
    console.log(`\n── ${label}\n   TIDAK ADA: ${jalur}`)
    return
  }
  const ukuran = statSync(jalur).size
  console.log(`\n── ${label}\n   ${jalur}  (${mb(ukuran)})`)
  try {
    const sesi = await ort.InferenceSession.create(jalur, {
      executionProviders: ['cpu'],
      graphOptimizationLevel: 'disabled',
    })
    console.log('   inputs :', JSON.stringify(sesi.inputNames))
    console.log('   outputs:', JSON.stringify(sesi.outputNames))
    // onnxruntime-node mengetik metadata sebagai array; di runtime ia dipakai
    // sebagai map nama→metadata, jadi kita lewati lewat Record.
    const metaMasuk = sesi.inputMetadata as unknown as Record<string, { type: string, isTensor: boolean }>
    const metaKeluar = sesi.outputMetadata as unknown as Record<string, { type: string, isTensor: boolean }>
    for (const nama of sesi.inputNames) {
      const meta = metaMasuk[nama]
      if (meta)
        console.log(`     in  ${nama}: ${meta.type} isTensor=${meta.isTensor}`)
    }
    for (const nama of sesi.outputNames) {
      const meta = metaKeluar[nama]
      if (meta)
        console.log(`     out ${nama}: ${meta.type} isTensor=${meta.isTensor}`)
    }
    await sesi.release()
  }
  catch (err) {
    console.log('   GAGAL dibuka:', (err as Error).message)
  }
}

/** Cari berkas .onnx di beberapa lokasi kandidat dan periksa semuanya. */
async function utama(): Promise<void> {
  console.log('=== SPIKE RVC — memvalidasi asumsi rencana §5 ===')
  console.log('akar repo:', akar)

  // ── 1. Konversi .pth → .onnx ────────────────────────────────────────────
  const pth = jalurPthBawaan()
  const keluaran = join(akar, 'assets', 'voices', 'silverwolf', 'model.onnx')
  console.log('\n[1] Konversi .pth → .onnx')
  console.log('    sumber:', pth, existsSync(pth) ? `(${mb(statSync(pth).size)})` : '(TIDAK ADA)')

  if (existsSync(pth)) {
    try {
      const hasil = await konversiPthKeOnnx(pth, keluaran)
      console.log('    OK — sampleRate:', hasil.sampleRate, 'Hz')
      console.log('    versi:', hasil.versi, '| useF0:', hasil.useF0, '| bobot:', hasil.jumlahBobot)
      console.log('    keluaran:', hasil.jalurKeluar, `(${mb(hasil.byte)})`)
    }
    catch (err) {
      console.log('    GAGAL:', (err as Error).message)
    }
  }
  else {
    console.log('    Dilewati: checkpoint .pth tidak ada di mesin ini.')
  }

  // ── 2. Periksa setiap ONNX yang relevan ─────────────────────────────────
  console.log('\n[2] Metadata tensor model ONNX')
  await periksaOnnx('RMVPE (f0) — sudah ONNX', join(akar, 'aset', 'suara', 'model-dasar', 'rmvpe.onnx'))
  await periksaOnnx('Generator RVC hasil konversi', keluaran)
  await periksaOnnx(
    'ContentVec/HuBERT ONNX (kalau sudah disediakan)',
    join(akar, 'assets', 'encoders', 'contentvec.onnx'),
  )

  // ── 3. Laporkan apa yang belum ada ──────────────────────────────────────
  const hubertPt = join(akar, 'aset', 'suara', 'model-dasar', 'hubert_base.pt')
  const contentvec = join(akar, 'assets', 'encoders', 'contentvec.onnx')
  console.log('\n[3] Aset yang masih kurang untuk Fase 4')
  console.log('    hubert_base.pt :', existsSync(hubertPt) ? 'ADA (PyTorch, belum ONNX)' : 'tidak ada')
  console.log('    contentvec.onnx:', existsSync(contentvec) ? 'ADA' : 'BELUM — perlu unduh vec-768-layer-12.onnx')
  console.log('    rmvpe.onnx     :', existsSync(join(akar, 'aset', 'suara', 'model-dasar', 'rmvpe.onnx')) ? 'ADA' : 'tidak ada')

  console.log('\n=== SPIKE selesai ===')
}

await utama()
