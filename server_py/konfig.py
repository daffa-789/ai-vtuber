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


KUNCI = nilai("GEMINI_API_KEY")
PORT = angka("VTUBER_PORT", 8787)

# Terukur 2026-09-24 pada kunci tingkat gratis: gemini-3.5-flash dan -lite balas
# 503 "high demand", sedangkan gemini-3-flash-preview 3/3 lolos. Urutan coba
# utama -> cadangan, bukan menunggu dengan diam.
MODEL = nilai("VTUBER_MODEL", "gemini-3-flash-preview")
MODEL_CADANGAN = daftar("VTUBER_MODEL_CADANGAN", "gemini-3.5-flash,gemini-3.5-flash-lite")

TTS_MODEL = nilai("VTUBER_TTS_MODEL", "gemini-3.8-flash-lite-tts")
TTS_CADANGAN = daftar("VTUBER_TTS_CADANGAN", "gemini-3.8-flash-tts")
TTS_SUARA = nilai("VTUBER_TTS_VOICE", "Kore")
TTS_PER_KALIMAT = bool_("VTUBER_TTS_PER_KALIMAT", True)
STT_MODEL = nilai("VTUBER_STT_MODEL", "gemini-3.5-transcribe")

JEDA_FAKTA = angka("VTUBER_JEDA_FAKTA", 8)

# VTUBER_STUB=1: /api/chat menjawab dengan aliran kalengan dan TTS memulangkan
# hening pendek. Buat apa: menguji rantai streaming -> tag -> wajah -> rahang
# tanpa satu pun panggilan berbayar, dan tanpa server Node terpisah -- halaman
# ini sudah disajikan oleh proses yang sama, jadi tiruan harus hidup di sini juga.
STUB = nilai("VTUBER_STUB", "").strip().lower() in ("1", "true", "ya", "on")
MAKS_PESAN = 24
MAKS_KARAKTER = 4000
MAKS_BODY = 64 * 1024
MAKS_AUDIO = 2 * 1024 * 1024
