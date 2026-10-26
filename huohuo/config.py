"""Konfigurasi global HuoHuo AI Vtuber.

Membaca nilai dari `.env` dengan fallback yang aman dan sesuai dengan profil
terkunci proyek (2026-10-08).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from . import profil_suara as suara


def _app_root() -> Path:
    """Akar path: folder bundle saat dibekukan (PyInstaller), selain itu root repo."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


# Root path dari proyek
ROOT_DIR = _app_root()

# Cek .env di root repo atau di AI Vtuber WINUI3 jika ada
if (ROOT_DIR / ".env").is_file():
    load_dotenv(ROOT_DIR / ".env")
elif (ROOT_DIR / "AI Vtuber WINUI3" / ".env").is_file():
    load_dotenv(ROOT_DIR / "AI Vtuber WINUI3" / ".env")


def resolve_path(*candidates: Path | str, require_file: bool = False) -> Path:
    """Mengembalikan kandidat jalur pertama yang benar-benar ada."""
    for c in candidates:
        if not c:
            continue
        p = Path(c)
        if not p.is_absolute():
            p = ROOT_DIR / p
        if require_file:
            if p.is_file():
                return p
        elif p.exists():
            return p

    for c in candidates:
        if c:
            p = Path(c)
            return p if p.is_absolute() else (ROOT_DIR / p)
    return ROOT_DIR


@dataclass
class AppConfig:
    # ── Direktori Inti ──
    root_dir: Path = ROOT_DIR
    model_dir: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "model",
        ROOT_DIR / "AI Vtuber WINUI3" / "model",
    ))
    assets_dir: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "assets",
        ROOT_DIR / "AI Vtuber WINUI3" / "assets",
    ))
    memory_dir: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "silver_wolf_memory",
        ROOT_DIR / "AI Vtuber WINUI3" / "silver_wolf_memory",
    ))

    # ── LLM ──
    # Aplikasi hanya menjadi KLIEN server OpenAI-compatible di luar proses ini
    # (llama-server, dinyalakan lewat start_llm.bat). Jalur "aplikasi memilih
    # dan memuat berkas GGUF sendiri" sudah lama tidak ada, jadi tidak ada lagi
    # config.model_path di sini -- dulu menunjuk berkas Gemma yang sudah dihapus.
    llama_endpoint: str = os.getenv("VTUBER_LLAMA_ENDPOINT", "http://127.0.0.1:8080/v1")
    llama_timeout_detik: int = int(os.getenv("VTUBER_LLAMA_TIMEOUT_DETIK", "120"))

    # ── Suara (Piper TTS + RVC) ──
    piper_exe: Path = field(default_factory=lambda: resolve_path(
        os.getenv("VTUBER_PIPER_PATH", ""),
        Path(os.path.expanduser("~")) / ".workbuddy-ai" / "binaries" / "python" / "envs" / "default" / "Scripts" / "piper.exe",
        ROOT_DIR / "tools" / "tts" / "piper.exe",
        require_file=True,
    ))
    piper_model: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "assets" / "piper" / "id_ID-news_tts-medium.onnx",
        ROOT_DIR / "AI Vtuber WINUI3" / "assets" / "piper" / "id_ID-news_tts-medium.onnx",
        require_file=True,
    ))
    piper_length_scale: float = float(os.getenv("VTUBER_TTS_PIPER_PANJANG", "0.9"))
    piper_noise_scale: float = float(os.getenv("VTUBER_TTS_PIPER_NOISE", "0.667"))
    piper_noise_w: float = float(os.getenv("VTUBER_TTS_PIPER_NOISE_W", "0.8"))

    # ── Backend TTS ──
    # "gemini" memberi intonasi yang bisa diperintah; "piper" tetap dipakai
    # sebagai cadangan otomatis kalau key tidak ada atau jaringan bermasalah.
    tts_backend: str = os.getenv("VTUBER_TTS_BACKEND", suara.TTS_BACKEND).lower()
    tts_rantai: str = os.getenv("VTUBER_TTS_RANTAI", suara.TTS_RANTAI).lower()
    # Key dibaca dari GOOGLE_API_KEY atau GEMINI_API_KEY. Jangan pernah menulis
    # nilainya ke berkas yang terlacak -- .env sudah di-gitignore.
    gemini_api_key: str = (
        os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    )
    gemini_tts_model: str = os.getenv("VTUBER_GEMINI_TTS_MODEL", suara.GEMINI_TTS_MODEL)
    gemini_tts_voice: str = os.getenv("VTUBER_GEMINI_TTS_VOICE", suara.GEMINI_TTS_VOICE)
    gemini_tts_gaya: str = os.getenv("VTUBER_GEMINI_TTS_GAYA", suara.GEMINI_TTS_GAYA)
    gemini_timeout_detik: int = int(
        os.getenv("VTUBER_GEMINI_TIMEOUT_DETIK", str(suara.GEMINI_TIMEOUT_DETIK))
    )

    # Suara. Aplikasi HANYA menjadi klien layanan RVC lewat HTTP, jadi di sini
    # cukup alamat dan sakunya. Semua parameter konversi (transpose, index rate,
    # f0, EQ, muat/bongkar model) hidup di rvc/rvc_service.py lewat
    # huohuo/profil_suara.py — tidak diduplikasi di sini lagi.
    rvc_aktif: bool = suara.ya(os.getenv("VTUBER_RVC"), True)
    rvc_service_url: str = os.getenv("VTUBER_RVC_URL", suara.URL_LAYANAN)
    rvc_timeout_detik: int = int(
        os.getenv("VTUBER_RVC_TIMEOUT_DETIK", str(suara.WAKTU_HUBUNG_DETIK))
    )
    # Layanan RVC menahan ~2,5 GB dan mengundurkan diri saat menganggur, karena
    # hanya proses yang mati benar-benar mengembalikan RAM (melepas model di
    # dalam proses sudah diukur: gc + trim hanya memulihkan 0,06 GB). Adapter
    # menyalakannya kembali saat butuh, jadi start_rvc.bat tidak perlu dijalankan
    # tangan setiap kali.
    rvc_auto_mulai: bool = suara.ya(os.getenv("VTUBER_RVC_AUTO_MULAI"), True)
    rvc_siap_detik: int = int(os.getenv("VTUBER_RVC_SIAP_DETIK", "90"))
    rvc_python: Path = field(default_factory=lambda: resolve_path(
        os.getenv("VTUBER_RVC_PYTHON", ""),
        ROOT_DIR / "rvc-env" / "Scripts" / "python.exe",
        require_file=True,
    ))
    rvc_skrip: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "rvc" / "rvc_service.py",
        require_file=True,
    ))

    # ── Masukan Suara (STT + VAD) untuk Voice-to-Voice ──
    voice_in_aktif: bool = os.getenv("VTUBER_VOICE_IN", "tidak").lower() in (
        "ya", "true", "1", "yes",
    )
    stt_backend: str = os.getenv("VTUBER_STT_BACKEND", "whisper").lower()
    stt_model: str = os.getenv("VTUBER_STT_MODEL", "base")
    stt_language: str = os.getenv("VTUBER_STT_LANG", "id")
    stt_device: str = os.getenv("VTUBER_STT_DEVICE", "cpu")
    audio_input_rate: int = int(os.getenv("VTUBER_AUDIO_RATE", "16000"))
    audio_input_block: int = int(os.getenv("VTUBER_AUDIO_BLOCK", "320"))
    audio_input_device: Optional[int] = (
        int(os.environ["VTUBER_AUDIO_DEVICE"])
        if os.getenv("VTUBER_AUDIO_DEVICE", "").strip().lstrip("-").isdigit()
        else None
    )
    vad_rms_threshold: float = float(os.getenv("VTUBER_VAD_RMS", "500"))

    # ── Live2D Web UI ──
    live2d_model_path: Path = field(default_factory=lambda: resolve_path(
        ROOT_DIR / "assets" / "live2d" / "huohuo" / "huohuo.model3.json",
        ROOT_DIR / "AI Vtuber WINUI3" / "assets" / "live2d" / "huohuo" / "huohuo.model3.json",
        require_file=True,
    ))
    ui_width: int = int(os.getenv("VTUBER_UI_WIDTH", "480"))
    ui_height: int = int(os.getenv("VTUBER_UI_HEIGHT", "780"))
    ui_fps: int = int(os.getenv("VTUBER_UI_FPS", "60"))
    # Ikon jendela/taskbar. Berkas boleh tidak ada (mis. clone tanpa aset) —
    # pemanggil memeriksa is_file() sebelum memakainya.
    window_icon_path: Path = field(
        default_factory=lambda: resolve_path(ROOT_DIR / "assets" / "ikon" / "icon.ico")
    )

    # ── Proactive Companion (F3) ──
    proactive_aktif: bool = os.getenv("VTUBER_PROACTIVE", "ya").lower() in ("ya", "true", "1", "yes")
    idle_threshold_detik: int = int(os.getenv("VTUBER_IDLE_SECONDS", "300"))
    window_position_file: Path = field(
        default_factory=lambda: resolve_path(ROOT_DIR / "data" / "window_position.json")
    )


# Singleton konfigurasi bawaan
config = AppConfig()
