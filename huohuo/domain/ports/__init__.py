"""Domain Ports (Abstract Interfaces)."""

from huohuo.domain.ports.audio_input_port import AudioInputPort
from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.llm_port import LLMInferencePort, LLMPort
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort
from huohuo.domain.ports.speech_to_text_port import SpeechToTextPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort

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
