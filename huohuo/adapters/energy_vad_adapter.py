"""Adapter: EnergyVADAdapter.

Deteksi aktivitas suara berbasis energi (RMS) pada frame PCM mono 16-bit LE.
Ringan, offline, tanpa model, memakai stdlib saja. Cocok sebagai default saat
backend VAD cerdas belum terpasang.
"""

from __future__ import annotations

import array
import math

from huohuo.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)


class EnergyVADAdapter(VoiceActivityDetectionPort):
    """VAD ambang-energi sederhana."""

    # RMS di bawah nilai ini dianggap keheningan (skala int16 penuh ~32768).
    SILENCE_RMS = 500

    def __init__(self, rms_threshold: float = SILENCE_RMS):
        self.rms_threshold = float(rms_threshold)

    @staticmethod
    def rms(frame: bytes) -> float:
        """Menghitung root-mean-square amplitude frame int16 LE."""
        if not frame:
            return 0.0
        # Ambil hanya sampel utuh 16-bit.
        usable = len(frame) - (len(frame) % 2)
        samples = array.array("h")
        samples.frombytes(frame[:usable])
        if not samples:
            return 0.0
        total = sum(s * s for s in samples)
        return math.sqrt(total / len(samples))

    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        return self.rms(frame) >= self.rms_threshold
