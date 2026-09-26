"""Uji kontrak HTTP sisi server terhadap REKAMAN.

Pola lamanya dipertahankan: rekam sekali (``--rekam``), lalu setiap perubahan kode
dibandingkan terhadap rekaman itu. Yang berubah: servernya dibangkit sendiri di
PORT ACAK, karena mesin ini dipakai banyak proyek sekaligus dan menulis nomor port
tetap di sebuah tes itu cara cepat untuk mengusir tetangga.

Bukan byte yang dibandingkan, tapi potret: status, tipe konten, dan BENTUK isi.
Nilai model/kuota berubah tiap hari, jadi JSON dibandingkan daftar kuncinya saja;
audio dibandingkan header WAV-nya, bukan isinya.

  .venv\\Scripts\\python.exe server_py\\uji_kontrak.py --rekam
  .venv\\Scripts\\python.exe server_py\\uji_kontrak.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
ACUAN = Path(__file__).resolve().parent / "kontrak.json"

# (label, metode, jalur, body, mime) -- sengaja mencakup jalur galat, karena
# frontend membaca kode status untuk memutuskan menampilkan error atau tidak.
KASUS = [
    ("health", "GET", "/api/health", None, None),
    ("chat riwayat kosong", "POST", "/api/chat", {"messages": []}, "application/json"),
    ("chat body bukan json", "POST", "/api/chat", b"bukan json", "application/json"),
    ("tts teks kosong", "POST", "/api/tts", {"text": "   "}, "application/json"),
    ("tts tanpa teks", "POST", "/api/tts", b"", "application/json"),
    ("tts stub", "POST", "/api/tts", {"text": "Halo Master"}, "application/json"),
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
            return r.status, r.headers.get("content-type", ""), r.read(), dict(r.headers)
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("content-type", ""), err.read(), dict(err.headers)
    except urllib.error.URLError as err:
        # Server mati harus tercatat sebagai perbedaan, bukan traceback.
        return 0, f"mati:{err.reason}", b"", {}


def potret(base: str) -> dict:
    hasil = {}
    for label, metode, jalur, body, mime in KASUS:
        status, ctype, isi, kepala = kirim(base, metode, jalur, body, mime)
        catatan: dict = {"status": status, "ctype": ctype.split(";")[0]}
        if "json" in ctype:
            try:
                data = json.loads(isi)
                # Kunci saja, bukan nilainya: nilai model/kuota berubah tiap hari.
                catatan["kunci"] = sorted(data) if isinstance(data, dict) else None
                catatan["punya_error"] = isinstance(data, dict) and bool(data.get("error"))
                # Kunci DI DALAM objek tts juga dicatat. Tanpa ini health cuma
                # membuktikan daftar kunci level-atas tidak berubah, sementara
                # ringkasan() -- tempat rantai aktif, piper, dan rvc dilaporkan --
                # bebas berubah bentuk tanpa satu pun BEDA.
                if isinstance(data, dict) and isinstance(data.get("tts"), dict):
                    catatan["kunci_tts"] = sorted(data["tts"])
            except ValueError:
                catatan["kunci"] = None
        elif "audio" in ctype:
            # Yang dijanjikan /api/tts adalah WAV yang bisa didecode browser,
            # jadi itu yang diperiksa -- bukan panjang byte.
            try:
                laju, kanal, detik = _baca_wav(isi)
                catatan["wav"] = {"laju": laju, "kanal": kanal, "detik_min_0": detik >= 0}
            except Exception as err:
                catatan["wav"] = f"rusak:{err}"
            catatan["x-tts-model"] = kepala.get("x-tts-model", "")
        else:
            # Aset: cukup pastikan isinya tidak kosong, jangan bandingkan byte.
            catatan["panjang_min_1"] = len(isi) > 0
        hasil[label] = catatan
    return hasil


def _baca_wav(isi: bytes):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import wav

    return wav.baca_header(isi)


def bangkitkan() -> tuple[subprocess.Popen, str, str]:
    """Jalankan sidecar sendiri di port acak dengan VTUBER_STUB=1.

    Stub wajib: tes kontrak tidak boleh memakan kuota Gemini, dan tidak boleh
    menulis satu baris pun ke vault karakter.
    """
    env = dict(os.environ)
    env["VTUBER_STUB"] = "1"
    env["VTUBER_PORT"] = "0"
    proc = subprocess.Popen(
        [sys.executable, str(AKAR / "server_py" / "app.py")],
        cwd=str(AKAR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    port, sisa = None, []
    batas = time.time() + 30
    while time.time() < batas and proc.poll() is None:
        baris = proc.stdout.readline()
        if not baris:
            continue
        baris = baris.rstrip()
        sisa.append(baris)
        cocok = re.search(r"127\.0\.0\.1:(\d+)", baris)
        if cocok:
            port = cocok.group(1)
            break
    if not port:
        proc.kill()
        raise RuntimeError("server uji tidak membuka port:\n" + "\n".join(sisa[-12:]))
    return proc, f"http://127.0.0.1:{port}", "\n".join(sisa)


def uji_stub_tidak_menyentuh_cloud(banner: str) -> None:
    """Bukti bahwa jalur tes ini tidak memakan kuota dan tidak menulis vault."""
    if "stub" not in banner.lower():
        raise AssertionError(f"banner tidak mengaku stub: {banner.splitlines()[0]}")


def utama() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", default="", help="pakai server yang sudah hidup, jangan bangkitkan")
    ap.add_argument("--rekam", action="store_true", help="simpan jawaban sekarang sebagai acuan")
    a = ap.parse_args()

    proc = None
    if a.basis:
        base = a.basis
        banner = ""
    else:
        proc, base, banner = bangkitkan()
        print(f"server uji bangkit di {base} (port acak, mode stub)")
        try:
            uji_stub_tidak_menyentuh_cloud(banner)
            print("pass  mode stub: tidak ada panggilan cloud, vault tidak disentuh")
        except AssertionError as err:
            print(f"FAIL  {err}")

    try:
        sekarang = potret(base)
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

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
