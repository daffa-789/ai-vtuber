"""Application DTOs (Data Transfer Objects)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserInteractionRequest:
    text: str
    play_audio: bool = True
    blocking_audio: bool = False


@dataclass
class InteractionResponse:
    raw_reply: str
    cleaned_reply: str
    emotion: str
    kizuna_level: int
    kizuna_stage: str
    mood_label: str
    audio_bytes: Optional[bytes] = None


@dataclass
class HeadpatResponse:
    reply_text: str
    emotion: str = "kaget"
    kizuna_level: int = 1
    audio_bytes: Optional[bytes] = None


@dataclass
class CompanionStatusDTO:
    level: int
    stage: str
    points: float
    streak_days: int
    total_messages: int
    total_touches: int
    mood_label: str


@dataclass
class StreamChunkDTO:
    chunk_id: int
    text: str
    emotion: str
    audio_bytes: Optional[bytes] = None
    is_last: bool = False

