"""Unduh Cubism Core resmi Live2D ke public/.

Pengganti scripts/fetch-assets.js. Hanya satu hal yang benar-benar bisa diunduh
dari internet: core-nya. Yang dulu disalin skrip Node dari `node_modules`
(@ricky0123/vad-web dan onnxruntime-web, 83 + 6 MB) TIDAK bisa dibangkitkan ulang
lewat skrip ini -- `node_modules` sudah dihapus bersama Vite, dan itu bukan
sesuatu yang layak disembunyikan di balik port Python. Lihat --periksa.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
CORE_URL = "https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"
CORE = AKAR / "public" / "live2dcubismcore.min.js"

# Aset yang ada di disk tapi tidak bisa dibuat ulang tanpa npm.
YANG_TIDAK_BISA = {
    "public/vad": 6 * 1024 * 1024,
    "public/ort": 83 * 1024 * 1024,
}


def unduh(url: str, tujuan: Path) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:
        byte = resp.read()
    if not byte:
        raise RuntimeError("jawaban kosong")
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    sementara = tujuan.with_suffix(tujuan.suffix + ".part")
    sementara.write_bytes(byte)
    sementara.replace(tujuan)
    return byte


def periksa() -> int:
    print(f"Cubism Core : {'ADA ' if CORE.is_file() else 'HILANG'} {CORE.relative_to(AKAR)}"
          + (f" ({CORE.stat().st_size:,} B)" if CORE.is_file() else ""))
    for nama, kiraan in YANG_TIDAK_BISA.items():
        folder = AKAR / nama
        if folder.is_dir():
            isi = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
            print(f"{nama:<14}: ADA {isi:,} B -- di .gitignore, TIDAK bisa dibuat ulang tanpa npm")
        else:
            print(f"{nama:<14}: HILANG (~{kiraan // (1024*1024)} MB) dan tidak bisa diunduh dari sini")
    if not (AKAR / "public" / "models" / "penyihir").is_dir():
        print(
            "model karakter: HILANG -- folder ini tidak bisa dibangkitkan dari internet. "
            "Salinan ekspresi + penyihir.model3.json bisa diunduh dari halaman "
            "/perkakas.html; berkas .moc3/tekstur/fisika harus disalin dari mesin asalnya."
        )
    return 0


def utama() -> int:
    urai = argparse.ArgumentParser(description="sediakan aset Live2D dari internet")
    urai.add_argument("--periksa", action="store_true", help="lapor tanpa mengunduh")
    urai.add_argument("--paksa", action="store_true", help="unduh ulang walau sudah ada")
    arg = urai.parse_args()

    if arg.periksa:
        return periksa()

    if CORE.is_file() and not arg.paksa:
        print(f"sudah ada: {CORE.relative_to(AKAR)} ({CORE.stat().st_size:,} B) -- lewati")
    else:
        try:
            byte = unduh(CORE_URL, CORE)
        except (urllib.error.URLError, RuntimeError) as err:
            print(f"GALAT mengunduh Cubism Core: {err}", file=sys.stderr)
            return 1
        print(f"OK: {CORE.relative_to(AKAR)} ({len(byte):,} B)")
    print()
    return periksa()


if __name__ == "__main__":
    sys.exit(utama())
