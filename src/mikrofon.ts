import { MicVAD, utils } from '@ricky0123/vad-web';

type VAD = Awaited<ReturnType<typeof MicVAD.new>>;

let vad: VAD | null = null;

/**
 * Deteksi bicara jalan sepenuhnya di mesin ini (Silero VAD lewat onnxruntime-web);
 * hanya potongan yang terdeteksi sebagai suara yang dikirim untuk disalin.
 */
export async function nyalakanMikrofon(
  onUcapan: (wav: ArrayBuffer) => void,
  onStatus: (s: string) => void,
) {
  if (vad) return;

  vad = await MicVAD.new({
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

  await vad.start();
}

export function jedaMikrofon() {
  vad?.pause();
}

export async function matikanMikrofon() {
  await vad?.destroy();
  vad = null;
}

export function lanjutMikrofon() {
  vad?.start();
}

export async function salinAudio(wav: ArrayBuffer): Promise<string> {
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
