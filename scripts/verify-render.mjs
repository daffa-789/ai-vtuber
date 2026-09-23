// Buka halaman di Chromium nyata (bukan headless) supaya WebGL memakai GPU asli,
// ukur FPS, pastikan framing tetap benar setelah resize, lalu simpan bukti render.
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const url = process.argv[2] || 'http://localhost:5173/';
const MAX_RASIO = 1.05; // model tidak boleh lebih tinggi dari layar; 0.96 = target layout
const MIN_RASIO = 0.5; // di bawah ini = scale melompat ke ukuran asli

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1200, height: 820 } });

await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 20000 });
await page.waitForTimeout(2500);

const geom = () =>
  page.evaluate(() => {
    const { app, model } = window.__vtuber;
    window.__vtuber.layout(model);
    const b = model.getBounds(); // bounds sudah mencakup scale + posisi aktif
    return {
      screenH: app.screen.height,
      scale: +model.scale.y.toFixed(4),
      tinggiLayar: +b.height.toFixed(1),
      rasio: +(b.height / app.screen.height).toFixed(3),
      atas: +b.y.toFixed(1),
      bawah: +(b.y + b.height).toFixed(1),
      fps: document.getElementById('fps').textContent,
      status: document.getElementById('status').textContent,
    };
  });

const gl = await page.evaluate(() => {
  const ctx = document.createElement('canvas').getContext('webgl');
  const dbg = ctx?.getExtension('WEBGL_debug_renderer_info');
  return dbg ? ctx.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'webgl-tanpa-info';
});

const awal = await geom();
await mkdir('.shots', { recursive: true });
await page.screenshot({ path: '.shots/fase0.png' });

await page.setViewportSize({ width: 780, height: 560 });
await page.waitForTimeout(1500);
const setelahResize = await geom();

await page.locator('#expr button').first().click();
await page.waitForTimeout(1200);
await page.screenshot({ path: '.shots/fase0-ekspresi.png' });

const pass = [awal, setelahResize].every((g) => g.rasio <= MAX_RASIO && g.rasio > MIN_RASIO);

console.log('GPU            :', gl);
console.log('saat load      :', JSON.stringify(awal));
console.log('setelah resize :', JSON.stringify(setelahResize));
console.log(pass ? 'PASS framing tetap benar' : 'FAIL framing melompat');

await browser.close();
process.exit(pass ? 0 : 1);
