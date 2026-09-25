// Buka halaman di Chromium nyata (bukan headless) supaya WebGL memakai GPU asli,
// lalu ukur empat hal yang pernah menjatuhkan avatar ini:
//   1. framing tidak melompat setelah resize;
//   2. backing store kanvas ikut devicePixelRatio SESUDAH halaman terbuka --
//      zoom browser mengubah rasio piksel, dan kalau kanvas tidak ikut, avatar
//      terlihat burik (keluhan yang melahirkan pemeriksaan ini);
//   3. semua wajah/pose/gerakan dari .env benar-benar terpasang, dan pose bisa
//      ditumpuk di atas ekspresi wajah;
//   4. irama render: tab latar harus NOL frame (bukan cuma FPS rendah), dan
//      harus hidup lagi begitu muncul -- dengan angka FPS yang ikut pulih.
//
//   python server_py/app.py            (jalankan dulu, catat portnya dari log)
//   node scripts/verify-render.mjs [url]
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const url = process.argv[2] || 'http://127.0.0.1:8787/';
const MAX_RASIO = 1.05; // model tidak boleh lebih tinggi dari layar; 0.96 = target layout
const MIN_RASIO = 0.5; // di bawah ini = scale melompat ke ukuran asli
const ZOOM_UJI = 2.5;

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1200, height: 820 }, deviceScaleFactor: 1 });

await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });
await page.waitForTimeout(2500);

/** @type {{nama: string, lolos: boolean, catatan: string}[]} */
const hasil = [];
const cek = (nama, lolos, catatan = '') => {
  hasil.push({ nama, lolos: !!lolos, catatan });
  console.log(`${lolos ? 'ok  ' : 'FAIL'} ${nama}${catatan ? ` — ${catatan}` : ''}`);
};

const geom = () =>
  page.evaluate(() => {
    const { app, model } = window.__vtuber;
    window.__vtuber.layout(model);
    const b = model.getBounds(); // bounds sudah mencakup scale + posisi aktif
    return {
      rasio: +(b.height / app.screen.height).toFixed(3),
      skala: +model.scale.y.toFixed(4),
      fps: document.getElementById('fps').textContent,
      status: document.getElementById('status').textContent,
    };
  });

const piksel = () => page.evaluate(() => window.__vtuber.resolusi());
const konfigRender = () => page.evaluate(() => window.__vtuber.konfig.render);

const gl = await page.evaluate(() => {
  const ctx = document.createElement('canvas').getContext('webgl');
  const dbg = ctx?.getExtension('WEBGL_debug_renderer_info');
  return dbg ? ctx.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'webgl-tanpa-info';
});

// ---------------------------------------------------------------- 1. framing
const awal = await geom();
await mkdir('.shots', { recursive: true });
await page.screenshot({ path: '.shots/fase0.png' });

await page.setViewportSize({ width: 780, height: 560 });
await page.waitForTimeout(1500);
const setelahResize = await geom();

for (const [m, g] of [
  ['saat load', awal],
  ['setelah resize', setelahResize],
]) {
  cek(`framing ${m}`, g.rasio <= MAX_RASIO && g.rasio > MIN_RASIO, `rasio ${g.rasio}, skala ${g.skala}, ${g.fps} FPS`);
}

// --------------------------------------------- 2. ketajaman mengikuti zoom
const batas = await konfigRender();
/** Nilai yang seharusnya dipakai aplikasi untuk sebuah devicePixelRatio. */
const seharusnya = (dpr) => (batas.skala !== null ? batas.skala : Math.min(dpr, batas.skalaMaks));

const kecil = await piksel();
cek(
  'resolusi = devicePixelRatio (dibatasi VITE_RENDER_SKALA_MAKS)',
  Math.abs(kecil.resolution - seharusnya(kecil.dpr)) < 0.01,
  `dpr ${kecil.dpr} -> ${kecil.resolution}x; kanvas ${kecil.piksel[0]}x${kecil.piksel[1]} untuk ${kecil.css[0]}x${kecil.css[1]} css`,
);

// Simulasi zoom browser: rasio piksel dinaikkan TANPA memuat ulang halaman.
// Inilah yang dulu membuat avatar burik: kanvas tetap pada backing store lama.
// Ukuran FISIK jendela ditahan tetap (780x560 piksel perangkat), jadi CSS px
// mengecil saat DPR naik -- persis Ctrl + + pada jendela asli. Membekukan ukuran
// CSS menghasilkan FAIL palsu: tanpa perubahan ukuran, peristiwa resize tidak
// pernah terkirim dan aplikasi memang tidak punya alasan untuk mengubah apa pun.
const cdp = await page.context().newCDPSession(page);
// Jendela fisik 1100x760: pada 780x560 yang tersisa untuk kolom avatar cuma
// 312x224 css saat DPR 2.5, kanvasnya kolaps ke lebar 0, dan defisit 0 lolos
// tanpa mengukur apa pun.
const JENDELA = [1100, 760];
await page.setViewportSize({ width: JENDELA[0], height: JENDELA[1] });
await page.waitForTimeout(900);
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: Math.round(JENDELA[0] / ZOOM_UJI),
  height: Math.round(JENDELA[1] / ZOOM_UJI),
  deviceScaleFactor: ZOOM_UJI,
  mobile: false,
});
await page.waitForTimeout(1000);
const besar = await piksel();
cek(
  `zoom ${ZOOM_UJI}x tidak meregangkan kanvas`,
  // css[0] > 0 wajib: kanvas selebar nol membuat defisit 0 berarti "tidak terukur",
  // bukan "tajam".
  besar.css[0] > 0 &&
    Math.abs(besar.resolution - seharusnya(ZOOM_UJI)) < 0.06 &&
    besar.defisit <= 1.05,
  `dpr ${besar.dpr} -> ${besar.resolution}x, piksel ${besar.piksel[0]}x${besar.piksel[1]} untuk ${besar.css[0]}x${besar.css[1]} css, diregangkan ${besar.defisit}x, ${besar.piksel[0] * besar.piksel[1] / 1e6} MP`,
);

await cdp.send('Emulation.clearDeviceMetricsOverride');
await page.setViewportSize({ width: 780, height: 560 });
await page.waitForTimeout(900);
const pulih = await piksel();
cek('zoom dikembalikan ikut mengecil', pulih.defisit <= 1.05 && pulih.piksel[0] > 0, `dpr ${pulih.dpr} -> ${pulih.resolution}x`);

// ------------------------------------------- 3. isi .env benar-benar terpakai
const konfig = await page.evaluate(() => {
  const v = window.__vtuber;
  const teks = (selektor) => [...document.querySelectorAll(selektor)].map((b) => b.textContent);
  return {
    wajah: v.konfig.wajah.map((w) => w.nama),
    pose: v.konfig.pose.map((p) => p.nama),
    gerakan: v.konfig.gerakan.map((g) => g.nama),
    dasar: v.konfig.ekspresiDasar,
    terpasang: v.ekspresiTerpasang,
    peringatan: v.peringatan,
    tombol: { expr: teks('#expr button'), pose: teks('#pose button'), gerak: teks('#gerak button') },
  };
});

const sama = (a, b) => a.join('|') === b.join('|');
cek(
  'tombol panel = daftar .env',
  sama(konfig.wajah, konfig.tombol.expr) && sama(konfig.pose, konfig.tombol.pose) && sama(konfig.gerakan, konfig.tombol.gerak),
  `${konfig.wajah.length} wajah + ${konfig.pose.length} pose + ${konfig.gerakan.length} gerakan`,
);
cek(
  'ekspresi terpasang tanpa peringatan',
  konfig.peringatan.length === 0 && konfig.terpasang.length === konfig.wajah.length + konfig.pose.length,
  konfig.peringatan.slice(0, 3).join(' | ') || `${konfig.terpasang.length} ekspresi, dasar "${konfig.dasar}"`,
);

// Pose di atas wajah. Nilai parameter DIBACA DARI DALAM FRAME: di luar frame
// Cubism selalu mengembalikan nilai tersimpan, jadi pembacaan dari luar menipu.
const sampel = await page.evaluate(async () => {
  const v = window.__vtuber;
  const inti = v.model.internalModel.coreModel;
  const ID = ['Param68', 'Param72']; // mata berair (wajah sedih) + tongkat sihir (pose)
  v.setEkspresi('sedih');
  v.setPose('tongkat', true);
  await new Promise((r) => setTimeout(r, 2500)); // beri waktu pudar + layers settle
  const satuFrame = new Promise((done) => {
    v.model.internalModel.on('beforeModelUpdate', () => {
      const keluar = {};
      for (const id of ID) keluar[id] = +inti.getParameterValueById(id).toFixed(2);
      done(keluar);
    });
  });
  const keluar = await Promise.race([
    satuFrame,
    new Promise((r) => setTimeout(() => r(null), 3000)),
  ]);
  v.setPose('tongkat', false);
  return keluar;
});
cek(
  'pose ditumpuk di atas wajah',
  !!sampel && sampel.Param68 > 1 && sampel.Param72 > 1,
  JSON.stringify(sampel),
);

await page.locator('#expr button').first().click();
await page.waitForTimeout(1200);
await page.screenshot({ path: '.shots/fase0-ekspresi.png' });

// ------------------------------------- 4. irama: berhenti saat tidak dilihat
// Yang diukur di sini persis dua hal yang bikin modul irama.js ditulis:
//   tersembunyi -> NOL frame (bukan "FPS kecil"), dan tidak ada rAF tertinggal;
//   muncul lagi -> gambar jalan lagi dan angka FPS-nya ikut pulih.
// Halaman dijamin dalam keadaan terlihat lagi sebelum pemeriksaan dimulai,
// kalau tidak dia akan menguji dirinya sendiri dalam keadaan mati.
const hitungFrame = (ms) =>
  page.evaluate(
    (durasi) =>
      new Promise((done) => {
        const t = window.__vtuber.app.ticker;
        let n = 0;
        const dengar = () => (n += 1);
        t.add(dengar);
        setTimeout(() => {
          t.remove(dengar);
          done(n);
        }, durasi);
      }),
    ms,
  );

const iramaBawaan = await page.evaluate(() => window.__vtuber.konfig.irama);
const framePenuh = await hitungFrame(1000);
cek(
  'halaman terlihat & fokus = menggambar penuh',
  !(await page.evaluate(() => document.hidden)) && framePenuh > 10,
  `${framePenuh} frame/1s, target ${iramaBawaan.fpsSaatTakFokus} FPS saat tak fokus, jedaSaatSembunyi=${iramaBawaan.jedaSaatSembunyi}`,
);

// Keadaan "tidak dilihat" TIDAK BISA dipancing dari luar di mesin ini -- itu
// sudah diukur, bukan diasumsikan: jendela yang CDP-laporannya `minimized` tetap
// melaporkan visibility=visible, hidden=false, dan rAF jalan 60 FPS; jendela lain
// yang dinaikkan dengan SetForegroundWindow tidak membuat document.hasFocus()
// jadi false. Jadi yang dipura-pura di sini HANYA dua getter DOM itu. Peristiwanya
// nyata (visibilitychange / blur sungguhan), dan yang diukur juga nyata: berapa
// frame yang benar-benar digambar.
await page.evaluate(() => {
  window.__pura = ({ sembunyi, fokus }) => {
    if (sembunyi !== undefined) Object.defineProperty(document, 'hidden', { configurable: true, get: () => sembunyi });
    if (fokus !== undefined) document.hasFocus = () => fokus;
    document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event(fokus ? 'focus' : 'blur'));
  };
  window.__lepas = () => {
    delete document.hidden;
    delete document.hasFocus;
    document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event('focus'));
  };
});

const target = iramaBawaan.fpsSaatTakFokus || 0;

// 4b. tersembunyi -> nol frame, benar-benar nol, bukan "FPS kecil".
await page.evaluate(() => window.__pura({ sembunyi: true, fokus: true }));
const sembunyi = await page.evaluate(() => ({
  ...window.__vtuber.irama.status(),
  fps: document.getElementById('fps').textContent,
}));
const frameSembunyi = await hitungFrame(1000);
cek(
  'tersembunyi = nol frame',
  sembunyi.sembunyi && !sembunyi.jalan && frameSembunyi === 0 && sembunyi.fps === 'jeda',
  `${frameSembunyi} frame dalam 1s (baseline ${framePenuh}), label FPS "${sembunyi.fps}", ticker jalan=${sembunyi.jalan}`,
);

// 4c. muncul lagi -> jalan lagi, dan angka FPS-nya ikut pulih, bukan warisan.
await page.evaluate(() => window.__pura({ sembunyi: false, fokus: true }));
await page.waitForTimeout(1500);
const lanjut = await page.evaluate(() => ({
  ...window.__vtuber.irama.status(),
  fps: document.getElementById('fps').textContent,
}));
const frameLanjut = await hitungFrame(1000);
cek(
  'muncul lagi = menggambar lagi',
  lanjut.jalan && frameLanjut > 10 && Number(lanjut.fps) > 10,
  `${frameLanjut} frame dalam 1s, label FPS "${lanjut.fps}"`,
);

// 4d. terlihat tapi tidak fokus -> dibatasi, dan batasnya TERUKUR, bukan cuma
// properti yang disetel. Dua sisi diuji: tidak boleh masih 60, tidak boleh diam.
await page.evaluate(() => window.__pura({ fokus: false }));
await page.waitForTimeout(1500);
const takFokus = await page.evaluate(() => window.__vtuber.irama.status());
const frameTakFokus = await hitungFrame(1200);
const lajuTakFokus = Math.round((frameTakFokus * 1000) / 1200);
cek(
  `tak fokus = FPS dibatasi ke ${target}`,
  Math.abs(takFokus.batasFps - target) < 0.5 &&
    takFokus.jalan &&
    lajuTakFokus <= target * 1.25 &&
    lajuTakFokus >= target * 0.6,
  `maxFPS ${takFokus.batasFps}, terukur ${lajuTakFokus} FPS dari ${frameTakFokus} frame/1,2s, baseline ${framePenuh} FPS`,
);

// 4e. pura-pura dilepas -> keadaan nyata kembali (kalau ini gagal, pemeriksaan di
// atas cuma mengukur mock-nya sendiri).
await page.evaluate(() => window.__lepas());
await page.waitForTimeout(1500);
const pulihIrama = await page.evaluate(() => window.__vtuber.irama.status());
const framePulih = await hitungFrame(1000);
cek(
  'keadaan nyata kembali penuh',
  pulihIrama.batasFps === 0 && framePulih > 10 && !pulihIrama.jeda,
  `maxFPS ${pulihIrama.batasFps}, ${framePulih} frame/1s, hidden nyata=${pulihIrama.sembunyi}`,
);

const lulus = hasil.every((h) => h.lolos);
console.log('\nGPU            :', gl);
console.log('status         :', awal.status);
console.log('saat load      :', JSON.stringify(awal));
console.log('setelah resize :', JSON.stringify(setelahResize));
console.log('piksel         :', JSON.stringify({ kecil, besar, pulih }));
console.log(lulus ? `PASS ${hasil.length}/${hasil.length} pemeriksaan` : `FAIL ${hasil.filter((h) => !h.lolos).length} dari ${hasil.length} pemeriksaan`);

await browser.close();
process.exit(lulus ? 0 : 1);
