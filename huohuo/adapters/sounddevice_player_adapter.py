"""Adapter: SounddevicePlayerAdapter.

Implements AudioPlayerPort for in-memory WAV audio playback.
Features realtime RMS lip-sync event streaming and multi-backend fallback.
"""

from __future__ import annotations

import io
import threading
import time
import wave
from typing import Callable, Iterable, Optional

from huohuo.domain.ports.audio_player_port import AudioPlayerPort

try:
    import numpy as np
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except Exception:
    _HAS_SOUNDDEVICE = False

try:
    import winsound
    _HAS_WINSOUND = True
except Exception:
    _HAS_WINSOUND = False


class SounddevicePlayerAdapter(AudioPlayerPort):
    """Concrete audio player adapter using sounddevice with winsound fallback."""

    def __init__(self):
        self._playing = False
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(
        self,
        audio_bytes: bytes,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = True,
    ) -> bool:
        """Play WAV bytes in-memory and stream lip-sync levels."""
        if not audio_bytes:
            return False

        def _worker() -> None:
            with self._lock:
                self._playing = True
                try:
                    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        framerate = wf.getframerate()
                        frames = wf.readframes(wf.getnframes())

                    if _HAS_SOUNDDEVICE:
                        try:
                            dtype = np.int16 if sampwidth == 2 else np.int32
                            audio_data = np.frombuffer(frames, dtype=dtype)
                            if channels > 1:
                                audio_data = audio_data.reshape(-1, channels)

                            max_val = float(np.iinfo(dtype).max)
                            float_data = audio_data.astype(np.float32) / max_val

                            sd.play(float_data, framerate)

                            if on_lip_sync:
                                chunk_size = int(framerate * 0.05)  # 50ms window
                                total_chunks = len(audio_data) // chunk_size
                                for i in range(total_chunks):
                                    if not self._playing:
                                        break
                                    chunk = float_data[i * chunk_size : (i + 1) * chunk_size]
                                    rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                                    level = min(1.0, rms * 4.0)
                                    on_lip_sync(level)
                                    time.sleep(0.048)
                                on_lip_sync(0.0)

                            sd.wait()
                        except Exception:
                            # Fallback if sounddevice encounters device errors
                            if _HAS_WINSOUND:
                                winsound.PlaySound(
                                    audio_bytes,
                                    winsound.SND_MEMORY | winsound.SND_SYNC,
                                )
                    elif _HAS_WINSOUND:
                        winsound.PlaySound(
                            audio_bytes,
                            winsound.SND_MEMORY | winsound.SND_SYNC,
                        )
                except Exception:
                    pass
                finally:
                    self._playing = False
                    if on_lip_sync:
                        try:
                            on_lip_sync(0.0)
                        except Exception:
                            pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        if blocking:
            t.join()
        return True

    def play_stream(
        self,
        audio_stream: Iterable[bytes],
        on_lip_sync: Optional[Callable[[float], None]] = None,
        on_chunk_start: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Continuously play audio chunks without resetting mouth position to 0 between chunks."""
        with self._lock:
            self._playing = True
            chunk_idx = 0
            try:
                for audio_bytes in audio_stream:
                    if not self._playing:
                        break
                    if not audio_bytes:
                        continue

                    if on_chunk_start:
                        try:
                            on_chunk_start(chunk_idx)
                        except Exception:
                            pass
                    chunk_idx += 1

                    try:
                        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                            channels = wf.getnchannels()
                            sampwidth = wf.getsampwidth()
                            framerate = wf.getframerate()
                            frames = wf.readframes(wf.getnframes())

                        if _HAS_SOUNDDEVICE:
                            try:
                                dtype = np.int16 if sampwidth == 2 else np.int32
                                audio_data = np.frombuffer(frames, dtype=dtype)
                                if channels > 1:
                                    audio_data = audio_data.reshape(-1, channels)

                                max_val = float(np.iinfo(dtype).max)
                                float_data = audio_data.astype(np.float32) / max_val

                                sd.play(float_data, framerate)

                                if on_lip_sync:
                                    chunk_size = int(framerate * 0.05)  # 50ms window
                                    total_chunks = len(audio_data) // chunk_size
                                    for i in range(total_chunks):
                                        if not self._playing:
                                            break
                                        chunk = float_data[i * chunk_size : (i + 1) * chunk_size]
                                        rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                                        level = min(1.0, rms * 4.0)
                                        on_lip_sync(level)
                                        time.sleep(0.048)
                                    # Mouth is NOT reset to 0.0 here between consecutive chunks!

                                sd.wait()
                            except Exception:
                                if _HAS_WINSOUND:
                                    winsound.PlaySound(
                                        audio_bytes,
                                        winsound.SND_MEMORY | winsound.SND_SYNC,
                                    )
                        elif _HAS_WINSOUND:
                            winsound.PlaySound(
                                audio_bytes,
                                winsound.SND_MEMORY | winsound.SND_SYNC,
                            )
                    except Exception:
                        pass
            finally:
                self._playing = False
                if on_lip_sync:
                    try:
                        on_lip_sync(0.0)
                    except Exception:
                        pass
        return True

    def stop(self) -> None:
        """Stop current audio playback."""
        self._playing = False
        if _HAS_SOUNDDEVICE:
            try:
                sd.stop()
            except Exception:
                pass
