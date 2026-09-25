// Potret wajah tiap ekspresi, disusun jadi satu kontak sheet supaya peta
// tag->wajah bisa dikoreksi dengan mata sendiri, bukan dari nama parameter.
//
//   python server_py/app.py            (satu jendela Chromium dibuka di sini)
//   node scripts/kontak-ekspresi.mjs [url]
import { mkdir, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';

const url = process.argv[2] || 'http://127.0.0.1:8787/';
const KOLOM = 3;

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 900, height: 900 }, deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 30000 });
await page.waitForTimeout(3500);

await rm('.shots/ekspresi', { recursive: true, force: true });
await mkdir('.shots/ekspresi', { recursive: true });

// Kedip otomatis dimatikan: tanpa itu satu potret bisa tertangkap setengah kedip
// dan terbaca sebagai ekspresi yang berbeda.
// Lalu perbesar dan geser sampai titik ~24% dari atas model (setara wajah) ke tengah.
await page.evaluate(() => {
  const { app, model, layout } = window.__vtuber;
  model.internalModel.eyeBlink = null;
  layout(model);
  model.scale.set(model.scale.y * 3);
  model.x = app.screen.width / 2;
  model.y = app.screen.height / 2 + model.height * 0.76;
});

const clip = await page.evaluate(() => {
  const k = document.getElementById('stage').getBoundingClientRect();
  return { x: k.x + k.width / 2 - 170, y: k.y + k.height / 2 - 170, width: 340, height: 340 };
});

const nama = await page.evaluate(() =>
  [...document.querySelectorAll('#expr button')].map((b) => b.textContent),
);

// Pemanasan: berkas .exp3.json baru diunduh saat pertama kali dipakai, dan
// pergantian ekspresi butuh ~1 detik untuk pudar. Tanpa langkah ini potret pertama
// tiap ekspresi masih menampakkan wajah sebelumnya.
for (const n of nama) {
  await page.evaluate((ekspresi) => window.__vtuber.setEkspresi(ekspresi), n);
  await page.waitForTimeout(300);
}

// Dinomori supaya ffmpeg bisa membacanya sebagai barisan %02d; petakan namanya
// dicetak di akhir.
let i = 0;
for (const n of nama) {
  await page.evaluate((ekspresi) => window.__vtuber.setEkspresi(ekspresi), n);
  await page.waitForTimeout(2500); // sengaja lama: kalau ada yang menimpa ekspresi, di sini kelihatan
  await page.screenshot({ path: `.shots/ekspresi/${String(i).padStart(2, '0')}.png`, clip });
  i++;
}

const baris = Math.ceil(nama.length / KOLOM);
execFileSync('ffmpeg', [
  '-y', '-framerate', '1', '-i', '.shots/ekspresi/%02d.png',
  '-vf', `tile=${KOLOM}x${baris}:padding=6:color=0x22263a`,
  '-frames:v', '1', '.shots/kontak-ekspresi.png',
]);
console.log('petakan :', nama.map((n, k) => `${String(k).padStart(2, '0')}=${n}`).join(' '));
console.log(`-> .shots/kontak-ekspresi.png (${nama.length} potret, clip ${JSON.stringify(clip)})`);
await browser.close();
