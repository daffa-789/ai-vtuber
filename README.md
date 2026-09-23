# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer, loop chat, ekspresi, text-to-speech, dan input mikrofon sudah
berjalan. Memori jangka panjang masih dalam pengerjaan.

## Menjalankan

Prasyarat: Node.js 20.6+ (butuh flag `--env-file-if-exists`).

```bash
npm install
npm run assets        # unduh model Live2D + salin aset VAD (tidak ikut ke git, lihat Lisensi)
cp .env.example .env  # lalu isi GEMINI_API_KEY
npm run server        # sidecar di 127.0.0.1:8787
npm run dev           # buka http://localhost:5173
```

Di halaman, klik **nyalakan** pada baris Mikrofon sekali — browser meminta izin mic,
dan setelah itu cukup bicara. Mengetik tetap bisa dipakai berdampingan.

## Cara kerja

```
mikrofon -> VAD Silero (lokal) -> WAV -> STT  -\
                                                >-- teks --> Gemini Flash --> teks + [tag]
papan ketik ----------------------------------/                                    |
                                                                              ekspresi Live2D
                                                              Gemini TTS -> WAV 24kHz
                                                                       |
                                                        AnalyserNode -> ParamMouthOpenY
```

- **`server/index.mjs`** — sidecar Node. Satu-satunya pemegang API key, hanya
  listen di `127.0.0.1`, dan membungkus PCM mentah dari Gemini menjadi WAV.
  Sudah dilengkapi percobaan ulang berjenjang untuk 503/429.
- **`persona.md`** — sifat dan gaya bicara karakter. Ini konfigurasi, bukan model
  yang dilatih: diedit langsung, dan selalu dikirim sebagai system instruction.
- **`src/ekspresi.ts`** — menerjemahkan tag dari model menjadi nama ekspresi
  Live2D, sekaligus mengupas tag itu dari layar saat teks masih mengalir.
- **`src/mikrofon.ts`** — VAD berjalan di mesin ini; hanya potongan yang terdeteksi
  sebagai bicara yang dikirim untuk disalin.
- **`src/suara.ts`** — memutar WAV dan mengukur amplitudo per frame.
- **Setengah dupleks** — mikrofon ditahan selama dia bicara, dan sengaja tidak
  menyerahkan audio yang terpotong oleh penahanan itu, supaya dia tidak menyalin
  suaranya sendiri.
- **Gerak mulut** tidak memakai penempatan fonem per kata, melainkan amplitudo
  audio yang sedang diputar, dan ditulis pada event `afterMotionUpdate` supaya
  tidak ditimpa animasi idle.

## Batas kuota yang nyata

Dengan kunci API tingkat gratis, terukur langsung dari jawaban server:

| Model | Kepentingan | Batas terukur |
|---|---|---|
| `gemini-3.5-transcribe` | penyalin suara | **3 permintaan per menit** |
| `gemini-3.5-flash` | otak percakapan | lolos, tapi pernah 503 "high demand" |
| `gemini-2.5-flash-preview-tts` | suara | lolos, 8-31 detik per kalimat |

Angka itu membuat mode "selalu mendengarkan" tidak nyaman dipakai sebelum akunmu
naik tingkat. Ganti model lewat `VTUBER_STT_MODEL` di `.env` jika mentok.

## Verifikasi

```bash
node scripts/verify-render.mjs      # framing, FPS pada GPU asli, ketahanan setelah resize
node scripts/verify-chat.mjs        # rantai tag -> wajah
node scripts/verify-suara.mjs       # rahang mengikuti audio
node scripts/verify-mikrofon.mjs    # mic -> VAD -> STT -> balasan -> wajah
node scripts/kontak-ekspresi.mjs    # kontak sheet 8 ekspresi untuk koreksi peta wajah
```

Empat tes pertama memakai server tiruan atau fixture, jadi **tidak menyentuh API**
dan aman dijalankan berulang kali. Hanya `kontak-ekspresi` yang membuka jendela.
`verify-mikrofon` memakai mikrofon palsu Chromium yang memutar `test/fixture-suara.wav`,
sehingga jalur mic teruji tanpa merekam apa pun.

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
- **[vad-web](https://github.com/ricky0123/vad)** oleh ricky0123 — MIT. Pembungkus
  deteksi bicara untuk browser.
- **[Silero VAD](https://github.com/snakers4/silero-vad)** — MIT. Model deteksi
  suara yang benar-benar berjalan di mesinmu.
- **[ONNX Runtime Web](https://github.com/microsoft/onnxruntime)** — MIT.
- **[@google/genai](https://github.com/googleapis/js-genai)** — Apache-2.0, SDK
  resmi Google untuk Gemini API, Gemini TTS, dan penyalinan suara.
- **[Vite](https://github.com/vitejs/vite)** dan **[TypeScript](https://github.com/microsoft/TypeScript)** — MIT.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori dan diambil ulang dengan `npm run assets`. Untuk karakter publik,
gunakan model milik sendiri.
