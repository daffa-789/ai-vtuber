# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer, loop chat, ekspresi, text-to-speech, input mikrofon, dan memori
jangka panjang sudah berjalan. Memory karakter ditulis sebagai catatan Markdown di
vault Obsidian, jadi bisa dibaca dan disunting langsung.

## Menjalankan

Prasyarat: Node.js 20.6+ (butuh flag `--env-file-if-exists`).

```bash
npm install
npm run assets        # unduh Cubism core + contoh model Haru + salin aset VAD
npm run pasang-model  # pasang model karakter dari New Model/魔女 (lihat Model karakter)
cp .env.example .env  # lalu isi GEMINI_API_KEY
npm run server        # sidecar di 127.0.0.1:8787
npm run dev           # buka http://localhost:5173
```

Di halaman, klik **nyalakan** pada baris Mikrofon sekali — browser meminta izin mic,
dan setelah itu cukup bicara. Mengetik tetap bisa dipakai berdampingan.

## Model karakter

Karakternya model Live2D Cubism 4 (279 parameter, 617 art mesh, tekstur 8192),
dipasang dari folder `New Model/魔女/` ke `public/models/penyihir/` dengan nama
berkas Indonesia:

```
public/models/penyihir/
  penyihir.model3.json      daftar ekspresi + motion, ini yang dibaca aplikasi
  penyihir.moc3             geometri yang sudah dikompilasi (jangan disunting)
  penyihir.physics3.json    rambut, baju, perhiasan bergoyang
  penyihir.cdi3.json        label parameter untuk editor — sudah dialihbahasakan
  tekstur/texture_00.png    8192x8192
  tekstur/texture_01.png    4096x8192
  ekspresi/*.exp3.json      sembilan wajah, namanya sama dengan tag di persona.md
  gerakan/sedih-melambai.motion3.json
```

Sembilan ekspresi itu saya susun sendiri dari lapisan parameter aslinya: model ini
datang dengan 13 berkas ekspresi bernama singkatan pinyin Mandarin, dan sebagian
besarnya bukan wajah melainkan aksesori. Hasil pembacaan potret (`.shots/lembar-f.png`,
`.shots/lembar-g.png`), tersimpan juga sebagai label di `penyihir.cdi3.json`:

| Singkatan | Arti sebenarnya | Dipakai untuk |
|---|---|---|
| `ku` | mata berair + alis naik | `sedih` |
| `sq` | cemberut | `sebal` |
| `h` | setetes keringat + bayangan muram di mata | `bingung` |
| `xx` / `x` | pupil bintang / pupil hati | `semangat` / `goda` |
| `mz` `fz` `yj` `zs1` `zs2` `cw` `hdj` | topi, tongkat sihir, kacamata, memamerkan barang, hantu kecil, tangan memeluk | tidak dipakai chat; masih ada di berkas sumber |

`netral`, `senyum`, `kaget`, dan `lelah` tidak punya lapisan sendiri di model aslinya,
jadi keempatnya saya rakit dari parameter dasar (`ParamEyeLOpen`, `ParamBrowLY`,
`ParamMouthForm`, `Param50`). Rentang tiap parameter dibaca dari model yang sedang
berjalan, bukan ditebak.

Napass, goyang kepala, dan kedip tidak butuh berkas motion — pustaka `pixi-live2d-display`
sudah menyetelnya sendiri, dan itu alasan `gerakan/` sengaja tidak dipasang sebagai Idle:
kalau ada motion yang jalan, pustaka justru mematikan kedip otomatisnya.

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
- **`server/obsidian.mjs`** — menulis/membaca catatan karakter ke vault Obsidian lewat
  Local REST API; token diambil dari `~/.qoder/settings.json`, bukan dari berkas di repo.
- **`server/memori.mjs`** — kebijakan memori: apa yang masuk prompt, bagaimana mood
  bergeser dari tag ekspresi, dan kapan fakta baru diekstrak.
- **Setengah dupleks** — mikrofon ditahan selama dia bicara, dan sengaja tidak
  menyerahkan audio yang terpotong oleh penahanan itu, supaya dia tidak menyalin
  suaranya sendiri.
- **Gerak mulut** tidak memakai penempatan fonem per kata, melainkan amplitudo
  audio yang sedang diputar, dan ditulis pada event `afterMotionUpdate` supaya
  tidak ditimpa animasi idle.

## Memori karakter

Dia tidak dilatih. Yang membuatnya terasa "ingat" adalah tiga catatan Markdown di
vault, yang dibaca ulang dan disuntikkan ke system prompt setiap kali menjawab:

```
Qoder Memory/Project/Desktop AI VTUBER/Karakter/
  Fakta.md              daftar hal yang dia ingat tentangmu
  Mood.md               valensi, energi, afinitas, jumlah pertukaran
  Riwayat/2026-09-23.md percakapan hari itu, satu baris per tukaran
```

Semuanya bisa kamu buka dan sunting langsung di Obsidian. Menghapus satu baris di
`Fakta.md` berarti dia benar-benar lupa hal itu pada balasan berikutnya.

Alur penulisannya: setiap balasan selesai → tag ekspresinya dibaca → mood bergeser
dan riwayat harian bertambah. Ekstraksi fakta memakai model dan hanya berjalan tiap
`VTUBER_JEDA_FAKTA` pertukaran, karena ia menambah satu panggilan API.

Mood bergeser dari tag yang dia pakai sendiri, tanpa panggilan tambahan: `[semangat]`
menaikkan valensi, `[sedih]` dan `[sebal]` menurunkannya, dan setiap pertukaran
menaikkan afinitas sedikit. Kalau valensinya jatuh, system prompt berikutnya berisi
"kamu lagi agak berat hari ini" — itu sebabnya nadanya berubah lintas sesi.

Kalau Obsidian sedang tidak jalan, memori dilewati dengan satu baris peringatan dan
percakapan tetap berjalan.

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

- **Model karakter "Penyihir"** (`public/models/penyihir`) — model Cubism 4
  buatan pihak ketiga yang tidak dibuat proyek ini; nama folder aslinya `魔女`
  ("penyihir" dalam bahasa Mandarin). Berkasnya sengaja tidak diunduh lewat skrip
  maupun diunggah ke repositori — hanya dipasang dari folder `New Model/` di mesin
  ini lewat `npm run pasang-model`. Cek ulang lisensi pembuatnya sebelum dipakai
  untuk siaran publik.
- **Contoh model Haru** (`haru_greeter_t03`) — bahan gratis resmi dari
  [Live2D Inc.](https://www.live2d.com/en/learn/sample/), tunduk pada
  *Live2D Free Material License Agreement*. Diunduh `npm run assets`, tidak lagi
  dipakai aplikasi tapi tetap tersedia untuk dibandingkan.
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
