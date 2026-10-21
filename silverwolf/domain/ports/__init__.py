"""Domain Ports (Abstract Interfaces)."""

from silverwolf.domain.ports.audio_input_port import AudioInputPort
from silverwolf.domain.ports.audio_player_port import AudioPlayerPort
from silverwolf.domain.ports.companion_ui_port import CompanionUIPort
from silverwolf.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from silverwolf.domain.ports.llm_port import LLMInferencePort, LLMPort
from silverwolf.domain.ports.memory_vault_port import MemoryVaultPort
from silverwolf.domain.ports.speech_to_text_port import SpeechToTextPort
from silverwolf.domain.ports.tts_port import TTSPort
from silverwolf.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)
from silverwolf.domain.ports.voice_conversion_port import VoiceConversionPort

__all__ = [
    "AudioInputPort",
    "AudioPlayerPort",
    "CompanionUIPort",
    "KizunaRepositoryPort",
    "LLMInferencePort",
    "LLMPort",
    "MemoryVaultPort",
    "SpeechToTextPort",
    "TTSPort",
    "VoiceActivityDetectionPort",
    "VoiceConversionPort",
]
