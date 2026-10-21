"""Unit tests: Feature F2 — Voice-to-Voice pipeline (STT / VAD / AudioInput ports).

Semua pengujian memakai mock adapter sehingga berjalan deterministik tanpa
model Whisper, perangkat mikrofon, maupun GUI.
"""

from __future__ import annotations

import struct

from silverwolf.adapters.energy_vad_adapter import EnergyVADAdapter
from silverwolf.adapters.faster_whisper_adapter import FasterWhisperAdapter
from silverwolf.adapters.mock_audio_input_adapter import MockAudioInputAdapter
from silverwolf.adapters.mock_stt_adapter import MockSTTAdapter
from silverwolf.adapters.mock_vad_adapter import MockVADAdapter
from silverwolf.application.dtos.interaction_dto import UserInteractionRequest
from silverwolf.application.use_cases.voice_interaction_use_case import (
    VoiceInteractionUseCase,
)
from silverwolf.domain.ports.audio_input_port import AudioInputPort
from silverwolf.domain.ports.speech_to_text_port import SpeechToTextPort
from silverwolf.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)


def _pcm(value: int, n: int = 320) -> bytes:
    """Bangun frame PCM mono 16-bit LE berisi amplitudo konstan."""
    return b"".join(struct.pack("<h", value) for _ in range(n))


# ── Ports adalah abstract: tidak dapat diinstansiasi langsung ─────────────────
def test_ports_are_abstract():
    import pytest

    for port in (SpeechToTextPort, VoiceActivityDetectionPort, AudioInputPort):
        with pytest.raises(TypeError):
            port()  # type: ignore[abstract]


# ── Energy VAD ────────────────────────────────────────────────────────────────
def test_energy_vad_detects_loud_and_ignores_silence():
    vad = EnergyVADAdapter(rms_threshold=500)
    assert vad.is_speech(_pcm(12000)) is True
    assert vad.is_speech(_pcm(0)) is False
    assert vad.rms(b"") == 0.0


def test_energy_vad_rms_matches_amplitude():
    vad = EnergyVADAdapter()
    assert abs(vad.rms(_pcm(8000)) - 8000) < 1.0


# ── Mock STT / VAD / Audio input ───────────────────────────────────────────────
def test_mock_stt_returns_transcripts_in_order():
    stt = MockSTTAdapter(transcripts=["satu", "dua"])
    assert stt.transcribe(_pcm(3000)) == "satu"
    assert stt.transcribe(_pcm(3000)) == "dua"
    assert len(stt.received_audio) == 2


def test_mock_vad_and_audio_input_iteration():
    vad = MockVADAdapter(speech_frames=2)
    audio = MockAudioInputAdapter([_pcm(4000), _pcm(4000), _pcm(4000)])
    audio.open()
    frames = [audio.read_frame() for _ in range(4)]
    assert frames[:3] == [_pcm(4000)] * 3
    assert frames[3] is None
    assert vad.is_speech(_pcm(4000)) is True
    assert vad.is_speech(b"") is False


# ── Voice use case end-to-end dengan mock ─────────────────────────────────────
def test_voice_use_case_transcribes_and_responds():
    stt = MockSTTAdapter(transcripts=["Halo Silver Wolf, kamu cantik."])
    vad = MockVADAdapter(speech_frames=-1)
    audio = MockAudioInputAdapter([_pcm(9000), _pcm(9000), _pcm(9000)])

    captured: list[UserInteractionRequest] = []
    uc = VoiceInteractionUseCase(
        stt_port=stt,
        vad_port=vad,
        audio_input_port=audio,
        responder=lambda req: captured.append(req),
    )

    text = uc.execute_once(timeout_seconds=1.0, play_audio=True)
    assert text == "Halo Silver Wolf, kamu cantik."
    assert len(captured) == 1
    assert captured[0].text == text
    assert captured[0].play_audio is True


def test_voice_use_case_on_transcript_callback():
    stt = MockSTTAdapter(transcripts=["ujaran"])
    vad = MockVADAdapter(speech_frames=-1)
    audio = MockAudioInputAdapter([_pcm(9000)])
    seen: list[str] = []
    uc = VoiceInteractionUseCase(stt, vad, audio)
    out = uc.execute_once(timeout_seconds=1.0, on_transcript=seen.append)
    assert out == "ujaran"
    assert seen == ["ujaran"]


def test_voice_use_case_returns_empty_on_silence():
    stt = MockSTTAdapter(transcripts=["tidak seharusnya dipanggil"])
    vad = EnergyVADAdapter(rms_threshold=500)
    audio = MockAudioInputAdapter([_pcm(0), _pcm(0), _pcm(0)])
    uc = VoiceInteractionUseCase(stt, vad, audio)
    assert uc.transcribe_utterance(timeout_seconds=1.0) == ""


# ── Adapter nyata: degradasi anggun saat backend tidak terpasang ───────────────
def test_faster_whisper_degrades_without_package():
    adapter = FasterWhisperAdapter()
    available = adapter.is_available()
    assert isinstance(available, bool)
    result = adapter.transcribe(_pcm(3000), sample_rate=16000)
    assert isinstance(result, str)  # "" saat model/whisper belum ada, tanpa exception


# ── Wiring container: port baru terdaftar rapi ────────────────────────────────
def test_container_wires_voice_ports_and_use_case():
    from silverwolf.infrastructure.container import create_container

    stt = MockSTTAdapter(transcripts=["tes wiring"])
    vad = MockVADAdapter(speech_frames=-1)
    audio = MockAudioInputAdapter([_pcm(9000)])
    container = create_container(stt_port=stt, vad_port=vad, audio_input_port=audio)

    assert container.stt_port is stt
    assert container.vad_port is vad
    assert container.audio_input_port is audio
    assert container.voice_interaction_use_case is not None
    assert container.voice_interaction_use_case.stt is stt
