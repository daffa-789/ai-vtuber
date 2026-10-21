"""Port Mood dari C# HuoHuo.Core.Domain.Mood.

Mengelola status suasana hati HuoHuo (Valensi, Energi, Afinitas, Pertukaran)
dan memperbaruinya berdasarkan tag emosi dialog.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

NILAI_TAG = {
    "senyum": 0.25,
    "semangat": 0.35,
    "goda": 0.3,
    "netral": 0.05,
    "bingung": 0.0,
    "kaget": 0.1,
    "lelah": -0.05,
    "sedih": -0.1,
    "sebal": -0.05,
}

BASELINE_ENERGI = 0.8


def _jepit(n: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, n))


@dataclass
class Mood:
    valensi: float = 0.6
    energi: float = 0.8
    afinitas: float = 0.9
    pertukaran: int = 0
    alasan: Optional[str] = None

    @classmethod
    def awal(cls) -> Mood:
        """Kondisi awal suasana hati yang ceria dan penuh afinitas."""
        return cls(valensi=0.6, energi=0.8, afinitas=0.9, pertukaran=0)

    @classmethod
    def perbarui(cls, lama: Optional[Mood], tag: Optional[str]) -> Mood:
        """Memperbarui nilai valensi, energi, dan afinitas berdasarkan interaksi."""
        dasar = lama if lama is not None else cls.awal()
        delta = NILAI_TAG.get(tag or "netral", 0.0)
        naik_energi = 0.1 if tag in ("semangat", "goda") else 0.0

        valensi_baru = _jepit((dasar.valensi * 0.7) + (0.3 * 0.5) + (delta * 0.3), -0.4, 1.0)
        energi_baru = _jepit((dasar.energi * 0.8) + (BASELINE_ENERGI * 0.2) + naik_energi, 0.4, 1.0)
        afinitas_baru = _jepit(dasar.afinitas + 0.02, 0.4, 1.0)

        return cls(
            valensi=valensi_baru,
            energi=energi_baru,
            afinitas=afinitas_baru,
            pertukaran=dasar.pertukaran + 1,
            alasan=f"tag terakhir: {tag or 'tidak ada'}",
        )

    def suasana(self) -> str:
        """Menghasilkan kalimat konteks suasana hati untuk prompt sistem."""
        if self.valensi > 0.4 and self.energi > 0.6:
            return (
                "Kamu lagi dalam mood sangat bahagia dan ceria, "
                "suka bermanja dan menggoda pacarmu dengan manis dan usil."
            )
        if self.valensi > 0.2:
            return (
                "Kamu lagi santai, sayang banget sama pacarmu, "
                "dan senang ngobrol atau mabar bareng."
            )
        if self.valensi < -0.2:
            return (
                "Kamu lagi agak cemberut menggemaskan (tsundere manja), "
                "pengen diperhatiin dan disayang sama pacarmu."
            )
        return "Kamu santai, manis, penuh perhatian, dan senang menemani pacarmu."
