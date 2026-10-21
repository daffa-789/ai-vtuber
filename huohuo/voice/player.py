"""In-memory audio player untuk HuoHuo.

Memutar data audio WAV langsung dari memori (RAM) tanpa meninggalkan berkas
sementara di disk, sesuai permintaan Master:
"simpan di memory lalu play, dan hapus berkasnya biar tidak penuh".

Mendukung callback lip-sync (RMS amplitude) agar mulut Live2D bergerak sinkron.
"""

from __future__ import annotations

import io
import threading
import time
import wave
from typing import Callable, Optional

try:
    import numpy as np
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False


class AudioPlayer:
    def __init__(self):
        self._playing = False
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play_wav_bytes(
        self,
        wav_bytes: bytes,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = False,
    ) -> None:
        """Memutar data WAV dari memori.

        Jika `on_lip_sync` diberikan, fungsi akan menghitung volume/RMS secara berkala
        dan mengirimkan nilai [0.0 .. 1.0] ke callback untuk menggerakkan mulut model.
        """
        if not wav_bytes:
            return

        def _worker():
            with self._lock:
                self._playing = True
                try:
                    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        framerate = wf.getframerate()
                        frames = wf.readframes(wf.getnframes())

                    if _HAS_SOUNDDEVICE:
                        # Konversi bytes ke numpy array untuk sounddevice
                        dtype = np.int16 if sampwidth == 2 else np.int32
                        audio_data = np.frombuffer(frames, dtype=dtype)
                        if channels > 1:
                            audio_data = audio_data.reshape(-1, channels)

                        # Normalisasi ke float32 [-1.0, 1.0]
                        max_val = float(np.iinfo(dtype).max)
                        float_data = audio_data.astype(np.float32) / max_val

                        # Putar audio
                        sd.play(float_data, framerate)

                        # Thread lipsync sederhana jika callback disediakan
                        if on_lip_sync:
                            chunk_size = int(framerate * 0.05)  # 50ms window
                            total_chunks = len(audio_data) // chunk_size
                            for i in range(total_chunks):
                                if not self._playing:
                                    break
                                chunk = float_data[i * chunk_size : (i + 1) * chunk_size]
                                rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                                # Skala RMS ke [0..1]
                                level = min(1.0, rms * 4.0)
                                on_lip_sync(level)
                                time.sleep(0.048)
                            on_lip_sync(0.0)

                        sd.wait()
                    elif _HAS_WINSOUND:
                        # Fallback ke Windows winsound dari memori
                        winsound.PlaySound(
                            wav_bytes,
                            winsound.SND_MEMORY | (winsound.SND_SYNC if blocking else winsound.SND_ASYNC),
                        )
                except Exception as err:
                    print(f"[AudioPlayer] Galat pemutaran audio: {err}")
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

    def stop(self) -> None:
        """Menghentikan pemutaran audio."""
        self._playing = False
        if _HAS_SOUNDDEVICE:
            try:
                sd.stop()
            except Exception:
                pass


# Singleton player bawaan
player = AudioPlayer()
