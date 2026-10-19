"""Port CharacterVault dan ChatHistory dari C# SilverWolf.Core.Domain.

Menyimpan dan membaca fakta jangka panjang Master, suasana hati (Mood),
serta riwayat harian dari folder `silver_wolf_memory`.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from silverwolf.core.mood import Mood


class CharacterVault:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def available(self) -> bool:
        return self.root.is_dir()

    def baca(self, nama: str) -> Optional[str]:
        jalur = self.root / nama
        if not jalur.is_file():
            return None
        try:
            return jalur.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def tulis(self, nama: str, isi: str) -> None:
        jalur = self.root / nama
        jalur.parent.mkdir(parents=True, exist_ok=True)
        # Tulis secara atomic memakai file sementara
        temp = jalur.with_suffix(f".{os.getpid()}.tmp")
        temp.write_text(isi, encoding="utf-8")
        temp.replace(jalur)

    def baca_persona(self) -> str:
        """Membaca berkas persona.md atau fallback ke teks default jika belum ada."""
        isi = self.baca("persona.md")
        if isi:
            return isi
        isi_fallback = self.baca("silverwolf-persona.md")
        return isi_fallback or "Silver Wolf: gamer girl & hacker jenius."

    def baca_fakta(self) -> List[str]:
        teks = self.baca("Fakta.md")
        if not teks:
            return []
        fakta = []
        for line in teks.splitlines():
            line = line.strip()
            if line.startswith("- "):
                isi = line[2:].strip()
                if isi and not isi.startswith("_"):
                    fakta.append(isi)
        return fakta

    def simpan_fakta(self, daftar_fakta: List[str]) -> None:
        panduan = (
            "Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.\n"
            "Hanya simpan yang pernah Master tulis sendiri atau yang terukur dari mesin ini.\n\n"
        )
        if daftar_fakta:
            isi = panduan + "\n".join(f"- {f}" for f in daftar_fakta)
        else:
            isi = panduan + "_Belum ada fakta tersimpan._"

        hari = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        konten = (
            "---\n"
            "type: memory\n"
            "kind: karakter\n"
            "wilayah: waifu\n"
            'name: "fakta-silverwolf"\n'
            'description: "Fakta yang Silver Wolf ingat tentang Master"\n'
            'project: "Desktop AI VTUBER"\n'
            f'updated: "{hari}"\n'
            "tags:\n"
            '  - "memory/karakter"\n'
            '  - "wilayah/waifu"\n'
            '  - "project/Desktop AI VTUBER"\n'
            "links:\n"
            '  - "[[silverwolf-persona]]"\n'
            '  - "[[Mood]]"\n'
            '  - "[[Riwayat]]"\n'
            "---\n\n"
            "# Fakta yang Silver Wolf ingat tentang Master\n\n"
            f"{isi}\n"
        )
        self.tulis("Fakta.md", konten)

    def baca_mood(self) -> Optional[Mood]:
        teks = self.baca("Mood.md")
        if not teks:
            return None

        def ambil_angka(kunci: str) -> float:
            m = re.search(rf"{kunci}: (-?[\d.]+)", teks)
            return float(m.group(1)) if m else float("nan")

        valensi = ambil_angka("Valensi")
        energi = ambil_angka("Energi")
        afinitas = ambil_angka("Afinitas")

        if any(v != v for v in (valensi, energi, afinitas)):  # check for NaN
            return None

        m_pertukaran = re.search(r"Pertukaran tercatat: (\d+)", teks)
        pertukaran = int(m_pertukaran.group(1)) if m_pertukaran else 0

        m_alasan = re.search(r"Alasan: (.+)", teks)
        alasan = m_alasan.group(1).strip() if m_alasan else None

        return Mood(
            valensi=valensi,
            energi=energi,
            afinitas=afinitas,
            pertukaran=pertukaran,
            alasan=alasan,
        )

    def simpan_mood(self, mood: Mood) -> None:
        hari = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        waktu_iso = datetime.now(timezone.utc).isoformat()
        baris = [
            f"Valensi: {mood.valensi:.2f} (-1 berat .. +1 senang)",
            f"Energi: {mood.energi:.2f}",
            f"Afinitas: {mood.afinitas:.2f} (0 jauh .. 1 dekat)",
            f"Pertukaran tercatat: {mood.pertukaran}",
            f"Terakhir diperbarui: {waktu_iso}",
        ]
        if mood.alasan:
            baris.append(f"Alasan: {mood.alasan}")

        konten = (
            "---\n"
            "type: memory\n"
            "kind: karakter\n"
            "wilayah: waifu\n"
            'name: "mood-silverwolf"\n'
            'description: "Suasana hati Silver Wolf saat ini"\n'
            'project: "Desktop AI VTUBER"\n'
            f'updated: "{hari}"\n'
            "tags:\n"
            '  - "memory/karakter"\n'
            '  - "wilayah/waifu"\n'
            '  - "project/Desktop AI VTUBER"\n'
            "links:\n"
            '  - "[[silverwolf-persona]]"\n'
            '  - "[[Fakta]]"\n'
            '  - "[[Riwayat]]"\n'
            "---\n\n"
            "# Suasana hati Silver Wolf saat ini\n\n"
            + "\n".join(baris)
            + "\n"
        )
        self.tulis("Mood.md", konten)

    def catat_riwayat(self, user_msg: str, assistant_msg: str) -> None:
        hari = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        jam = datetime.now().strftime("%H:%M:%S")
        nama = f"Riwayat/{hari}.md"
        lama = self.baca(nama) or ""
        baris_lama = [b for b in lama.splitlines() if b.startswith("- ")]
        baris_lama.append(f"- [{jam}] Master: {user_msg}")
        baris_lama.append(f"- [{jam}] Silver Wolf: {assistant_msg}")

        konten = (
            "---\n"
            "type: memory\n"
            "kind: riwayat\n"
            f'name: "riwayat-{hari}"\n'
            f'description: "Riwayat percakapan {hari}"\n'
            f'updated: "{hari}"\n'
            "---\n\n"
            f"# Riwayat percakapan {hari}\n\n"
            + "\n".join(baris_lama)
            + "\n"
        )
        self.tulis(nama, konten)


class ChatHistory:
    """Mengelola riwayat pesan sesi aktif."""

    def __init__(self, batas_pesan: int = 20):
        self.batas_pesan = batas_pesan
        self.pesan: List[dict] = []

    def tambah(self, role: str, content: str) -> None:
        self.pesan.append({"role": role, "content": content})
        if len(self.pesan) > self.batas_pesan * 2:
            self.pesan = self.pesan[-self.batas_pesan:]

    def ke_format_llm(self) -> List[dict]:
        return list(self.pesan)

    def bersihkan(self) -> None:
        self.pesan.clear()
