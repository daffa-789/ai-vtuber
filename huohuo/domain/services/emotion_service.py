"""Domain Service: EmotionParserService.

Mengekstrak tag emosi dari teks balasan LLM dan membersihkan teks untuk konsumsi pengguna.
"""

from __future__ import annotations
import re
from typing import Optional
from huohuo.domain.value_objects.emotion import EmotionTag

PATTERN_TAG = re.compile(r"^\s*\[([a-zA-Z0-9_\-]+)\]", re.UNICODE)


class EmotionParserService:
    """Parser domain untuk mengekstrak emosi resmi HuoHuo."""

    @staticmethod
    def parse(raw_text: str) -> tuple[Optional[str], str]:
        if not raw_text:
            return None, ""

        clean = raw_text.strip()
        match = PATTERN_TAG.match(clean)

        if match:
            kandidat = match.group(1).lower()
            # Buang tag kurung di awal walau tak dikenal (mis. [euforia]) supaya
            # tidak bocor ke teks; hanya emosi valid yang dikembalikan.
            teks_bersih = clean[match.end():].strip()
            if kandidat in EmotionTag.valid_tags():
                return kandidat, teks_bersih
            return None, teks_bersih

        return None, clean
