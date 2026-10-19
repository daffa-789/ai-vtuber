"""Port EmotionTags dari C# SilverWolf.Core.Domain.EmotionTags.

Daftar tag emosi resmi Silver Wolf untuk Live2D dan TTS.
"""

from __future__ import annotations

from typing import Optional, Set

SEMUA = [
    "netral", "senyum", "semangat", "kaget", "bingung", "lelah", "goda", "sebal", "sedih"
]

_DIKENAL: Set[str] = {t.lower() for t in SEMUA}


def dikenali(tag: Optional[str]) -> bool:
    """Apakah tag dikenali oleh sistem ekspresi."""
    return tag is not None and tag.lower() in _DIKENAL


def untuk_prompt() -> str:
    """Format string tag emosi untuk prompt sistem: [netral], [senyum], ..."""
    return ", ".join(f"[{t}]" for t in SEMUA)
