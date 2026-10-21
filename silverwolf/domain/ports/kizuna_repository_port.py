"""Domain Port: KizunaRepositoryPort.

Mendefinisikan kontrak abstrak untuk persistensi status ikatan Kizuna.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from silverwolf.domain.entities.kizuna import KizunaState


class KizunaRepositoryPort(ABC):
    """Port abstrak untuk penyimpanan dan pembacaan KizunaState."""

    @abstractmethod
    def load(self) -> KizunaState:
        """Memuat status kizuna dari penyimpanan."""
        pass

    @abstractmethod
    def save(self, state: KizunaState) -> None:
        """Menyimpan status kizuna ke penyimpanan."""
        pass
