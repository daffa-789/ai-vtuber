// Unduh model Haru (Cubism 4) dari aset uji pixi-live2d-display + Cubism core resmi.
// Lihat public/models/haru/README.md untuk catatan lisensi.
import { copyFile, mkdir, readdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';

const REPO = 'guansss/pixi-live2d-display';
const REF = 'master';
const PREFIX = 'test/assets/haru/';
const OUT = resolve('public/models/haru');
const CORE = 'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js';

async function save(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, buf);
  return buf.length;
}

const tree = await fetch(
  `https://api.github.com/repos/${REPO}/git/trees/${REF}?recursive=1`,
  { headers: { 'user-agent': 'node-fetch' } },
).then((r) => r.json());

if (!tree.tree) throw new Error(`GitHub API: ${tree.message}`);

const paths = tree.tree
  .filter((e) => e.type === 'blob' && e.path.startsWith(PREFIX))
  .map((e) => e.path.slice(PREFIX.length));

let bytes = 0;
for (const p of paths) {
  const raw = `https://raw.githubusercontent.com/${REPO}/${REF}/${PREFIX}${p}`;
  bytes += await save(raw, join(OUT, p));
  console.log(`  ok  ${p}`);
}

bytes += await save(CORE, resolve('public/live2dcubismcore.min.js'));

// Salin aset VAD dari node_modules supaya aplikasi tidak bergantung ke CDN saat jalan.
// vad-web mencari aset relatif terhadap baseAssetPath/onnxWASMBasePath yang kita set.
const VAD = 'node_modules/@ricky0123/vad-web/dist';
const ORT = 'node_modules/onnxruntime-web/dist';
const salin = [];
for (const f of ['silero_vad_v5.onnx', 'silero_vad_v6.onnx', 'silero_vad_legacy.onnx', 'vad.worklet.bundle.min.js']) {
  salin.push([`${VAD}/${f}`, `public/vad/${f}`]);
}
for (const f of await readdir(ORT)) {
  if (f.startsWith('ort-wasm-simd-threaded') && (f.endsWith('.wasm') || f.endsWith('.mjs'))) {
    salin.push([`${ORT}/${f}`, `public/ort/${f}`]);
  }
}

let jumlah = 0;
for (const [src, dest] of salin) {
  await mkdir(dirname(resolve(dest)), { recursive: true });
  await copyFile(resolve(src), resolve(dest));
  jumlah += 1;
}

console.log(`selesai — ${paths.length + 1} file diunduh (${(bytes / 1024 / 1024).toFixed(1)} MB), ${jumlah} aset VAD disalin`);
