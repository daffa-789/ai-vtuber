"""Unduh `llama-server` binary (backend Vulkan) untuk jalur GPU terintegrasi.

Butuh internet SEKALI, lalu tidak pernah lagi: hasilnya berkas DLL/EXE di
`bin/llama/`. Model GGUF-nya TIDAK diunduh di sini -- yang sudah ada di `model/`
dipakai apa adanya.

Kenapa binary jadi dan bukan `pip install llama-cpp-python` dengan backend Vulkan:
llama-cpp-python harus dikompilasi ulang untuk tiap backend, dan mesin ini tidak
punya `cl`/`cmake`/`gcc` (sudah dikurusi 27 Sep). Rilis resmi llama.cpp menyertakan
build Windows Vulkan jadi, jadi itu satu-satunya jalur GPU yang realistis di laptop
tanpa GPU diskret.

Versi dipaku ke yang TERUKUR di mesin ini (lihat README bagian "GPU"), bukan ke
"terbaru": build llama.cpp berubah cepat dan angka 171 tok/s itu angka b11206.

Jalankan:  .venv\\Scripts\\python.exe scripts\\unduh_llama.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
TUJUAN = AKAR / "bin" / "llama"

VERSI = "b11206"
BERKAS_ZIP = f"llama-{VERSI}-bin-win-vulkan-x64.zip"
UNDUH = f"https://github.com/ggml-org/llama.cpp/releases/download/{VERSI}/{BERKAS_ZIP}"

# Ukuran zip yang kukurusi saat versi ini dipaku (27 Sep). Bukan pengganti hash:
# GitHub tidak mempublikasikan sha256 untuk aset release, jadi ini pagar "berkasnya
# tidak separuh jalan", dan hash sebenarnya dicetak supaya bisa dibandingkan nanti.
UKURAN_ZIP = 33_061_785

PERLU = ("llama-server.exe", "ggml-vulkan.dll", "ggml.dll", "ggml-base.dll")


def sha256(jalur: Path) -> str:
    h = hashlib.sha256()
    with jalur.open("rb") as f:
        for potong in iter(lambda: f.read(1024 * 1024), b""):
            h.update(potong)
    return h.hexdigest()


def unduh(ke: Path) -> bool:
    print(f"mengunduh {UNDUH}")
    try:
        with urllib.request.urlopen(UNDUH, timeout=120) as r, ke.open("wb") as f:
            total = int(r.headers.get("content-length") or 0)
            sudah = 0
            while True:
                potong = r.read(1024 * 256)
                if not potong:
                    break
                f.write(potong)
                sudah += len(potong)
                if total:
                    print(
                        f"\r  {sudah/1e6:.1f} / {total/1e6:.1f} MB",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
            print(file=sys.stderr)
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        print(f"\nGAGAL unduh: {err}", file=sys.stderr)
        print("Perlu internet sekali untuk langkah ini. Jalur CPU tetap jalan tanpa itu:", file=sys.stderr)
        print("  set VTUBER_LLM_PROVIDER=local di .env", file=sys.stderr)
        return False
    return True


def utama() -> int:
    p = argparse.ArgumentParser(description="Pasang llama-server Vulkan untuk Elaina")
    p.add_argument("--paksa", action="store_true", help="unduh ulang meski sudah terpasang")
    args = p.parse_args()

    if all((TUJUAN / n).is_file() for n in PERLU) and not args.paksa:
        print(f"sudah terpasang di {TUJUAN} -- pakai --paksa untuk menimpa")
        return 0

    TUJUAN.mkdir(parents=True, exist_ok=True)
    sementara = TUJUAN.parent / BERKAS_ZIP
    if not unduh(sementara):
        return 1

    ukuran = sementara.stat().st_size
    if ukuran != UKURAN_ZIP:
        print(
            f"WARNING: ukuran zip {ukuran} != yang dipaku {UKURAN_ZIP}. "
            "Bisa jadi GitHub mengirim berkas berbeda; lanjut, tapi bandingkan hash di bawah.",
            file=sys.stderr,
        )
    print(f"sha256 zip : {sha256(sementara)}")

    try:
        with zipfile.ZipFile(sementara) as z:
            rusak = z.testzip()
            if rusak is not None:
                print(f"zip rusak di dalam: {rusak}", file=sys.stderr)
                return 1
            z.extractall(TUJUAN)
            print(f"{len(z.namelist())} berkas diekstrak ke {TUJUAN}")
    except zipfile.BadZipFile as err:
        print(f"zip tidak valid: {err}", file=sys.stderr)
        return 1
    finally:
        sementara.unlink(missing_ok=True)

    kurang = [n for n in PERLU if not (TUJUAN / n).is_file()]
    if kurang:
        print(f"TIDAK lengkap, hilang: {kurang}", file=sys.stderr)
        return 1

    # Bukti terakhir dan paling murah: binary-nya benar-benar melihat GPU.
    import subprocess

    try:
        hasil = subprocess.run(
            [str(TUJUAN / "llama-server.exe"), "--list-devices"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(TUJUAN),
        )
        keluaran = (hasil.stdout or "") + (hasil.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as err:
        print(f"llama-server tidak bisa dijalankan: {err}", file=sys.stderr)
        return 1
    if "Vulkan" not in keluaran:
        print("llama-server jalan tapi TIDAK melihat perangkat Vulkan:", file=sys.stderr)
        print(json.dumps({"keluaran": keluaran.strip()[:400]}, ensure_ascii=False), file=sys.stderr)
        return 1
    for baris in keluaran.splitlines():
        if "Vulkan" in baris:
            print(f"  {baris.strip()}")
    print(f"\nselesai -- set VTUBER_LLM_PROVIDER=vulkan di .env lalu jalankan servernya")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
