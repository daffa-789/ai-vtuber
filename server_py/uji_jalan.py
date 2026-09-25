"""Uji "server ini benar-benar bisa naik" -- tanpa mengikat port.

Alasan berkas ini ada: banner startup ditulis sebagai kode di dalam utama(), jadi
kesalahan di dalamnya baru kelihatan setelah prosesnya mati. Dua kali mode normal
(non-stub) mati begitu saja karena baris print-nya sendiri -- py_compile lolos,
karena yang salah adalah nama variabel yang baru dipakai saat jalan. Tes ini
menutup celah itu dengan memanggil banner di DUA mode, plus mengimpor semua modul.

Yang TIDAK ditutup: galat di dalam penanganan request (itu ranji uji_kontrak.py)
dan galat yang cuma muncul kalau Gemini benar-benar dipanggil.

  .venv\\Scripts\\python.exe server_py\\uji_jalan.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODUL = ["konfig", "memori", "vault", "gemini", "statis", "app"]
gagal = 0


def cek(label: str, lolos: bool, detail: str = "") -> None:
    global gagal
    print(f"{'PASS' if lolos else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")
    if not lolos:
        gagal += 1


for nama in MODUL:
    try:
        importlib.import_module(nama)
        cek(f"impor {nama}.py", True)
    except Exception as err:  # noqa: BLE001 - justru galat inilah yang dicari
        cek(f"impor {nama}.py", False, f"{type(err).__name__}: {err}")

aplikasi = sys.modules.get("app")
if aplikasi is None:
    cek("banner", False, "app.py tidak terimpor, banner tidak bisa diuji")
else:
    stub_asli = aplikasi.STUB
    try:
        aplikasi.STUB = False
        try:
            normal = aplikasi.baris_banner(8787)
        except Exception as err:  # noqa: BLE001
            normal = f"__RAUH__ {type(err).__name__}: {err}"
        aplikasi.STUB = True
        try:
            tiruan = aplikasi.baris_banner(8787)
        except Exception as err:  # noqa: BLE001
            tiruan = f"__RAUH__ {type(err).__name__}: {err}"
    finally:
        aplikasi.STUB = stub_asli

    cek(
        "banner mode normal tidak rokoh",
        "__RAUH__" not in normal and aplikasi.MODEL in normal and "stub" not in normal,
        normal,
    )
    cek(
        "banner mode stub mengaku stub dan mengaku diam",
        "__RAUH__" not in tiruan and "stub" in tiruan and "diam" in tiruan,
        tiruan,
    )

print(f"\n{'PASS' if gagal == 0 else 'FAIL'} {gagal} galat dari {len(MODUL) + 2} pemeriksaan")
sys.exit(1 if gagal else 0)
