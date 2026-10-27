"""Adapter for local Supertonic 3 speech synthesis."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from threading import RLock
from typing import Optional

from huohuo.config import AppConfig, config
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.services.text_speech_service import TextSpeechService
from huohuo.infrastructure.audio_artifacts import simpan_wav


class SupertonicTTSAdapter(TTSPort):
    """Synthesize Indonesian locally, then archive the raw WAV before RVC."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config
        self._engine = None
        self._voice_style = None
        self._lock = RLock()

    @property
    def tersedia(self) -> bool:
        """Only activate when both the SDK and downloaded model are present."""
        model_dir = Path(self.cfg.supertonic_model_dir)
        return (
            importlib.util.find_spec("supertonic") is not None
            and model_dir.is_dir()
            and any(model_dir.rglob("*.onnx"))
            and (model_dir / "voice_styles").is_dir()
        )

    def _muat(self):
        if self._engine is None:
            from supertonic import TTS

            self._engine = TTS(
                model="supertonic-3",
                model_dir=str(self.cfg.supertonic_model_dir),
                auto_download=False,
                intra_op_num_threads=2,
                inter_op_num_threads=1,
            )
            self._voice_style = self._engine.get_voice_style(
                voice_name=self.cfg.supertonic_voice
            )
        return self._engine, self._voice_style

    def _intonasi(self, gaya: Optional[str]) -> tuple[str, float, str]:
        """Map HuoHuo's emotions to subtle speed and supported expression tags."""
        deskripsi = (gaya or "").lower()
        speed = float(self.cfg.supertonic_speed)
        ekspresi = ""
        label = "netral"

        if any(k in deskripsi for k in ("frightened", "anxious")):
            ekspresi, speed, label = "<breath> ", min(speed, 0.88), "takut"
        elif any(k in deskripsi for k in ("nervous", "timid")):
            ekspresi, speed, label = "<breath> ", min(speed, 0.89), "gugup"
        elif any(k in deskripsi for k in ("embarrassed", "hesitant")):
            ekspresi, speed, label = "<breath> ", min(speed, 0.91), "malu"
        elif "startled" in deskripsi or "surprised" in deskripsi:
            ekspresi, speed, label = "<breath> ", max(speed, 0.98), "kaget"
        elif "confused" in deskripsi or "uncertain" in deskripsi:
            ekspresi, speed, label = "<breath> ", min(speed, 0.92), "bingung"
        elif "sad" in deskripsi:
            ekspresi, speed, label = "<sigh> ", min(speed, 0.91), "sedih"
        elif "tired" in deskripsi or "sleepy" in deskripsi:
            ekspresi, speed, label = "<sigh> ", min(speed, 0.88), "lelah"
        elif "annoyed" in deskripsi or "pouting" in deskripsi:
            speed, label = max(speed, 0.97), "sebal"
        elif "excited" in deskripsi or "energetic" in deskripsi:
            speed, label = max(speed, 1.00), "semangat"
        elif "playful" in deskripsi or "teasing" in deskripsi:
            speed, label = max(speed, 0.96), "goda"
        elif "smiling" in deskripsi or "warm" in deskripsi:
            speed, label = max(speed, 0.96), "senyum"

        return ekspresi, min(1.15, max(0.7, speed)), label

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        cleaned_text = TextSpeechService.bersihkan_untuk_tts(text)
        if not cleaned_text or not self.tersedia:
            return None

        ekspresi, speed, label = self._intonasi(gaya)
        spoken_text = f"{ekspresi}{cleaned_text}"
        tmp_path: Optional[Path] = None
        try:
            with self._lock:
                engine, voice_style = self._muat()
                audio, _duration = engine.synthesize(
                    spoken_text,
                    voice_style=voice_style,
                    total_steps=int(self.cfg.supertonic_steps),
                    speed=speed,
                    lang="id",
                    verbose=False,
                )
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                engine.save_audio(audio, str(tmp_path))
                wav_bytes = tmp_path.read_bytes()

            if not wav_bytes:
                return None
            simpan_wav(
                getattr(self.cfg, "audio_output_dir", config.audio_output_dir),
                "raw",
                wav_bytes,
                label,
            )
            return wav_bytes
        except Exception as galat:  # noqa: BLE001
            print(f"[TTS] Supertonic gagal ({type(galat).__name__})")
            return None
        finally:
            if tmp_path and tmp_path.is_file():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
