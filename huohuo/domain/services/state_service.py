"""Domain Service: StateParserService.

Mengekstrak blok `<state>...</state>` dari balasan LLM supaya aplikasi bisa
melacak "keadaan hidup" HuoHuo (energi, aktivitas, quest) ala RyzaChat — TANPA
function-calling, cukup tag terstruktur di akhir kalimat yang dibuang dari teks.

Format yang dipahami (fleksibel, key=value dipisah ';' atau baris baru):
    <state>energi=80; aktivitas=belajar bareng; quest=nugas 3/5</state>
Key Inggris juga diterima (energy/activity/progress/mood).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

STATE_BLOCK = re.compile(r"<\s*state\s*>(.*?)<\s*/\s*state\s*>", re.IGNORECASE | re.DOTALL)

_ALIAS = {
    "energy": "energi",
    "activity": "aktivitas",
    "aktifitas": "aktivitas",
    "progress": "progres",
    "mood": "mood",
    "suasana": "mood",
}


class StateParserService:
    """Parser untuk blok <state> pada balasan karakter."""

    @staticmethod
    def parse(raw_text: str) -> Tuple[Dict[str, object], str]:
        """Kembalikan (state_dict, teks_bersih). state_dict kosong bila tak ada blok."""
        if not raw_text:
            return {}, ""

        match = STATE_BLOCK.search(raw_text)
        if not match:
            return {}, raw_text.strip()

        body = match.group(1)
        clean = (raw_text[: match.start()] + raw_text[match.end():]).strip()

        state: Dict[str, object] = {}
        for part in re.split(r"[;\n]+", body):
            if "=" not in part:
                continue
            key, _, val = part.partition("=")
            key = key.strip().lower()
            val = val.strip()
            if not key or not val:
                continue
            key = _ALIAS.get(key, key)
            if key == "energi":
                digits = re.sub(r"[^0-9]", "", val)
                if digits:
                    state["energi"] = max(0, min(100, int(digits[:3])))
            else:
                state[key] = val

        return state, clean

    @staticmethod
    def format_for_prompt(energi: int, aktivitas: str, quest: str) -> str:
        """Render keadaan terkini untuk disuntikkan ke system prompt (kontinuitas)."""
        quest_part = f" | quest: {quest}" if quest else ""
        return (
            f"[KEADAAN HATIMU SEKARANG] energi={energi}/100 | lagi: {aktivitas}{quest_part}. "
            "Sisipkan kelanjutan aktivitas/quest ini secara natural ke percakapan, dan "
            "sesekali ajak Master melakukan sesuatu bareng (biar hidup, bukan cuma menjawab)."
        )
