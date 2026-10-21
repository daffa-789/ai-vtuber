"""Domain Port: CompanionUIPort.

Mendefinisikan kontrak abstrak untuk pembaruan tampilan UI Desktop Companion.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class CompanionUIPort(ABC):
    """Port abstrak untuk mengontrol antarmuka avatar dan balon obrolan."""

    @abstractmethod
    def show_bubble(self, text: str, emotion: str = "senyum") -> None:
        """Menampilkan balon dialog kata-kata Silver Wolf."""
        pass

    @abstractmethod
    def set_expression(self, emotion: str) -> None:
        """Mengubah ekspresi wajah avatar Live2D."""
        pass

    @abstractmethod
    def set_kizuna_status(self, status_text: str) -> None:
        """Memperbarui teks status ikatan/mood di pojok UI."""
        pass

    @abstractmethod
    def set_mouth_open(self, level: float) -> None:
        """Menggerakkan mulut avatar (lip-sync 0.0 - 1.0)."""
        pass
