"""Render kalimat yang sama lewat beberapa resep supaya Master bisa MEMILIH
dengan telinga, bukan dengan angka.

Ini langkah yang tidak bisa digantikan meterik: RTF sudah terukur lewat
ukur-latensi, tapi apakah hasil Piper+RVC masih terdengar seperti karakternya
-- atau seperti robot yang sedang membaca berita -- hanya bisa dinilai didengar.

    python scripts/adu_suara.py
    python scripts/adu_suara.py --transpose 0,5,12 --f0 rmvpe
    python scripts/adu_suara.py --resep piper,piper+rvc --kalimat "Coba dengar ini."

Halaman hasilnya TIDAK dibuka sendiri (Master sering sedang mengerjakan jendela
lain); jalankan dengan --buka, atau buka alamat yang dicetak di akhir. Berkas WAV
tetap di disk kalau mau dipindahkan atau dibandingkan lagi besok.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "server_py"))

import konfig  # noqa: E402
import tts_piper  # noqa: E402
import tts_rvc  # noqa: E402
import wav as wav_mod  # noqa: E402

KALIMAT = [
    "Selamat malam, Master.",
    "Saya sedang tidak ingin mengurus perkara orang lain.",
    "Kalau Master minta tolong, saya bantu, tapi saya protes dulu.",
]

GAYA = """
body{font:15px/1.5 "Segoe UI",system-ui,sans-serif;background:#0d1119;color:#e8e6e3;
     padding:24px;max-width:46rem;margin:0 auto}
h1{font:600 21px/1.3 Palatino,Georgia,serif;margin:0 0 6px}
h3{font:400 16px/1.4 Palatino,Georgia,serif;margin:26px 0 8px;color:#e8b673}
.k{display:flex;align-items:center;gap:12px;margin:6px 0}
.n{width:13rem;opacity:.72;flex:none}
.w{opacity:.5;font:12px/1 Consolas,Cascadia,monospace;flex:none;width:5.5rem;text-align:right}
p{opacity:.72}
"""


def utama() -> int:
    urai = argparse.ArgumentParser(description="adu resep suara untuk dipilih dengan telinga")
    urai.add_argument("--resep", default="piper,piper+rvc")
    urai.add_argument("--transpose", default="0,12", help="khusus resep yang memuat rvc")
    urai.add_argument("--f0", default="pm")
    urai.add_argument("--kalimat", default="", help="satu kalimat, mengganti bawaan")
    urai.add_argument(
        "--buka",
        action="store_true",
        help="buka peramban sendiri (bawaannya TIDAK: Master sedang kerja di jendela lain)",
    )
    arg = urai.parse_args()

    keluar = Path(os.environ.get("TEMP", str(AKAR / "var"))) / "adu-suara-elaina"
    keluar.mkdir(parents=True, exist_ok=True)
    kalimat = [arg.kalimat] if arg.kalimat else KALIMAT
    resep_list = [r.strip() for r in arg.resep.split(",") if r.strip()]

    if any("piper" in r for r in resep_list) and not tts_piper.muat():
        print(f"piper tidak siap: {tts_piper.alasan_tidak_tersedia()}", file=sys.stderr)
        return 2
    if any("rvc" in r for r in resep_list):
        konfig.RVC_F0 = arg.f0
        try:
            tts_rvc.muat()
        except Exception as err:
            print(f"rvc tidak siap: {str(err)[:200]}", file=sys.stderr)
            return 2

    # Satu varian per (resep, transpose). ubah() menerapkan param sendiri di tiap
    # panggilan, jadi mengubah konfig.RVC_TRANSPOSE di sini sudah cukup.
    varian: list[tuple[str, list[str], int | None]] = []
    for resep in resep_list:
        tahap = [t.strip() for t in resep.split("+") if t.strip()]
        if "rvc" in tahap:
            for tr in [int(x) for x in arg.transpose.split(",") if x.strip()]:
                varian.append((f"rvc t{tr:+d}" if tr else "rvc t0", tahap, tr))
        else:
            varian.append((resep, tahap, None))

    waktu: dict[str, list[float]] = {v[0]: [] for v in varian}
    hasil: list[list[tuple[str, Path]]] = [[] for _ in kalimat]

    for i, teks in enumerate(kalimat):
        for label, tahap, tr in varian:
            if tr is not None:
                konfig.RVC_TRANSPOSE = tr
            audio: bytes | None = None
            t0 = time.perf_counter()
            try:
                for nama in tahap:
                    if nama == "piper":
                        audio = tts_piper.sintesis(teks)
                    elif nama == "rvc":
                        audio = tts_rvc.ubah(audio, label)
                    else:
                        raise RuntimeError(f"tahap tidak dikenal: {nama}")
            except Exception as err:
                print(f"{label:<10} GALAT {str(err)[:90]}", file=sys.stderr)
                audio = None
            waktu[label].append(time.perf_counter() - t0)
            if audio:
                tujuan = keluar / f"{i + 1}-{label.replace(' ', '')}.wav"
                tujuan.write_bytes(audio)
                hasil[i].append((label, tujuan))

    print(f"{'varian':<10} " + " ".join(f"{k:>7}" for k in range(1, len(kalimat) + 1)))
    for label, _, _ in varian:
        print(f"{label:<10} " + " ".join(f"{d:6.2f}s" for d in waktu[label]))

    html = [
        "<!doctype html><meta charset=utf-8>",
        "<title>adu suara Elaina</title><style>" + GAYA + "</style>",
        "<h1>Adu resep suara</h1>",
        f"<p>f0 RVC = {arg.f0}. Tiap baris memakai kalimat yang sama persis. "
        "Angka di kanan adalah panjang audio, bukan dasar memilih.</p>",
    ]
    for i, teks in enumerate(kalimat):
        html.append(f"<h3>{teks}</h3>")
        for label, path in hasil[i]:
            try:
                detik = wav_mod.baca_header(path.read_bytes())[2]
            except wav_mod.WavRusak:
                detik = 0.0
            html.append(
                f'<div class="k"><span class="n">{label}</span>'
                f'<audio controls preload="none" src="{path.name}"></audio>'
                f'<span class="w">{detik:.2f} dtk</span></div>'
            )
    berkas_html = keluar / "dengar.html"
    berkas_html.write_text("\n".join(html), encoding="utf-8")
    print(f"\nhalaman: {berkas_html}")

    if arg.buka:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(berkas_html)])
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(utama())
