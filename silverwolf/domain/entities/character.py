"""Domain Entity: Character & Memory Models."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Persona:
    content: str
    version: str = "1.0"


@dataclass
class CharacterFacts:
    content: str
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


@dataclass
class MemoryEntry:
    timestamp: str
    user_message: str
    assistant_reply: str


@dataclass
class Character:
    name: str = "Silver Wolf"
    persona: str = "Gamer girl & hacker jenius"
    title: str = "Stellaron Hunter"
    lore: str = "Ahli komputasi realitas dan game retro"
