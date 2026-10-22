"""Bangun executable Windows HuoHuo memakai PyInstaller (onedir).

Pemakaian:
    uv pip install pyinstaller        # sekali saja
    python build_exe.py               # -> dist/huohuo/huohuo.exe

Catatan: modul berat opsional (torch / faster-whisper / RVC / fairseq) tidak
dibundel (dikecualikan di packaging/huohuo.spec) supaya exe ringan. Suara
timbre HuoHuo (RVC) & STT mic tetap butuh dependensi itu terpasang di
lingkungan tempat exe dijalankan; sintesis Piper memakai piper.exe eksternal.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(ROOT, "packaging", "huohuo.spec")


def main() -> int:
    if not os.path.isfile(SPEC):
        print(f"Spec tidak ditemukan: {SPEC}", file=sys.stderr)
        return 1
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller belum terpasang. Jalankan: uv pip install pyinstaller", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", SPEC]
    print("Menjalankan:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
