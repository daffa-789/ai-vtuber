"""Satu sumber kebenaran untuk profil suara HuoHuo.

Berkas ini sengaja TIDAK punya dependensi apa pun (tidak import config, tidak
import dotenv, tidak import httpx). Alasannya: nilai di sini dipakai oleh dua
pihak yang berbeda lingkungan Python-nya —

  * `huohuo/config.py`            -> venv utama aplikasi
  * `rvc/rvc_service.py`          -> `rvc-env` (Python 3.10, tanpa dotenv/httpx)

Sebelumnya angka yang sama ditulis dua kali, dan itu persis sumber bug yang
membuat `.env` tidak berpengaruh pada suara. Sekarang keduanya membaca dari sini.

Nilai di bawah adalah DEFAULT, dipakai hanya kalau kuncinya tidak ada di `.env`.
Profil ini hasil tuning 2026-10-26 (gejala "cempreng"); dasar pengukurannya ada
di `tools/tts/README.md`.
"""

from __future__ import annotations

# ── Model RVC ────────────────────────────────────────────────────────────────
MODEL_NAMA = "HuoHuo"
VERSI = "v2"
SUBFER = "cpu"

# ── Parameter konversi ───────────────────────────────────────────────────────
TRANSPOSE = -2          # semitone; titik awal lama dari Piper, dapat diatur lewat .env
INDEKS_LAJU = 0.6       # bobot retrieval index; 0 = timbre hanya dari .pth
METODE_F0 = "rmvpe"     # `harvest` terukur justru lebih kasar
PENCUCIAN = 3           # filter_radius: pembesaran median pada kontur pitch
CAMPUR_RMS = 0.8        # rms_mix_rate
PROTEKSI = 0.6          # proteksi konsonan; 0,33 -> lebih banyak artefak logam

# ── Koreksi nada pasca-konversi ──────────────────────────────────────────────
# EQ pasca-RVC mengikuti pengukuran keluaran model HuoHuo dari pipeline lama.
# Shelf tinggi memotong zona tajam, shelf rendah mengembalikan badan suara.
EQ_AKTIF = True
EQ_TINGGI_HZ = 6000.0
EQ_TINGGI_DB = -12.0
EQ_RENDAH_HZ = 200.0
EQ_RENDAH_DB = 1.5

# ── Backend TTS (sumber audio SEBELUM RVC) ───────────────────────────────────
# Supertonic 3: lokal, mendukung Bahasa Indonesia, dan punya tag napas/sigh.
# Piper tetap jadi cadangan lokal bila model Supertonic belum tersedia.
TTS_RANTAI = "supertonic,piper"
SUPERTONIC_MODEL_DIR = "assets/supertonic-3"
SUPERTONIC_VOICE = "F2"
SUPERTONIC_STEPS = 8
SUPERTONIC_SPEED = 0.94

# Koreksi kecil F0 di RVC per emosi (semitone), di atas TRANSPOSE dasar.
# Rentang sengaja sempit supaya karakter tetap terdengar seperti Huohuo.
TRANSPOSE_PER_EMOSI = {
    "netral": 0,
    "senyum": 1,
    "semangat": 2,
    "kaget": 2,
    "bingung": 1,
    "malu": 1,
    "gugup": 1,
    "takut": 2,
    "lelah": -2,
    "goda": 1,
    "sebal": -1,
    "sedih": -2,
}

# ── Layanan HTTP ─────────────────────────────────────────────────────────────
PORT = 8081
URL_LAYANAN = f"http://127.0.0.1:{PORT}"
WAKTU_HUBUNG_DETIK = 180

# Muat model saat layanan start? False = malas, dimuat pada permintaan pertama.
MUAT_BOOT = False
# Berhenti total setelah menganggur sekian detik. Hanya proses yang mati bisa
# mengembalikan RAM-nya (melepas model di dalam proses terbukti cuma memulihkan
# 0,06 GB), jadi ini "keluar dari proses", bukan "lepaskan model". RVCAdapter
# menyalakan ulang layanan ini saat dibutuhkan. 0 = jangan pernah berhenti.
IDLE_HAPUS_DETIK = 180.0


def ya(teks: str, bawaan: bool = False) -> bool:
    """Tafsir nilai .env jadi boolean (`ya`/`true`/`1`/`yes` = True)."""
    if teks is None:
        return bawaan
    return teks.strip().lower() in ("ya", "true", "1", "yes", "on")
