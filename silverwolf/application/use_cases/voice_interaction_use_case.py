"""Use Case: VoiceInteractionUseCase.

Mengorkestrasi satu putaran input suara (Voice-to-Voice) sepenuhnya pada
abstraksi port: AudioInput -> VAD (segmentasi ujaran) -> STT -> use case
respons streaming. Layer ini tidak mengenal mikrofon, model, maupun UI,
sehingga dapat diuji penuh dengan mock adapter.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from silverwolf.application.dtos.interaction_dto import UserInteractionRequest
from silverwolf.domain.ports.audio_input_port import AudioInputPort
from silverwolf.domain.ports.speech_to_text_port import SpeechToTextPort
from silverwolf.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)

# Ambang sunyi (detik) untuk menutup ujaran setelah suara berhenti.
SILENCE_FRAMES_TO_CLOSE = 12


class VoiceInteractionUseCase:
    """Pipeline Voice-to-Voice: dengar ujaran, transkripsi, lalu respons."""

    def __init__(
        self,
        stt_port: SpeechToTextPort,
        vad_port: VoiceActivityDetectionPort,
        audio_input_port: AudioInputPort,
        responder: Optional[Callable[[UserInteractionRequest], object]] = None,
    ):
        self.stt = stt_port
        self.vad = vad_port
        self.audio = audio_input_port
        self.responder = responder
        self._stop_event = threading.Event()

    def transcribe_utterance(self, timeout_seconds: float = 8.0) -> str:
        """Merekam satu ujaran (VAD), mentranskripsinya (STT), mengembalikan teks.

        Menghasilkan string kosong bila tidak ada ujaran atau STT tidak tersedia.
        """
        frame_ms = 20.0
        frames: list[bytes] = []
        started = False
        silence_run = 0
        max_frames = int(timeout_seconds * (1000.0 / frame_ms)) + 50

        self.audio.open()
        try:
            for _ in range(max_frames):
                if self._stop_event.is_set():
                    break
                frame = self.audio.read_frame(timeout=frame_ms / 1000.0 + 0.05)
                if frame is None:
                    break
                speech = self.vad.is_speech(frame, self.audio.sample_rate)
                if speech:
                    started = True
                    silence_run = 0
                    frames.append(frame)
                elif started:
                    silence_run += 1
                    frames.append(frame)
                    if silence_run >= SILENCE_FRAMES_TO_CLOSE:
                        break
                if started and len(frames) >= max_frames:
                    break
        finally:
            self.audio.close()

        if not started or not frames:
            return ""

        pcm = b"".join(frames)
        try:
            return (self.stt.transcribe(pcm, self.audio.sample_rate) or "").strip()
        except Exception:
            return ""

    def process_utterance(
        self,
        text: str,
        play_audio: bool = True,
        blocking_audio: bool = False,
    ) -> None:
        """Mengirim hasil transkripsi ke use case respons (agak default)."""
        if not text or self.responder is None:
            return
        request = UserInteractionRequest(
            text=text, play_audio=play_audio, blocking_audio=blocking_audio
        )
        try:
            self.responder(request)
        except Exception:
            pass

    def execute_once(
        self,
        timeout_seconds: float = 8.0,
        play_audio: bool = True,
        on_transcript: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Satu putaran penuh: dengar -> transkripsi -> beri tahu -> respons."""
        text = self.transcribe_utterance(timeout_seconds=timeout_seconds)
        if text:
            if on_transcript is not None:
                try:
                    on_transcript(text)
                except Exception:
                    pass
            self.process_utterance(text, play_audio=play_audio)
        return text

    def stop(self) -> None:
        """Sinyal berhenti kooperatif untuk loop listen_forever."""
        self._stop_event.set()

    def reset(self) -> None:
        self._stop_event.clear()
