// Penjaga regresi dua perilaku yang dulu rusak diam-diam:
//   1. tombol gerakan harus benar-benar memulai motion (butuh prioritas >= 1),
//   2. pamer-barang-1 / -2 saling eksklusif supaya tangannya tidak jadi empat.
// Jalankan: node scripts/verify-gerak.mjs [url]   (butuh server hidup + Playwright global)
// pamer-barang-1 / pamer-barang-2 saling eksklusif (tidak 4 tangan).
import { chromium } from 'playwright';

const url = process.argv[2] || 'http://127.0.0.1:8787/';
const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1100, height: 800 } });
const galat = [];
page.on('pageerror', (e) => galat.push(e.message));

await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 30000 });
await page.waitForTimeout(2500);

const gagal = [];

// --- 1. tombol gerakan ---
await page.locator('#gerak button').first().click();
await page.waitForTimeout(700);
const gerak = await page.evaluate(() => {
  const mm = window.__vtuber.model.internalModel.motionManager;
  return { main: mm.playing, prioritas: mm.state.currentPriority, grup: mm.state.currentGroup };
});
console.log('setelah pencet "sedih-melambai":', JSON.stringify(gerak));
if (!gerak.main) gagal.push('motion tidak mulai (playing=false)');

await page.waitForTimeout(3200);
const selesai = await page.evaluate(() => window.__vtuber.model.internalModel.motionManager.playing);
console.log('setelah 3,2 detik (durasi 2,98):', selesai ? 'MASIH main — loop tidak mati' : 'selesai sendiri, benar');

// --- 2. pose saling eksklusif ---
const status = () =>
  page.evaluate(() => ({
    nyala: window.__vtuber.pose.nyala,
    tombol: [...document.querySelectorAll('#pose button')].filter((b) => b.classList.contains('aktif')).map((b) => b.textContent),
  }));

const klik = async (nama) => {
  await page.locator(`#pose button:text-is("${nama}")`).click();
  await page.waitForTimeout(400);
  return status();
};

const a = await klik('pamer-barang-1');
console.log('pencet pamer-barang-1 :', JSON.stringify(a));
const b = await klik('pamer-barang-2');
console.log('pencet pamer-barang-2 :', JSON.stringify(b));
const c = await klik('pamer-barang-1');
console.log('pencet pamer-barang-1 :', JSON.stringify(c));
const d = await klik('pamer-barang-1');
console.log('pencet sekali lagi    :', JSON.stringify(d));

const hanyaSatu = (s) => s.nyala.length <= 1;
if (!a.nyala.includes('pamer-barang-1')) gagal.push('pamer-barang-1 tidak menyala');
if (!hanyaSatu(b) || !b.nyala.includes('pamer-barang-2')) gagal.push('pamer-barang-2 tidak mengambil alih (masih dua pose)');
if (!hanyaSatu(c) || !c.nyala.includes('pamer-barang-1')) gagal.push('pamer-barang-1 tidak mengambil alih');
if (d.nyala.length !== 0) gagal.push('klik keempat seharusnya mematikan, masih ada: ' + d.nyala);

// Pose lain tidak boleh ikut padam saat bertukar pamer-barang.
await klik('tongkat');
const e = await klik('pamer-barang-2');
console.log('tongkat + pamer-barang-2:', JSON.stringify(e));
if (!e.nyala.includes('tongkat')) gagal.push('tongkat ikut padam — seharusnya hanya sesama pamer-barang yang bersaing');

console.log('\ngalat halaman :', galat.length ? galat : 'tidak ada');
console.log(gagal.length ? 'FAIL\n  ' + gagal.join('\n  ') : 'PASS motion jalan + pamer-barang saling eksklusif');
await browser.close();
process.exit(gagal.length ? 1 : 0);
