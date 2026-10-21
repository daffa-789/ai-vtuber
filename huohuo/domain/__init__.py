"""HuoHuo Domain Layer.

Contains pure business logic, entities, value objects, domain services, and ports.
Free of external I/O or framework dependencies.
"""

from huohuo.domain.entities.character import Character, MemoryEntry
from huohuo.domain.entities.chat_message import ChatMessage, ChatRole
from huohuo.domain.entities.kizuna import KizunaMilestone, KizunaSnapshot, KizunaState
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.value_objects.emotion import EmotionTag

__all__ = [
    "Character",
    "ChatMessage",
    "ChatRole",
    "EmotionTag",
    "KizunaMilestone",
    "KizunaSnapshot",
    "KizunaState",
    "MemoryEntry",
    "MoodState",
]