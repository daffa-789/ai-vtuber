"""Domain Value Object: EmotionTag.

Mendefinisikan daftar emosi resmi yang didukung oleh model Live2D Silver Wolf.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional


class EmotionTag(str, Enum):
    SENYUM = "senyum"
    GODA = "goda"
    SEBAL = "sebal"
    KAGET = "kaget"
    BINGUNG = "bingung"
    LELAH = "lelah"
    SEMANGAT = "semangat"
    SEDIH = "sedih"
    NETRAL = "netral"

    @classmethod
    def from_str(cls, tag_str: Optional[str]) -> EmotionTag:
        """Konversi string ke EmotionTag yang valid dengan fallback ke NETRAL."""
        if not tag_str:
            return cls.NETRAL
        clean = tag_str.strip().lower().replace("[", "").replace("]", "")
        for member in cls:
            if member.value == clean:
                return member
        return cls.NETRAL

    @classmethod
    def valid_tags(cls) -> set[str]:
        return {m.value for m in cls}
