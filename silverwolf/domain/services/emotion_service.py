"""Domain Service: EmotionParserService.

Mengekstrak tag emosi dari teks balasan LLM dan membersihkan teks untuk konsumsi pengguna.
"""

from __future__ import annotations
import re
from typing import Optional
from silverwolf.domain.value_objects.emotion import EmotionTag

PATTERN_TAG = re.compile(r"^\s*\[([a-zA-Z0-9_\-]+)\]", re.UNICODE)


class EmotionParserService:
    """Parser domain untuk mengekstrak emosi resmi Silver Wolf."""

    @staticmethod
    def parse(raw_text: str) -> tuple[Optional[str], str]:
        if not raw_text:
            return None, ""

        clean = raw_text.strip()
        match = PATTERN_TAG.match(clean)

        if match:
            kandidat = match.group(1).lower()
            if kandidat in EmotionTag.valid_tags():
                teks_bersih = clean[match.end():].strip()
                return kandidat, teks_bersih

        return None, clean
