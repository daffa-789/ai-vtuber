// Uji ujung-ke-ujung: streaming dari sidecar -> pengupasan tag -> wajah Live2D.
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1100, height: 760 } });
page.on('console', (m) => {
  if (m.type() === 'warning' || m.type() === 'error') console.log(`  [browser ${m.type()}] ${m.text()}`);
});

await page.addInitScript(() => {
  window.__snap = [];
  const catat = () => {
    const aktif = document.querySelector('#expr button.aktif');
    window.__snap.push({
      teks: document.getElementById('log')?.innerText ?? '',
      aktif: aktif?.textContent ?? null,
    });
  };
  // addInitScript jalan sebelum DOM ada, jadi pantau dokumen itu sendiri,
  // bukan documentElement yang saat titik ini masih null.
  new MutationObserver(catat).observe(document, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ['class'],
  });
});

await page.goto(process.argv[2] || 'http://127.0.0.1:8787/', { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });

// Tes ini menunggu teks spesifik dari mode VTUBER_STUB=1. Kalau port 8787
// malah dipakai sidecar asli, balasannya dari Gemini dan tidak pernah cocok --
// jadi berhenti sekarang dengan pesan yang jelas, bukan timeout membingungkan.
const model = await page.evaluate(async () => {
  const h = await fetch('/api/health').then((r) => r.json());
  return h.model;
});
if (model !== 'stub') {
  console.log(`FAIL: butuh server tiruan (VTUBER_STUB=1) di port itu, dapat model "${model}". Jalankan: set VTUBER_STUB=1 && python server_py/app.py`);
  await browser.close();
  process.exit(1);
}

const health = await page.textContent('#health');
await page.fill('#isi', 'hai');
await page.click('#form button[type=submit]');

// Sampel aktif + teks tiap 40ms selama stream berlangsung, supaya urutan wajah terlihat.
const jejak = await page.evaluate(async () => {
  const out = [];
  const akhir = performance.now() + 1400;
  while (performance.now() < akhir) {
    const a = document.querySelector('#expr button.aktif');
    const t = document.querySelector('.pesan.assistant:last-child');
    const baris = `${a?.textContent ?? '-'}|${t?.textContent ?? ''}`;
    if (out[out.length - 1] !== baris) out.push(baris);
    await new Promise((r) => setTimeout(r, 40));
  }
  return out;
});
console.log('jejak waktu:');
jejak.forEach((j) => console.log('   ', j));

await page.waitForFunction(
  () => document.querySelector('.pesan.assistant:last-child')?.textContent?.includes('diam sih'),
  null,
  { timeout: 15000 },
);
await page.waitForTimeout(400);

const hasil = await page.evaluate(() => ({
  balasan: document.querySelector('.pesan.assistant:last-child')?.textContent,
  riwayat: JSON.parse(localStorage.getItem('vtuber.riwayat') ?? '[]'),
  aktif: document.querySelector('#expr button.aktif')?.textContent ?? null,
  pernahAktif: [...new Set(window.__snap.map((s) => s.aktif).filter(Boolean))],
  adaSisaKurung: window.__snap.some((s) => s.teks.includes('[') || s.teks.includes(']')),
}));

const lolos =
  hasil.balasan === 'Halo Master. kok diam sih' &&
  !hasil.adaSisaKurung &&
  hasil.pernahAktif.includes('senyum') &&
  hasil.aktif === 'sebal' &&
  hasil.riwayat.length === 2 &&
  !hasil.riwayat[1].content.includes('[');

console.log('health  :', health);
console.log('balasan :', JSON.stringify(hasil.balasan));
console.log('wajah   :', hasil.pernahAktif, '-> aktif', hasil.aktif);
console.log('kurung  :', hasil.adaSisaKurung ? 'BOCOR ke layar' : 'bersih');
console.log('localStorage :', JSON.stringify(hasil.riwayat));
await page.screenshot({ path: '.shots/fase1-chat.png' });
await browser.close();

console.log(lolos ? 'PASS' : 'FAIL');
process.exit(lolos ? 0 : 1);
