"""Port KizunaEngine dari C# HuoHuo.Core.Domain.Kizuna.

Menjaga kompatibilitas 100% dengan berkas format `@aituber-onair/kizuna`:
- Membaca dan menulis `silver_wolf_memory/kizuna/huohuo_kizuna_v1.json`.
- Menghitung akumulasi poin ikatan, level keintiman, streak interaksi, dan riwayat.
- Menghasilkan string konteks ikatan untuk disuntikkan ke prompt sistem.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class KizunaSnapshot:
    points: float
    level: int
    streak: int
    total_interactions: int
    stage: str
    warmth: float


class KizunaEngine:
    def __init__(self, storage_path: Path | str, user_id: str = "master"):
        self.storage_path = Path(storage_path)
        self.user_id = user_id
        self._data: Dict[str, Any] = {
            "format": "@aituber-onair/kizuna",
            "version": 1,
            "users": {},
        }
        self.load()

    def load(self) -> None:
        """Memuat berkas JSON kizuna jika ada."""
        if self.storage_path.is_file():
            try:
                content = self.storage_path.read_text(encoding="utf-8")
                self._data = json.loads(content)
            except Exception:
                pass

        if "users" not in self._data:
            self._data["users"] = {}

        if self.user_id not in self._data["users"]:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._data["users"][self.user_id] = {
                "id": self.user_id,
                "displayName": self.user_id,
                "role": "guest",
                "points": 0.0,
                "level": 1,
                "achievements": [],
                "scars": [],
                "triggeredThresholds": [],
                "stats": {
                    "totalInteractions": 0,
                    "totalPointsEarned": 0.0,
                    "continuity": {
                        "streak": 1,
                        "totalActiveBuckets": 1,
                        "lastContactAt": now_iso,
                        "lastBucketKey": "",
                        "lastBucketIndex": None,
                    },
                    "favoriteEmotions": {},
                    "lastPointsEarned": now_iso,
                    "interactionHistory": [],
                    "dynamics": {
                        "warmth": 1.0,
                        "warmthUpdatedAt": now_iso,
                        "conflictChilled": False,
                        "trend": "steady",
                        "currentStage": "acquaintance",
                    },
                },
                "firstSeen": now_iso,
                "lastSeen": now_iso,
            }

    def save(self) -> None:
        """Menyimpan data kizuna ke disk secara atomik."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.storage_path.with_suffix(f".{os.getpid()}.tmp")
        temp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.storage_path)

    @property
    def user(self) -> Dict[str, Any]:
        return self._data["users"][self.user_id]

    def _resolve_stage(self, points: float) -> str:
        if points < 50:
            return "kenalan"
        if points < 150:
            return "teman_dekat"
        if points < 300:
            return "sahabat"
        return "kekasih_tercinta"

    def record_message(self, text: Optional[str] = None, points: float = 2.0) -> KizunaSnapshot:
        """Mencatat interaksi obrolan pesan dari Master."""
        u = self.user
        now_iso = datetime.now(timezone.utc).isoformat()

        u["points"] += points
        u["stats"]["totalPointsEarned"] += points
        u["stats"]["totalInteractions"] += 1
        u["lastSeen"] = now_iso
        u["stats"]["lastPointsEarned"] = now_iso

        # Hitung level: setiap 50 poin = 1 level
        u["level"] = max(1, int(u["points"] // 50) + 1)

        # Catat riwayat singkat (simpan 50 terakhir)
        history = u["stats"]["interactionHistory"]
        record = {
            "id": f"interaction_{int(time.time() * 1000)}",
            "timestamp": now_iso,
            "points": points,
            "kind": "message",
            "summary": (text or "")[:100],
        }
        history.append(record)
        if len(history) > 50:
            u["stats"]["interactionHistory"] = history[-50:]

        self.save()
        return self.get_snapshot()

    def record_touch(self) -> KizunaSnapshot:
        """Mencatat interaksi sentuhan (headpat/elusan kepala di avatar)."""
        return self.record_message(text="*elusan kepala di rambut*", points=3.5)

    def get_snapshot(self) -> KizunaSnapshot:
        u = self.user
        points = float(u.get("points", 0.0))
        level = int(u.get("level", 1))
        streak = int(u.get("stats", {}).get("continuity", {}).get("streak", 1))
        total = int(u.get("stats", {}).get("totalInteractions", 0))
        stage = self._resolve_stage(points)
        warmth = float(u.get("stats", {}).get("dynamics", {}).get("warmth", 1.0))
        return KizunaSnapshot(
            points=points,
            level=level,
            streak=streak,
            total_interactions=total,
            stage=stage,
            warmth=warmth,
        )

    def get_prompt_context(self) -> str:
        """Format konteks ikatan untuk diinjeksi ke system prompt."""
        snap = self.get_snapshot()
        tahap_teks = {
            "kenalan": "Baru mulai dekat, ramah tapi sedikit usil",
            "teman_dekat": "Teman dekat yang seru, suka bercanda dan saling ledek",
            "sahabat": "Sangat dekat dan nyaman, chemistry sangat kuat",
            "kekasih_tercinta": "Pacar resmi yang sangat sayang, mesra, manja, dan protektif",
        }.get(snap.stage, "Sangat dekat dan penuh kasih sayang")

        return (
            f"## Konteks Hubungan Ikatan (Kizuna)\n"
            f"- Status: {tahap_teks} (Level {snap.level}, {snap.points:.1f} poin ikatan)\n"
            f"- Total interaksi obrolan: {snap.total_interactions} kali bersama Master.\n"
            f"- Tunjukkan kedekatan emosional yang sesuai dengan ikatan ini."
        )
