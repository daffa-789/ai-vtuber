# Silver Wolf

Kompanion desktop AI — karakter Live2D yang hidup di layar, bicara dengan suara sendiri,
dan mengingat percakapan. Monorepo TypeScript dengan arsitektur mengikuti
[Project AIRI](https://github.com/moeru-ai/airi) (pnpm workspaces + Turborepo + Vue 3 + Vite + Electron).

> **Status: migrasi berjalan.** Runtime Python/Flask lama sudah dihapus; app TypeScript
> baru sampai Fase 0 (scaffold). Belum ada endpoint yang berfungsi. Lihat "Peta jalan" di bawah.

## Struktur

```
apps/
  stage-web/          Vite + Vue 3 + UnoCSS — halaman karakter (browser)
  stage-tamagotchi/   Electron — jendela pet transparan, always-on-top, tembus klik
  server/             Sidecar Node — LLM (llama.cpp) + STT (whisper)
packages/
  core-config/        Skema .env + koerser (port dari konfigurasi lama)
  core-character/     Persona, perakitan prompt, mood, tag wajah, vault memori
  core-agent/         Orkestrasi chat + provider LLM
  pipelines-audio/    Rantai suara: piper → rvc, cache, WAV
  provider-inference/ Antarmuka Brain / Ears / Mouth / Body
  stage-ui/           Komponen Vue + store Pinia
  stage-ui-live2d/    Renderer Live2D + mesin wajah
  audio/              Tangkap mic + VAD + pemutar
  server-shared/      Tipe protokol sidecar
  server-runtime/     Inti sidecar
```

Scope paket: `@silverwolf/*`. Paket internal dikonsumsi **sebagai sumber TS** (tanpa langkah build) —
Vite/tsx men-transpile langsung.

## Menjalankan

```bash
corepack enable
corepack prepare pnpm@9.15.0 --activate
pnpm install

pnpm typecheck   # tsc --noEmit di semua paket
pnpm test        # vitest di semua paket
pnpm dev         # stage-web (Vite)
pnpm dev:tamagotchi
```

> **Catatan lingkungan (Windows terkunci):** `pnpm install` memakai `ignore-scripts=true`
> karena sebagian postinstall memanggil `wmic.exe` yang diblokir kebijakan keamanan mesin.
> Binary esbuild/turbo tetap tersedia lewat paket platform. **Electron** butuh unduhan
> binary-nya secara eksplisit saat Fase 5.
>
> Skrip root memakai `pnpm -r`, bukan `turbo run`, karena turbo tidak bisa spawn proses anak
> di lingkungan ini (`ERROR_PIPE_BUSY`). `turbo.json` tetap ada dan varian `pnpm turbo:*`
> disediakan untuk CI / mesin normal.

## Model & aset

Semua model berukuran besar **tidak ikut git**. Tata letak:

| Lokasi | Isi | Catatan |
|---|---|---|
| `assets/` | Rumah baru aset: `voices/`, `encoders/`, `piper/`, `whisper/`, `llm/` | gitignored |
| `public/models/silverwolf/` | Model Live2D (`.moc3`, tekstur, ekspresi, gerakan) | gitignored — lisensi Live2D |
| `public/live2dcubismcore.min.js` | Cubism Core | gitignored — lisensi Live2D |
| `aset/suara/` | Piper ONNX, checkpoint RVC, hubert/rmvpe, whisper | gitignored |
| `model/` | LLM GGUF (Llama-3.2-3B-Instruct Q4_K_M) | gitignored |
| `bin/llama/` | llama.cpp build Vulkan (`llama-server.exe`) | gitignored |
| `silver_wolf_memory/` | Persona + memori karakter | gitignored — **berisi fakta pribadi** |

### Konversi model RVC

`rvc-onnx-web` mengubah checkpoint PyTorch `.pth` menjadi ONNX, murni TypeScript:

```bash
pnpm voice:convert    # .pth → assets/voices/silverwolf/model.onnx
pnpm spike:rvc        # periksa nama/dimensi tensor semua model ONNX
```

Peringatan: hanya **RVC v2**; korelasi audio akhir **~78%** karena ada operator
`RandomNormalLike` yang sengaja acak — timbre yang sedikit berbeda itu normal.
Berkas `.index` FAISS tidak ditangani oleh konverter ini.

**Fakta terverifikasi** (dari `pnpm spike:rvc`):

| Model | Input | Output |
|---|---|---|
| Generator RVC (105 MB) | `phone`, `phone_lengths`, `pitch`, `nsff0`, `sid` | `audio`, `sr` (=40000) |
| RMVPE f0 (345 MB) | `input` (mel spectrogram 16 kHz) | `output` |

Masih kurang untuk Fase 4: **`vec-768-layer-12.onnx`** (ContentVec). RVC v2 memerlukan
ContentVec 768-dim layer-12 — **bukan** `hubert-base-ls960`.

## Peta jalan

| Fase | Isi | Status |
|---|---|---|
| 0 | Scaffold monorepo (pnpm, turbo, tsconfig, uno, vitest) | **selesai** |
| 1 | Inti sidecar Node (`core-config`, `core-character`, `core-agent`, `apps/server`) | berikutnya |
| 2 | Stage web MVP (Vue 3 + Live2D, chat + TTS + mic) | |
| 3 | Rantai TTS di browser (piper ONNX + espeak-ng WASM + cache) | |
| 4 | Pipeline RVC di browser (ContentVec → RMVPE → generator, onnxruntime-web) | |
| 5 | Jendela pet Electron (transparan, tray, hotkey, tembus klik) | |
| 6 | Verifikasi paritas + penutupan | |

Rencana lengkap: `~/.workbuddy-ai/plans/` (dokumen rencana migrasi).

## Cadangan

`_cadangan/` menyimpan arsip runtime Python lama (riwayat git lengkap, berkas sumber, dan
skrip `var/`) dari saat migrasi. Boleh dihapus setelah Fase 2 terbukti stabil.

## Lisensi & penggunaan

Model Live2D dan Cubism Core tunduk pada lisensi Live2D Inc. dan tidak boleh diedarkan
sebagai berkas lepas. Teknologi kloning suara hanya untuk proyek kreatif dengan izin —
jangan untuk peniruan identitas, penipuan, atau pelecehan.
