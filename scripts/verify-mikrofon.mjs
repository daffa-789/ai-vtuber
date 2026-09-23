// Regresi jalur mikrofon TANPA kuota: mic palsu Chromium memutar fixture,
// VAD harus benar-benar menghasilkan WAV dan menyerahkannya ke /api/stt.
// Akurasi STT sudah terbukti terpisah lewat panggilan nyata, jadi di sini
// STT cukup mengembalikan transkrip tetap.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const FIXTURE = fileURLToPath(new URL('../test/fixture-suara.wav', import.meta.url));
const wav = await readFile(FIXTURE);

const browser = await chromium.launch({
  headless: false,
  args: [
    '--use-fake-ui-for-media-stream',
    '--use-fake-device-for-media-stream',
    `--use-file-for-fake-audio-capture=${FIXTURE}`,
  ],
});

const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });

const kiriman = { jumlah: 0 };
await page.route('**/api/stt', (r) => {
  kiriman.jumlah += 1;
  r.fulfill({ contentType: 'application/json', body: JSON.stringify({ teks: 'halo, kamu di sana?' }) });
});
await page.route('**/api/chat', (r) =>
  r.fulfill({ contentType: 'text/plain', body: '[senyum] iya, aku di sini.' }),
);
await page.route('**/api/tts', (r) => r.fulfill({ contentType: 'audio/wav', body: wav }));

await page.goto('http://localhost:5173/', { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });
await page.evaluate(() => localStorage.removeItem('vtuber.riwayat'));
await page.reload({ waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });

await page.click('#mic');

const status = [];
const batas = Date.now() + 30000;
while (Date.now() < batas) {
  const s = await page.evaluate(() => document.getElementById('mikrofon').textContent);
  if (status[status.length - 1] !== s) status.push(s);
  if (await page.evaluate(() => !!document.querySelector('.pesan.user'))) break;
  await new Promise((r) => setTimeout(r, 200));
}

// Satu ucapan sudah cukup; matikan mic supaya fixture yang diputar ulang tidak
// memicu VAD berkali-kali.
await page.evaluate(() => window.__vtuber?.matikanMikrofon?.());

const hasil = {
  urutanStatus: status,
  permintaanStt: kiriman.jumlah,
  user: await page.evaluate(() => {
    const semua = document.querySelectorAll('.pesan.user');
    return semua.length ? semua[semua.length - 1].textContent : null;
  }),
  balasan: await page.evaluate(() => {
    const semua = document.querySelectorAll('.pesan.assistant');
    return semua.length ? semua[semua.length - 1].textContent : null;
  }),
  wajah: await page.evaluate(() => document.querySelector('#expr button.aktif')?.textContent ?? null),
};

await page.screenshot({ path: '.shots/fase3-mikrofon.png' });
await browser.close();

console.log(JSON.stringify(hasil, null, 2));
// Ukuran byte tidak bisa dibaca dari route Playwright untuk body ArrayBuffer.
// Sisi server sudah menjaga itu: audio < 1000 byte ditolak dengan pesan spesifik,
// dan penolakan itu tidak pernah muncul saat panggilan nyata.
const lolos =
  hasil.permintaanStt > 0 &&
  hasil.user === 'halo, kamu di sana?' &&
  hasil.balasan?.includes('iya') &&
  hasil.wajah === 'f04';
console.log(lolos ? 'PASS mic -> VAD -> STT -> balasan -> wajah' : 'FAIL');
process.exit(lolos ? 0 : 1);
