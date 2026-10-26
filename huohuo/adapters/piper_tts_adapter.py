"""Adapter: PiperTTSAdapter.

Implements TTSPort using Piper TTS for in-memory speech synthesis.
Ensures zero persistent disk footprint by reading WAV bytes immediately into RAM.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from huohuo.config import AppConfig, config
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.services.text_speech_service import TextSpeechService


class PiperTTSAdapter(TTSPort):
    """Concrete adapter for Piper Text-to-Speech synthesis."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        """Synthesize text into WAV bytes in-memory.

        `gaya` diterima supaya cocok dengan TTSPort tapi sengaja diabaikan:
        Piper tidak punya tuas intonasi. Itu justru alasan backend Gemini ada.
        """
        cleaned_text = TextSpeechService.bersihkan_untuk_tts(text)
        if not cleaned_text:
            return None

        piper_exe = Path(self.cfg.piper_exe)
        piper_model = Path(self.cfg.piper_model)

        if not piper_exe.is_file() or not piper_model.is_file():
            # Gracefully handle missing model/binary in dev environments
            return None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            cmd = [
                str(piper_exe),
                "-m", str(piper_model),
                "--length-scale", str(self.cfg.piper_length_scale),
                "--noise-scale", str(self.cfg.piper_noise_scale),
                "--noise-w-scale", str(self.cfg.piper_noise_w),
                "-f", str(tmp_path),
            ]
            res = subprocess.run(
                cmd,
                input=cleaned_text,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if res.returncode != 0:
                return None

            if tmp_path.is_file() and tmp_path.stat().st_size > 0:
                return tmp_path.read_bytes()
            return None
        except Exception:
            return None
        finally:
            if tmp_path.is_file():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
