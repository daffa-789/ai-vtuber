"""Domain Port: VoiceConversionPort.

Mendefinisikan kontrak abstrak untuk konversi timbre/karakter suara (misal: RVC).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class VoiceConversionPort(ABC):
    """Port abstrak untuk Voice Conversion."""

    @abstractmethod
    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        """Mengonversi audio WAV menjadi karakter suara HuoHuo."""
        pass
