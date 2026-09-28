"""Engine TTS lokal: Piper (VITS ONNX, espeak-ng tertanam di dalam paketnya).

Voice-nya `id_ID-news_tts-medium` -- 61 MB, 22,05 kHz, jalan di CPU tanpa GPU.
MODEL CARD-nya jujur: satu penutur, kualitas medium, hasil fine-tune dari suara
Inggris `lessac`. Jadi yang didengar itu suara berita laki-laki berlogat asing,
BUKAN suara karakter. Warna suaranya baru datang dari RVC (tts_rvc.py); Piper
menyumbang lafal dan irama.

Impor `piper` sengaja diletakkan DI DALAM fungsi. Itu keputusan struktural, bukan
gaya: main.py dan konfig.py tidak boleh menyeret paket ratusan MB hanya untuk menjawab
/api/chat -- server harus tetap bisa naik di venv yang belum
`pip install -r requirements.txt`.
"""

from __future__ import annotations

import io
import threading
import wave
from pathlib import Path

import konfig
from konfig import AKAR

NAMA = "piper"

_suara = None
_lock = threading.Lock()
_galat_terakhir = ""


def jalur_model() -> Path:
    p = Path(konfig.PIPER_MODEL)
    return p if p.is_absolute() else AKAR / p


def tersedia() -> bool:
    """Berkas .onnx ada DAN paket piper bisa DI-Temukan. Murah, tidak mengimpor.

    Sengaja find_spec, bukan `import piper`: tersedia() dipanggil banner dan
    /api/health, sementara mengimpor piper menyeret onnxruntime. Paket terpasang
    tapi rusak tetap ketahuan -- di muat(), lewat alasan_tidak_tersedia().
    """
    return jalur_model().is_file() and _terpasang()


def _terpasang() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("piper") is not None
    except Exception:
        return False


def _impor():
    global _galat_terakhir
    try:
        import piper  # noqa: PLC0415  -- impor tertunda: lihat docstring modul

        return piper
    except Exception as err:  # ImportError apa pun = engine ini tidak ada
        _galat_terakhir = f"piper tidak bisa diimpor: {err}"
        return None


def muat(paksa: bool = False) -> bool:
    """Buka voice sekali; panggilan berikutnya tidak membaca 61 MB lagi."""
    global _suara
    with _lock:
        if _suara is not None and not paksa:
            return True
        piper = _impor()
        if piper is None:
            return False
        jalur = jalur_model()
        if not jalur.is_file():
            _galat_terakhir = f"model piper tidak ada: {jalur}"
            return False
        try:
            _suara = piper.PiperVoice.load(str(jalur))
            return True
        except Exception as err:
            _galat_terakhir = f"muat piper gagal: {err}"
            _suara = None
            return False


def laju() -> int:
    """Laju sampel keluaran -- dibutuhkan RVC dan kunci cache."""
    global _galat_terakhir
    with _lock:
        if _suara is None and not muat():
            return 0
        cfg = getattr(_suara, "config", None)
        return int(getattr(cfg, "sample_rate", 0) or 0)


def patokan_cache() -> str:
    """Bagian dari kunci cache: ganti berkas/parameter -> hash berubah sendiri."""
    jalur = jalur_model()
    try:
        st = jalur.stat()
        tanda = f"{st.st_size}:{int(st.st_mtime)}"
    except OSError:
        tanda = "tidak-ada"
    return f"piper|{jalur.name}|{konfig.PIPER_VOLUME}|{konfig.PIPER_PANJANG}|{tanda}"


def sintesis(teks: str) -> bytes:
    """WAV PCM16 mono utuh di RAM. Melempar RuntimeError kalau engine mati."""
    global _galat_terakhir
    piper = _impor()
    if piper is None or not muat():
        raise RuntimeError(_galat_terakhir or "piper tidak siap")

    syn = piper.SynthesisConfig(
        volume=max(konfig.PIPER_VOLUME, 0) / 100.0,
        length_scale=konfig.PIPER_PANJANG,
    )
    wad = io.BytesIO()
    try:
        with wave.open(wad, "wb") as berkas_wav:
            _suara.synthesize_wav(teks, berkas_wav, syn_config=syn)
    except TypeError:
        # SynthesisConfig 1.8.0 mungkin tidak menerima salah satu kata kunci ini;
        # lebih baik bersuara dengan nilai bawaan daripada halaman bisu.
        with wave.open(wad, "wb") as berkas_wav:
            _suara.synthesize_wav(teks, berkas_wav)
    except Exception as err:
        _galat_terakhir = f"sintesis piper gagal: {err}"
        raise RuntimeError(_galat_terakhir) from err

    byte = wad.getvalue()
    if len(byte) <= 44:
        raise RuntimeError("piper memulangkan WAV kosong")
    return byte


def alasan_tidak_tersedia() -> str:
    if not jalur_model().is_file():
        return f"model piper belum diunduh: {jalur_model()} (salin .onnx + .onnx.json ke folder itu)"
    if not _terpasang():
        return "paket piper-tts belum diinstal"
    return _galat_terakhir or "piper siap"
