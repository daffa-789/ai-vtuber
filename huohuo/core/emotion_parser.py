"""Port EmotionParser dari C# HuoHuo.Core.Text.EmotionParser.

Aturan invarian yang dijaga:
1. Bila tidak ada tag, extract_emotion mengembalikan teks tanpa dipangkas ({clean_text: teks}),
   sedangkan clean_emotion_tags selalu memangkas (strip).
2. TagRegex untuk ekstraksi emosi tetap r'\\[([a-zA-Z]+)\\]' (case-insensitive).
3. CleanupRegex membuang semua tag [...] yang tidak mengandung spasi/baris baru (maks 40 karakter)
   dan bukan tautan Markdown [teks](url).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

TAG_REGEX = re.compile(r"\[([a-zA-Z]+)\]", re.IGNORECASE)
CLEANUP_REGEX = re.compile(r"\[[^\]\n\s]{1,40}\](?!\()\s*", re.IGNORECASE)


@dataclass(frozen=True)
class HasilEmosi:
    emotion: Optional[str]
    clean_text: str


def extract_emotion(teks: Optional[str]) -> HasilEmosi:
    """Ekstraksi tag emosi pertama dan bersihkan teks dari seluruh tag format."""
    if not teks:
        return HasilEmosi(emotion=None, clean_text=teks or "")

    match = TAG_REGEX.search(teks)
    if not match:
        # PENTING: Jangan dipangkas bila tidak ada tag
        return HasilEmosi(emotion=None, clean_text=teks)

    emosi = match.group(1).lower()
    bersih = CLEANUP_REGEX.sub("", teks).strip()
    return HasilEmosi(emotion=emosi, clean_text=bersih)


def clean_emotion_tags(teks: Optional[str]) -> str:
    """Membersihkan seluruh tag emosi/aksi tanpa mengekstrak nilai emosinya."""
    if not teks:
        return ""
    return CLEANUP_REGEX.sub("", teks).strip()


def add_emotion_tag(emosi: str, teks: str) -> str:
    """Menambahkan awalan tag emosi."""
    return f"[{emosi}] {teks}"


def emotion_to_talk_style(emosi: Optional[str], fallback: str = "neutral") -> str:
    """Memetakan tag emosi ke gaya bicara Live2D/TTS."""
    if not emosi:
        return fallback

    e = emosi.lower()
    if e in ("angry", "marah", "sebal"):
        return "angry"
    if e in ("happy", "senang", "senyum", "semangat", "goda"):
        return "happy"
    if e in ("sad", "sedih", "lelah"):
        return "sad"
    if e in ("surprised", "kaget", "bingung"):
        return "surprised"
    if e in ("relaxed", "santai"):
        return "talk"
    return fallback
