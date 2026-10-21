"""Konfigurasi global Silver Wolf AI Vtuber.

Membaca nilai dari `.env` dengan fallback yang aman dan sesuai dengan profil
terkunci proyek (2026-10-08).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Root path dari proyek
ROOT_DIR = Path(__file__).resolve().parents[1]

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

    # ── Model GGUF / LLM ──
    model_path: Path = field(default_factory=lambda: resolve_path(
        os.getenv("VTUBER_LOCAL_MODEL_PATH", ""),
        ROOT_DIR / "model" / "Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf",
        ROOT_DIR / "AI Vtuber WINUI3" / "model" / "Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf",
        require_file=True,
    ))
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

    # RVC parameter terkunci
    rvc_aktif: bool = os.getenv("VTUBER_RVC", "ya").lower() in ("ya", "true", "1", "yes")
    rvc_model_nama: str = os.getenv("VTUBER_RVC_MODEL", "SilverWolfJP")
    rvc_versi: str = os.getenv("VTUBER_RVC_VERSI", "v2")
    rvc_transpose: int = int(os.getenv("VTUBER_RVC_TRANSPOSE", "-3"))
    rvc_index_rate: float = float(os.getenv("VTUBER_RVC_INDEKS_LAJU", "0.6"))
    rvc_f0: str = os.getenv("VTUBER_RVC_F0", "rmvpe")
    rvc_filter_radius: int = int(os.getenv("VTUBER_RVC_PENCUCIAN", "3"))
    rvc_rms_mix: float = float(os.getenv("VTUBER_RVC_CAMPUR_RMS", "0.8"))
    rvc_protect: float = float(os.getenv("VTUBER_RVC_PROTEKSI", "0.33"))

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
        ROOT_DIR / "assets" / "live2d" / "silverwolf" / "silverwolf.model3.json",
        ROOT_DIR / "AI Vtuber WINUI3" / "assets" / "live2d" / "silverwolf" / "silverwolf.model3.json",
        require_file=True,
    ))
    ui_width: int = int(os.getenv("VTUBER_UI_WIDTH", "480"))
    ui_height: int = int(os.getenv("VTUBER_UI_HEIGHT", "780"))
    ui_fps: int = int(os.getenv("VTUBER_UI_FPS", "60"))


# Singleton konfigurasi bawaan
config = AppConfig()
