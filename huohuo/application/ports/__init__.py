"""Application Ports (Abstract Interfaces & Protocols).

Exposes all outbound and inbound ports required by application use cases.
Points to domain ports ensuring Clean Architecture layer compliance.
"""

from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.llm_port import LLMInferencePort, LLMPort
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort

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
