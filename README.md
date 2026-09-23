# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer, loop chat, ekspresi, dan text-to-speech sudah berjalan.
Input mikrofon dan memori jangka panjang masih dalam pengerjaan.

## Menjalankan

Prasyarat: Node.js 20.6+ (butuh flag `--env-file-if-exists`).

```bash
npm install
npm run assets        # unduh model Live2D + Cubism core (tidak ikut ke git, lihat Lisensi)
cp .env.example .env  # lalu isi GEMINI_API_KEY
npm run server        # sidecar di 127.0.0.1:8787
npm run dev           # buka http://localhost:5173
```

## Cara kerja

```
mikrofon (belum) ─┐
                  ├─> STT ─> Gemini 3.5 Flash ─> teks ─> Gemini TTS ─> WAV 24kHz
papan ketik ──────┘              │                                    │
                          tag [senyum]                        AnalyserNode (amplitudo)
                                 │                                    │
                          ekspresi Live2D                      ParamMouthOpenY
```

- **`server/index.mjs`** — sidecar Node. Satu-satunya pemegang API key, hanya
  listen di `127.0.0.1`, dan membungkus PCM mentah dari Gemini menjadi WAV.
  Sudah dilengkapi percobaan ulang berjenjang untuk 503/429, karena kunci API
  baru sering kena batas kapasitas.
- **`persona.md`** — sifat dan gaya bicara karakter. Ini konfigurasi, bukan model
  yang dilatih: diedit langsung, dan selalu dikirim sebagai system instruction.
- **`src/ekspresi.ts`** — menerjemahkan tag dari model menjadi nama ekspresi
  Live2D, sekaligus mengupas tag itu dari layar saat teks masih mengalir.
- **`src/suara.ts`** — memutar WAV dan mengukur amplitudo per frame.
- **Gerak mulut** tidak memakai penempatan fonem per kata, melainkan amplitudo
  audio yang sedang diputar, dan ditulis pada event `afterMotionUpdate` supaya
  tidak ditimpa animasi idle.

## Verifikasi

```bash
npm run verifikasi        # framing, FPS pada GPU asli, ketahanan setelah resize
node scripts/verify-chat.mjs    # rantai tag -> wajah, pakai server tiruan
node scripts/verify-suara.mjs   # rahang mengikuti audio, pakai fixture WAV asli
node scripts/kontak-ekspresi.mjs  # kontak sheet 8 ekspresi untuk koreksi peta wajah
```

`verify-chat` dan `verify-suara` tidak menyentuh API berbayar — keduanya memakai
stub, sehingga aman dijalankan berulang kali.

## Kredit

Aset dan pustaka pihak ketiga yang dipakai proyek ini, beserta pemiliknya:

- **Model karakter "Haru"** (`haru_greeter_t03`) — bahan gratis resmi dari
  [Live2D Inc.](https://www.live2d.com/en/learn/sample/), tunduk pada
  *Live2D Free Material License Agreement*.
- **Live2D Cubism Core for Web** (`live2dcubismcore.min.js`) — SDK resmi
  [Live2D Inc.](https://www.live2d.com/en/sdk/download/web/), *Cubism SDK License*.
- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)**
  oleh guansss — MIT. Tempat contoh model Haru diambil.
- **[PixiJS](https://github.com/pixijs/pixijs)** — MIT. Renderer WebGL.
- **[@google/genai](https://github.com/googleapis/js-genai)** — Apache-2.0, SDK
  resmi Google untuk Gemini API dan Gemini TTS.
- **[Vite](https://github.com/vitejs/vite)** dan **[TypeScript](https://github.com/microsoft/TypeScript)** — MIT.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori dan diambil ulang dengan `npm run assets`. Untuk karakter publik,
gunakan model milik sendiri.
