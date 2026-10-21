"""Port TeksUcapan dari C# HuoHuo.Core.Text.TeksUcapan.

Normalisasi teks ucapan SEBELUM disintesis menjadi suara:
- Membuang formatting Markdown (*, **, `, #, -, [link](url)) agar tidak diucapkan TTS sebagai "bintang" dsb.
- Membuang narasi dalam tanda petik ganda agar hanya dialog yang diucapkan.
- Mempertahankan intonasi tanda baca (.,!?).
"""

from __future__ import annotations

import re
from typing import List, Optional

from huohuo.core.sentence_splitter import potong_kalimat

TEBAL_MIRING = re.compile(r"\*{1,3}([^*\n]+)\*{1,3}")
# Lookbehind di Python harus fixed-width, jadi gunakan capture group (prefix)
MIRING_GARIS_BAWAH = re.compile(r"(^|[\s(])_([^_\n]+)_(?=$|[\s.,!?;)])")
KODE = re.compile(r"`{1,3}([^`\n]+)`{1,3}")
JUDUL = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
BUTIR_DAFTAR = re.compile(r"^\s{0,4}[-*+]\s+", re.MULTILINE)
DAFTAR_NOMOR = re.compile(r"^\s{0,4}\d+[.)]\s+", re.MULTILINE)
TAUTAN = re.compile(r"\[([^\]\n]+)\]\([^)\n]*\)")

BINTANG_SISA = re.compile(r"\*+")
GARIS_BAWAH_SISA = re.compile(r"(^|[\s(])_+|(?=$|[\s.,!?;)])_+")
BACKTICK_SISA = re.compile(r"`+")
PAGAR_SISA = re.compile(r"^\s{0,3}#+\s*", re.MULTILINE)

PISAH_PANJANG = re.compile(r"\s*[—–]\s*")
SIMBOL_HIAS = re.compile(r"[•▪▫◦‣·※→←↑↓]")

NARASI_LURUS = re.compile(r'"[^"\n]*"')
NARASI_TIPIS = re.compile(r'“[^”\n]*”')
SPASI_GANDA = re.compile(r"[ \t]{2,}")
SPASI_SEBELUM_TANDA = re.compile(r"\s+([.,!?;:])")


def bersihkan(teks: Optional[str]) -> str:
    """Bersihkan penanda Markdown agar teks natural saat diucapkan TTS."""
    if not teks or not teks.strip():
        return ""

    hasil = teks

    # 1. Bentuk berpasangan — ambil isi, buang penanda
    hasil = TEBAL_MIRING.sub(r"\1", hasil)
    hasil = KODE.sub(r"\1", hasil)
    hasil = MIRING_GARIS_BAWAH.sub(r"\1\2", hasil)

    # 2. Struktur baris — judul, butir, nomor, link
    hasil = JUDUL.sub("", hasil)
    hasil = BUTIR_DAFTAR.sub("", hasil)
    hasil = DAFTAR_NOMOR.sub("", hasil)
    hasil = TAUTAN.sub(r"\1", hasil)

    # 3. Sisa simbol tunggal
    hasil = BINTANG_SISA.sub("", hasil)
    hasil = GARIS_BAWAH_SISA.sub(r"\1", hasil)
    hasil = BACKTICK_SISA.sub("", hasil)
    hasil = PAGAR_SISA.sub("", hasil)

    # 4. Simbol hias & dash
    hasil = PISAH_PANJANG.sub(", ", hasil)
    hasil = SIMBOL_HIAS.sub("", hasil)

    # 5. Rapikan spasi
    hasil = SPASI_GANDA.sub(" ", hasil)
    hasil = SPASI_SEBELUM_TANDA.sub(r"\1", hasil)

    return hasil.strip()


def buang_narasi(teks: Optional[str]) -> str:
    """Buang narasi situasi di dalam tanda petik ganda agar hanya dialog yang disuarakan."""
    if not teks or not teks.strip():
        return ""

    hasil = NARASI_LURUS.sub(" ", teks)
    hasil = NARASI_TIPIS.sub(" ", hasil)
    hasil = SPASI_GANDA.sub(" ", hasil)
    hasil = SPASI_SEBELUM_TANDA.sub(r"\1", hasil)
    return hasil.strip()


def bersihkan_per_kalimat(teks: Optional[str], minimal: int = 12) -> List[str]:
    """Pecah teks menjadi kalimat lalu bersihkan masing-masing untuk pipeline suara."""
    potong = potong_kalimat(teks, minimal)
    daftar = list(potong.kalimat)
    if potong.sisa and potong.sisa.strip():
        daftar.append(potong.sisa)

    hasil: List[str] = []
    for kalimat in daftar:
        b = bersihkan(kalimat)
        if b:
            hasil.append(b)
    return hasil
