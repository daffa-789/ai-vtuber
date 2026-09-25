// Unduh Cubism Core resmi Live2D dan salin aset VAD/ORT lokal jika ada.
import { copyFile, mkdir, readdir, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const CORE = 'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js';
const CORE_DEST = resolve('public/live2dcubismcore.min.js');

async function save(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, buf);
  return buf.length;
}

if (!existsSync(CORE_DEST)) {
  console.log('Mengunduh Live2D Cubism Core...');
  const bytes = await save(CORE, CORE_DEST);
  console.log(`Live2D Cubism Core berhasil diunduh (${(bytes / 1024).toFixed(1)} KB).`);
} else {
  console.log('Live2D Cubism Core sudah tersedia.');
}

// Salin aset VAD dari node_modules jika folder node_modules ada
const VAD = 'node_modules/@ricky0123/vad-web/dist';
const ORT = 'node_modules/onnxruntime-web/dist';

if (existsSync(VAD) && existsSync(ORT)) {
  const salin = [];
  for (const f of ['silero_vad_v5.onnx', 'silero_vad_v6.onnx', 'silero_vad_legacy.onnx', 'vad.worklet.bundle.min.js']) {
    salin.push([`${VAD}/${f}`, `public/vad/${f}`]);
  }
  for (const f of await readdir(ORT)) {
    if (f.startsWith('ort-wasm-simd-threaded') && (f.endsWith('.wasm') || f.endsWith('.js'))) {
      salin.push([`${ORT}/${f}`, `public/ort/${f}`]);
    }
  }

  let jumlah = 0;
  for (const [src, dest] of salin) {
    if (existsSync(src)) {
      await mkdir(dirname(resolve(dest)), { recursive: true });
      await copyFile(resolve(src), resolve(dest));
      jumlah += 1;
    }
  }
  console.log(`${jumlah} aset VAD disalin dari node_modules.`);
}

console.log('Pemeriksaan aset selesai.');
