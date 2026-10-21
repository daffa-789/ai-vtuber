"""Domain Port: VoiceActivityDetectionPort.

Kontrak abstrak untuk mendeteksi aktivitas suara (awal dan akhir ujaran)
dari stream PCM, independen dari teknik (energi, WebRTC VAD, model) yang dipakai.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator


class VoiceActivityDetectionPort(ABC):
    """Port abstrak untuk deteksi aktivitas suara (Voice Activity Detection)."""

    @abstractmethod
    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        """Menentukan apakah satu frame PCM mono 16-bit LE berisi suara."""
        pass

    def detect_segments(
        self,
        pcm_stream: Iterator[bytes],
        sample_rate: int = 16000,
    ) -> Iterator[bytes]:
        """Merangkai frame-frame audio menjadi segmen ujaran utuh.

        Default: meneruskan setiap frame yang terdeteksi sebagai suara.
        Adapter boleh mengoverride dengan agregasi segmen yang lebih cerdas.
        """
        for frame in pcm_stream:
            if self.is_speech(frame, sample_rate):
                yield frame
