"""Penyimpanan WAV sumber dan hasil RVC untuk tiap balasan."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


def simpan_wav(
    akar: Path,
    tahap: str,
    data: bytes,
    label: Optional[str] = None,
) -> Optional[Path]:
    """Arsipkan audio WAV tanpa membuat kegagalan arsip menghentikan obrolan."""
    if not data or tahap not in {"raw", "rvc"}:
        return None

    folder = Path(akar) / tahap
    nama_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", (label or "audio")).strip("_")[:24]
    cap_waktu = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    tujuan = folder / f"{cap_waktu}_{nama_label}_{uuid.uuid4().hex[:8]}.wav"
    sementara = tujuan.with_name(f".{tujuan.stem}.tmp")

    try:
        folder.mkdir(parents=True, exist_ok=True)
        sementara.write_bytes(data)
        sementara.replace(tujuan)
        return tujuan
    except OSError:
        try:
            sementara.unlink(missing_ok=True)
        except OSError:
            pass
        return None
