# Silver Wolf // AI Vtuber Desktop Companion (Pure Python)

Proyek ini telah dimigrasikan sepenuhnya menjadi ekosistem **Python murni** yang menggabungkan:
1. **Logika Inti Karakter & Memori (`silverwolf.core`)**:
   - `EmotionParser`: Mendeteksi tag emosi (`[senyum]`, `[goda]`, `[kaget]`, dll.) dan membersihkan teks.
   - `TeksUcapan`: Menghilangkan format Markdown agar mesin TTS tidak mengucapkan tanda baca seperti "bintang".
   - `PersonaComposer`: Membangun system prompt dengan injeksi aturan cemburu, fakta Master, dan suasana hati.
   - `KizunaEngine`: Menghitung poin ikatan, level keintiman, streak interaksi, dan riwayat obrolan (`silver_wolf_memory/kizuna/silverwolf_kizuna_v1.json`).
   - `CharacterVault`: Membaca dan menyimpan fakta Master, suasana hati (`Mood.md`), serta riwayat percakapan harian.
2. **Pipeline Suara In-Memory (`silverwolf.voice`)**:
   - Piper TTS Bahasa Indonesia (`assets/piper/id_ID-news_tts-medium.onnx`) menghasilkan suara jernih.
   - RVC v2 (`SilverWolfJP`) mengubah timbre suara menjadi Silver Wolf.
   - Pemutaran audio langsung dari memori RAM (in-memory) tanpa penumpukan berkas sampah di disk.
3. **Supervisor Inferensi LLM (`silverwolf.inference`)**:
   - Terhubung ke `llama-server` lokal (model Gemma 4 E4B GGUF 5.3 GB) via API kompatibel OpenAI.
   - Mode fallback in-character Silver Wolf otomatis bila model lokal sedang offline.
4. **Desktop Live2D Companion UI (`silverwolf.ui`)**:
   - Jendela transparan frameless berbasis Microsoft Edge WebView2 (`pywebview`).
   - Model Live2D Cubism Web (`assets/live2d/silverwolf/silverwolf.model3.json`) dengan:
     - Pelacakan tatapan mata & kepala mengikuti kursor mouse.
     - 9 ekspresi wajah (`senyum`, `goda`, `sebal`, `kaget`, `bingung`, `lelah`, `semangat`, `sedih`, `netral`).
     - Sinkronisasi gerak bibir (lip-sync) secara realtime saat Silver Wolf berbicara.
     - Balon dialog dan panel chat input interaktif di bagian bawah.

---

## 🚀 Cara Menjalankan

### 1. Menjalankan Antarmuka Desktop Companion (Live2D GUI)
```powershell
.\.venv\Scripts\python.exe main.py
```

### 2. Menjalankan Mode Percakapan Terminal (CLI)
Jika Anda hanya ingin mengobrol via terminal tanpa jendela grafis:
```powershell
.\.venv\Scripts\python.exe main.py --cli
```

### 3. Menguji Sintesis Suara
Untuk menguji coba sintesis teks ke suara secara langsung:
```powershell
.\.venv\Scripts\python.exe main.py --test-voice
```

---

## 🧪 Menjalankan Pengujian Otomatis

Seluruh modul inti diverifikasi dengan unit test `pytest`:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 📂 Struktur Berkas Proyek

```text
E:\AI Vtuber Project\
  ├── assets/                # Aset Live2D, model Piper TTS, dan checkpoint RVC
  ├── model/                 # Model Gemma-4-E4B GGUF (5.3 GB)
  ├── silver_wolf_memory/    # Memori karakter (fakta, mood, persona, dan data kizuna)
  ├── silverwolf/            # Modul Python Silver Wolf
  │     ├── core/            # Parser emosi, normalisasi teks, persona, dan kizuna
  │     ├── voice/           # Piper TTS, RVC, dan in-memory audio player
  │     ├── inference/       # Klien llama-server dan fallback mode
  │     └── ui/              # Desktop companion WebView2 dan static WebGL Live2D
  ├── tests/                 # Unit test otomatis (24 tests lulus)
  ├── tools/                 # Skrip pembantu diagnostik & TTS
  ├── .env                   # Pengaturan parameter suara dan inferensi
  ├── main.py                # Titik masuk utama aplikasi
  ├── pyproject.toml         # Konfigurasi paket Python
  └── requirements.txt       # Daftar dependensi Python
```
