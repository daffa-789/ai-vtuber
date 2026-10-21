"""Application Use Cases."""

from huohuo.application.use_cases.process_interaction_use_case import (
    ProcessUserInteractionUseCase,
)
from huohuo.application.use_cases.synthesize_voice_use_case import (
    SynthesizeVoiceUseCase,
)
from huohuo.application.use_cases.touch_headpat_use_case import (
    TouchHeadpatUseCase,
)
from huohuo.application.use_cases.voice_interaction_use_case import (
    VoiceInteractionUseCase,
)

__all__ = [
    "ProcessUserInteractionUseCase",
    "SynthesizeVoiceUseCase",
    "TouchHeadpatUseCase",
    "VoiceInteractionUseCase",
]
