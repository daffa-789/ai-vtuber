// Sidecar lokal: satu-satunya tempat API key berada. Frontend tidak pernah
// menyentuh key, dan tidak ada CORS yang perlu dibuka karena akses lewat proxy Vite.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { GoogleGenAI } from '@google/genai';

const PORT = Number(process.env.VTUBER_PORT ?? 8787);
const MODEL = process.env.VTUBER_MODEL ?? 'gemini-3.5-flash';
const TTS_MODEL = process.env.VTUBER_TTS_MODEL ?? 'gemini-2.5-flash-preview-tts';
const TTS_VOICE = process.env.VTUBER_TTS_VOICE ?? 'Kore';
const KEY = process.env.GEMINI_API_KEY ?? '';
const MAX_PESAN = 24;
const MAKS_KARAKTER = 4000;
const MAKS_BODY = 64 * 1024;
const TUNDA_COBA = [1500, 4000];

// Google menumpuk JSON error di dalam string message, dan kodenya ada di dua lapis.
function bersihkanError(err) {
  let pesan = err?.message ?? String(err);
  for (let i = 0; i < 3; i++) {
    try {
      const dalam = JSON.parse(pesan)?.error;
      if (!dalam) break;
      pesan = typeof dalam === 'string' ? dalam : (dalam.message ?? pesan);
    } catch {
      break;
    }
  }
  return pesan.replace(/\s+/g, ' ').trim();
}

// Key baru sering kena 503 "high demand" sementara kuota belum naik. Ini kondisi
// nyata, bukan teoritis: panggilan pertama lolos, beberapa berikutnya ditolak.
function layakDicoba(error) {
  return /503|429|UNAVAILABLE|RESOURCE_EXHAUSTED|high demand|rate/i.test(error);
}

const persona = await readFile(new URL('../persona.md', import.meta.url), 'utf8');
const ai = KEY ? new GoogleGenAI({ apiKey: KEY }) : null;

function json(res, kode, data) {
  const body = JSON.stringify(data);
  res.writeHead(kode, { 'content-type': 'application/json; charset=utf-8' });
  res.end(body);
}

function bacaBody(req) {
  return new Promise((selesai, gagal) => {
    let teks = '';
    req.on('data', (c) => {
      teks += c;
      if (teks.length > MAKS_BODY) gagal(new Error('body terlalu besar'));
    });
    req.on('end', () => selesai(teks));
    req.on('error', gagal);
  });
}

// Peran harus dibatasi ke dua nilai yang dikenali API, isi harus string pendek.
function rapikanRiwayat(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((m) => m && typeof m.content === 'string' && m.content.trim())
    .map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content.slice(0, MAKS_KARAKTER) }],
    }))
    .slice(-MAX_PESAN);
}

async function chat(req, res) {
  if (!ai) {
    json(res, 501, {
      error: 'GEMINI_API_KEY belum diisi. Salin .env.example jadi .env lalu isi.',
    });
    return;
  }

  let riwayat;
  try {
    riwayat = rapikanRiwayat(JSON.parse(await bacaBody(req)).messages);
  } catch {
    json(res, 400, { error: 'body harus JSON: { messages: [{role, content}] }' });
    return;
  }

  if (!riwayat.length) {
    json(res, 400, { error: 'riwayat kosong' });
    return;
  }

  const permintaan = {
    model: MODEL,
    contents: riwayat,
    config: {
      systemInstruction: persona,
      generationConfig: { temperature: 0.9, maxOutputTokens: 400 },
    },
  };

  let stream = null;
  let errorTerakhir = '';
  for (let percobaan = 0; percobaan <= TUNDA_COBA.length; percobaan++) {
    try {
      stream = await ai.models.generateContentStream(permintaan);
      break;
    } catch (err) {
      errorTerakhir = bersihkanError(err);
      if (!layakDicoba(errorTerakhir) || percobaan === TUNDA_COBA.length) break;
      console.warn(`503/429, percobaan ke-${percobaan + 2} dalam ${TUNDA_COBA[percobaan]}ms`);
      await new Promise((r) => setTimeout(r, TUNDA_COBA[percobaan]));
    }
  }

  if (!stream) {
    json(res, 503, { error: errorTerakhir || 'Gemini menolak permintaan' });
    return;
  }

  res.writeHead(200, {
    'content-type': 'text/plain; charset=utf-8',
    'cache-control': 'no-store',
    'x-accel-buffering': 'no',
  });

  // Setelah byte pertama terkirim status tidak bisa diubah lagi, jadi
  // kegagalan di tengah stream cukup menutup aliran; frontend menampilkan parsial.
  try {
    for await (const chunk of stream) res.write(chunk.text ?? '');
  } catch (err) {
    console.error('stream terputus:', err.message);
  }
  res.end();
}

// Gemini TTS memulangkan PCM mentah tanpa header, jadi dibungkus WAV di sini.
function pcmKeWav(pcm, sampleRate, channels) {
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write('WAVEfmt ', 8);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * channels * 2, 28);
  header.writeUInt16LE(channels * 2, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}

async function tts(req, res) {
  if (!ai) {
    json(res, 501, { error: 'GEMINI_API_KEY belum diisi.' });
    return;
  }

  let teks;
  try {
    teks = String(JSON.parse(await bacaBody(req)).text ?? '').slice(0, MAKS_KARAKTER);
  } catch {
    json(res, 400, { error: 'body harus JSON: { text }' });
    return;
  }

  if (!teks.trim()) {
    json(res, 400, { error: 'teks kosong' });
    return;
  }

  try {
    const r = await ai.models.generateContent({
      model: TTS_MODEL,
      contents: teks,
      config: {
        responseModalities: ['AUDIO'],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: TTS_VOICE } } },
      },
    });

    const audio = r.candidates?.[0]?.content?.parts?.find((p) => p.inlineData)?.inlineData;
    if (!audio?.data) {
      json(res, 502, { error: 'model tidak mengembalikan audio' });
      return;
    }

    // Contoh mime: "audio/L16;codec=pcm;rate=24000" atau "audio/l16; rate=24000; channels=1"
    const angka = [...audio.mimeType.matchAll(/(rate|channels)=(\d+)/g)].map((m) => +m[2]);
    const sampleRate = angka[0] ?? 24000;
    const channels = angka[1] ?? 1;
    const wav = pcmKeWav(Buffer.from(audio.data, 'base64'), sampleRate, channels);

    res.writeHead(200, {
      'content-type': 'audio/wav',
      'content-length': wav.length,
      'cache-control': 'no-store',
    });
    res.end(wav);
  } catch (err) {
    json(res, 503, { error: bersihkanError(err) });
  }
}

createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/api/health') {
    json(res, 200, { ok: true, model: MODEL, key: Boolean(ai) });
  } else if (req.method === 'POST' && req.url === '/api/chat') {
    chat(req, res).catch((err) => {
      console.error(err);
      if (!res.headersSent) json(res, 500, { error: err.message });
      else res.end();
    });
  } else if (req.method === 'POST' && req.url === '/api/tts') {
    tts(req, res).catch((err) => {
      console.error(err);
      if (!res.headersSent) json(res, 500, { error: err.message });
      else res.end();
    });
  } else {
    json(res, 404, { error: 'tidak ada endpoint itu' });
  }
}).listen(PORT, '127.0.0.1', () => {
  console.log(`sidecar http://127.0.0.1:${PORT} | model=${MODEL} | key=${ai ? 'siap' : 'BELUM ADA'}`);
});
