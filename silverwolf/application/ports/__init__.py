"""Application Ports (Abstract Interfaces & Protocols).

Exposes all outbound and inbound ports required by application use cases.
Points to domain ports ensuring Clean Architecture layer compliance.
"""

from silverwolf.domain.ports.audio_player_port import AudioPlayerPort
from silverwolf.domain.ports.companion_ui_port import CompanionUIPort
from silverwolf.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from silverwolf.domain.ports.llm_port import LLMInferencePort, LLMPort
from silverwolf.domain.ports.memory_vault_port import MemoryVaultPort
from silverwolf.domain.ports.tts_port import TTSPort
from silverwolf.domain.ports.voice_conversion_port import VoiceConversionPort

__all__ = [
    "AudioPlayerPort",
    "CompanionUIPort",
    "KizunaRepositoryPort",
    "LLMInferencePort",
    "LLMPort",
    "MemoryVaultPort",
    "TTSPort",
    "VoiceConversionPort",
]
