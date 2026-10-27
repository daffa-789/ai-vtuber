"""Adapter: PiperTTSAdapter.

Implements TTSPort using local Piper TTS and archives the raw WAV before RVC.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from huohuo.config import AppConfig, config
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.services.text_speech_service import TextSpeechService
from huohuo.infrastructure.audio_artifacts import simpan_wav


_PROSODI = (
    ("excited", "semangat", 0.84, 0.10, 0.05),
    ("surprised", "kaget", 0.88, 0.08, 0.04),
    ("playful", "goda", 0.92, 0.04, 0.04),
    ("smiling", "senyum", 0.96, 0.02, 0.00),
    ("annoyed", "sebal", 1.00, -0.02, -0.02),
    ("confused", "bingung", 1.03, 0.03, 0.02),
    ("sad", "sedih", 1.07, -0.05, -0.05),
    ("tired", "lelah", 1.12, -0.08, -0.08),
)


class PiperTTSAdapter(TTSPort):
    """Concrete adapter for Piper Text-to-Speech synthesis."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    def _prosodi(self, gaya: Optional[str]) -> tuple[float, float, float, str]:
        """Gunakan kontrol prosodi Piper yang paling dekat dengan tag emosi."""
        length = self.cfg.piper_length_scale
        noise = self.cfg.piper_noise_scale
        noise_w = self.cfg.piper_noise_w
        gaya_normal = (gaya or "").lower()
        label = "netral"

        for kata_kunci, emosi, faktor_panjang, delta_noise, delta_noise_w in _PROSODI:
            if kata_kunci in gaya_normal:
                length *= faktor_panjang
                noise += delta_noise
                noise_w += delta_noise_w
                label = emosi
                break

        # Nilai di atas satu cenderung membuat variasi artikulasi berlebihan.
        return (
            min(1.35, max(0.65, length)),
            min(0.95, max(0.35, noise)),
            min(0.95, max(0.35, noise_w)),
            label,
        )

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        """Synthesize text into WAV bytes in-memory.

        Piper tidak menerima instruksi akting bebas seperti TTS generatif, tetapi
        length/noise scale dapat memberi perbedaan tempo dan variasi yang ringan.
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
            length, noise, noise_w, label = self._prosodi(gaya)
            cmd = [
                str(piper_exe),
                "-m", str(piper_model),
                "--length-scale", f"{length:.3f}",
                "--noise-scale", f"{noise:.3f}",
                "--noise-w-scale", f"{noise_w:.3f}",
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
                wav_bytes = tmp_path.read_bytes()
                simpan_wav(
                    getattr(self.cfg, "audio_output_dir", config.audio_output_dir),
                    "raw",
                    wav_bytes,
                    label,
                )
                return wav_bytes
            return None
        except Exception:
            return None
        finally:
            if tmp_path.is_file():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
