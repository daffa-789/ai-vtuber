"""Sediakan model Whisper lokal untuk STT (butuh internet sekali per model).

Model disimpan di `aset/suara/whisper/<nama>/` dan sesudah itu tidak pernah disentuh
lagi: `stt_whisper.py` membukanya langsung dari disk, tanpa HuggingFace hub, tanpa
cek versi, tanpa koneksi.

Kenapa faster-whisper (CTranslate2) dan bukan whisper.cpp: whisper.cpp tidak
mengeluarkan binary Windows jadi di rilis v1.9.4 (sudah dikurusi 27 Sep -- hanya
source zip), dan mesin ini tidak punya compiler. CTranslate2 punya wheel jadi.
Kenapa bukan OpenVINO/Vosk: Vosk tidak punya model bahasa Indonesia sama sekali
(halaman modelnya kukurusi: 0 hasil), OpenVINO menarik ±1,5 GB lagi.

Jalankan:  .venv\\Scripts\\python.exe scripts\\sedia_stt.py --model base,small
          .venv\\Scripts\\python.exe scripts\\sedia_stt.py --periksa
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
TUJUAN = AKAR / "aset" / "suara" / "whisper"

# repo HuggingFace -> folder lokal. Ukuran = berkas model.bin yang terukur saat
# skrip ini ditulis; dipakai --periksa untuk mengenali unduhan separuh jalan.
MODEL = {
    "base": {"repo": "Systran/faster-whisper-base", "perkiraan_mb": 74},
    "small": {"repo": "Systran/faster-whisper-small", "perkiraan_mb": 244},
    "medium": {"repo": "Systran/faster-whisper-medium", "perkiraan_mb": 968},
}
BERKAS_WAJIB = ("model.bin", "config.json", "tokenizer.json")


def sudah_ada(nama: str) -> bool:
    folder = TUJUAN / nama
    return folder.is_dir() and all((folder / b).is_file() for b in BERKAS_WAJIB)


def utama() -> int:
    p = argparse.ArgumentParser(description="Unduh model Whisper untuk /api/stt offline")
    p.add_argument("--model", default="base", help="dipisah koma: base,small,medium")
    p.add_argument("--periksa", action="store_true", help="lapor keadaan, jangan unduh")
    p.add_argument("--paksa", action="store_true", help="unduh ulang meski sudah ada")
    args = p.parse_args()

    nama_diminta = [m.strip() for m in args.model.split(",") if m.strip()]
    for n in nama_diminta:
        if n not in MODEL:
            print(f"model tak dikenal: {n} (pilihan: {', '.join(MODEL)})", file=sys.stderr)
            return 2

    if args.periksa:
        for n in nama_diminta:
            tanda = "ADA" if sudah_ada(n) else "BELUM"
            folder = TUJUAN / n
            mb = (
                sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / 1e6
                if folder.is_dir()
                else 0
            )
            print(f"{tanda:5} {n:7} {mb:7.0f} MB  {folder}")
        return 0 if all(sudah_ada(n) for n in nama_diminta) else 1

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub tidak ada (ikut dipasang bersama faster-whisper)", file=sys.stderr)
        return 1

    TUJUAN.mkdir(parents=True, exist_ok=True)
    gagal = 0
    for n in nama_diminta:
        if sudah_ada(n) and not args.paksa:
            print(f"{n}: sudah ada, dilewati (--paksa untuk menimpa)")
            continue
        print(f"mengunduh {MODEL[n]['repo']} -> {TUJUAN / n}")
        try:
            snapshot_download(
                repo_id=MODEL[n]["repo"],
                local_dir=str(TUJUAN / n),
                allow_patterns=list(BERKAS_WAJIB) + ["vocabulary.txt", "preprocessor_config.json"],
            )
        except Exception as err:  # jaringan, disk, atau repo berubah
            print(f"  GAGAL {n}: {err}", file=sys.stderr)
            gagal += 1
            continue
        if not sudah_ada(n):
            print("  hasil tidak lengkap:", BERKAS_WAJIB, file=sys.stderr)
            gagal += 1
        else:
            mb = sum(f.stat().st_size for f in (TUJUAN / n).rglob("*") if f.is_file()) / 1e6
            print(f"  selesai: {mb:.0f} MB")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(utama())
