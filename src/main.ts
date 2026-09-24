import * as PIXI from 'pixi.js';
// Entri utama paket ini Cubism 2; model .moc3 butuh entri Cubism 4.
import { Live2DModel, MotionPreloadStrategy } from 'pixi-live2d-display/cubism4';
import { pasangChat } from './chat';
import { EKSPRESI_DASAR } from './ekspresi';
import { matikanMikrofon } from './mikrofon';
import { tingkatMulut } from './suara';

// pixi-live2d-display membaca PIXI dari global saat jalan di browser.
(window as unknown as { PIXI: typeof PIXI }).PIXI = PIXI;
Live2DModel.registerTicker(PIXI.Ticker);

const MODEL_URL = '/models/penyihir/penyihir.model3.json';

const canvas = document.getElementById('stage') as HTMLCanvasElement;
const statusEl = document.getElementById('status') as HTMLElement;
const fpsEl = document.getElementById('fps') as HTMLElement;
const exprEl = document.getElementById('expr') as HTMLElement;

const app = new PIXI.Application({
  view: canvas,
  width: canvas.clientWidth,
  height: canvas.clientHeight,
  backgroundAlpha: 0,
  antialias: true,
  // Tanpa ini kanvas cuma punya sebakal piksel sebanyak CSS px, jadi di layar
  // berskala 125% browser merentangkannya dan wajah model terlihat lembut.
  // Ditahan di 2 supaya layar 3x tidak melipatgandakan beban GPU.
  resolution: Math.min(window.devicePixelRatio || 1, 2),
});

function layout(model: Live2DModel) {
  // model.height sudah dikalikan scale aktif, jadi reset dulu supaya fungsi ini
  // tetap benar saat dipanggil ulang setelah resize.
  model.scale.set(1);
  const scale = (app.screen.height * 0.96) / model.height;
  model.scale.set(scale);
  model.anchor.set(0.5, 1);
  model.x = app.screen.width / 2;
  model.y = app.screen.height;
}

async function boot() {
  // motionPreload 'none': model ini hanya punya satu motion isyarat, jadi
  // tidak ada gunanya menariknya sebelum benar-benar dipakai.
  const model = await Live2DModel.from(MODEL_URL, {
    autoInteract: true,
    motionPreload: MotionPreloadStrategy.NONE,
  });
  app.stage.addChild(model);
  layout(model);

  const inti = model.internalModel.coreModel as unknown as {
    setParameterValueById(id: string, value: number): void;
  };
  // afterMotionUpdate = setelah motion menulis parameter, jadi mulut dari audio
  // tidak ditimpa animasi idle pada frame yang sama.
  let mulutAktif = 0;
  model.internalModel.on('afterMotionUpdate', () => {
    mulutAktif = tingkatMulut();
    inti.setParameterValueById('ParamMouthOpenY', mulutAktif);
  });

  const tombol = new Map<string, HTMLButtonElement>();
  const setEkspresi = (nama: string) => {
    model.expression(nama);
    tombol.forEach((btn, key) => btn.classList.toggle('aktif', key === nama));
  };

  // Tipe ModelSettings belum mencakup expressions, padahal isinya ada di runtime.
  const settings = model.internalModel.settings as unknown as {
    expressions?: { Name?: string; name?: string }[];
  };
  const names: string[] = (settings.expressions ?? []).map((e) => e.Name ?? e.name ?? '');

  names.forEach((name) => {
    const btn = document.createElement('button');
    btn.textContent = name;
    btn.onclick = () => setEkspresi(name);
    tombol.set(name, btn);
    exprEl.appendChild(btn);
  });

  const lapor = () => {
    // app.screen dibagi resolution, jadi hasilnya pecah tanpa dibulatkan.
    statusEl.textContent = `siap — ${names.length} ekspresi, ${Math.round(app.screen.width)}x${Math.round(app.screen.height)}`;
  };

  window.addEventListener('resize', () => {
    app.renderer.resize(canvas.clientWidth, canvas.clientHeight);
    layout(model);
    lapor();
  });

  let frames = 0;
  let last = performance.now();
  app.ticker.add(() => {
    frames += 1;
    const now = performance.now();
    if (now - last >= 1000) {
      fpsEl.textContent = String(Math.round((frames * 1000) / (now - last)));
      frames = 0;
      last = now;
    }
  });

  pasangChat(setEkspresi);
  setEkspresi(EKSPRESI_DASAR);
  lapor();

  // Permukaan debug untuk skrip verifikasi; bukan bagian dari runtime aplikasi.
  (window as unknown as { __vtuber: unknown }).__vtuber = {
    app,
    model,
    layout,
    setEkspresi,
    matikanMikrofon,
    get mulut() {
      return mulutAktif;
    },
  };
}

boot().catch((err: unknown) => {
  statusEl.textContent = `gagal: ${err instanceof Error ? err.message : String(err)}`;
  console.error(err);
});
