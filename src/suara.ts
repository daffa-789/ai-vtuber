// Suara + gerak mulut. Mulut tidak ditebak dari teks, tapi dari amplitudo audio
// yang sedang diputar, jadi tidak perlu pelurusan fonem bahasa Indonesia.
let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let sampel: Uint8Array | null = null;
let sumber: AudioBufferSourceNode | null = null;
let berbicara = false;
let mulut = 0;

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

export function tingkatMulut(): number {
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

export async function bicarakan(teks: string): Promise<void> {
  const res = await fetch('/api/tts', {
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

  hentikan();
  berbicara = true;

  await new Promise<void>((selesai) => {
    const src = audio.createBufferSource();
    src.buffer = buffer;
    src.connect(analyser!);
    src.onended = () => {
      berbicara = false;
      sumber = null;
      selesai();
    };
    src.start();
    sumber = src;
  });
}
