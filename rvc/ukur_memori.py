"""Diagnostik: cara paling hemat melepaskan memori layanan RVC?

Alasannya ada di riwayat: menahan model terus membuat llama-server paging
(gen turun ke ~2,5 tok/s) dan stack berulang kali kena OOM. Pertanyaannya
bukan "bagaimana cara membongkar model" tapi "cara mana yang benar-benar
mengembalikan RAM ke sistem". Jawabannya sudah diukur dan tidak intuitif:
melepas objek di dalam proses TIDAK mengembalikan memori; hanya proses yang
mati yang mengembalikan seluruhnya.

Jalankan (butuh rvc-env, dan akan menyalakan model sungguhan ~40 dtk):

    rvc-env\\Scripts\\python.exe rvc\\ukur_memori.py

Skrip ini TIDAK mengubah apa pun — hanya mengukur lalu keluar.
"""

from __future__ import annotations

import ctypes
import gc
import os
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PORT = int(os.getenv("VTUBER_RVC_PORT", "8081"))
SUMBER = ROOT / "tmp-ukur" / "piper_raw.wav"


# ── Pengukuran memori Windows lewat ctypes ───────────────────────────────────
# TANPA argtypes/restype eksplisit, ctypes memotong HANDLE dan SIZE_T jadi
# 32 bit, jadi semua panggilan gagal SENYAP dan mengembalikan 0. Itu sudah
# sempat menipu sekali; jangan dihapus.

class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _WORKINGSET(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_size_t),
        ("QuotaUsed", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeak", ctypes.c_size_t),
        ("WorkingSetSizePeak", ctypes.c_size_t),
    ]


_kernel32 = ctypes.windll.kernel32
_psapi = ctypes.windll.psapi
_kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
_kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.GetCurrentProcess.restype = wintypes.HANDLE
_kernel32.SetProcessWorkingSetSizeEx.restype = wintypes.BOOL
_kernel32.SetProcessWorkingSetSizeEx.argtypes = [
    wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD
]
_psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
_psapi.GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(_WORKINGSET), wintypes.DWORD
]


def ram_bebas() -> float:
    """RAM fisik bebas (GB)."""
    m = _MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return float("nan")
    return m.ullAvailPhys / 1024 ** 3


def working_set(pid: int) -> float:
    """Working set satu proses (GB). NaN kalau tidak terbaca.

    Pada lingkungan ini OpenProcess ke proses anak sering ditolak, jadi hasil
    NaN itu normal dan pemanggil WAJIB menapinya -- jangan sampai tercetak
    sebagai angka sungguhan.
    """
    h = _kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
    if not h:
        return float("nan")
    try:
        w = _WORKINGSET()
        w.cb = ctypes.sizeof(_WORKINGSET)
        if not _psapi.GetProcessMemoryInfo(h, ctypes.byref(w), w.cb):
            return float("nan")
        return w.WorkingSetSize / 1024 ** 3
    finally:
        _kernel32.CloseHandle(h)


def _ws(pid: int) -> str:
    """Working set sebagai teks, atau string kosong kalau tidak terbaca."""
    g = working_set(pid)
    return "" if g != g else f"  ws={g:.2f} GB"


def paksa_trim() -> bool:
    """Minta Windows menarik kembali working set proses ini."""
    return bool(_kernel32.SetProcessWorkingSetSizeEx(
        _kernel32.GetCurrentProcess(),
        ctypes.c_size_t(-1), ctypes.c_size_t(-1), 0x2,
    ))


# ── Uji lewat layanan sungguhan (jalur yang benar-benar dipakai aplikasi) ─────

def _health() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _status() -> dict:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=3) as r:
            import json

            return json.loads(r.read().decode())
    except Exception:
        return {}


def _convert(data: bytes) -> tuple[int, float]:
    import time as _t

    awal = _t.time()
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/convert", data=data,
        headers={"Content-Type": "audio/wav"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return len(r.read()), _t.time() - awal


def uji_layanan(idle_detik: int = 45) -> int:
    """Uji siklus penuh: start -> konversi -> idle -> proses harus mati."""
    if not SUMBER.is_file():
        print(f"LEWAT: tidak ada {SUMBER}. Buat dulu: "
              f".venv\\Scripts\\python.exe main.py --test-voice, atau salin WAV apa pun.")
        return 1

    env = dict(os.environ, VTUBER_RVC_IDLE_HAPUS=str(idle_detik), PYTHONPATH=str(ROOT))
    PY = ROOT / "rvc-env" / "Scripts" / "python.exe"
    if not PY.is_file():
        print(f"LEWAT: {PY} tidak ada.")
        return 1

    data = SUMBER.read_bytes()
    awal_bebas = ram_bebas()
    print(f"RAM bebas awal                 : {awal_bebas:5.2f} GB")

    proses = subprocess.Popen(
        [str(PY), str(ROOT / "rvc" / "rvc_service.py")],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(40):
            time.sleep(2)
            if _health():
                break
        print(f"setelah start (model belum)    : {ram_bebas():5.2f} GB{_ws(proses.pid)}")

        n, dt = _convert(data)
        puncak = ram_bebas()
        print(f"konversi #1 {n} bytes {dt:5.1f} dtk    : {puncak:5.2f} GB{_ws(proses.pid)}"
              "  <-- model terpasang")

        n, dt = _convert(data)
        print(f"konversi #2 {n} bytes {dt:5.1f} dtk    : {ram_bebas():5.2f} GB  "
              f"(hangat, harusnya jauh lebih cepat)")

        print(f"menunggu {idle_detik + 15} dtk tanpa permintaan ...")
        time.sleep(idle_detik + 15)
        hidup = _health()
        sekarang = ram_bebas()
        print(f"layanan masih hidup?           : {hidup}")
        print(f"RAM bebas sekarang             : {sekarang:5.2f} GB")
        print(f"kembali sejak puncak           : {sekarang - puncak:+.2f} GB")
        print()
        if not hidup and sekarang - puncak > 0.8:
            print("VERDIK: proses MENGUNDURKAN DIRI dan RAM kembali. Ini yang benar.")
            return 0
        if hidup:
            print("VERDIK: watchdog TIDAK mematikan proses -- periksa IDLE_HAPUS "
                  "dan _penjaga_idle di rvc_service.py.")
            return 2
        print("VERDIK: proses mati tapi RAM tidak kembali -- tidak mungkin, "
              "kemungkinan ada proses lain yang mengganggu pengukuran.")
        return 2
    finally:
        if proses.poll() is None:
            proses.terminate()
            try:
                proses.wait(timeout=15)
            except Exception:
                proses.kill()


def uji_pelepasan_di_dalam_proses() -> None:
    """Buktikan gc + trim TIDAK cukup (dipakai untuk memutuskan arsitektur)."""
    sys.path.insert(0, str(ROOT))
    from rvc.indeks_brute import pasang

    pasang()
    import torch
    from rvc_python.infer import RVCInference

    nama = os.getenv("VTUBER_RVC_MODEL", "HuoHuo")
    folder = ROOT / "assets" / "rvc" / nama
    versi = os.getenv("VTUBER_RVC_VERSI", "v2")
    indeks = next(iter(sorted(folder.glob(f"*{nama}_{versi}.index"))), None)

    print(f"torch {torch.__version__} | _host_emptyCache: "
          f"{hasattr(torch._C, '_host_emptyCache')}")
    awal = ram_bebas()
    rvc = RVCInference(device="cpu", model_path=str(folder / f"{nama}.pth"),
                       index_path=str(indeks) if indeks else "", version=versi)
    rvc.set_params(f0up_key=-2, index_rate=0.6, f0method="rmvpe", filter_radius=3,
                   rms_mix_rate=0.8, protect=0.6, resample_sr=0)
    if SUMBER.is_file():
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            rvc.infer_file(str(SUMBER), str(Path(td) / "o.wav"))
    terpasang = ram_bebas()
    print(f"model + konversi memakan        : {abs(terpasang - awal):.2f} GB")

    del rvc
    gc.collect()
    gc.collect()
    time.sleep(2)
    setelah_gc = ram_bebas()
    print(f"gc saja memulihkan              : {setelah_gc - terpasang:+.2f} GB")

    ok = paksa_trim()
    time.sleep(2)
    gc.collect()
    setelah_trim = ram_bebas()
    print(f"gc + trim (trim={ok}) memulihkan  : {setelah_trim - terpasang:+.2f} GB")
    print("\nKesimpulan yang diharapkan: gc ~0, trim sebagian kecil -> "
          "karena itu layanan harus BERHENTI, bukan melepas model.")


if __name__ == "__main__":
    apa = sys.argv[1] if len(sys.argv) > 1 else "layanan"
    if apa == "gc":
        uji_pelepasan_di_dalam_proses()
    else:
        sys.exit(uji_layanan())
