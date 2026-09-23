// Potret wajah tiap ekspresi, disusun jadi satu kontak sheet supaya peta
// tag->wajah bisa dikoreksi dengan mata sendiri, bukan dari nama parameter.
import { mkdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1000, height: 780 } });
await page.goto('http://localhost:5173/', { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });

await mkdir('.shots/ekspresi', { recursive: true });

// Area wajah: kotak di bagian atas model, dihitung dari bounds asli.
const clip = await page.evaluate(() => {
  const { app, model } = window.__vtuber;
  const b = model.getBounds();
  const kanvas = document.getElementById('stage').getBoundingClientRect();
  const skala = kanvas.width / app.screen.width;
  const tengah = (b.x + b.width / 2) * skala + kanvas.left;
  const atas = b.y * skala + kanvas.top;
  const lebar = b.width * skala * 0.34;
  return { x: Math.max(0, tengah - lebar / 2), y: Math.max(0, atas + lebar * 0.04), width: lebar, height: lebar };
});

const nama = await page.evaluate(() =>
  [...document.querySelectorAll('#expr button')].map((b) => b.textContent),
);

for (const n of nama) {
  await page.evaluate((ekspresi) => window.__vtuber.setEkspresi(ekspresi), n);
  await page.waitForTimeout(2200); // sengaja lama: kalau motion idle menimpa ekspresi, di sini kelihatan
  await page.screenshot({ path: `.shots/ekspresi/${n}.png`, clip });
  console.log('potret', n);
}

await browser.close();

execFileSync('ffmpeg', [
  '-y', '-framerate', '1', '-i', '.shots/ekspresi/f%02d.png',
  '-vf', `tile=${Math.ceil(nama.length / 2)}x2:padding=6:color=0x22263a`,
  '-frames:v', '1', '.shots/kontak-ekspresi.png',
]);
console.log(`kotak clip ${JSON.stringify(clip)} -> .shots/kontak-ekspresi.png`);
