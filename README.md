# HuoHuo // AI Vtuber Desktop Companion (Pure Python)

Teman desktop berbasis avatar Live2D HuoHuo (Honkai: Star Rail) yang bicara
Bahasa Indonesia, mengingat Master, dan bereaksi terhadap sentuhan serta suara.

---

## 🚀 Cara Menjalankan

Aplikasi ini **bukan** program tunggal. Ia klien dari dua proses lain yang harus
hidup lebih dulu, jadi urutannya penting:

| # | Perintah | Menyediakan | Alamat |
|---|---|---|---|
| 1 | `.\start_llm.bat` | otak LLM (`llama-server`) | `127.0.0.1:8080` |
| 2 | *(opsional)* `.\start_rvc.bat` | timbre suara HuoHuo (RVC) | `127.0.0.1:8081` |
| 3 | `.\.venv\Scripts\python.exe main.py` | jendela avatar | `127.0.0.1:8990` |

Tanpa langkah 1 balasan jatuh ke mode fallback. Langkah 2 tidak wajib: aplikasi
menyalakan layanan RVC sendiri saat pertama kali butuh (`VTUBER_RVC_AUTO_MULAI`),
dan layanan itu berhenti sendiri saat menganggur supaya RAM lepas. Menjalankan
`start_rvc.bat` tetap berguna kalau ingin suaranya siap seketika.

Mode lain:

```powershell
.\.venv\Scripts\python.exe main.py --cli          # obrolan di terminal, tanpa jendela
.\.venv\Scripts\python.exe main.py --test-voice   # uji Piper -> RVC -> speaker
.\.venv\Scripts\python.exe main.py --voice-in     # jawab satu ujaran dari mikrofon
.\.venv\Scripts\python.exe main.py --voice-loop   # terus mendengarkan mikrofon
```

Konfigurasi: salin `.env.example` menjadi `.env` lalu sesuaikan. Hanya kunci
yang tercantum di `.env.example` yang dibaca kode. **Setelah mengubah `.env`,
restart `start_rvc.bat`** — layanan RVC memuatnya sekali saat start.

## 🧪 Pengujian

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Terakhir terukur 130 lulus (75 unit + 55 e2e). CI menjalankan unit + e2e di
`windows-latest` memakai Microsoft Edge bawaan runner (`channel="msedge"`), jadi
tidak ada unduhan Chromium.

## ⚙️ Batasan perangkat ini (penting sebelum menyentuh performa)

Mesin pengembangan adalah laptop **16 GB RAM dengan Intel Iris Xe — tidak ada
VRAM diskrit**. Konsekuensinya, dan ini sering salah dipahami:

- Build llama.cpp yang terpasang (`tools/llama.cpp`, dari
  `llama-b11822-bin-win-cpu-x64.zip`) adalah **build CPU**: tidak ada
  `ggml-vulkan.dll`, jadi `-ngl 0` pada `start_llm.bat` bukan kelalaian.
- "Memaksimalkan VRAM" tidak tersedia sebagai tuas. Memori GPU di sini adalah
  RAM bersama yang sama; menaruh bobot model di iGPU tidak menambah memori,
  hanya memindahkan komputasi.
- Anggaran nyata: `llama-server` ~4,5 GB + model RVC ~2,4 GB + jendela
  WebView2. Itu sudah melewati sisa RAM kalau browser tetap terbuka, dan
  gejalanya bukan crash, melainkan **paging** — token/detik turun ke ~2,5 dan
  proses bisa kena OOM tanpa pesan.
- Karena itu layanan RVC **mengundurkan diri** setelah menganggur
  (`VTUBER_RVC_IDLE_HAPUS`, bawaan 180 dtk) dan dihidupkan lagi oleh adapter saat
  dibutuhkan. Melepas model dari dalam proses bukan solusinya — itu sudah dicoba
  dan terbukti hanya mengembalikan 0,06 GB; hanya proses yang mati mengembalikan
  seluruh ~2,5 GB.

### Offload GPU (Vulkan) sudah diuji dan KALAH — jangan diulang

Diukur 26 Okt memakai build resmi versi SAMA (`llama-b11822-bin-win-vulkan-x64`)
dengan `-ngl 99`, dibandingkan build CPU pada model, prompt persona asli
(814 token), dan kondisi mesin yang sama:

| metrik | CPU `-ngl 0` | Vulkan `-ngl 99` |
|---|---|---|
| gen tok/s | **5,2 / 4,5 / 5,6** | 4,4 / 3,7 / 4,3 |
| balasan utuh | **31,6 / 17,1 / 12,6 dtk** | 36,2 / 23,7 / 19,6 dtk |
| prompt eval dingin | 35,0 tok/s | **45,1 tok/s** |
| RAM private terkomit | **2.622 MB** | 4.262 MB (+1,6 GB) |

Decode — bagian yang menentukan rasa cepat saat mengobrol — justru melambat
sekitar 20 %, dan bobot di iGPU menambah **1,6 GB memori terkomit** karena
memori Vulkan dipinjam dari 16 GB yang sama. Prefill memang 29 % lebih cepat,
tapi itu hampir tidak pernah terbayar: dengan `keep_alive=-1` sistem prompt
sudah ter-cache (796 dari 814 token), jadi prompt eval berikutnya nyaris gratis.

Kesimpulan: `-ngl 0` pada build CPU adalah konfigurasi terbaik untuk perangkat
ini, dan itu sudah jadi bawaan `start_llm.bat`. Kalau nanti ada versi llama.cpp
yang mau dicoba ulang, tinggal unduh
`llama-b<versi>-bin-win-vulkan-x64.zip` ke `tools\`, lalu
`set VTUBER_LLAMA_DIR=...\tools\llama.cpp-vulkan` — launcher sudah mendukungnya.

## 📂 Struktur

```text
E:\AI Vtuber Project\
  ├── assets/                # Live2D, model Piper, checkpoint RVC (sebagian gitignored)
  ├── model/                 # GGUF untuk llama-server (Qwen3.5-4B, gitignored)
  ├── tools/                 # Skrip diagnostik & TTS (gitignored, kecuali yang dilacak)
  ├── rvc/                   # Layanan konversi suara (jalan di rvc-env, BUKAN .venv)
  │     ├── rvc_service.py   # HTTP :8081, muat/bongkar model, koreksi nada
  │     └── indeks_brute.py  # pencarian tetangga terdekat pengganti faiss
  ├── huohuo/                # Modul Python HuoHuo
  │     ├── core/            # Parser emosi, normalisasi teks, persona, kizuna
  │     ├── profil_suara.py  # SATU sumber kebenaran default parameter suara
  │     ├── adapters/        # Implementasi port: llama, piper, RVC(HTTP), STT, UI
  │     ├── application/     # Use cases (process_interaction, synthesize_voice, ...)
  │     ├── domain/          # Entitas, port, dan service murni
  │     ├── infrastructure/  # Container dependency injection
  │     └── ui/              # Jendela pywebview + server statis + posisi jendela
  ├── silver_wolf_memory/    # Memori karakter (nama folder warisan, isinya HuoHuo)
  ├── tests/                 # unit/ dan e2e/ (Playwright)
  ├── .env.example           # Daftar kunci yang benar-benar dibaca kode
  ├── main.py                # Titik masuk
  └── pyproject.toml         # Konfigurasi paket Python
```

Suara TIDAK lagi diproses di dalam aplikasi. Rantai lamanya (`huohuo.voice`,
pipeline in-process) sudah dihapus dan digantikan layanan HTTP di `rvc/`,
karena `rvc-python` membutuhkan Python 3.10 + fairseq yang tidak bisa hidup
berdampingan dengan dependensi aplikasi utama.
