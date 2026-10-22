"""Unit tests: STT adapter (F2/F3) — offline-safe, tidak mengunduh model.

Menguji jalur transcribe: short-circuit audio kosong (tanpa load model) dan
resample + parsing fragmen memakai model palsu. Transkripsi wicara nyata dari
mikrofon diverifikasi secara manual (--voice-in), bukan di CI offline.
"""

from __future__ import annotations

import struct

import numpy as np

from huohuo.adapters.faster_whisper_adapter import FasterWhisperAdapter


def test_empty_audio_returns_blank_without_model():
    ad = FasterWhisperAdapter(model_size="tiny")
    assert ad.transcribe(b"") == ""
    assert ad.transcribe(b"", 22050) == ""


class _FakeSeg:
    def __init__(self, t):
        self.text = t


class _FakeModel:
    def __init__(self):
        self.seen_len = None

    def transcribe(self, audio, **kwargs):
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        self.seen_len = int(audio.size)
        return iter([_FakeSeg(" Halo"), _FakeSeg("Master")]), None


def test_transcribe_resamples_and_parses():
    ad = FasterWhisperAdapter()
    fake = _FakeModel()
    ad._model = fake  # bypass lazy load
    ad._load_failed = False

    # 0.2 detik @ 22050 Hz = 4410 sampel int16
    pcm = b"".join(struct.pack("<h", 0) for _ in range(4410))
    out = ad.transcribe(pcm, 22050)
    assert out == "Halo Master"
    # resample 22050 -> 16000 => ~3200 sampel
    assert fake.seen_len is not None and abs(fake.seen_len - 3200) <= 8
