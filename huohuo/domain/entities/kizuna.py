"""Domain Entity: KizunaState.

Menghitung tingkat keintiman/ikatan (Kizuna), streak harian, level, dan tahapan hubungan HuoHuo dengan Master.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class KizunaMilestone:
    level: int
    tahap: str
    deskripsi: str
    terbuka: bool = False
    terbuka_pada: Optional[str] = None


@dataclass
class KizunaSnapshot:
    level: int
    stage: str
    points: float
    next_level_points: float
    streak_days: int
    daily_interactions: int
    total_messages: int
    total_touches: int
    milestone_summary: str


@dataclass
class KizunaState:
    points: float = 0.0
    level: int = 1
    stage: str = "Asing"
    streak_days: int = 0
    last_interaction: Optional[str] = None
    daily_interactions: int = 0
    total_messages: int = 0
    total_touches: int = 0
    milestones: list[KizunaMilestone] = field(default_factory=list)

    @classmethod
    def create_default(cls) -> KizunaState:
        default_milestones = [
            KizunaMilestone(1, "Asing", "Pertemuan pertama, HuoHuo masih menjaga jarak dan bersikap tsundere.", True, datetime.now().isoformat()),
            KizunaMilestone(5, "Teman Main", "Mulai menganggap Master sebagai rekan game yang cukup asyik."),
            KizunaMilestone(10, "Partner Terpercaya", "Sering mengajak mabar, curhat santai, dan mulai perhatian."),
            KizunaMilestone(20, "Gamer Romantis", "Menunjukkan sisi manja, sedikit cemburu jika Master membahas orang lain."),
            KizunaMilestone(30, "Ikatan Abadi", "HuoHuo sepenuhnya mempercayai dan menyayangi Master sebagai pasangan gamer sejatinya."),
        ]
        return cls(milestones=default_milestones)

    def calculate_level(self) -> int:
        pts = self.points
        if pts < 50:
            return 1
        elif pts < 150:
            return 2
        elif pts < 300:
            return 3
        elif pts < 500:
            return 4
        elif pts < 750:
            return 5
        elif pts < 1100:
            return 6
        elif pts < 1500:
            return 7
        elif pts < 2000:
            return 8
        elif pts < 2600:
            return 9
        else:
            return min(30, 10 + int((pts - 2600) // 800))

    def calculate_stage(self, lvl: int) -> str:
        if lvl < 5:
            return "Asing / Kenalan"
        elif lvl < 10:
            return "Teman Main Game"
        elif lvl < 20:
            return "Partner Terpercaya"
        elif lvl < 30:
            return "Gamer Romantis"
        return "Ikatan Abadi"

    def record_message(self, text: str) -> KizunaSnapshot:
        """Mencatat interaksi pesan teks dan menambahkan poin kizuna."""
        pts_earned = 1.0
        if len(text) > 30:
            pts_earned += 0.5
        if any(w in text.lower() for w in ("mabar", "game", "sayang", "manis", "semangat", "hebat")):
            pts_earned += 1.0

        self.points += pts_earned
        self.total_messages += 1
        self.daily_interactions += 1
        self.last_interaction = datetime.now().isoformat()

        self.level = self.calculate_level()
        self.stage = self.calculate_stage(self.level)
        self._check_milestones()
        return self.get_snapshot()

    def record_touch(self) -> KizunaSnapshot:
        """Mencatat interaksi sentuhan / headpat avatar."""
        self.points += 0.8
        self.total_touches += 1
        self.daily_interactions += 1
        self.last_interaction = datetime.now().isoformat()

        self.level = self.calculate_level()
        self.stage = self.calculate_stage(self.level)
        self._check_milestones()
        return self.get_snapshot()

    def _check_milestones(self):
        for m in self.milestones:
            if not m.terbuka and self.level >= m.level:
                m.terbuka = True
                m.terbuka_pada = datetime.now().isoformat()

    def get_snapshot(self) -> KizunaSnapshot:
        unlocked = [m.tahap for m in self.milestones if m.terbuka]
        summary = f"Terbuka: {', '.join(unlocked)}" if unlocked else "Belum ada"
        return KizunaSnapshot(
            level=self.level,
            stage=self.stage,
            points=self.points,
            next_level_points=float(self.level * 100),
            streak_days=self.streak_days,
            daily_interactions=self.daily_interactions,
            total_messages=self.total_messages,
            total_touches=self.total_touches,
            milestone_summary=summary,
        )

    def get_prompt_context(self) -> str:
        snap = self.get_snapshot()
        return (
            f"[STATUS IKATAN KIZUNA DENGAN MASTER]\n"
            f"- Tingkat Hubungan: Level {snap.level} ({snap.stage})\n"
            f"- Kedekatan: {snap.points:.1f} poin keintiman\n"
            f"- Riwayat: {snap.total_messages} obrolan, {snap.total_touches} sentuhan fisik\n"
            f"- Milestone: {snap.milestone_summary}\n"
            f"Instruksi Sikap: Sesuaikan responmu dengan Level {snap.level}. Semakin tinggi level, kamu semakin terbuka, sayang, dan tidak ragu menunjukkan rasa cemburu bila Master mengabaikanmu."
        )
