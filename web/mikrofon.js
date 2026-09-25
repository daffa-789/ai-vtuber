// Deteksi bicara di mesin sendiri (Silero VAD lewat onnxruntime-web).
//
// Belum dipakai halaman: jalur mikrofon sengaja dilepas dari UI (lihat README),
// berkas ini dipindah utuh supaya tinggal disambung lagi. Beda dengan versi TS
// dulu, pustakanya sekarang UMD yang dimuat index.html -- kalau mic diaktifkan,
// tambahkan <script src="/lib/vad.bundle.min.js"></script> di atas dan pakai
// `window.vad.MicVAD`.
const vad = () => window.vad || {};

let instance = null;

/**
 * Hanya potongan yang terdeteksi sebagai bicara yang dikirim untuk disalin,
 * jadi tidak ada audio terus-menerus yang keluar dari mesin ini.
 */
export async function nyalakanMikrofon(onUcapan, onStatus) {
  if (instance) return;
  const { MicVAD, utils } = vad();
  if (!MicVAD) throw new Error('pustaka VAD belum dimuat (tambahkan /lib/vad.bundle.min.js)');

  instance = await MicVAD.new({
    baseAssetPath: '/vad/',
    onnxWASMBasePath: '/ort/',
    positiveSpeechThreshold: 0.6,
    negativeSpeechThreshold: 0.45,
    preSpeechPadMs: 250, // awalan kata sering terpotong tanpa bantalan ini
    redemptionMs: 500,
    minSpeechMs: 250,
    // Jangan serahkan audio yang terpotong saat kita pause: hasilnya adalah
    // suaranya sendiri yang ikut disalin dan dibalas.
    submitUserSpeechOnPause: false,
    onSpeechStart: () => onStatus('mendengar…'),
    onSpeechEnd: (audio) => {
      onUcapan(utils.encodeWAV(audio, 1, 16000, 16));
    },
    onVADMisfire: () => onStatus('aktif, bicara saja'),
  });

  await instance.start();
}

export function jedaMikrofon() {
  instance?.pause();
}

export async function matikanMikrofon() {
  // MicVAD tidak punya stop(); yang ada destroy().
  await instance?.destroy();
  instance = null;
}

export function lanjutMikrofon() {
  instance?.start();
}

export async function salinAudio(wav) {
  const res = await fetch('/api/stt', {
    method: 'POST',
    headers: { 'content-type': 'audio/wav' },
    body: wav,
  });

  if (!res.ok) {
    const pesan = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(pesan.error ?? 'STT gagal');
  }

  return (await res.json()).teks ?? '';
}
