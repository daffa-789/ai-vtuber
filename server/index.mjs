// Sidecar lokal: satu-satunya tempat API key berada. Frontend tidak pernah
// menyentuh key, dan tidak ada CORS yang perlu dibuka karena akses lewat proxy Vite.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { GoogleGenAI } from '@google/genai';
import { gabungSystem, perbaruiMood, ekstrakFakta } from './memori.mjs';
import * as vault from './obsidian.mjs';

const PORT = Number(process.env.VTUBER_PORT ?? 8787);
const MODEL = process.env.VTUBER_MODEL ?? 'gemini-3.5-flash';
const TTS_MODEL = process.env.VTUBER_TTS_MODEL ?? 'gemini-2.5-flash-preview-tts';
const TTS_VOICE = process.env.VTUBER_TTS_VOICE ?? 'Kore';
const STT_MODEL = process.env.VTUBER_STT_MODEL ?? 'gemini-3.5-transcribe';
const MAKS_AUDIO = 2 * 1024 * 1024;
const KEY = process.env.GEMINI_API_KEY ?? '';
const MAX_PESAN = 24;
const JEDA_EKSTRAKSI = Number(process.env.VTUBER_JEDA_FAKTA ?? 8);
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

  // Memori dibaca lebih dulu supaya yang dia ingat ikut membentuk jawaban ini.
  let fakta = [];
  let mood = null;
  if (vault.tersedia()) {
    try {
      [fakta, mood] = await Promise.all([vault.bacaFakta(), vault.bacaMood()]);
    } catch (err) {
      console.warn('memori tidak terbaca:', err.message);
    }
  }

  const permintaan = {
    model: MODEL,
    contents: riwayat,
    config: {
      systemInstruction: gabungSystem(persona, fakta, mood),
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
  let mentah = '';
  try {
    for await (const chunk of stream) {
      const potong = chunk.text ?? '';
      mentah += potong;
      res.write(potong);
    }
  } catch (err) {
    console.error('stream terputus:', err.message);
  }
  res.end();

  await simpanMemori(riwayat, mentah, fakta, mood);
}

/**
 * Ditulis setelah balasan terkirim, bukan sebelumnya: kegagalan vault atau
 * ekstraksi fakta tidak boleh membuat percakapan yang sudah terjawab jadi rusak.
 */
async function simpanMemori(riwayat, mentah, faktaLama, moodLama) {
  if (!vault.tersedia() || !mentah.trim()) return;

  try {
    const tag = mentah.match(/^\s*\[([^\]]{1,20})\]/)?.[1]?.toLowerCase() ?? null;
    const isi = mentah.replace(/^\s*\[[^\]]{1,20}\]\s*/, '').trim();
    const tanya = riwayat.at(-1)?.parts?.[0]?.text ?? '';

    const mood = perbaruiMood(moodLama, tag);
    await vault.catatHari(`**Master:** ${tanya} → **Haru:** ${isi} _(${tag ?? 'tanpa tag'})_`);
    await vault.simpanMood(mood);

    // Ekstraksi fakta menambah satu panggilan API, jadi sengaja jarang.
    if (mood.pertukaran % JEDA_EKSTRAKSI === 0) {
      const percakapan = riwayat.slice(-12).map((m) => ({
        role: m.role,
        content: m.parts.map((p) => p.text).join(' '),
      }));
      const baru = await ekstrakFakta(ai, MODEL, percakapan, faktaLama);
      if (baru.length) {
        await vault.simpanFakta([...new Set([...faktaLama, ...baru])].slice(-40));
        console.log(`fakta baru tersimpan: ${baru.length}`);
      }
    }
  } catch (err) {
    console.warn('memori gagal ditulis:', err.message);
  }
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

// Body-nya WAV mentah (bukan JSON) supaya frontend tidak perlu base64 dua kali.
async function stt(req, res) {
  if (!ai) {
    json(res, 501, { error: 'GEMINI_API_KEY belum diisi.' });
    return;
  }

  const bagian = [];
  let ukuran = 0;
  for await (const potong of req) {
    ukuran += potong.length;
    if (ukuran > MAKS_AUDIO) {
      json(res, 413, { error: 'audio terlalu besar' });
      req.destroy();
      return;
    }
    bagian.push(potong);
  }

  if (ukuran < 1000) {
    json(res, 400, { error: 'audio terlalu pendek atau kosong' });
    return;
  }

  try {
    const r = await ai.models.generateContent({
      model: STT_MODEL,
      contents: {
        parts: [{ inlineData: { mimeType: 'audio/wav', data: Buffer.concat(bagian).toString('base64') } }],
      },
    });

    const part = r.candidates?.[0]?.content?.parts?.[0];
    // Model transcribe menaruh hasil di audioTranscription, bukan di .text.
    const teks = (part?.audioTranscription?.text ?? part?.text ?? '').trim();
    json(res, 200, { teks });
  } catch (err) {
    json(res, 503, { error: bersihkanError(err) });
  }
}

const server = createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/api/health') {
    json(res, 200, {
      ok: true,
      model: MODEL,
      key: Boolean(ai),
      memori: vault.tersedia() ? 'vault Obsidian' : vault.alasanTidakTersedia(),
    });
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
  } else if (req.method === 'POST' && req.url === '/api/stt') {
    stt(req, res).catch((err) => {
      console.error(err);
      if (!res.headersSent) json(res, 500, { error: err.message });
      else res.end();
    });
  } else {
    json(res, 404, { error: 'tidak ada endpoint itu' });
  }
});

// Mesin ini dipakai banyak proyek sekaligus, jadi port tetap adalah asumsi yang
// salah. Kalau port sudah dipakai proses lain, kita laporkan -- tidak mengosongkannya.
server.on('error', (err) => {
  if (err.code !== 'EADDRINUSE') throw err;
  console.error(`port ${PORT} sudah dipakai proses lain; tidak kukosongkan.`);
  console.error('jalankan di port bebas:  VTUBER_PORT=0 npm run server   (0 = acak)');
  console.error('lalu samakan VTUBER_PORT di .env supaya proxy Vite ikut ke sana.');
  process.exit(1);
});

server.listen(PORT, '127.0.0.1', () => {
  const { port } = server.address();
  console.log(
    `sidecar http://127.0.0.1:${port} | key=${ai ? 'siap' : 'BELUM ADA'} | chat=${MODEL} | tts=${TTS_MODEL}/${TTS_VOICE} | stt=${STT_MODEL} | memori=${vault.tersedia() ? 'vault Obsidian' : 'mati'}`,
  );
  if (String(port) !== String(PORT)) console.log(`catatan: VTUBER_PORT di .env masih ${PORT}`);
});
