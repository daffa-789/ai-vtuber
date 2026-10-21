"""Domain Port: SpeechToTextPort.

Kontrak abstrak untuk mentranskripsikan audio (suara Master) menjadi teks,
tanpa dependensi pada library STT atau perangkat keras fisik mana pun.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class SpeechToTextPort(ABC):
    """Port abstrak untuk transkripsi wicara-ke-teks (Bahasa Indonesia)."""

    @property
    def language(self) -> str:
        """Kode bahasa bawaan transkripsi (ISO-639-1)."""
        return "id"

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Mentranskripsikan PCM mono 16-bit little-endian menjadi teks.

        Mengembalikan string kosong bila audio tidak dapat ditranskripsikan
        (misalnya backend/model tidak tersedia), tanpa melempar exception.
        """
        pass

    def is_available(self) -> bool:
        """Status apakah backend STT nyata siap dipakai (mock selalu True)."""
        return True
