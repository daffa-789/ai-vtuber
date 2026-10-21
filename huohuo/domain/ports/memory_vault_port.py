"""Domain Port: MemoryVaultPort.

Mendefinisikan kontrak abstrak untuk membaca dan menyimpan fakta Master, suasana hati, dan riwayat obrolan harian.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from huohuo.domain.entities.mood import MoodState


class MemoryVaultPort(ABC):
    """Port abstrak untuk persistensi memori karakter."""

    @abstractmethod
    def load_persona(self) -> str:
        """Membaca isi teks persona karakter."""
        pass

    @abstractmethod
    def load_facts(self) -> str:
        """Membaca ringkasan fakta tentang Master."""
        pass

    @abstractmethod
    def load_mood(self) -> Optional[MoodState]:
        """Membaca status suasana hati terakhir."""
        pass

    @abstractmethod
    def save_mood(self, mood: MoodState) -> None:
        """Menyimpan status suasana hati baru."""
        pass

    @abstractmethod
    def record_history(self, user_text: str, reply_text: str) -> None:
        """Mencatat interaksi percakapan ke riwayat harian."""
        pass
