"""Domain Port: AudioPlayerPort.

Mendefinisikan kontrak abstrak untuk pemutaran audio dan callback sinkronisasi bibir (lip-sync).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Iterable, Optional


class AudioPlayerPort(ABC):
    """Port abstrak untuk pemutaran audio in-memory dengan realtime lip-sync."""

    @abstractmethod
    def play(
        self,
        audio_bytes: bytes,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = True,
    ) -> bool:
        """Memutar audio WAV bytes ke output speaker."""
        pass

    @abstractmethod
    def play_stream(
        self,
        audio_stream: Iterable[bytes],
        on_lip_sync: Optional[Callable[[float], None]] = None,
        on_chunk_start: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Memutar stream audio multi-chunk WAV secara kontinyu tanpa mereset bibir antar chunk."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Menghentikan pemutaran audio yang sedang berjalan."""
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Status apakah audio sedang diputar."""
        pass
