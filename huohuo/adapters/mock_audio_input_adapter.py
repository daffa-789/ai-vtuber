"""Adapter: MockAudioInputAdapter.

Test double AudioInputPort yang menghasilkan frame PCM dari daftar yang
telah disiapkan, lalu None. Memungkinkan pengujian alur Voice-to-Voice
tanpa perangkat mikrofon fisik.
"""

from __future__ import annotations

from typing import Iterable, Optional

from huohuo.domain.ports.audio_input_port import AudioInputPort


class MockAudioInputAdapter(AudioInputPort):
    """Sumber audio palsu dari frame-frame yang disediakan."""

    def __init__(self, frames: Iterable[bytes], sample_rate: int = 16000):
        self._all_frames = list(frames)
        self._sample_rate = int(sample_rate)
        self._index = 0
        self._open = False

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def open(self) -> None:
        self._open = True

    def read_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        if self._index >= len(self._all_frames):
            return None
        frame = self._all_frames[self._index]
        self._index += 1
        return frame

    def close(self) -> None:
        self._open = False
        self._index = 0
