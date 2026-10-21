"""Domain Port: TTSPort.

Mendefinisikan kontrak abstrak untuk sintesis suara teks-ke-ucapan (TTS).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class TTSPort(ABC):
    """Port abstrak untuk Text-to-Speech synthesis."""

    @abstractmethod
    def synthesize(self, text: str) -> Optional[bytes]:
        """Menghasilkan audio WAV dalam bentuk bytes dari teks input."""
        pass
