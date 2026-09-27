"""Engine STT lokal: Whisper lewat faster-whisper (CTranslate2), murni CPU.

Ini yang menutup lubang "offline" yang selama ini jujur diakui README: mic dulu
ditranskrip Web Speech API browser, dan di Chrome/Edge audio itu naik ke server
Google/Microsoft. Sekarang browser hanya mengirim WAV ke /api/stt dan transkripsinya
dibuat di mesin ini.

Bentuk datanya sengaja paling membosankan: WAV 16 kHz mono 16-bit dari browser ->
`wave` (stdlib) -> numpy float32 -> `model.transcribe()`. Tidak ada ffmpeg, tidak ada
PyAV, tidak ada dekoder pihak ketiga yang bisa diam-diam menghubungi jaringan.

Satu jebakan yang harus diingat: `vad_filter=True` pada faster-whisper menarik model
Silero dari HuggingFace saat pertama dipakai. Di sini selalu False -- batas dengar
dijaga di sisi browser, dan satu unduhan senyap saat Master mencabut LAN adalah
regresi terhadap tujuan berkas ini.
"""

from __future__ import annotations

import io
import threading
import wave
from pathlib import Path

import konfig

NAMA = "whisper"
LAJU_TARGET = 16000  # satu-satunya laju yang dimengerti Whisper

_model = None
_lock = threading.Lock()
_galat_terakhir = ""


class GalatSTT(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


def folder_model() -> Path:
    p = Path(konfig.STT_MODEL_PATH)
    return p if p.is_absolute() else konfig.AKAR / p


def jalur_model() -> Path:
    return folder_model() / konfig.STT_MODEL


def _berkas_wajib() -> tuple[str, ...]:
    return ("model.bin", "config.json", "tokenizer.json")


def tersedia() -> bool:
    """Murah dan tidak mengimpor: berkas model lengkap di disk + paketnya terpasang."""
    return all((jalur_model() / b).is_file() for b in _berkas_wajib()) and _terpasang()


def _terpasang() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def alasan_tidak_tersedia() -> str:
    if not _terpasang():
        return "faster-whisper belum dipasang: .venv\\Scripts\\pip install faster-whisper"
    if not jalur_model().is_dir():
        return (
            f"model '{konfig.STT_MODEL}' belum ada di {jalur_model()} -- salin foldernya "
            "(config.json + model.bin + tokenizer.json) dari mesin sumber"
        )
    kurang = [b for b in _berkas_wajib() if not (jalur_model() / b).is_file()]
    if kurang:
        return f"model '{konfig.STT_MODEL}' tidak lengkap: {kurang}"
    return _galat_terakhir or "siap"


def muat(paksa: bool = False):
    """Buka model sekali saja; panggilan berikutnya hanya mengembalikan yang lama."""
    global _model, _galat_terakhir
    with _lock:
        if _model is not None and not paksa:
            return _model
        try:
            from faster_whisper import WhisperModel  # noqa: PLC0415 -- impor tertunda
        except Exception as err:
            _galat_terakhir = f"faster-whisper tidak bisa diimpor: {err}"
            return None
        if not tersedia():
            _galat_terakhir = alasan_tidak_tersedia()
            return None
        try:
            # Jalur folder LENGKAP, bukan nama model + download_root. Nama saja
            # membuat faster-whisper mencari snapshot HuggingFace
            # (`<root>/models--Systran--faster-whisper-base/snapshots/...`) dan
            # menolak dengan "outgoing traffic has been disabled" -- terbukti 27 Sep,
            # galat itu muncul justru karena kita melarang jaringan dengan benar.
            _model = WhisperModel(
                str(jalur_model()),
                device="cpu",
                compute_type=konfig.STT_KOMPUTASI,  # int8: separuh RAM, akurasi nyaris sama
                cpu_threads=konfig.STT_THREADS,
            )
        except Exception as err:
            _galat_terakhir = f"model whisper gagal dimuat: {err}"
            _model = None
            return None
        _galat_terakhir = ""
        return _model


def _pcm16_ke_float(bingkai: bytes, kanal: int):
    import numpy as np

    data = np.frombuffer(bingkai, dtype="<i2").astype(np.float32) / 32768.0
    if kanal > 1:
        data = data.reshape(-1, kanal).mean(axis=1)
    return data


def baca_wav(byte: bytes) -> tuple["object", int]:
    """WAV -> (float32 mono, laju sampel). Galat jelas kalau bukan PCM 16-bit."""
    try:
        with wave.open(io.BytesIO(byte), "rb") as w:
            laju, kanal, lebar = w.getframerate(), w.getnchannels(), w.getsampwidth()
            bingkai = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as err:
        raise GalatSTT(f"bukan WAV yang bisa dibaca: {err}")
    if lebar != 2:
        raise GalatSTT(f"kedalaman {lebar * 8}-bit tidak didukung, hanya 16-bit")
    if not bingkai:
        raise GalatSTT("WAV tidak berisi audio")
    return _pcm16_ke_float(bingkai, kanal), laju


def resample(data, laju: int):
    """Linear ke 16 kHz. Cukup untuk ucapan; dan tidak butuh paket apa pun."""
    if laju == LAJU_TARGET:
        return data
    import numpy as np

    panjang_baru = int(len(data) * LAJU_TARGET / laju)
    if panjang_baru <= 0:
        raise GalatSTT("audio terlalu pendek")
    lama = np.linspace(0.0, len(data) - 1, len(data))
    baru = np.linspace(0.0, len(data) - 1, panjang_baru)
    return np.interp(baru, lama, data).astype(np.float32)


def transkripsi(byte_wav: bytes) -> str:
    """WAV dari browser -> teks. Generator Whisper digabung jadi satu string."""
    model = muat()
    if model is None:
        raise GalatSTT(_galat_terakhir or alasan_tidak_tersedia())

    data, laju = baca_wav(byte_wav)
    audio = resample(data, laju)

    try:
        potongan, info = model.transcribe(
            audio,
            language=konfig.STT_BAHASA or None,
            beam_size=konfig.STT_BEAM,
            vad_filter=False,  # lihat docstring modul
            condition_on_previous_text=False,  # mic = satu giliran bicara, bukan dokumen
            without_timestamps=True,
        )
        teks = " ".join(p.text.strip() for p in potongan if p.text.strip()).strip()
    except Exception as err:
        raise GalatSTT(f"transkripsi gagal: {err}")
    return teks


def ringkasan() -> str:
    if _model is None:
        return f"stt:{'siap' if tersedia() else 'TIDAK ADA'}"
    return f"stt:{konfig.STT_MODEL}/{konfig.STT_KOMPUTASI} threads={konfig.STT_THREADS}"
