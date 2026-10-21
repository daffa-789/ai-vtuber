"""Adapter: MarkdownVaultRepository.

Implements MemoryVaultPort using Obsidian-compatible Markdown files with YAML frontmatter.
Atomic file writes ensure data integrity across crashes.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from huohuo.config import config
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort


class MarkdownVaultRepository(MemoryVaultPort):
    """Concrete repository for persona, facts, mood, and chat history in Markdown."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        if root_dir is None:
            self.root = Path(config.memory_dir)
        else:
            self.root = Path(root_dir)

    def _read_file(self, rel_path: str) -> Optional[str]:
        target = self.root / rel_path
        if not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def _write_file(self, rel_path: str, content: str) -> None:
        target = self.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_suffix(f".{os.getpid()}.tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(target)

    def load_persona(self) -> str:
        """Load character persona markdown or return default."""
        content = self._read_file("persona.md")
        if content:
            return content
        fallback = self._read_file("huohuo-persona.md")
        return fallback or "HuoHuo: gamer girl & hacker jenius."

    def load_facts(self) -> str:
        """Load bulleted facts remembered about Master."""
        text = self._read_file("Fakta.md")
        if not text:
            return ""
        facts = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- "):
                val = line[2:].strip()
                if val and not val.startswith("_"):
                    facts.append(val)
        return "\n".join(f"- {f}" for f in facts)

    def load_mood(self) -> Optional[MoodState]:
        """Load latest mood state from Mood.md."""
        text = self._read_file("Mood.md")
        if not text:
            return None

        def extract_num(key: str) -> float:
            m = re.search(rf"{key}: (-?[\d.]+)", text)
            return float(m.group(1)) if m else float("nan")

        valensi = extract_num("Valensi")
        arousal = extract_num("Energi")  # Energi maps to arousal

        if valensi != valensi or arousal != arousal:
            return None

        # Re-derive label
        return MoodState(
            valensi=valensi,
            arousal=arousal,
            label=MoodState._tentukan_label(valensi, arousal),
        )

    def save_mood(self, mood: MoodState) -> None:
        """Save mood state to Mood.md with YAML frontmatter."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()
        lines = [
            f"Valensi: {mood.valensi:.2f} (-1 berat .. +1 senang)",
            f"Energi: {mood.arousal:.2f}",
            f"Afinitas: 0.85",
            f"Label: {mood.label}",
            f"Terakhir diperbarui: {now_iso}",
        ]

        content = (
            "---\n"
            "type: memory\n"
            "kind: karakter\n"
            "wilayah: waifu\n"
            'name: "mood-huohuo"\n'
            'description: "Suasana hati HuoHuo saat ini"\n'
            'project: "Desktop AI VTUBER"\n'
            f'updated: "{today}"\n'
            "tags:\n"
            '  - "memory/karakter"\n'
            '  - "wilayah/waifu"\n'
            '  - "project/Desktop AI VTUBER"\n'
            "links:\n"
            '  - "[[huohuo-persona]]"\n'
            '  - "[[Fakta]]"\n'
            '  - "[[Riwayat]]"\n'
            "---\n\n"
            "# Suasana hati HuoHuo saat ini\n\n"
            + "\n".join(lines)
            + "\n"
        )
        self._write_file("Mood.md", content)

    def record_history(self, user_text: str, reply_text: str) -> None:
        """Append user interaction to Riwayat/YYYY-MM-DD.md."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        rel_path = f"Riwayat/{today}.md"

        old_content = self._read_file(rel_path) or ""
        old_lines = [b for b in old_content.splitlines() if b.startswith("- ")]
        old_lines.append(f"- [{now_time}] Master: {user_text}")
        old_lines.append(f"- [{now_time}] HuoHuo: {reply_text}")

        content = (
            "---\n"
            "type: memory\n"
            "kind: riwayat\n"
            f'name: "riwayat-{today}"\n'
            f'description: "Riwayat percakapan {today}"\n'
            f'updated: "{today}"\n'
            "---\n\n"
            f"# Riwayat percakapan {today}\n\n"
            + "\n".join(old_lines)
            + "\n"
        )
        self._write_file(rel_path, content)
