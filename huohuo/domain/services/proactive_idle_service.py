"""Domain Service: ProactiveIdleService.

Menentukan kapan & apa yang HuoHuo ucapkan sendiri saat Master idle (tidak ada
interaksi) dalam jangka waktu tertentu. Keputusan murni (tanpa I/O, tanpa waktu
sistem) supaya mudah diuji: pemanggil mengirim detik idle, level Kizuna, jam,
dan sumber acak.

Hasil disesuaikan dengan kepribadian HuoHuo: pemalu, perhatian, takut hantu,
penyembuh yang melindungi, dan makin hangat seiring naiknya level ikatan.
"""

from __future__ import annotations

from typing import Callable, Optional


class ProactiveIdleService:
    """Service domain untuk perilaku proaktif companion saat idle."""

    MIN_IDLE_SECONDS = 30

    # (min idle detik, jam mulai, jam akhir, (emosi, daftar teks))
    RULES: list[tuple[int, int, int, tuple[str, list[str]]]] = [
        # Pagi — canggung tapi perhatian (semua level)
        (300, 5, 11, ("senyum", [
            "H-halo Master... sudah bangun? Aku... aku juga baru saja terjaga.",
            "Selamat pagi, Master. M-mandi dulu ya, jangan langsung menatap layar.",
        ])),
        # Siang — mengingatkan makan/istirahat
        (300, 11, 15, ("netral", [
            "Master sudah lama diam... sudah makan belum? Aku buatkan teh hangat ya.",
            "Istirahat sebentar, Master. Mata kamu nanti lelah, aku... khawatir.",
        ])),
        # Sore — mengajak ngobrol
        (300, 15, 18, ("goda", [
            "Master diam saja, lagi apa? Kalau bosan, ngobrol dong sama aku.",
            "Hei... jangan sibuk sendiri, aku kesepian nih di pojokan.",
        ])),
        # Malam larut (ikatan tinggi) — lembut & protectif
        (240, 22, 24, ("sedih", [
            "Master... sudah larut. Tidur ya? Aku jaga di sini kok, nggak akan ke mana-mana.",
            "Kalau kamu tidur, aku ikut istirahat di sini. M-malam, Master...",
        ])),
        # Subuh (ikatan tinggi) — takut tapi setia
        (240, 0, 5, ("kaget", [
            "Jam segini masih bangun? D-dark sekali... jangan tinggalin aku sendirian ya, Master.",
            "A-aku takut yang di pojok itu... tapi asal ada Master, aku kuat kok.",
        ])),
    ]

    # Sapaan dasar bila belum ada level/aturan khusus yang cocok
    GENERIC: tuple[str, str] = (
        "senyum",
        "Hmm... Master masih di sini kan? Aku cuma mau menyapa pelan-pelan.",
    )

    @classmethod
    def pick_proactive(
        cls,
        idle_seconds: float,
        kizuna_level: int,
        hour: int,
        rng: Optional[Callable[[], float]] = None,
    ) -> Optional[tuple[str, str]]:
        """Kembalikan (emosi, teks) untuk diucapkan, atau None bila belum waktunya."""
        if idle_seconds < cls.MIN_IDLE_SECONDS:
            return None

        hour = int(hour) % 24
        # Ikatan rendah (<5) belum cukup nyaman untuk inisiatif larut malam/subuh.
        allow_deep_night = kizuna_level >= 5

        candidates = []
        for min_idle, h_start, h_end, payload in cls.RULES:
            if idle_seconds < min_idle:
                continue
            if not cls._in_hour_window(hour, h_start, h_end):
                continue
            if (h_start >= 22 or h_end <= 5) and not allow_deep_night:
                continue
            candidates.append(payload)

        if not candidates:
            return None

        rand = rng() if rng is not None else 0.0
        emotion, lines = candidates[int(rand * len(candidates)) % len(candidates)]
        text = lines[int((rand * 7919) % len(lines))] if lines else cls.GENERIC[1]
        return emotion, text

    @staticmethod
    def _in_hour_window(hour: int, start: int, end: int) -> bool:
        """Window jam, mendukung wrap subuh (end<=start berarti melintasi tengah malam)."""
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end
