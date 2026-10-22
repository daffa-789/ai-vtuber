"""Adapter: FasterWhisperAdapter.

Implementasi SpeechToTextPort offline memakai faster-whisper (CTranslate2),
ringan dan mendukung Bahasa Indonesia. Impornya bersifat lazy: bila paket
`faster-whisper` belum terpasang, adapter ini tetap dapat diinstruksikan dan
`transcribe()` mengembalikan string kosong tanpa menjatuhkan aplikasi.
"""

from __future__ import annotations

import array
import math
from typing import Optional

from huohuo.domain.ports.speech_to_text_port import SpeechToTextPort


class FasterWhisperAdapter(SpeechToTextPort):
    """STT Whisper offline dengan pemuatan model malas (lazy)."""

    def __init__(
        self,
        model_size: str = "base",
        language: str = "id",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self._language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._load_failed = False

    @property
    def language(self) -> str:
        return self._language

    def _ensure_model(self):
        if self._model is not None or self._load_failed:
            return self._model
        try:
            from faster_whisper import WhisperModel  # lazy import opsional

            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        except Exception:
            self._load_failed = True
            self._model = None
        return self._model

    def is_available(self) -> bool:
        return self._ensure_model() is not None

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        if not audio_bytes:
            return ""
        model = self._ensure_model()
        if model is None:
            return ""
        try:
            import numpy as np

            pcm = array.array("h")
            usable = len(audio_bytes) - (len(audio_bytes) % 2)
            pcm.frombytes(audio_bytes[:usable])
            floats = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

            # faster-whisper mengharapkan audio 16 kHz mono; resample bila perlu.
            sr = int(sample_rate) or 16000
            if sr != 16000 and floats.size > 0:
                from scipy.signal import resample_poly

                g = math.gcd(16000, sr)
                floats = resample_poly(floats, 16000 // g, sr // g).astype(np.float32)

            segments, _info = model.transcribe(
                floats, language=self._language, beam_size=5, vad_filter=True
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception:
            return ""
