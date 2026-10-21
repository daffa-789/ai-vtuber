"""Unit test untuk pipeline suara dan player."""

from huohuo.voice.pipeline import VoicePipeline
from huohuo.voice.player import AudioPlayer


def test_voice_pipeline_sintesis_piper():
    vp = VoicePipeline()
    # Sintesis kalimat singkat
    wav = vp.synthesize_piper("Halo Master!")
    assert wav is not None
    assert len(wav) > 1000
    # Cek header RIFF / WAVE
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_audio_player_state():
    player = AudioPlayer()
    assert player.is_playing is False
