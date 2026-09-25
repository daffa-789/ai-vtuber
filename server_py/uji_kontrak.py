"""Uji kontrak sisi server terhadap rekaman, bukan terhadap server lain.

Dulu berkas ini bernama uji_paritas.py dan membandingkan sisi Node dengan sisi
Python. Setelah Node dihapus, tes itu berubah jadi membandingkan server dengan
dirinya sendiri: selalu PASS, dan PASS yang tidak bisa gagal lebih berbahaya
daripada tidak ada tes sama sekali.

Sekarang bentuknya: rekam jawaban server yang benar sekali (``--rekam``), lalu
setiap perubahan kode diuji terhadap rekaman itu.

  .venv\\Scripts\\python.exe server_py\\uji_kontrak.py --rekam
  .venv\\Scripts\\python.exe server_py\\uji_kontrak.py
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ACUAN = Path(__file__).resolve().parent / "kontrak.json"
BASE = "http://127.0.0.1:8787"

# (label, metode, jalur, body, mime) -- sengaja mencakup jalur galat, karena
# frontend membaca kode status untuk memutuskan menampilkan error atau tidak.
KASUS = [
    ("health", "GET", "/api/health", None, None),
    ("chat riwayat kosong", "POST", "/api/chat", {"messages": []}, "application/json"),
    ("chat body bukan json", "POST", "/api/chat", b"bukan json", "application/json"),
    ("tts teks kosong", "POST", "/api/tts", {"text": "   "}, "application/json"),
    ("tts tanpa teks", "POST", "/api/tts", b"", "application/json"),
    ("stt audio pendek", "POST", "/api/stt", b"pendek", "audio/wav"),
    ("endpoint tak dikenal POST", "POST", "/api/tidak-ada", {}, "application/json"),
    ("asset halaman", "GET", "/", None, None),
    ("asset modul", "GET", "/main.js", None, None),
    ("asset model", "GET", "/models/penyihir/penyihir.model3.json", None, None),
]


def kirim(base: str, metode: str, jalur: str, body, mime):
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    kepala = {"content-type": mime} if mime else {}
    perm = urllib.request.Request(base + jalur, data=data, method=metode, headers=kepala)
    try:
        with urllib.request.urlopen(perm, timeout=60) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("content-type", ""), err.read()
    except urllib.error.URLError as err:
        # Server mati harus tercatat sebagai perbedaan, bukan traceback.
        return 0, f"mati:{err.reason}", b""


def potret(base: str) -> dict:
    """Ringkasan yang bisa dibandingkan: status, tipe, dan bentuk isinya."""
    hasil = {}
    for label, metode, jalur, body, mime in KASUS:
        status, ctype, isi = kirim(base, metode, jalur, body, mime)
        catatan = {"status": status, "ctype": ctype.split(";")[0]}
        if "json" in ctype:
            try:
                data = json.loads(isi)
                # Kunci saja, bukan nilainya: nilai model/kuota berubah tiap hari.
                catatan["kunci"] = sorted(data) if isinstance(data, dict) else None
                catatan["punya_error"] = isinstance(data, dict) and bool(data.get("error"))
            except ValueError:
                catatan["kunci"] = None
        else:
            # Aset: cukup pastikan isinya tidak kosong, jangan bandingkan byte.
            catatan["panjang_min_1"] = len(isi) > 0
        hasil[label] = catatan
    return hasil


def utama() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", default=BASE)
    ap.add_argument("--rekam", action="store_true", help="simpan jawaban sekarang sebagai acuan")
    a = ap.parse_args()

    sekarang = potret(a.basis)
    if a.rekam:
        ACUAN.write_text(json.dumps(sekarang, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"tercatat {len(sekarang)} kasus -> {ACUAN.name}")
        return 0

    if not ACUAN.exists():
        print(f"tidak ada {ACUAN.name}. Jalankan dulu: python server_py/uji_kontrak.py --rekam")
        return 1

    acuan = json.loads(ACUAN.read_text(encoding="utf-8"))
    beda = [k for k in set(acuan) | set(sekarang) if acuan.get(k) != sekarang.get(k)]
    for k in sorted(sekarang):
        if k in beda:
            print(f"BEDA  {k:<26} acuan={acuan.get(k)}  sekarang={sekarang[k]}")
    if beda:
        print(f"\nFAIL {len(beda)} dari {len(sekarang)} kontrak berubah")
        return 1
    print(f"PASS {len(sekarang)}/{len(sekarang)} kontrak cocok dengan rekaman")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
