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
| 2 | `.\start_rvc.bat` | timbre suara HuoHuo (RVC) | `127.0.0.1:8081` |
| 3 | `.\.venv\Scripts\python.exe main.py` | jendela avatar | `127.0.0.1:8990` |

Tanpa langkah 1 balasan jatuh ke mode fallback; tanpa langkah 2 suara masih
keluar tapi jadi suara Piper generik, bukan HuoHuo.

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

Terakhir terukur 123 lulus (68 unit + 55 e2e). CI menjalankan unit + e2e di
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
- Karena itu model RVC dimuat malas dan **dibongkar otomatis** setelah
  menganggur (`VTUBER_RVC_IDLE_HAPUS`, bawaan 180 dtk) supaya RAM kembali ke
  sistem saat tidak dipakai mengobrol.

### Kalau mau mencoba offload GPU (belum terukur)

`start_llm.bat` sudah bisa diarahkan ke build lain tanpa disunting:

```powershell
# unduh llama-b<ver>-bin-win-vulkan-x64.zip, ekstrak ke tools\llama.cpp-vulkan
set VTUBER_LLAMA_DIR=E:\AI Vtuber Project\tools\llama.cpp-vulkan
set VTUBER_LLAMA_NGL=99
.\start_llm.bat
```

Jalankan dengan `-ngl 0` lebih dulu untuk memastikan build-nya hidup, baru
naikkan `VTUBER_LLAMA_NGL`. Yang diawasi: `Vulkan0` harus muncul di log
`--list-devices`, dan RAM bebas tidak boleh jatuh di bawah ~1 GB. Kalau muncul
`OutOfDeviceMemory` atau balasan malah melambat, kembalikan ke build CPU dengan
mengosongkan `VTUBER_LLAMA_DIR` — tidak ada yang perlu dikutak-atik di repo.

Belum pernah diukur pada mesin ini, jadi jangan anggap lebih cepat.

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
