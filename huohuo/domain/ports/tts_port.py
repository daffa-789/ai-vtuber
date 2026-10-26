"""Domain Port: TTSPort.

Mendefinisikan kontrak abstrak untuk sintesis suara teks-ke-ucapan (TTS).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class TTSPort(ABC):
    """Port abstrak untuk Text-to-Speech synthesis."""

    @abstractmethod
    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        """Menghasilkan audio WAV dalam bentuk bytes dari teks input.

        `gaya` adalah deskripsi gaya/intonasi bicara (mis. "playful and teasing")
        untuk backend yang mendukungnya. Backend yang tidak mendukung -- seperti
        Piper -- boleh mengabaikannya begitu saja, jadi pemanggil tidak perlu
        tahu TTS apa yang sedang dipakai.
        """
        pass
