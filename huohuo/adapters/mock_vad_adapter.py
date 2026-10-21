"""Adapter: MockVADAdapter.

Test double untuk VoiceActivityDetectionPort. Menandai setiap frame berdimensi
bukan-nol sebagai suara sehingga alur Voice-to-Voice dapat diuji deterministik
tanpa sinyal audio nyata.
"""

from __future__ import annotations

from huohuo.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)


class MockVADAdapter(VoiceActivityDetectionPort):
    """VAD palsu: semua non-kosong adalah suara, atau pola yang dispesifikasi."""

    def __init__(self, speech_frames: int = -1):
        """speech_frames: jumlah frame pertama yang dianggap suara (-1 = semua)."""
        self._speech_frames = speech_frames
        self._seen = 0

    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        self._seen += 1
        if not frame:
            return False
        if self._speech_frames < 0:
            return True
        return self._seen <= self._speech_frames
