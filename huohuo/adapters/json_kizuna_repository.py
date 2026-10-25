"""Adapter: JsonKizunaRepository.

Implements KizunaRepositoryPort using JSON file persistence with atomic writes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from huohuo.config import config
from huohuo.domain.entities.kizuna import KizunaMilestone, KizunaState
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort


class JsonKizunaRepository(KizunaRepositoryPort):
    """Concrete repository for persisting KizunaState to JSON."""

    def __init__(self, file_path: Optional[Path | str] = None):
        if file_path is None:
            self.file_path = config.memory_dir / "kizuna" / "huohuo_kizuna_v1.json"
        else:
            self.file_path = Path(file_path)

    def load(self) -> KizunaState:
        """Load KizunaState from JSON file or return default."""
        if not self.file_path.is_file():
            state = KizunaState.create_default()
            self.save(state)
            return state

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            milestones = [
                KizunaMilestone(
                    level=m["level"],
                    tahap=m["tahap"],
                    deskripsi=m["deskripsi"],
                    terbuka=m.get("terbuka", False),
                    terbuka_pada=m.get("terbuka_pada"),
                )
                for m in data.get("milestones", [])
            ]
            state = KizunaState(
                points=data.get("points", 0.0),
                level=data.get("level", 1),
                stage=data.get("stage", "Asing"),
                streak_days=data.get("streak_days", 0),
                last_interaction=data.get("last_interaction"),
                daily_interactions=data.get("daily_interactions", 0),
                total_messages=data.get("total_messages", 0),
                total_touches=data.get("total_touches", 0),
                milestones=milestones,
                energi=data.get("energi", 100),
                aktivitas=data.get("aktivitas", "mengobrol"),
                quest=data.get("quest", ""),
            )
            return state
        except Exception:
            return KizunaState.create_default()

    def save(self, state: KizunaState) -> None:
        """Persist KizunaState atomically to JSON file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "points": state.points,
            "level": state.level,
            "stage": state.stage,
            "streak_days": state.streak_days,
            "last_interaction": state.last_interaction,
            "daily_interactions": state.daily_interactions,
            "total_messages": state.total_messages,
            "total_touches": state.total_touches,
            "energi": state.energi,
            "aktivitas": state.aktivitas,
            "quest": state.quest,
            "milestones": [
                {
                    "level": m.level,
                    "tahap": m.tahap,
                    "deskripsi": m.deskripsi,
                    "terbuka": m.terbuka,
                    "terbuka_pada": m.terbuka_pada,
                }
                for m in state.milestones
            ],
        }

        temp_path = self.file_path.with_suffix(f".{os.getpid()}.tmp")
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(self.file_path)
