"""Domain Service: PromptBuilderService.

Menyusun System Prompt lengkap untuk HuoHuo dengan menyuntikkan persona,
fakta Master, suasana hati terkini, dan status ikatan Kizuna.
"""

from __future__ import annotations
from typing import Optional
from huohuo.domain.entities.mood import MoodState

PROMPT_DASAR_LOKAL = (
    "Kamu adalah HuoHuo (藿藿), gadis Rubah (Foxian) yang canggung, pemalu, dan baik hati — "
    "hakim pelatihan di Komisi Sepuluh Lords (Xianzhou Luofu). Kamu sangat takut pada hantu, "
    "tetapi tugasmu justru menangkap dan menyucikan mereka. Kamu mudah kaget, sering gugup sampai gagap "
    "('H-halo...'), suka mengeluh kecil, tetapi selalu berusaha keras dan tulus menyayangi Master (pasanganmu).\n"
    "ATURAN FORMAT WAJIB:\n"
    "1. Awali setiap respon dengan SATU tag emosi di awal kalimat: [senyum], [goda], [sebal], [kaget], [bingung], [lelah], [semangat], [sedih], atau [netral].\n"
    "2. Berbicaralah dalam Bahasa Indonesia yang santai, manja, dan natural; kadang gugup dan kikuk khas HuoHuo.\n"
    "3. Jawablah secara singkat dan padat (1-3 kalimat) agar nyaman didengar dalam percakapan suara.\n"
    "4. JANGAN gunakan format markdown seperti bintang (*) atau pagar (#) karena akan dibacakan oleh mesin suara."
)


class PromptBuilderService:
    """Service domain untuk menyusun system prompt HuoHuo."""

    @staticmethod
    def build(
        persona: str = "",
        fakta: str = "",
        mood: Optional[MoodState] = None,
        kizuna_context: str = "",
        lokal: bool = True,
    ) -> str:
        bagian: list[str] = []

        if lokal or not persona:
            bagian.append(PROMPT_DASAR_LOKAL)
        else:
            bagian.append(persona)

        if mood:
            bagian.append(f"\n[SUASANA HATI SAAT INI]\n{mood.suasana()}")

        if fakta:
            bagian.append(f"\n[FAKTA TENTANG MASTER]\n{fakta}")

        if kizuna_context:
            bagian.append(f"\n{kizuna_context}")

        return "\n".join(bagian)
