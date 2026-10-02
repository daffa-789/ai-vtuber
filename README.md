# Silver Wolf

Kompanion **desktop** AI — karakter Live2D yang hidup di layar, bicara dengan suara
sendiri, dan mengingat percakapan.

Aplikasi ini **desktop-only**: tidak ada lagi jalur peramban. UI (Vue 3 + Live2D)
hanya dihidangkan di dalam jendela Electron, dan seluruh logika server — konfigurasi,
persona, memori, inferensi, penyajian aset — berjalan di **sidecar Go** yang
dikompilasi menjadi satu binary.

```
Electron (jendela, tray, hotkey)  ──spawn──▶  silverwolf-sidecar.exe (Go)
        ▲ renderer Vue + Live2D                    ├─ baca .env
        └───────── HTTP 127.0.0.1 ─────────────────┤─ jalankan llama-server
                                                   ├─ susun prompt + memori
                                                   └─ sajikan /api/* dan aset
```

> **Status: sidecar Node sudah diganti Go.** Paket TypeScript `server-runtime`,
> `server-shared`, dan `core-agent` dihapus; `apps/server` (sidecar Node) dihapus;
> `apps/stage-web` dipindah menjadi `apps/stage-tamagotchi/renderer`.

## Struktur

```
apps/
  stage-tamagotchi/       Electron desktop — jendela, tray, hotkey
    src/main/             Proses utama: menjalankan sidecar Go, baca port-nya
    src/preload/          Jembatan konteks-terisolasi
    renderer/             Vue 3 + UnoCSS + Live2D (satu-satunya wujud UI)
sidecar/                  Sidecar Go (modul github.com/daffa-789/ai-vtuber/sidecar)
  internal/config/        Parser `.env` + koerser bertipe + penemuan akar
  internal/character/     Persona, perakitan prompt, mood, tag wajah, vault memori
  internal/agent/         Orkestrasi chat + penyimpanan memori
  internal/inference/     Provider OpenAI-compatible (llama-server / Ollama) + stub
  internal/llama/         Pemilihan model GGUF + pengelola proses llama-server
  internal/server/        HTTP: /api/health, /api/chat (aliran), berkas statis
packages/                 Paket TypeScript yang masih dipakai renderer/skrip
  core-config/            Skema `.env` + koerser (dipakai skrip pipelines-audio)
  core-character/         Persona, prompt, mood, tag wajah, vault memori
  pipelines-audio/        Rantai suara: piper → rvc, cache, WAV
  provider-inference/     Antarmuka Brain / Ears / Mouth / Body
  stage-ui/               Komponen Vue + store Pinia
  stage-ui-live2d/        Renderer Live2D + mesin wajah
  audio/                  Tangkap mic + VAD + pemutar
```

Scope paket: `@silverwolf/*`. Paket internal dikonsumsi **sebagai sumber TS** (tanpa
langkah build) — Vite/tsx men-transpile langsung.

## Menjalankan

Butuh **Go 1.24+** dan **Node 20+**.

```bash
npm install

npm run sidecar:build   # -> bin/silverwolf-sidecar.exe
npm run dev             # Electron + renderer (dev server Vite)
npm run build:win       # installer NSIS

npm run typecheck
npm test                # vitest (TypeScript) + go test (Go)
```

Skrip yang tersedia:

| Skrip | Isi |
|---|---|
| `sidecar:build` | `go build` sidecar menjadi `bin/silverwolf-sidecar.exe` |
| `sidecar:test` | `go test ./...` di dalam `sidecar/` |
| `dev` / `dev:tamagotchi` | Electron dalam mode pengembangan |
| `build` | `sidecar:build` lalu bundel `out/` (main, preload, renderer) |
| `build:win` | `build` lalu installer NSIS |
| `test:ts` | Hanya suite TypeScript |

Proses utama Electron menjalankan sidecar dengan `-port 0`, lalu membaca baris
`port=<angka>` yang dicetak sidecar ke stdout — jadi tidak ada port yang ditebak
atau bentrok dengan sidecar yang sudah berjalan.

Untuk menguji tanpa model besar, isi `VTUBER_STUB=ya` (atau biarkan aplikasi
terkemas tanpa model GGUF: ia otomatis masuk mode tiruan).

> **Catatan lingkungan (Windows terkunci):** install dependency memakai `ignore-scripts=true`
> karena sebagian postinstall memanggil `wmic.exe` yang diblokir kebijakan keamanan mesin.
> Binary esbuild/turbo tetap tersedia lewat paket platform. **Electron** butuh unduhan
> binary-nya secara eksplisit saat instalasi.
>
> Skrip root memakai npm, bukan `turbo run`, karena turbo tidak bisa spawn proses anak
> di lingkungan ini (`ERROR_PIPE_BUSY`). `turbo.json` tetap ada dan varian `npm run turbo:*`
> disediakan untuk CI / mesin normal.

## Model & aset

Semua model berukuran besar **tidak ikut git**. Tata letak:

| Lokasi | Isi | Catatan |
|---|---|---|
| `assets/` | Rumah baru aset: `voices/`, `encoders/`, `piper/`, `whisper/`, `llm/` | gitignored |
| `public/models/silverwolf/` | Model Live2D (`.moc3`, tekstur, ekspresi, gerakan) | gitignored — lisensi Live2D |
| `public/live2dcubismcore.min.js` | Cubism Core | gitignored — lisensi Live2D |
| `aset/suara/` | Piper ONNX, checkpoint RVC, hubert/rmvpe, whisper | gitignored |
| `model/` | LLM GGUF (MiniCPM5-2B Q4_K_M, 1 Okt 2026) | gitignored |
| `bin/llama/` | llama.cpp build Vulkan (`llama-server.exe`) | gitignored |
| `bin/` | Hasil `go build` sidecar (`silverwolf-sidecar.exe`) | gitignored |
| `silver_wolf_memory/` | Persona + memori karakter | gitignored — **berisi fakta pribadi** |

### Ganti model GGUF

Model dipilih lewat `VTUBER_LOCAL_MODEL_PATH`. Dua flag llama-server **wajib**
untuk MiniCPM5 (dan untuk varian *thinking* Qwen3):

| Flag | Kunci `.env` | Alasan |
|---|---|---|
| `--min-p 0` | `VTUBER_LOCAL_MIN_P=0` | bawaan llama.cpp `0,05` membuat MiniCPM5 mengulang kalimat |
| `-rea off` | `VTUBER_LOCAL_REASONING=off` | mode berpikir mengawali balasan dengan `<think>`, merusak pembacaan tag emosi |

Keduanya sudah di-default-kan di `sidecar/internal/config` dan di `.env`. Bila ingin
mengaktifkan mode berpikir untuk tugas penalaran, setel `VTUBER_LOCAL_REASONING=on`
**dan** naikkan `max_tokens` di `sidecar/internal/server/server.go` — batas 512 saat ini
akan habis di dalam blok `<think>`.

> MiniCPM5 tercatat hanya untuk EN + ZH. Persona dan prompt proyek ini berbahasa
> Indonesia, jadi kualitasnya di bawah Llama-3.2-3B. Qwen3 disiapkan sebagai
> pembanding.

### Konversi model RVC

`rvc-onnx-web` mengubah checkpoint PyTorch `.pth` menjadi ONNX, murni TypeScript:

```bash
npm run voice:convert  # .pth → assets/voices/silverwolf/model.onnx
npm run spike:rvc      # periksa nama/dimensi tensor semua model ONNX
```

Peringatan: hanya **RVC v2**; korelasi audio akhir **~78%** karena ada operator
`RandomNormalLike` yang sengaja acak — timbre yang sedikit berbeda itu normal.
Berkas `.index` FAISS tidak ditangani oleh konverter ini.

**Fakta terverifikasi** (dari `npm run spike:rvc`):

| Model | Input | Output |
|---|---|---|
| Generator RVC (105 MB) | `phone`, `phone_lengths`, `pitch`, `nsff0`, `sid` | `audio`, `sr` (=40000) |
| RMVPE f0 (345 MB) | `input` (mel spectrogram 16 kHz) | `output` |

Masih kurang: **`vec-768-layer-12.onnx`** (ContentVec). RVC v2 memerlukan
ContentVec 768-dim layer-12 — **bukan** `hubert-base-ls960`.

## Peta jalan

| Fase | Isi | Status |
|---|---|---|
| 0 | Scaffold TypeScript (npm, turbo, tsconfig, uno, vitest) | **selesai** |
| 1 | Inti sidecar — sekarang Go (`sidecar/`) | **selesai** |
| 2 | Stage MVP (Vue 3 + Live2D, chat + TTS + mic) | **selesai** |
| 3 | Rantai TTS (piper ONNX + espeak-ng WASM + cache) | **selesai** |
| 4 | Pipeline RVC (ContentVec → F0 → generator, onnxruntime-web) | **selesai** — aset model diperlukan |
| 5 | Aplikasi Electron Windows (tray, hotkey, installer NSIS) | **selesai** |
| 6 | Fokus desktop-only: jalur peramban dibuang, sidecar pindah ke Go | **selesai** |
| 7 | Verifikasi paritas + penutupan | |

## Cadangan

`_cadangan/` menyimpan arsip runtime Python lama (riwayat git lengkap, berkas sumber, dan
skrip `var/`) dari saat migrasi. Boleh dihapus.

## Lisensi & penggunaan

Model Live2D dan Cubism Core tunduk pada lisensi Live2D Inc. dan tidak boleh diedarkan
sebagai berkas lepas. Teknologi kloning suara hanya untuk proyek kreatif dengan izin —
jangan untuk peniruan identitas, penipuan, atau pelecehan.

## Desktop Windows, suara, dan mikrofon

Aplikasi desktop berada di `apps/stage-tamagotchi`. Ia menyediakan jendela native,
tray, close-to-tray, dan hotkey global **Ctrl+Shift+S**. Data pribadi dan model tidak
ditanam di installer. Pada Windows, klik tray → **Buka folder model & konfigurasi**,
lalu isi tata letak berikut di folder tersebut:

```text
.env
assets/
  piper/id_ID-news_tts-medium.onnx
  piper/id_ID-news_tts-medium.onnx.json
  encoders/vec-768-layer-12.onnx
  voices/silverwolf/model.onnx
  live2d/live2dcubismcore.min.js
  live2d/silverwolf/silverwolf.model3.json (+ tekstur/ekspresi/gerakan)
model/MiniCPM5-2B-Q4_K_M.gguf
bin/llama/llama-server.exe (+ DLL Vulkan)
silver_wolf_memory/persona.md
```

- **STT:** Whisper ONNX melalui `@huggingface/transformers`; model diunduh dan di-cache
  saat pemakaian pertama, lalu inferensi berjalan lokal.
- **TTS:** Piper + eSpeak-ng WASM melalui `@mintplex-labs/piper-tts-web`, memakai model
  Indonesia lokal di atas.
- **RVC:** ContentVec 768 + ekstraksi F0 lokal + generator RVC v2 melalui
  `onnxruntime-web`. Bila model RVC tidak ada/gagal, audio Piper tetap diputar.

Sidecar Go ikut terpasang di `resources/bin/silverwolf-sidecar.exe`; bila binary itu
hilang, proses utama menolak mulai dengan pesan yang menyuruh menjalankan
`npm run sidecar:build`.

```bash
npm run assets:verify
npm run dev
npm run build:win
```

Perintah terakhir menghasilkan `apps/stage-tamagotchi/release/Silver-Wolf-Setup-0.1.0.exe`.
Workflow `.github/workflows/build-windows.yml` memasang Go, mengompilasi sidecar, lalu
membangun installer pada runner Windows dan mengunggahnya sebagai artifact.
