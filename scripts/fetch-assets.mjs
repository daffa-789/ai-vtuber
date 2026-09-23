// Unduh model Haru (Cubism 4) dari aset uji pixi-live2d-display + Cubism core resmi.
// Lihat public/models/haru/README.md untuk catatan lisensi.
import { mkdir, writeFile } from 'node:fs/promises';
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
console.log(`selesai — ${paths.length + 1} file, ${(bytes / 1024 / 1024).toFixed(1)} MB`);
