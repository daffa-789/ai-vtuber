"""Penyimpanan posisi jendela companion antarjalankan (fitur F3).

Dipisah dari `huohuo/ui/app.py`: dua fungsi murni tanpa keadaan, jadi bisa
diuji tanpa membuka jendela sama sekali.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple


def baca_posisi(path) -> Tuple[Optional[int], Optional[int]]:
    """Baca koordinat jendela terakhir; kembalikan (None, None) bila tidak ada/invalid."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        x, y = int(data["x"]), int(data["y"])
        return (x, y) if x >= 0 and y >= 0 else (None, None)
    except Exception:
        return (None, None)


def simpan_posisi(path, x, y) -> None:
    """Simpan koordinat jendela terakhir ke berkas konfigurasi lokal."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"x": int(x), "y": int(y)}), encoding="utf-8")
    except Exception:
        pass
