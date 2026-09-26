"""Konfigurasi sisi server Python.

Baca dari environment dulu, baru dari berkas .env di akar proyek -- sama seperti
`node --env-file-if-exists=.env`. Kunci yang dibaca di sini hanya VTUBER_* dan
GEMINI_API_KEY; 34 kunci VITE_* di .env itu milik frontend dan tidak boleh
menyentuh sisi server.
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


def baca_env(jalur: Path) -> dict[str, str]:
    """Parser .env minimal: `KUNCI=nilai`, `#` komentar, spasi di sekitar `=`."""
    if not jalur.exists():
        return {}
    hasil: dict[str, str] = {}
    for baris in jalur.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, _, nilai = baris.partition("=")
        hasil[kunci.strip()] = _bersih(nilai)
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

    Sengaja HANYA berprefiks VITE_: GEMINI_API_KEY dan VTUBER_* tidak boleh
    dibubuhkan ke halaman. Ini pengganti `import.meta.env` milik Vite.
    """
    hasil = {k: v for k, v in _ENV.items() if k.startswith("VITE_")}
    hasil.update({k: v for k, v in os.environ.items() if k.startswith("VITE_")})
    return hasil


KUNCI = ""
PORT = angka("VTUBER_PORT", 8787)

# Otak percakapan:
# - 'local' / 'llama_cpp': Model GGUF offline di folder model/ (tanpa dependensi luar)
# - 'ollama': Server daemon Ollama di http://127.0.0.1:11434
LLM_PROVIDER = nilai("VTUBER_LLM_PROVIDER", "local").lower()
LOCAL_MODEL_PATH = nilai("VTUBER_LOCAL_MODEL_PATH", "")
LOCAL_MODEL_THREADS = angka("VTUBER_LOCAL_MODEL_THREADS", 4)
LOCAL_MODEL_CTX = angka("VTUBER_LOCAL_MODEL_CTX", 8192)

OLLAMA_URL = nilai("VTUBER_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = nilai("VTUBER_OLLAMA_MODEL", "llama3.2:3b")

MODEL = "local"
MODEL_CADANGAN: list[str] = []

TTS_MODEL = "piper+rvc"
TTS_CADANGAN: list[str] = []
TTS_SUARA = ""
TTS_PER_KALIMAT = bool_("VTUBER_TTS_PER_KALIMAT", True)
STT_MODEL = "web_speech"

JEDA_FAKTA = angka("VTUBER_JEDA_FAKTA", 8)

# ── rantai engine suara ──────────────────────────────────────────────────────
# Rantai berisi RESEP offline: piper, rvc, piper+rvc, stub
TTS_RANTAI = daftar("VTUBER_TTS_RANTAI", "piper+rvc,piper")
TTS_BATAS_DETIK = angka("VTUBER_TTS_BATAS_DETIK", 20)
# Resep yang terbukti tidak selesai dalam TTS_BATAS_DETIK diistirahatkan selama ini
# (detik) sebelum dicoba lagi. Tanpa jeda, SETIAP kalimat dari jawaban panjang
# membayar ulang 20 dtk kegagalan yang sama -- dan penahan yang di depan (gemini)
# justru kebagian kuota yang habis karena menunggu.
TTS_JEDA_RESEP = angka("VTUBER_TTS_JEDA_RESEP", 60)

# ── piper (TTS Indonesia offline, 61 MB ONNX) ────────────────────────────────
PIPER_MODEL = nilai(
    "VTUBER_TTS_PIPER_MODEL", "aset/suara/piper/id_ID-news_tts-medium.onnx"
)
PIPER_SUARA = nilai("VTUBER_TTS_PIPER_SUARA", "id_ID-news_tts-medium")  # dipakai sedia
PIPER_VOLUME = angka("VTUBER_TTS_PIPER_VOLUME", 100)  # persen
PIPER_PANJANG = angka_float("VTUBER_TTS_PIPER_PANJANG", 1.0)  # length_scale: <1 lebih laju

# ── RVC (mengubah WARNA suara jadi Furina; TTS tetap menyumbang lafal+irama) ─
RVC_HIDUP = bool_("VTUBER_RVC", True)  # mati => rantai menyaring sendiri, tanpa error
RVC_FOLDER = nilai("VTUBER_RVC_FOLDER", "aset/suara/rvc")  # models_dir rvc_python
RVC_MODEL = nilai("VTUBER_RVC_MODEL", "furina")  # nama subfolder di RVC_FOLDER
RVC_INDEKS = nilai("VTUBER_RVC_INDEKS", "")  # kosong = ambil .index yang ada di folder
RVC_VERSI = nilai("VTUBER_RVC_VERSI", "v2")  # terverifikasi dari info checkpoint Furina
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
