"""Dua-klik: Silver Wolf muncul di desktop tanpa satu pun jendela konsol.

Berkas .pyw di Windows dijalankan pythonw.exe -- interpreter yang sama, tetapi
tanpa konsol. Guna utamanya persis di situ: `python.exe main.py` (dulu jalankan.bat)
selalu menyeret jendela hitam ke desktop, dan permintaan Master adalah tidak ada
jendela biasa selain karakternya. Jejak yang dulu cuma lewat konsol sekarang masuk
var/run.log dan var/pet.log (lihat main.py: sunyikan_konsol).

Kalau yang menggenggam asosiasi .pyw di mesin ini ternyata interpreter SISTEM,
dia melompat dulu ke .venv\Scripts\pythonw.exe: pywebview, Flask, llama-cpp, dan
sisa dependensinya hanya ada di dalam venv itu.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent
VENV = AKAR / ".venv"


def beritahu(teks: str) -> None:
    """pythonw tidak punya konsol: satu-satunya jalan mengirim pesan adalah kotak."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, teks, "Silver Wolf", 0x30)
    except Exception:
        pass


def jalan() -> int:
    pythonw_venv = VENV / "Scripts" / "pythonw.exe"
    if not VENV.exists():
        beritahu(
            "Folder .venv tidak ada di samping berkas ini.\n\n"
            "Buat dulu dari konsol:\n"
            "  py -3.10 -m venv .venv\n"
            "  .venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )
        return 1
    if str(VENV) != sys.prefix and pythonw_venv.exists():
        # execv, bukan Popen: proses ini digantikan, tidak ditinggal sebagai
        # interpreter sistem yang menganggur sampai jendela pet ditutup.
        os.execv(str(pythonw_venv), [str(pythonw_venv), str(AKAR / "main.py")])

    sys.path.insert(0, str(AKAR))
    try:
        import main
    except ImportError as err:
        beritahu(
            "Dependensi belum terpasang di .venv ini.\n\n"
            "  .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n\n"
            f"Detail: {err}"
        )
        return 1
    return main.utama(None)


if __name__ == "__main__":
    raise SystemExit(jalan())
