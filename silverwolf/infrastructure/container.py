"""Infrastructure: Composition Root / Dependency Injection Container.

Binds concrete adapters to domain/application ports and wires use cases.
Allows clean injection of real adapters or test doubles.
"""

from __future__ import annotations

from typing import Optional

from silverwolf.adapters.energy_vad_adapter import EnergyVADAdapter
from silverwolf.adapters.faster_whisper_adapter import FasterWhisperAdapter
from silverwolf.adapters.json_kizuna_repository import JsonKizunaRepository
from silverwolf.adapters.llama_server_adapter import LlamaServerAdapter
from silverwolf.adapters.markdown_vault_repository import MarkdownVaultRepository
from silverwolf.adapters.mock_stt_adapter import MockSTTAdapter
from silverwolf.adapters.piper_tts_adapter import PiperTTSAdapter
from silverwolf.adapters.rvc_adapter import RVCAdapter
from silverwolf.adapters.sounddevice_input_adapter import SounddeviceInputAdapter
from silverwolf.adapters.sounddevice_player_adapter import SounddevicePlayerAdapter
from silverwolf.adapters.webview_ui_adapter import WebviewUIAdapter
from silverwolf.application.use_cases.process_interaction_use_case import (
    ProcessUserInteractionUseCase,
)
from silverwolf.application.use_cases.stream_user_interaction_use_case import (
    StreamUserInteractionUseCase,
)
from silverwolf.application.use_cases.synthesize_voice_use_case import (
    SynthesizeVoiceUseCase,
)
from silverwolf.application.use_cases.touch_headpat_use_case import (
    TouchHeadpatUseCase,
)
from silverwolf.application.use_cases.voice_interaction_use_case import (
    VoiceInteractionUseCase,
)
from silverwolf.config import AppConfig, config
from silverwolf.domain.ports.audio_input_port import AudioInputPort
from silverwolf.domain.ports.audio_player_port import AudioPlayerPort
from silverwolf.domain.ports.companion_ui_port import CompanionUIPort
from silverwolf.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from silverwolf.domain.ports.llm_port import LLMInferencePort
from silverwolf.domain.ports.memory_vault_port import MemoryVaultPort
from silverwolf.domain.ports.speech_to_text_port import SpeechToTextPort
from silverwolf.domain.ports.tts_port import TTSPort
from silverwolf.domain.ports.voice_activity_detection_port import (
    VoiceActivityDetectionPort,
)
from silverwolf.domain.ports.voice_conversion_port import VoiceConversionPort
from silverwolf.domain.services.sentence_splitter_service import SentenceSplitterService


def build_stt_port(cfg: AppConfig) -> SpeechToTextPort:
    """Memilih adapter STT berdasarkan konfigurasi (whisper offline / mock)."""
    backend = (cfg.stt_backend or "whisper").lower()
    if backend == "mock":
        return MockSTTAdapter(language=cfg.stt_language)
    return FasterWhisperAdapter(
        model_size=cfg.stt_model,
        language=cfg.stt_language,
        device=cfg.stt_device,
    )


class Container:
    """Composition root container holding wired ports, adapters, and use cases."""

    def __init__(
        self,
        cfg: Optional[AppConfig] = None,
        llm_port: Optional[LLMInferencePort] = None,
        tts_port: Optional[TTSPort] = None,
        voice_conversion_port: Optional[VoiceConversionPort] = None,
        audio_player_port: Optional[AudioPlayerPort] = None,
        kizuna_repo: Optional[KizunaRepositoryPort] = None,
        memory_vault: Optional[MemoryVaultPort] = None,
        ui_port: Optional[CompanionUIPort] = None,
        splitter_service: Optional[SentenceSplitterService] = None,
        stt_port: Optional[SpeechToTextPort] = None,
        vad_port: Optional[VoiceActivityDetectionPort] = None,
        audio_input_port: Optional[AudioInputPort] = None,
    ):
        self.cfg = cfg or config

        # Instantiate adapters or use provided test doubles
        self.llm_port = llm_port or LlamaServerAdapter(cfg=self.cfg)
        self.tts_port = tts_port or PiperTTSAdapter(cfg=self.cfg)
        self.voice_conversion_port = voice_conversion_port or RVCAdapter(cfg=self.cfg)
        self.audio_player_port = audio_player_port or SounddevicePlayerAdapter()
        self.kizuna_repo = kizuna_repo or JsonKizunaRepository(
            self.cfg.memory_dir / "kizuna" / "silverwolf_kizuna_v1.json"
        )
        self.memory_vault = memory_vault or MarkdownVaultRepository(self.cfg.memory_dir)
        self.ui_port = ui_port or WebviewUIAdapter()

        # Voice-to-Voice input ports (STT / VAD / microphone capture)
        self.stt_port = stt_port or build_stt_port(self.cfg)
        self.vad_port = vad_port or EnergyVADAdapter(rms_threshold=self.cfg.vad_rms_threshold)
        self.audio_input_port = audio_input_port or SounddeviceInputAdapter(
            sample_rate=self.cfg.audio_input_rate,
            blocksize=self.cfg.audio_input_block,
            device=self.cfg.audio_input_device,
        )

        # Wire Use Cases
        self.synthesize_voice_use_case = SynthesizeVoiceUseCase(
            tts_port=self.tts_port,
            voice_conversion_port=self.voice_conversion_port,
            audio_player_port=self.audio_player_port,
        )

        self.process_interaction_use_case = ProcessUserInteractionUseCase(
            llm_port=self.llm_port,
            kizuna_repo=self.kizuna_repo,
            memory_vault=self.memory_vault,
            tts_port=self.tts_port,
            voice_conversion_port=self.voice_conversion_port,
            audio_player_port=self.audio_player_port,
            ui_port=self.ui_port,
        )

        self.touch_headpat_use_case = TouchHeadpatUseCase(
            kizuna_repo=self.kizuna_repo,
            tts_port=self.tts_port,
            voice_conversion_port=self.voice_conversion_port,
            audio_player_port=self.audio_player_port,
            ui_port=self.ui_port,
        )

        self.sentence_splitter_service = splitter_service or SentenceSplitterService()

        self.stream_user_interaction_use_case = StreamUserInteractionUseCase(
            llm_port=self.llm_port,
            kizuna_repo=self.kizuna_repo,
            memory_vault=self.memory_vault,
            tts_port=self.tts_port,
            voice_conversion_port=self.voice_conversion_port,
            audio_player_port=self.audio_player_port,
            ui_port=self.ui_port,
            splitter_service=self.sentence_splitter_service,
        )

        self.voice_interaction_use_case = VoiceInteractionUseCase(
            stt_port=self.stt_port,
            vad_port=self.vad_port,
            audio_input_port=self.audio_input_port,
            responder=lambda request: self.stream_user_interaction_use_case.execute_stream(request),
        )


def create_container(
    cfg: Optional[AppConfig] = None,
    **kwargs,
) -> Container:
    """Helper factory for initializing Container with default or customized ports."""
    return Container(cfg=cfg, **kwargs)
