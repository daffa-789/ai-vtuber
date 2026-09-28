"""Konfigurasi sisi server Python.

Baca dari environment dulu, baru dari berkas .env di akar proyek.
Kunci yang dibaca di sini adalah VTUBER_*; seluruh kunci VITE_* di .env
milik frontend dan tidak menyentuh sisi server.
"""

from __future__ import annotations

import os
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
AKAR_PERSONA = AKAR / "persona.md"
HOME = Path.home()


def _bersih(nilai: str) -> str:
    nilai = nilai.strip()
    if len(nilai) >= 2 and nilai[0] == nilai[-1] and nilai[0] in "\"'":
        return nilai[1:-1]
    return nilai


def _potong_komentar(nilai: str) -> str:
    """Buang komentar sebaris: `VTUBER_VULKAN_NGL=99  # semua lapis`.

    Parser ini dulunya tidak mengenal komentar sebaris, jadi nilai itu terbaca
    utuh "99  # semua lapis" -> `angka()` melempar ValueError -> diam-diam jatuh
    ke bawaan. Persis kelas bug "resep diabaikan tanpa pesan" yang sudah pernah
    terjadi di proyek ini. Aturan yang dipakai sama dengan dotenv: hanya `#` yang
    didahului spasi yang jadi komentar, supaya warna (`#fff`) dan resep param
    tetap utuh; nilai yang dikutip dipotong sampai kutip penutupnya saja.
    """
    mentah = nilai.strip()
    if len(mentah) >= 2 and mentah[0] in "\"'":
        kutip = mentah[0]
        akhir = mentah.find(kutip, 1)
        return mentah[1:akhir] if akhir > 0 else mentah[1:]
    for i, tanda in enumerate(mentah):
        if tanda == "#" and i > 0 and mentah[i - 1] in " \t":
            return mentah[:i].rstrip()
    return mentah


def baca_env(jalur: Path) -> dict[str, str]:
    """Parser .env minimal: `KUNCI=nilai`, `#` komentar, spasi di sekitar `=`.

    Berkas .env saja yang boleh berkomentar sebaris; nilai dari environment
    (`nilai()` di bawah) tidak dipotong, karena di sana `#` bisa memang bagian
    dari nilainya.
    """
    if not jalur.exists():
        return {}
    hasil: dict[str, str] = {}
    for baris in jalur.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, _, nilai = baris.partition("=")
        hasil[kunci.strip()] = _potong_komentar(nilai)
    return hasil


_ENV = baca_env(AKAR / ".env")


def nilai(kunci: str, bawaan: str = "") -> str:
    from_environ = os.environ.get(kunci)
    if from_environ is not None and from_environ.strip() != "":
        return _bersih(from_environ)
    return _ENV.get(kunci, bawaan)


def angka(kunci: str, bawaan: int) -> int:
    try:
        return int(str(nilai(kunci, str(bawaan))).strip())
    except ValueError:
        return bawaan


def angka_float(kunci: str, bawaan: float) -> float:
    """Kembar `angka()` untuk rasio (protect 0.33, length_scale 1.0).

    Tidak bisa lewat `angka()`: int("0.33") melempar ValueError lalu nilai
    Master diam-diam diganti bawaan -- persis kelas bug "resep diabaikan tanpa
    pesan" yang sudah pernah terjadi di proyek ini.
    """
    try:
        return float(str(nilai(kunci, str(bawaan))).strip())
    except ValueError:
        return bawaan


def bool_(kunci: str, bawaan: bool) -> bool:
    mentah = nilai(kunci, "true" if bawaan else "false").strip().lower()
    if mentah in ("true", "1", "ya", "on"):
        return True
    if mentah in ("false", "0", "tidak", "off"):
        return False
    return bawaan


def daftar(kunci: str, bawaan: str) -> list[str]:
    return [s.strip() for s in nilai(kunci, bawaan).split(",") if s.strip()]


def env_web() -> dict[str, str]:
    """Kunci VITE_* yang boleh sampai ke browser.

    Sengaja HANYA berprefiks VITE_: VTUBER_* tidak boleh dibubuhkan ke halaman.
    """
    hasil = {k: v for k, v in _ENV.items() if k.startswith("VITE_")}
    hasil.update({k: v for k, v in os.environ.items() if k.startswith("VITE_")})
    return hasil


PORT = angka("VTUBER_PORT", 8787)

# Wujud aplikasi: 'pet' = jendela melayang tanpa bingkai di desktop (bawaan,
# pywebview), 'browser' = Flask saja, Master buka sendiri di tab. Keduanya
# menyajikan HALAMAN YANG SAMA -- lihat web/tampak.js.
#
# Bawaannya 'pet' sejak 28 Sep: permintaan Master adalah karakter 2D yang hidup di
# desktop tanpa jendela biasa, dan itu persis yang dilakukan mode pet (frameless,
# color-key tembus pandang, WS_EX_TOOLWINDOW jadi tidak muncul di taskbar/Alt+Tab,
# tray + hotkey untuk memangginya kembali).
#
# Harga yang perlu diketahui: dia selalu DI ATAS jendela lain. Karena itu
# PET_SEMBUNYI bawaannya 'layar-penuh' -- 27 Sep bawaan pernah dipindah ke
# 'browser' justru karena karakter menutupi jendela yang dimaksimalkan, dan
# pembatalan itu bukan salah mode pet melainkan karena sembunyi-otomatisnya mati.
# --browser / VTUBER_TAMPAK=browser tetap ada sebagai jalan kembali.
TAMPAK = nilai("VTUBER_TAMPAK", "pet").lower()

# ── perilaku jendela pet: "biar tidak terasa seperti jendela" ────────────────
# Tidak ada cara membuat jendela benar-benar hilang di mesin ini -- menanamnya ke
# lapisan desktop sudah dicoba dan gagal (lihat RENCANA-DESKTOP.md, Fase 1). Jadi
# kesan itu dikejar lewat PERILAKU: dia minggir saat memang tidak muat di layar,
# dan Master punya ikon tray + hotkey supaya tidak pernah terkunci.
#
# Kapan dia minggir:
#   'tidak'                = selalu tampil. Bersama bawaan baru TAMPAK='pet' itu
#                            berarti dia menutupi jendela kerja yang dimaksimalkan.
#   'layar-penuh' (bawaan) = hanya saat jendela depan menutupi SELURUH monitor,
#                            termasuk pita taskbar -- video layar penuh, game.
#   'maksimal'             = juga saat jendela depan sekadar dimaksimalkan.
#                            Jangan dipakai kalau Master terbiasa kerja dengan
#                            jendela maksimal: karakternya akan hampir selalu
#                            sembunyi dan itu terasa seperti rusak.
# Sembunyi yang salah simpul pernah membuat karakter HILANG tanpa pesan -- itu
# alasan PET_TRAY bawaannya 'ya': selama tray hidup, Master selalu punya jalan
# untuk memangginya kembali.
PET_SEMBUNYI = nilai("VTUBER_PET_SEMBUNYI", "layar-penuh").lower()
PET_TRAY = bool_("VTUBER_PET_TRAY", True)
# Kosong = matikan hotkey. Bentuknya bebas urutannya: ctrl+shift+s
PET_HOTKEY = nilai("VTUBER_PET_HOTKEY", "ctrl+shift+s").lower()

# Otak percakapan:
# - 'local' / 'llama_cpp': Model GGUF offline di folder model/ (tanpa dependensi luar)
# - 'vulkan': GGUF yang SAMA, dihitung llama-server.exe di GPU terintegrasi (Iris Xe)
#   lewat proses anak yang dikelola main.py -- lihat model_vulkan.py
# - 'ollama': Server daemon Ollama di http://127.0.0.1:11434
LLM_PROVIDER = nilai("VTUBER_LLM_PROVIDER", "local").lower()
LOCAL_MODEL_PATH = nilai("VTUBER_LOCAL_MODEL_PATH", "")
LOCAL_MODEL_THREADS = angka("VTUBER_LOCAL_MODEL_THREADS", 4)
LOCAL_MODEL_CTX = angka("VTUBER_LOCAL_MODEL_CTX", 8192)

# ── jalur GPU terintegrasi (llama.cpp Vulkan) ────────────────────────────────
# Folder berisi llama-server.exe (build Vulkan resmi llama.cpp), BUKAN berkas .env:
# binary 92 MB ini tidak ikut ke git dan tidak boleh dianggap sumber.
LLAMA_SERVER = nilai("VTUBER_LLAMA_SERVER", "bin/llama")
# Jumlah lapis yang dititipkan ke GPU. 99 = semua. Angka ini BUKAN selera:
# terukur 27 Sep di mesin Master (pp2048 138->166 tok/s, tg 9,6 tok/s tetap sama),
# dan nilai tengah seperti 16 justru membuat token per detik jatuh (6,9).
VULKAN_NGL = angka("VTUBER_VULKAN_NGL", 99)
VULKAN_FA = bool_("VTUBER_VULKAN_FA", True)  # flash attention: ini yang membuat
# offload penuh akhirnya menang dari CPU -- tanpanya GPU malah kalah (lihat README).
VULKAN_CTX = angka("VTUBER_VULKAN_CTX", 0) or LOCAL_MODEL_CTX
VULKAN_PERANGKAT = nilai("VTUBER_VULKAN_PERANGKAT", "Vulkan0")
# Panaskan llama-server saat boot? YA untuk jalur ini, dan alasannya beda dari RVC:
# membaca 1,9 GB GGUF + kompilasi shader Vulkan itu 8-15 dtk, dan kalau terjadi di
# dalam /api/chat kalimat pertama lewat batas waktunya.
VULKAN_MUAT_BOOT = bool_("VTUBER_VULKAN_MUAT_BOOT", True)
# Simpan slot menganggur ke prompt cache supaya persona panjang tidak dihitung ulang
# tiap giliran bicara.
VULKAN_SLOT_DIAM = bool_("VTUBER_VULKAN_SLOT_DIAM", True)

OLLAMA_URL = nilai("VTUBER_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = nilai("VTUBER_OLLAMA_MODEL", "llama3.2:3b")

MODEL = "local"
MODEL_CADANGAN: list[str] = []

TTS_MODEL = "piper+rvc"
TTS_CADANGAN: list[str] = []
TTS_SUARA = ""
TTS_PER_KALIMAT = bool_("VTUBER_TTS_PER_KALIMAT", True)
STT_MODEL = nilai("VTUBER_STT_MODEL", "base")  # folder di STT_MODEL_PATH

# ── STT lokal (Whisper via faster-whisper / CTranslate2, CPU) ────────────────
# Dulu konstanta ini bernilai "web_speech" dan itu BUKAN offline: Web Speech API di
# Chrome/Edge mengunggah audio mic ke server Google/Microsoft. Sekarang browser
# mengirim WAV ke /api/stt dan transkripsinya dibuat di mesin ini (stt_whisper.py).
STT_HIDUP = bool_("VTUBER_STT", True)
STT_MODEL_PATH = nilai("VTUBER_STT_MODEL_PATH", "aset/suara/whisper")
STT_BAHASA = nilai("VTUBER_STT_BAHASA", "id")
STT_KOMPUTASI = nilai("VTUBER_STT_KOMPUTASI", "int8")
# 2 thread, bukan 4: jalur ini hidup berbarengan dengan llama-server yang juga
# meminta LOCAL_MODEL_THREADS, dan Whisper CPU lebih diuntungkan oleh inti yang
# tidak direbut.
STT_THREADS = angka("VTUBER_STT_THREADS", 2)
STT_BEAM = angka("VTUBER_STT_BEAM", 1)
STT_MUAT_BOOT = bool_("VTUBER_STT_MUAT_BOOT", False)
# Batas ukuran berkas yang diterima /api/stt -- ucapan 30 dtk @16 kHz mono 16-bit.
STT_MAKS_DETIK = angka("VTUBER_STT_MAKS_DETIK", 30)

JEDA_FAKTA = angka("VTUBER_JEDA_FAKTA", 8)

# ── rantai engine suara ──────────────────────────────────────────────────────
# Rantai berisi RESEP offline: piper, rvc, piper+rvc, stub
TTS_RANTAI = daftar("VTUBER_TTS_RANTAI", "piper+rvc,piper")
TTS_BATAS_DETIK = angka("VTUBER_TTS_BATAS_DETIK", 20)
# Resep yang terbukti tidak selesai dalam TTS_BATAS_DETIK diistirahatkan selama ini
# (detik) sebelum dicoba lagi.
TTS_JEDA_RESEP = angka("VTUBER_TTS_JEDA_RESEP", 60)

# ── piper (TTS Indonesia offline, 61 MB ONNX) ────────────────────────────────
PIPER_MODEL = nilai(
    "VTUBER_TTS_PIPER_MODEL", "aset/suara/piper/id_ID-news_tts-medium.onnx"
)
PIPER_SUARA = nilai("VTUBER_TTS_PIPER_SUARA", "id_ID-news_tts-medium")  # dipakai sedia
PIPER_VOLUME = angka("VTUBER_TTS_PIPER_VOLUME", 100)  # persen
PIPER_PANJANG = angka_float("VTUBER_TTS_PIPER_PANJANG", 1.0)  # length_scale: <1 lebih laju

# ── RVC (mengubah WARNA suara jadi Silver Wolf; TTS tetap menyumbang lafal+irama) ─
RVC_HIDUP = bool_("VTUBER_RVC", True)  # mati => rantai menyaring sendiri, tanpa error
RVC_FOLDER = nilai("VTUBER_RVC_FOLDER", "aset/suara/rvc")  # models_dir rvc_python
RVC_MODEL = nilai("VTUBER_RVC_MODEL", "furina")  # nama subfolder di RVC_FOLDER
RVC_INDEKS = nilai("VTUBER_RVC_INDEKS", "")  # kosong = ambil .index yang ada di folder
RVC_VERSI = nilai("VTUBER_RVC_VERSI", "v2")  # terverifikasi dari info checkpoint Silver Wolf JP
RVC_F0 = nilai("VTUBER_RVC_F0", "pm")  # pm|rmvpe (harvest|crepe: ditolak untuk CPU)
RVC_TRANSPOSE = angka("VTUBER_RVC_TRANSPOSE", 0)  # f0up_key; sumber = suara pria Piper
# 0 = JANGAN baca .index. Bukan selera: rvc_python melakukan faiss.read_index +
# index.reconstruct_n TANPA cache di SETIAP panggilan (pipeline.py:306-320), jadi
# index 507 MB berarti ±1 GB puncak RAM dan ratusan MB I/O per kalimat.
RVC_INDEKS_LAJU = angka_float("VTUBER_RVC_INDEKS_LAJU", 0.0)
RVC_PROTEKSI = angka_float("VTUBER_RVC_PROTEKSI", 0.33)  # protect
RVC_PENCUCIAN = angka("VTUBER_RVC_PENCUCIAN", 3)  # filter_radius
RVC_CAMPUR_RMS = angka_float("VTUBER_RVC_CAMPUR_RMS", 1.0)  # rms_mix_rate
RVC_RESAMPLE = angka("VTUBER_RVC_RESAMPLE", 0)  # 0 = biarkan laju asli model (40000)
# Muat model saat boot? bawaan TIDAK: boot harus tetap <1 detik dan tidak boleh
# bisa gagal hanya karena aset 560 MB belum ditaruh.
RVC_MUAT_BOOT = bool_("VTUBER_RVC_MUAT_BOOT", False)
RVC_BATAS_ANTREAN = angka("VTUBER_RVC_BATAS_ANTREAN", 8)

# ── cache hasil sintesis ─────────────────────────────────────────────────────
TTS_CACHE = bool_("VTUBER_TTS_CACHE", True)
TTS_CACHE_FOLDER = nilai("VTUBER_TTS_CACHE_FOLDER", "var/cache-suara")
TTS_CACHE_MAKS_MB = angka("VTUBER_TTS_CACHE_MAKS_MB", 250)
TTS_METERIK = bool_("VTUBER_TTS_METERIK", False)  # cetak median/p95 di banner + jsonl

# VTUBER_STUB=1: /api/chat menjawab dengan aliran kalengan dan TTS memulangkan
# hening pendek. Buat apa: menguji rantai streaming -> tag -> wajah -> rahang
# tanpa satu pun panggilan berbayar, dan tanpa server Node terpisah -- halaman
# ini sudah disajikan oleh proses yang sama, jadi tiruan harus hidup di sini juga.
STUB = bool_("VTUBER_STUB", False)
MAKS_PESAN = 24
MAKS_KARAKTER = 4000
MAKS_BODY = 64 * 1024
MAKS_AUDIO = 2 * 1024 * 1024
