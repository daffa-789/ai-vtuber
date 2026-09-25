// Uji jalur audio tanpa menyentuh API: chat dan TTS distub, tapi WAV-nya rekaman
// asli Gemini TTS (test/fixture-suara.wav) supaya amplitudo dan rahangnya nyata.
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const wav = await readFile(new URL('../test/fixture-suara.wav', import.meta.url));

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });

await page.route('**/api/health', (r) =>
  r.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, model: 'stub', key: true }) }),
);
await page.route('**/api/chat', (r) =>
  r.fulfill({ contentType: 'text/plain', body: '[senyum] Halo Master, ini suara asli dari Gemini TTS.' }),
);
await page.route('**/api/tts', (r) => r.fulfill({ contentType: 'audio/wav', body: wav }));

await page.goto(process.argv[2] || 'http://127.0.0.1:8787/', { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });
await page.evaluate(() => localStorage.removeItem('vtuber.riwayat'));
await page.reload({ waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });

const diamAwal = await page.evaluate(() => window.__vtuber.mulut);

await page.fill('#isi', 'tes suara');
await page.click('#form button[type=submit]');
await page.waitForFunction(() => document.getElementById('suara').textContent === 'menyusun suara…', null, {
  timeout: 20000,
});

// Sampel dari Node supaya bisa menjepret tepat saat rahang terbuka.
let puncak = 0;
let terjepret = false;
const batas = Date.now() + 10000;
while (Date.now() < batas) {
  const nilai = await page.evaluate(() => window.__vtuber.mulut);
  puncak = Math.max(puncak, nilai);
  if (!terjepret && nilai > 0.5) {
    terjepret = true;
    await page.screenshot({ path: '.shots/fase2-berbicara.png' });
  }
  const selesai = await page.evaluate(() => document.getElementById('suara').textContent === 'diam');
  if (selesai && terjepret) break;
  await new Promise((r) => setTimeout(r, 25));
}

const akhir = await page.evaluate(() => window.__vtuber.mulut);
const hasil = {
  diamAwal: +diamAwal.toFixed(3),
  puncakRahang: +puncak.toFixed(3),
  setelahSelesai: +akhir.toFixed(3),
  wajah: await page.evaluate(() => document.querySelector('#expr button.aktif')?.textContent ?? null),
  suara: await page.evaluate(() => document.getElementById('suara').textContent),
};

const lolos = hasil.puncakRahang > 0.15 && hasil.wajah === 'senyum' && hasil.suara === 'diam' && akhir < 0.05;
console.log(JSON.stringify(hasil));
console.log(lolos ? 'PASS rahang bergerak mengikuti audio' : 'FAIL rahang tidak bergerak');

await browser.close();
process.exit(lolos ? 0 : 1);
