"""Adapter: MockSTTAdapter.

Test double untuk SpeechToTextPort. Mengembalikan transkrip yang telah
ditentukan sebelumnya, memungkinkan use case Voice-to-Voice diuji tanpa
model Whisper atau perangkat mikrofon.
"""

from __future__ import annotations

from typing import Optional

from huohuo.domain.ports.speech_to_text_port import SpeechToTextPort


class MockSTTAdapter(SpeechToTextPort):
    """STT palsu yang mengembalikan daftar transkrip berurutan."""

    def __init__(self, transcripts: Optional[list[str]] = None, language: str = "id"):
        self._transcripts = list(transcripts) if transcripts else ["Halo HuoHuo."]
        self._call_index = 0
        self._language = language
        self.received_audio: list[tuple[int, int]] = []

    @property
    def language(self) -> str:
        return self._language

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        self.received_audio.append((len(audio_bytes), sample_rate))
        text = self._transcripts[self._call_index % len(self._transcripts)]
        self._call_index += 1
        return text
