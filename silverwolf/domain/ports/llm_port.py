"""Domain Port: LLMInferencePort.

Mendefinisikan kontrak abstrak untuk inferensi model bahasa (LLM).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generator, Optional


class LLMInferencePort(ABC):
    """Port abstrak untuk inferensi model bahasa."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        """Menghasilkan pasangan (emosi, teks_balasan) dari daftar pesan percakapan."""
        pass

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """Stream token-by-token completion dari model bahasa."""
        pass


# Alias kompatibilitas
LLMPort = LLMInferencePort
