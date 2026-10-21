"""Domain Service: TextSpeechService & SentenceSplitter.

Membersihkan markdown, emoji, dan tanda baca yang tidak perlu diucapkan oleh TTS,
serta memecah teks menjadi potongan kalimat natural.
"""

from __future__ import annotations
import re


class TextSpeechService:
    """Membersihkan format teks dari LLM agar siap disintesis oleh mesin TTS."""

    @staticmethod
    def bersihkan_untuk_tts(teks: str) -> str:
        if not teks:
            return ""

        t = teks
        # Hapus blok kode Markdown
        t = re.sub(r"```[\s\S]*?```", "", t)
        # Hapus inline code `kode`
        t = re.sub(r"`[^`]*`", "", t)
        # Hapus bold/italic markdown (*teks* atau **teks**)
        t = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", t)
        # Hapus tag emosi [senyum], [goda], dll.
        t = re.sub(r"\[[a-zA-Z0-9_\-]+\]", "", t)
        # Hapus URL
        t = re.sub(r"https?://\S+", "", t)
        # Hapus simbol khusus Markdown
        t = re.sub(r"[#_~>`]", "", t)
        # Rapikan spasi ganda
        t = re.sub(r"\s+", " ", t).strip()

        return t


def potong_kalimat(teks: str, max_karakter: int = 120) -> list[str]:
    """Memotong paragraf menjadi potongan kalimat pendek untuk streaming TTS."""
    if not teks or not teks.strip():
        return []

    # Pisahkan berdasarkan tanda titik, tanda tanya, atau tanda seru
    raw_splits = re.split(r"(?<=[.!?])\s+", teks.strip())
    hasil: list[str] = []

    for chunk in raw_splits:
        c = chunk.strip()
        if not c:
            continue
        if len(c) <= max_karakter:
            hasil.append(c)
        else:
            # Potong berdasarkan koma jika masih terlalu panjang
            sub_splits = re.split(r"(?<=[,])\s+", c)
            temp = ""
            for sub in sub_splits:
                if len(temp) + len(sub) + 1 <= max_karakter:
                    temp = f"{temp} {sub}".strip()
                else:
                    if temp:
                        hasil.append(temp)
                    temp = sub
            if temp:
                hasil.append(temp)

    return hasil or [teks.strip()]
