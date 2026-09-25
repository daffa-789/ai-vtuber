// Pemeriksaan rancangan panel: tata letak, cincin fokus, kontras, dan lampu.
//
// Ini bukan sekadar bikin potret. Empat hal di bawah pernah salah dan lolos
// tanpa ketahuan:
//   - gugus yang track grid-nya menyusut ke nol tetap menggambar isinya di luar
//     kotak sendiri -> tiga baris chip saling menimpa di layar 430px;
//   - `#isi:focus { outline: none }` menghapus cincin keyboard (terukur
//     "3px none") padahal aturan globalnya sudah ada;
//   - teks diagnostik kecil sempat 3.63:1 -- di bawah AA 4.5;
//   - composer lengket yang tembus pandang membuat teks log terbaca di
//     baliknya dan tampak seperti tabrakan layout.
//
// Butuh sisi tiruan, karena pemeriksaan ini MENGIRIM satu pesan:
//   set VTUBER_STUB=1 && set VTUBER_PORT=8788 && .venv\Scripts\python.exe server_py\app.py
//   node scripts/cek-rancangan.mjs http://127.0.0.1:8788/
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const url = process.argv[2] || 'http://127.0.0.1:8787/';
const AA = 4.5;
const browser = await chromium.launch();
const temuan = [];
const cek = (siapa, lolos, catatan = '') => {
  if (!lolos) temuan.push(`${siapa}: ${catatan || 'gagal'}`);
  return !!lolos;
};

/** Ukur semuanya dari dalam halaman: yang dinilai adalah CSS yang berlaku. */
const UKUR = () => {
  const L = (c) => {
    const [r, g, b] = c
      .match(/[\d.]+/g)
      .slice(0, 3)
      .map(Number)
      .map((v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const rasio = (a, b) => {
    const [x, y] = [L(a), L(b)].sort((m, n) => n - m);
    return +((x + 0.05) / (y + 0.05)).toFixed(2);
  };

  const panel = document.getElementById('panel');
  const pr = panel.getBoundingClientRect();
  const log = document.getElementById('log');

  // Gelembung hanya ada setelah ada pesan; sisipkan sampel sekali supaya yang
  // terukur aturan CSS-nya, bukan warna yang dihitung di kepala.
  const ada = log.querySelector('.pesan');
  const sampel = [];
  if (!ada) {
    for (const kls of ['assistant', 'user', 'gagal']) {
      const el = document.createElement('div');
      el.className = `pesan ${kls}`;
      el.textContent = 'uji';
      log.appendChild(el);
      sampel.push(el);
    }
  }

  // Kedua ujung latar panel: teks kecil harus menang di keduanya.
  const latar = ['rgb(23, 31, 46)', 'rgb(16, 21, 31)'];
  const kontras = {};
  for (const [nama, sel] of [
    ['raut', '#raut'],
    ['fps', '#fps'],
    ['status', '#status'],
    ['health', '#health'],
    ['label', '#meter .k'],
    ['eyebrow', '.gugus h2 i'],
    ['gelar', '#gelar'],
    ['chip', '#expr button'],
    ['lampu', '#suara'],
    ['assistant', '.pesan.assistant'],
    ['user', '.pesan.user'],
    ['gagal', '.pesan.gagal'],
  ]) {
    const el = document.querySelector(sel);
    if (el) kontras[nama] = Math.min(...latar.map((b) => rasio(getComputedStyle(el).color, b)));
  }
  sampel.forEach((el) => el.remove());

  const gugus = [...document.querySelectorAll('.gugus')].map((el) => {
    const b = el.getBoundingClientRect();
    return {
      nama: el.id || el.querySelector('h2')?.textContent?.trim() || '?',
      kotak: Math.round(b.height),
      isi: Math.round(el.scrollHeight),
    };
  });

  return {
    panelTinggi: Math.round(pr.height),
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    anakTerpotong: [...panel.children]
      .filter((el) => el.getBoundingClientRect().bottom > pr.bottom + 1)
      .map((el) => el.id || el.tagName.toLowerCase()),
    gugus,
    tindih: gugus.filter((g) => g.isi > g.kotak + 2).map((g) => g.nama),
    kontras,
    lampu: document.getElementById('suara').dataset.keadaan,
    lampuTeks: document.getElementById('suara').textContent,
    raut: document.getElementById('raut').textContent,
    chipAktif: document.querySelector('#expr button.aktif')?.textContent ?? null,
    gelembung: log.querySelectorAll('.pesan').length,
    logTinggi: Math.round(log.getBoundingClientRect().height),
    kosong: getComputedStyle(log, '::before').content,
    fontHeader: getComputedStyle(document.querySelector('h1')).fontFamily,
  };
};

/** Tab sungguhan: `el.focus()` bukan navigasi keyboard, dan Chromium memang
   tidak menampilkan cincin untuk focus programatik -- diukur dulu, ternyata
   "3px none" untuk tombol yang sama yang berlingkar penuh saat di-Tab. */
async function jejakTab(page) {
  // Jejaknya diambil dari peristiwa focusin, BUKAN dari membaca activeElement
  // setelah tiap penekanan. Cara baca-per-tekan sempat melewatkan #isi satu kali:
  // fokus berpindah lebih cepat daripada sampelnya, jadi jejaknya melompat dari
  // chip ke Kirim dan tes menyangka input tidak bisa di-Tab.
  await page.evaluate(() => {
    window.__jejak = [];
    document.addEventListener('focusin', (e) => {
      const el = e.target;
      if (!el || el === document.body) return;
      const g = getComputedStyle(el);
      window.__jejak.push({
        siapa: el.id || `${el.tagName.toLowerCase()}:${el.textContent.trim().slice(0, 12)}`,
        golongan:
          el.id === 'isi' ? 'isi'
            : el.closest('#form') ? 'kirim'
            : el.closest('#expr') ? 'chip'
            : el.closest('#pose') ? 'pose'
            : el.closest('#gerak') ? 'gerak'
            : 'lain',
        lingkar: `${g.outlineWidth} ${g.outlineStyle}`,
        cocok: el.matches(':focus-visible'),
      });
    });
    // Mulai dari chip pertama: setelah sebuah tombol diklik, kursor fokus sudah di
    // tengah daftar sehingga baris raut terlewat oleh Tab berikutnya.
    document.querySelector('#expr button')?.focus();
  });
  for (let i = 0; i < 22; i += 1) await page.keyboard.press('Tab');
  const jejak = await page.evaluate(() => window.__jejak.slice(1));
  const terlihat = jejak
    .filter((e) => e.cocok && /solid/.test(e.lingkar) && parseFloat(e.lingkar) >= 2)
    .map((e) => e.siapa);
  return { jejak, terlihat };
}

const daftar = [
  { nama: 'meja', lebar: 1280, tinggi: 800, kirim: true },
  { nama: 'sempit', lebar: 1280, tinggi: 620, kirim: true },
  { nama: 'kecil', lebar: 430, tinggi: 900, kirim: true },
  { nama: 'kosong', lebar: 1280, tinggi: 800, kirim: false },
];

for (const d of daftar) {
  const page = await browser.newPage({ viewport: { width: d.lebar, height: d.tinggi } });
  const galat = [];
  // Pesan driver WebGL (ReadPixels saat potret) bukan galat halaman.
  page.on('console', (m) =>
    (m.type() === 'error' || m.type() === 'warning') && !m.text().includes('GL Driver Message') && galat.push(m.text()),
  );
  page.on('pageerror', (e) => galat.push('pageerror: ' + e.message));

  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => !!window.__vtuber, null, { timeout: 25000 });
  await page.waitForTimeout(1500);

  const model = await page.evaluate(async () => (await fetch('/api/health').then((r) => r.json())).model);
  if (model !== 'stub') {
    console.log(`FAIL: butuh sisi tiruan di ${url}, dapat model "${model}". Jalankan: set VTUBER_STUB=1 && .venv\\Scripts\\python.exe server_py\\app.py`);
    await browser.close();
    process.exit(1);
  }


  await page.locator('#pose button').nth(1).click();
  if (d.kirim) {
    await page.fill('#isi', 'hai');
    await page.click('#form button[type=submit]');
    await page.waitForTimeout(700);
  }
  const u = await page.evaluate(UKUR);
  await mkdir('.shots', { recursive: true });
  await page.screenshot({ path: `.shots/rancangan-${d.nama}.png` });
  const tab = await jejakTab(page);
  await page.close();

  cek(d.nama, !u.overflowX, 'ada gulir horizontal');
  cek(d.nama, u.tindih.length === 0, `gugus menimpa: ${u.tindih.join(', ')}`);
  for (const perlu of ['chip', 'isi', 'kirim']) {
    const kena = tab.jejak.filter((e) => e.golongan === perlu);
    cek(d.nama, kena.length > 0, `tidak ada "${perlu}" dalam urutan Tab (ketemu: ${[...new Set(tab.jejak.map((e) => e.golongan))].join(', ')})`);
    for (const e of kena) {
      cek(d.nama, e.cocok && /solid/.test(e.lingkar) && parseFloat(e.lingkar) >= 2, `cincin keyboard ${e.siapa} = ${e.lingkar} focus-visible=${e.cocok}`);
    }
  }
  for (const [nama, k] of Object.entries(u.kontras)) {
    cek(d.nama, k >= AA, `kontras ${nama} ${k}:1 (butuh ${AA}:1)`);
  }
  cek(d.nama, u.raut === u.chipAktif, `meter raut "${u.raut}" != chip aktif "${u.chipAktif}"`);
  cek(d.nama, /Palatino|Book Antiqua|Georgia/.test(u.fontHeader), `font kepala jatuh ke default: ${u.fontHeader}`);

  if (d.kirim) {
    cek(d.nama, u.gelembung >= 2, `baru ${u.gelembung} gelembung`);
    cek(d.nama, u.lampu === 'berbicara' || u.lampu === 'diam', `keadaan lampu "${u.lampu}"`);
    cek(d.nama, u.logTinggi > 40, `log setinggi ${u.logTinggi}px`);
  } else {
    cek(d.nama, u.gelembung === 0, 'log harus mulai kosong');
    cek(d.nama, /Belum ada catatan/.test(u.kosong), `state kosong tidak muncul: ${u.kosong}`);
  }
  cek(d.nama, galat.length === 0, galat.join(' | '));

  console.log(
    `${d.nama.padEnd(6)} ${u.panelTinggi}px  log ${u.logTinggi}  gelembung ${u.gelembung}  ` +
      `lampu=${u.lampu}  raut=${u.raut}  kontras min ${Math.min(...Object.values(u.kontras))}:1  ` +
      `tindih=${u.tindih.length ? u.tindih.join(',') : 'tidak'}`,
  );
}

console.log(temuan.length ? `\nFAIL ${temuan.length} temuan:\n  - ${temuan.join('\n  - ')}` : '\nPASS rancangan lolos di empat ukuran');
await browser.close();
process.exit(temuan.length ? 1 : 0);
