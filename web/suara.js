// Suara + gerak mulut. Mulut tidak ditebak dari teks, tapi dari amplitudo audio
// yang sedang diputar, jadi tidak perlu pelurusan fonem bahasa Indonesia.
let ctx = null;
let analyser = null;
let sampel = null;
let sumber = null;
let berbicara = false;
let mulut = 0;
/** Ekor antrean putar + nomor generasi supaya "hentikan" membatalkan yang belum mulai. */
let ekor = Promise.resolve();
let generasi = 0;

const LANTAI_NOISE = 0.012;
const PENGUAT = 7;

async function pastikanKonteks() {
  if (!ctx) {
    ctx = new AudioContext();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.6;
    sampel = new Uint8Array(analyser.fftSize);
    analyser.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') await ctx.resume();
  return ctx;
}

export function tingkatMulut() {
  if (!berbicara || !analyser || !sampel) {
    mulut *= 0.6;
    return mulut;
  }

  analyser.getByteTimeDomainData(sampel);
  let jumlahKuadrat = 0;
  for (let i = 0; i < sampel.length; i++) {
    const v = (sampel[i] - 128) / 128;
    jumlahKuadrat += v * v;
  }

  const rms = Math.sqrt(jumlahKuadrat / sampel.length);
  const target = Math.min(1, Math.max(0, (rms - LANTAI_NOISE) * PENGUAT));
  // Buka cepat, tutup lambat: rahang yang menutup linear terlihat seperti kedip.
  mulut += (target - mulut) * (target > mulut ? 0.55 : 0.18);
  return mulut;
}

export function hentikan() {
  generasi += 1; // antrean yang belum kebagian tempat ikut gugur
  if (!sumber) return;
  sumber.onended = null;
  try {
    sumber.stop();
  } catch {
    // sudah berhenti sendiri
  }
  sumber = null;
  berbicara = false;
}

const API_BASE = typeof window !== 'undefined' && window.location?.protocol === 'file:'
  ? 'http://127.0.0.1:8787'
  : '';

/**
 * Satu potongan audio diunduh DAN diputar. Unduhannya dimulai begitu dipanggil,
 * pemutarannya menunggu potongan sebelumnya selesai -- jadi kalimat kedua sudah
 * di jalur saat kalimat pertama masih terdengar.
 */
async function putarPotongan(teks, angka) {
  const res = await fetch(`${API_BASE}/api/tts`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text: teks }),
  });

  if (!res.ok) {
    const pesan = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(pesan.error ?? 'TTS gagal');
  }

  const audio = await pastikanKonteks();
  const buffer = await audio.decodeAudioData(await res.arrayBuffer());
  if (generasi !== angka) return; // sudah keburu dipotong

  berbicara = true;
  await new Promise((selesai) => {
    const src = audio.createBufferSource();
    src.buffer = buffer;
    src.connect(analyser);
    src.onended = () => {
      berbicara = false;
      sumber = null;
      selesai();
    };
    src.start();
    sumber = src;
  });
}

/** Antre satu kalimat. Rantainya sendiri menahan kegagalan supaya satu potongan
 *  yang gagal tidak menghentikan sisa jawaban. */
export function antre(teks) {
  const potongan = teks.trim();
  if (!potongan) return Promise.resolve();
  const angka = generasi;
  const diunduh = putarPotongan(potongan, angka);
  ekor = ekor.then(() => diunduh).catch((err) => {
    if (angka === generasi) console.warn('potongan suara gugur:', err instanceof Error ? err.message : err);
  });
  return diunduh;
}

/** Semua yang sudah diantre sudah selesai diputar. */
export function selesai() {
  return ekor;
}

export async function bicarakan(teks) {
  hentikan();
  await antre(teks);
  await ekor;
}
