"""Domain Entity: MoodState.

Mengelola dimensi suasana hati (valensi dan arousal) serta transisi emosional HuoHuo.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class MoodState:
    valensi: float
    arousal: float
    label: str

    @classmethod
    def awal(cls) -> MoodState:
        """Kondisi awal HuoHuo saat pertama kali aktif."""
        return cls(valensi=0.6, arousal=0.5, label="Tenang / Santai")

    @classmethod
    def perbarui(cls, sekarang: MoodState, emosi: Optional[str]) -> MoodState:
        """Memperbarui suasana hati berdasarkan emosi yang diekspresikan."""
        if not emosi:
            return sekarang

        e = emosi.strip().lower().replace("[", "").replace("]", "")
        v, a = sekarang.valensi, sekarang.arousal

        peta_delta = {
            "senyum": (0.1, 0.05),
            "goda": (0.05, 0.15),
            "sebal": (-0.15, 0.1),
            "kaget": (0.0, 0.2),
            "bingung": (-0.05, 0.05),
            "lelah": (-0.05, -0.15),
            "semangat": (0.15, 0.2),
            "sedih": (-0.2, -0.1),
            "netral": (0.0, 0.0),
        }

        dv, da = peta_delta.get(e, (0.0, 0.0))
        valensi_baru = max(-1.0, min(1.0, v + dv))
        arousal_baru = max(0.0, min(1.0, a + da))

        return cls(
            valensi=valensi_baru,
            arousal=arousal_baru,
            label=cls._tentukan_label(valensi_baru, arousal_baru),
        )

    @staticmethod
    def _tentukan_label(v: float, a: float) -> str:
        if v >= 0.4 and a >= 0.5:
            return "Ceria / Antusias"
        elif v >= 0.3 and a < 0.5:
            return "Tenang / Santai"
        elif v < -0.2 and a >= 0.5:
            return "Sebal / Tsundere"
        elif v < -0.2 and a < 0.5:
            return "Lelah / Lesu"
        return "Netral / Standby"

    def suasana(self) -> str:
        return f"{self.label} (Valensi: {self.valensi:.2f}, Arousal: {self.arousal:.2f})"
