// Entri aplikasi. PIXI dan Live2DModel datang dari berkas UMD di index.html --
// tidak ada bundler lagi, jadi tidak ada `import 'pixi.js'` di sini.
const { Live2DModel, MotionPreloadStrategy } = PIXI.live2d;
// Tanpa registerTicker, model dimuat tapi tidak pernah bergerak.
Live2DModel.registerTicker(PIXI.Ticker);

import { pasangChat } from './chat.js';
import { pasangIrama } from './iriama.js';
import { setelan, skalaRender, ukuranPanggung } from './setelan.js';
import { tingkatMulut } from './suara.js';
import {
  LapisanPose,
  peringatanKonfigurasi,
  suntikEkspresi,
  tabelParameter,
} from './wajah.js';

const canvas = document.getElementById('stage');
const statusEl = document.getElementById('status');
const fpsEl = document.getElementById('fps');
const exprEl = document.getElementById('expr');
const poseEl = document.getElementById('pose');
const gerakEl = document.getElementById('gerak');

const app = new PIXI.Application({
  view: canvas,
  width: canvas.clientWidth,
  height: canvas.clientHeight,
  backgroundAlpha: 0,
  antialias: setelan.render.halus,
  // Tanpa mengikuti devicePixelRatio, backing store cuma punya sebakal piksel
  // sebanyak CSS px dan browser merentangkannya -- wajah model terlihat lembut.
  resolution: skalaRender(),
});

/**
 * Kotak avatar dipakai dari .env lewat variabel CSS, BUKAN lewat autoDensity.
 * autoDensity menulis lebar/tinggi inline berupa angka tetap, yang mematikan
 * aturan min() di index.html dan membuat kanvas berhenti ikut jendela.
 */
function terapkanPanggung() {
  const { lebar, tinggi } = ukuranPanggung();
  const gaya = document.documentElement.style;
  gaya.setProperty('--panggung-lebar', lebar);
  gaya.setProperty('--panggung-tinggi', tinggi);
}
terapkanPanggung();

/**
 * Zoom browser (Ctrl + +) mengubah devicePixelRatio TETAPI tidak mengubah
 * backing store kanvas yang sudah dibuat. Tanpa fungsi ini, memperbesar tampilan
 * membuat avatar buram sampai halaman dimuat ulang.
 */
function terapkanResolusi() {
  const butuh = skalaRender();
  const renderer = app.renderer;
  if (Math.abs(renderer.resolution - butuh) > 1e-3) renderer.resolution = butuh;
  const { clientWidth: lebar, clientHeight: tinggi } = canvas;
  // Selalu resize -- ukuran CSS kanvas bisa berubah tanpa resolusinya ikut
  // berubah -- TAPI viewport boleh 0x0 (jendela tersembunyi), dan resize(0,0)
  // membuang backing store yang sudah benar tanpa menghasilkan apa pun.
  if (lebar > 0 && tinggi > 0) renderer.resize(lebar, tinggi);
  return butuh;
}

/** Berapa kali lipat piksel yang harus diregangkan browser; 1 = tajam, > 1 = buram. */
function defisitPiksel() {
  const punya = canvas.width || 1;
  const butuh = canvas.clientWidth * (window.devicePixelRatio || 1);
  return +(butuh / punya).toFixed(2);
}

let modelAktif = null;

function layout(model) {
  // model.height sudah dikalikan scale aktif, jadi reset dulu supaya fungsi ini
  // tetap benar saat dipanggil ulang setelah resize.
  model.scale.set(1);
  const skala = (app.screen.height * setelan.avatar.zoom) / model.height;
  model.scale.set(skala);
  model.anchor.set(0.5, setelan.avatar.jangkar);
  model.x = app.screen.width * setelan.avatar.x;
  // Sprite memanjang dari y - a*h sampai y + (1-a)*h, jadi supaya tepi bawahnya
  // tetap menempel dasar kanvas pada nilai jangkar berapa pun.
  model.y = app.screen.height - (1 - setelan.avatar.jangkar) * model.height;
}

const peringatan = [];

function lapor() {
  const wajah = setelan.wajah.length;
  const pose = setelan.pose.length;
  const gerak = setelan.gerakan.length;
  const regang = defisitPiksel();
  statusEl.textContent =
    `siap — ${wajah} wajah, ${pose} pose, ${gerak} gerakan · ` +
    `${Math.round(app.screen.width)}×${Math.round(app.screen.height)} css · ` +
    `${canvas.width}×${canvas.height} px · ${app.renderer.resolution.toFixed(2)}×` +
    (regang > 1.05 ? ` · REGANG ${regang}×` : '') +
    (peringatan.length ? ` · ${peringatan.length} konfigurasi perlu dicek` : '');
}

/**
 * devicePixelRatio dilaporkan media query hanya untuk nilai SAAT INI, jadi
 * listenernya harus dipasang ulang setiap kali nilainya berubah -- zoom browser
 * menghasilkan nilai baru di setiap langkahnya.
 */
let mediaDpr = null;
function segarkan() {
  terapkanResolusi();
  if (modelAktif) layout(modelAktif);
  lapor();
}
function padaDpr() {
  pantauDpr();
  segarkan();
}
function pantauDpr() {
  mediaDpr?.removeEventListener('change', padaDpr);
  mediaDpr = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
  mediaDpr.addEventListener('change', padaDpr);
}

async function boot() {
  // motionPreload 'none': model ini hanya punya satu motion isyarat, jadi
  // tidak ada gunanya menariknya sebelum benar-benar dipakai.
  const model = await Live2DModel.from(setelan.modelUrl, {
    autoInteract: setelan.ikutiKursor,
    motionPreload: MotionPreloadStrategy.NONE,
  });
  modelAktif = model;
  app.stage.addChild(model);
  layout(model);

  const inti = model.internalModel.coreModel;

  // Motion tidak mengembalikan parameternya ke nilai awal saat selesai, jadi
  // gerakan "sedih melambai" meninggalkan air mata membeku di 30 selamanya.
  // Satu frame setelah motion selesai semua parameter ditulis ulang ke default;
  // aman karena ekspresi, kedip, fokus, dan fisika menulis setelah titik itu.
  let resetSetelahGerak = false;

  // afterMotionUpdate = setelah motion menulis parameter, jadi mulut dari audio
  // tidak ditimpa animasi idle pada frame yang sama.
  let mulutAktif = 0;
  model.internalModel.on('afterMotionUpdate', () => {
    if (resetSetelahGerak) {
      resetSetelahGerak = false;
      const p = inti.getModel().parameters;
      for (let i = 0; i < p.ids.length; i++) inti.setParameterValueById(p.ids[i], p.defaultValues[i]);
    }
    mulutAktif = tingkatMulut();
    inti.setParameterValueById('ParamMouthOpenY', mulutAktif);
  });

  // Kedip dan napas bawaan pustaka; keduanya bisa dimatikan dari .env.
  const internals = model.internalModel;
  if (!setelan.kedip) internals.eyeBlink = null;
  if (!setelan.napas) internals.breath = null;

  const terpasang = new Set(suntikEkspresi(model, setelan));
  peringatan.push(...peringatanKonfigurasi(inti));

  const pose = new LapisanPose(inti, tabelParameter(inti), setelan.pose, setelan.pudarDetik);
  // beforeModelUpdate = terakhir sebelum Cubism menulis nilainya, jadi pose
  // bertahan di atas ekspresi mana pun dan tidak dihapus oleh motion.
  model.internalModel.on('beforeModelUpdate', () => pose.perFrame());
  for (const nama of setelan.awalPose) pose.ubah(nama, true);

  const tombolWajah = new Map();
  const rautEl = document.getElementById('raut');
  const setEkspresi = (nama) => {
    if (!terpasang.has(nama)) {
      console.warn(`ekspresi "${nama}" tidak terpasang`);
      return;
    }
    model.expression(nama);
    tombolWajah.forEach((btn, key) => btn.classList.toggle('aktif', key === nama));
    // Meteran "raut" dibaca sekilas dari seberang ruangan; daftar chip tidak.
    // Ditulis di sini, BUKAN di tombolnya, karena wajah juga berganti dari tag
    // chat dan dari ekspresi dasar saat balasan tidak memakai tag.
    if (rautEl) rautEl.textContent = nama;
  };

  const tombolPose = new Map();
  const setPose = (nama, hidup) => {
    const nyala = pose.ubah(nama, hidup);
    tombolPose.get(nama)?.classList.toggle('aktif', nyala);
  };

  for (const e of setelan.wajah) {
    const btn = document.createElement('button');
    btn.textContent = e.nama;
    btn.onclick = () => setEkspresi(e.nama);
    tombolWajah.set(e.nama, btn);
    exprEl.appendChild(btn);
  }
  // Pose yang namanya sama hanya beda angka di akhir (pamer-barang-1 / -2) adalah
  // satu keluarga: model kehabisan tangan kalau keduanya nyala bersamaan.
  // Keluarga dihitung dari daftar .env, jadi menambah pamer-barang-3 tidak perlu
  // mengubah kode ini.
  const keluarga = new Map();
  for (const e of setelan.pose) {
    const akar = e.nama.replace(/-?\d+$/, '');
    if (akar === e.nama) continue;
    if (!keluarga.has(akar)) keluarga.set(akar, []);
    keluarga.get(akar).push(e.nama);
  }
  const satuSatu = new Set([...keluarga].filter(([, anggota]) => anggota.length > 1).flatMap(([, a]) => a));

  for (const e of setelan.pose) {
    const btn = document.createElement('button');
    btn.textContent = e.nama;
    btn.title = 'ditumpuk di atas wajah, bukan menggantikannya';
    btn.onclick = () => {
      if (!satuSatu.has(e.nama)) {
        setPose(e.nama);
        return;
      }
      const sudahNyala = pose.aktif(e.nama);
      // Padamkan seluruh keluarga dulu, baru nyalakan yang diklik -- jadi
      // berpindah, bukan menumpuk. Kalau yang diklik memang sedang nyala,
      // hasilnya mati semua (toggle biasa).
      for (const n of keluarga.get(e.nama.replace(/-?\d+$/, ''))) setPose(n, false);
      if (!sudahNyala) setPose(e.nama, true);
    };
    tombolPose.set(e.nama, btn);
    poseEl.appendChild(btn);
  }

  // Motion bawaan model ini Loop:true di berkas aslinya; salinan hasil pemasangan
  // sudah diubah jadi sekali-jalan, kalau tidak dia melambai selamanya.
  const definisiGerak = model.internalModel.motionManager.definitions ?? {};
  for (const g of setelan.gerakan) {
    const grup = definisiGerak[g.grup] ?? [];
    const indeks = grup.findIndex((m) => (m.File ?? '').endsWith(g.berkas));
    if (grup.length === 0) {
      peringatan.push(`gerakan "${g.nama}": grup "${g.grup}" tidak ada di model3.json`);
    } else if (indeks === -1) {
      peringatan.push(
        `gerakan "${g.nama}": ${g.berkas} tidak terdaftar di grup "${g.grup}" — jalankan pemasangan model`,
      );
    }
    const btn = document.createElement('button');
    btn.textContent = g.nama;
    btn.onclick = () => {
      model.internalModel.motionManager.once('motionFinish', () => {
        resetSetelahGerak = true;
      });
      // Prioritas 1: wajib, bukan 0 yang ditolak reserve().
      model.motion(g.grup, indeks === -1 ? undefined : indeks, 1);
    };
    gerakEl.appendChild(btn);
  }

  window.addEventListener('resize', segarkan);
  pantauDpr();

  let frames = 0;
  let last = performance.now();
  const meter = () => {
    frames += 1;
    const now = performance.now();
    if (now - last >= 1000) {
      fpsEl.textContent = String(Math.round((frames * 1000) / (now - last)));
      frames = 0;
      last = now;
    }
  };
  app.ticker.add(meter);

  const irama = pasangIrama({
    app,
    fpsEl,
    jedaSaatSembunyi: setelan.irama.jedaSaatSembunyi,
    fpsSaatTakFokus: setelan.irama.fpsSaatTakFokus,
    // Habis jeda, hitung ulang dari "sekarang": tanpa ini, frame pertama sesudah
    // bangun dibandingkan dengan waktu frame TERAKHIR SEBELUM jeda dan meterannya
    // menunjukkan 1 FPS selama satu detik penuh.
    setelahLanjut: () => {
      frames = 0;
      last = performance.now();
    },
  });

  pasangChat(setEkspresi, setPose);
  setEkspresi(setelan.ekspresiDasar);
  for (const nama of pose.nyala) tombolPose.get(nama)?.classList.add('aktif');
  peringatan.forEach((p) => console.warn(p));
  lapor();

  // Permukaan debug untuk skrip verifikasi; bukan bagian dari runtime aplikasi.
  window.__vtuber = {
    app,
    model,
    layout,
    setEkspresi,
    setPose,
    pose,
    konfig: setelan,
    irama,
    ekspresiTerpasang: [...terpasang],
    peringatan,
    resolusi: () => ({
      dpr: window.devicePixelRatio || 1,
      resolution: app.renderer.resolution,
      css: [canvas.clientWidth, canvas.clientHeight],
      piksel: [canvas.width, canvas.height],
      defisit: defisitPiksel(),
    }),
    get mulut() {
      return mulutAktif;
    },
  };
}

boot().catch((err) => {
  statusEl.textContent = `gagal: ${err instanceof Error ? err.message : String(err)}`;
  console.error(err);
});
