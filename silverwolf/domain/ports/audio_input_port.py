"""Domain Port: AudioInputPort.

Kontrak abstrak untuk mengambil frame audio mentah dari mikrofon, terpisah
dari logika VAD/STT sehingga mudah disubstitusi dengan test double.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class AudioInputPort(ABC):
    """Port abstrak untuk sumber audio masukan (mikrofon / berkas / mock)."""

    @abstractmethod
    def open(self) -> None:
        """Membuka stream masukan. Aman dipanggil berulang kali."""
        pass

    @abstractmethod
    def read_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """Mengembalikan satu frame PCM mono 16-bit LE, atau None saat berhenti."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Menutup stream masukan dan membebaskan perangkat keras."""
        pass

    @property
    def sample_rate(self) -> int:
        """Laju sampel (Hz) dari frame yang diproduksi port ini."""
        return 16000
