"""Adapter: SounddeviceInputAdapter.

Implementasi AudioInputPort memakai `sounddevice` (PortAudio). Membuka
InputStream mono 16-bit dan menerbitkan frame lewat antrean internal. Impor
dan pembukaan perangkat dilakukan malas sehingga container dapat dibangun
di lingkungan tanpa mikrofon (misalnya CI) tanpa error.
"""

from __future__ import annotations

import queue
from typing import Optional

from huohuo.domain.ports.audio_input_port import AudioInputPort


class SounddeviceInputAdapter(AudioInputPort):
    """Sumber audio mikrofon via sounddevice dengan frame PCM di antrean."""

    def __init__(self, sample_rate: int = 16000, blocksize: int = 320, device: Optional[int] = None):
        self._sample_rate = int(sample_rate)
        self.blocksize = int(blocksize)
        self.device = device
        self._stream = None
        self._frames: "queue.Queue[Optional[bytes]]" = queue.Queue(maxsize=256)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        try:
            raw = indata[:, 0].tobytes() if getattr(indata, "ndim", 1) > 1 else indata.tobytes()
            self._frames.put_nowait(raw)
        except Exception:
            pass

    def open(self) -> None:
        if self._stream is not None:
            return
        try:
            import sounddevice as sd

            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.blocksize,
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()
        except Exception:
            self._stream = None

    def read_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        if self._stream is None:
            self.open()
        if self._stream is None:
            return None
        try:
            return self._frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
