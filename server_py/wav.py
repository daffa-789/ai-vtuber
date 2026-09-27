"""Bungkusan dan pembacaan header WAV.

Rumah baru untuk tiga helper yang dulu hidup di server HTTP lama. Dipisahkan supaya jalur
suara (piper / rvc / cache) bisa memeriksa berkas audio tanpa mengimpor server --
mengimpor modul server berarti menjalankan konstanta modulnya, dan itu bukan sesuatu
yang aman dilakukan dari dalam tes.

`sudah_wav` dipertahankan apa adanya. Doknya bukan seremoni: membungkus ulang
WAV yang sudah lengkap menghasilkan berkas rusak, dan itulah penyebab "suara
hilang diam-diam saat model TTS diganti".
"""

from __future__ import annotations

import io
import re
import struct
import wave
from array import array


class WavRusak(Exception):
    """Berkas claim dirinya WAV tapi tidak bisa dibaca."""


# Ambang "berkas ini benar-benar ada isinya", dalam amplitudo PCM16 (0..32767).
# Tinggal di sini supaya jalur_suara dan tts_rvc memakai ANGKA YANG SAMA -- dua
# ambang berarti satu keluaran bisa lolos di satu tempat dan ditolak di tempat
# lain, dan itu kelas bug "suara hilang diam-diam" yang sama.
#
# 400 dipilih karena web/suara.js memakai LANTAI_NOISE 0,012 (~393 dari 32767):
# di bawah angka ini rahang tidak akan bergerak sama sekali, jadi "lolos pemeriksaan
# ini" berarti "dengar dan lihat", bukan sekadar "ada byte non-nol".
AMBANG_DENGAR = 400


def pcm_ke_wav(pcm: bytes, laju: int, kanal: int = 1) -> bytes:
    """Model TTS lama memulangkan PCM mentah tanpa header; dibungkus di sini."""
    header = (
        b"RIFF"
        + struct.pack("<I", 36 + len(pcm))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, kanal, laju, laju * kanal * 2, kanal * 2, 16)
        + b"data"
        + struct.pack("<I", len(pcm))
    )
    return header + pcm


def sudah_wav(bin: bytes) -> bool:
    """Model TTS baru sudah mengirim WAV lengkap; membungkusnya lagi = berkas rusak,
    dan itu yang bikin suara hilang diam-diam saat model diganti."""
    return len(bin) > 12 and bin[:4] == b"RIFF" and bin[8:12] == b"WAVE"


def laju_kanal(mime: str) -> tuple[int, int]:
    """Contoh mime: 'audio/wav' atau 'audio/L16;codec=pcm;rate=24000'."""
    angka = [int(n) for n in re.findall(r"(?:rate|channels)=(\d+)", mime)]
    return (angka[0] if angka else 24000, angka[1] if len(angka) > 1 else 1)


def baca_header(bin: bytes) -> tuple[int, int, float]:
    """(laju, kanal, detik) dari byte WAV.

    Ini satu-satunya cara jujur membuktikan "keluaran engine adalah audio yang
    bisa dipakai": panjang byte tidak cukup (44 byte header pun lolos `sudah_wav`),
    dan `wave` menolak berkas yang kepalanya saja mirip WAV.
    """
    if not sudah_wav(bin):
        raise WavRusak("bukan WAV: header RIFF/WAVE tidak ada")
    try:
        with wave.open(io.BytesIO(bin), "rb") as w:
            laju, kanal = w.getframerate(), w.getnchannels()
            if not laju:
                raise WavRusak("laju sampel nol")
            return (laju, kanal, w.getnframes() / float(laju))
    except wave.Error as err:
        raise WavRusak(f"header WAV tidak terbaca: {err}") from err


def puncak(bin: bytes, batas_frame: int = 4_000_000) -> int:
    """Amplitudo absolut terbesar di SELURUH berkas; 0 = hening total. stdlib saja.

    Alasan fungsi ini ada: `baca_header` mengukur DURASI, dan durasi tidak
    membedakan audio yang bagus dari berkas 40 kHz penuh nol. Keluaran seperti itu
    lolos `sudah_wav`, lolos `decodeAudioData` browser, membuat `berbicara = true`,
    tapi `tingkatMulut()` mentok di bawah lantai noise -- rahang diam total tanpa
    satu pun pesan galat, dan kalau hasil itu sempat masuk cache, kalimat yang sama
    hening selamanya.

    `batas_frame` itu PLAFON KEAMANAN (~100 detik @40 kHz), bukan jendela sampling.
    Pernah dibatasi 4096 frame dan salah dengan cara yang sunyi: keluaran RVC nyata
    membuka dengan ramp hening, jadi 0,1 detik pertama terukur puncak 66 sementara
    seluruh berkasnya 28.710 -- setiap kalimat RVC akan dinyatakan bisu dan rantai
    jatuh ke cloud diam-diam selamanya. Kalau suatu hari angka itu diganti jadi
    "cuplikan saja", itu bug, bukan optimasi.
    """
    try:
        with wave.open(io.BytesIO(bin), "rb") as w:
            if w.getsampwidth() != 2:
                return 1  # bukan PCM16; jangan sebut diam, kita tidak tahu
            kanal = max(w.getnchannels(), 1)
            tertinggi = 0
            sisa = min(w.getnframes(), batas_frame)
            while sisa > 0:
                data = w.readframes(min(sisa, 65536))
                if not data:
                    break
                sisa -= len(data) // (2 * kanal)
                contoh = array("h")
                contoh.frombytes(data[: len(data) - (len(data) % 2)])
                if not contoh:
                    continue
                tertinggi = max(tertinggi, abs(min(contoh)), abs(max(contoh)))
                if tertinggi >= 32767:
                    break  # tidak mungkin lebih tinggi; berhenti lebih awal
            return tertinggi
    except wave.Error as err:
        raise WavRusak(f"isi WAV tidak terbaca: {err}") from err
