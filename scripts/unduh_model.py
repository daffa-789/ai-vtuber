"""Skrip pengunduh model LLM offline (GGUF) ke folder model/.

Mendukung unduh berlanjut (resume), progress bar, dan multi-opsi:
- Llama-3.2-1B-Instruct (bawaan, cepat untuk CPU i5, ~808 MB)
- Llama-3.2-3B-Instruct (lebih cerdas, ~2.02 GB)
- Llama-3.2-1B-Instruct-Q2_K (paling ringan, ~490 MB)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

AKAR = Path(__file__).resolve().parent.parent
FOLDER_MODEL = AKAR / "model"

DAFTAR_MODEL = {
    "llama-1b": {
        "nama": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "deskripsi": "Llama 3.2 1B Instruct (Q4_K_M, ~808 MB) - Sangat cepat di CPU",
    },
    "llama-3b": {
        "nama": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "deskripsi": "Llama 3.2 3B Instruct (Q4_K_M, ~2.02 GB) - Lebih pintar, butuh RAM/CPU lebih",
    },
    "llama-1b-ringan": {
        "nama": "Llama-3.2-1B-Instruct-Q2_K.gguf",
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q2_K.gguf",
        "deskripsi": "Llama 3.2 1B Instruct (Q2_K, ~490 MB) - Paling ringan dan hemat bandwidth",
    },
}


def format_ukuran(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} TB"


def unduh_berkas(url: str, tujuan: Path) -> bool:
    FOLDER_MODEL.mkdir(parents=True, exist_ok=True)
    berkas_sementara = tujuan.with_suffix(tujuan.suffix + ".part")

    ukuran_sudah = 0
    if berkas_sementara.exists():
        ukuran_sudah = berkas_sementara.stat().st_size

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    if ukuran_sudah > 0:
        headers["Range"] = f"bytes={ukuran_sudah}-"
        print(f"Melanjutkan unduhan dari {format_ukuran(ukuran_sudah)}...")

    try:
        with requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True) as r:
            if r.status_code == 416:  # Range not satisfiable (mungkin sudah selesai)
                total_ukuran = ukuran_sudah
            elif r.status_code not in (200, 206):
                print(f"GALAT: Server mengembalikan HTTP {r.status_code}", file=sys.stderr)
                return False
            else:
                panjang_konten = r.headers.get("content-length")
                if r.status_code == 206:
                    total_ukuran = ukuran_sudah + int(panjang_konten or 0)
                else:
                    total_ukuran = int(panjang_konten or 0)
                    ukuran_sudah = 0  # server tidak mendukung partial, mulai dari 0

            mode = "ab" if ukuran_sudah > 0 and r.status_code == 206 else "wb"
            t0 = time.time()
            terunduh_sesi = 0

            print(f"Menyimpan ke: {tujuan.relative_to(AKAR)}")
            print(f"Ukuran total: {format_ukuran(total_ukuran)}")

            with open(berkas_sementara, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    terunduh_sesi += len(chunk)
                    skrg = ukuran_sudah + terunduh_sesi
                    dt = time.time() - t0
                    kecepatan = terunduh_sesi / dt if dt > 0 else 0
                    persen = (skrg / total_ukuran * 100) if total_ukuran > 0 else 0
                    sisa_detik = ((total_ukuran - skrg) / kecepatan) if kecepatan > 0 else 0

                    bar_panjang = 25
                    isi_bar = int(bar_panjang * persen / 100)
                    bar = "=" * isi_bar + "-" * (bar_panjang - isi_bar)

                    status = (
                        f"\r[{bar}] {persen:5.1f}% | {format_ukuran(skrg)}/{format_ukuran(total_ukuran)} | "
                        f"{format_ukuran(int(kecepatan))}/s | ETA: {int(sisa_detik)}s  "
                    )
                    sys.stdout.write(status)
                    sys.stdout.flush()

        print("\nUnduhan selesai! Memvalidasi berkas...")
        if berkas_sementara.exists():
            if tujuan.exists():
                tujuan.unlink()
            berkas_sementara.rename(tujuan)
            print(f"Model siap di: {tujuan.relative_to(AKAR)} ({format_ukuran(tujuan.stat().st_size)})")
            return True
    except Exception as err:
        print(f"\nGALAT saat mengunduh: {err}", file=sys.stderr)
        print("Anda dapat menjalankan kembali skrip ini untuk melanjutkan unduhan.", file=sys.stderr)
        return False
    return False


def periksa() -> int:
    print(f"Folder model: {FOLDER_MODEL.relative_to(AKAR)}")
    if not FOLDER_MODEL.exists():
        print("  Status: Folder belum dibuat.")
        return 0

    berkas_gguf = list(FOLDER_MODEL.glob("*.gguf"))
    berkas_part = list(FOLDER_MODEL.glob("*.part"))

    if not berkas_gguf and not berkas_part:
        print("  Belum ada model GGUF di folder model/.")
        print("  Gunakan 'python scripts/unduh_model.py' untuk mengunduh.")
        return 0

    for b in berkas_gguf:
        print(f"  [SIAP] {b.name} ({format_ukuran(b.stat().st_size)})")

    for p in berkas_part:
        print(f"  [SEPARUH] {p.name} ({format_ukuran(p.stat().st_size)}) - Belum selesai")

    return 0


def utama() -> int:
    parser = argparse.ArgumentParser(description="Unduh model LLM GGUF offline ke folder model/")
    parser.add_argument(
        "--pilih",
        choices=list(DAFTAR_MODEL.keys()),
        default="llama-1b",
        help="Pilihan model (default: llama-1b)",
    )
    parser.add_argument("--periksa", action="store_true", help="Periksa model yang ada di folder model/")
    args = parser.parse_args()

    if args.periksa:
        return periksa()

    info = DAFTAR_MODEL[args.pilih]
    tujuan = FOLDER_MODEL / info["nama"]

    if tujuan.exists():
        print(f"Model sudah ada di disk: {tujuan.relative_to(AKAR)} ({format_ukuran(tujuan.stat().st_size)})")
        print("Jika ingin mengunduh ulang, hapus berkas tersebut terlebih dahulu.")
        return 0

    print(f"Mengunduh model: {info['deskripsi']}")
    sukses = unduh_berkas(info["url"], tujuan)
    return 0 if sukses else 1


if __name__ == "__main__":
    sys.exit(utama())
