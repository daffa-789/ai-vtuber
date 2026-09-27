"""Penyedia LLM di GPU terintegrasi lewat `llama-server` bawaan llama.cpp (Vulkan).

Kenapa proses anak dan bukan `llama-cpp-python` dengan backend Vulkan:
llama-cpp-python harus DIKOMPILASI ulang untuk tiap backend, dan mesin Master tidak
punya `cl`/`cmake`/`gcc` (sudah dikurusi 27 Sep). Rilis resmi llama.cpp justru
menyertakan binary Windows jadi (`llama-b11206-bin-win-vulkan-x64.zip`), jadi jalur
GPU satu-satunya yang realistis di sini adalah menjalankan `llama-server.exe` dan
berbicara lewat HTTP OpenAI-compatible di 127.0.0.1. GGUF yang sudah ada dipakai
apa adanya -- tidak unduh ulang, tidak konversi.

Aturan yang dijaga modul ini:
  * port SELALU acak (Master menjalankan banyak proyek di satu mesin);
  * hanya bind 127.0.0.1 + API key acak per boot, supaya halaman/situs lain di
    mesin ini tidak bisa ikut memakai model;
  * kalau binary atau model tidak ada -> JANGAN diam-diam pindah. `tersedia()`
    bilang tidak, `alasan_tidak_tersedia()` bilang kenapa, dan app.py yang memutuskan
    (dengan peringatan keras di banner).
"""

from __future__ import annotations

import atexit
import ctypes
from ctypes import wintypes
import json
import os
import random
import secrets
import socket
import string
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Generator

import konfig
from konfig import AKAR

# Kelas galat yang SAMA dengan model_lokal: app.py sudah punya satu jalur penanganan
# (503 + pesan yang bisa dibaca Master). Dua kelas galat berarti dua cabang yang bisa
# lupa disinkronkan -- dan yang dilupakan biasanya jalur yang jarang dipakai.
from model_lokal import ModelLokalError

NAMA = "vulkan"
NAMAI = "llama-server"

_lock = threading.Lock()
_proses: subprocess.Popen | None = None
_alamat: str = ""
_kunci: str = ""
_terakhir_galat: str = ""
_waktu_muat: float = 0.0

# Waktu tunggu boot: model 1,9 GB dibaca dari NVMe + kompilasi shader Vulkan pertama
# kali. 60 dtk pernah terbukti kurang saat disk sedang dipakai yang lain.
BATAS_SIAP = 240


def jalur_binary() -> Path:
    p = Path(konfig.LLAMA_SERVER)
    return p if p.is_absolute() else AKAR / p


def _exe() -> Path:
    return jalur_binary() / (
        "llama-server.exe" if os.name == "nt" else "llama-server"
    )


def tersedia() -> bool:
    """Murah dan tidak menjalankan apa pun: binary + model ada di disk."""
    return _exe().is_file() and konfig.LLM_PROVIDER == NAMA


def alasan_tidak_tersedia() -> str:
    if not _exe().is_file():
        return (
            f"{_exe().name} tidak ada di {jalur_binary()} -- jalankan "
            "`python scripts/unduh_llama.py` (butuh internet sekali)"
        )
    if konfig.LLM_PROVIDER != NAMA:
        return f"provider aktif '{konfig.LLM_PROVIDER}', bukan '{NAMA}'"
    return _terakhir_galat or "siap"


def _port_kosong() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── jangan ada anak yatim memegang 2 GB ──────────────────────────────────────
# `atexit` dan `finally` TIDAK jalan saat proses induk dibunuh keras (Stop-Process,
# Task Manager, tombol X konsol). Itu terbukti di mesin ini 27 Sep: app.py ditutup
# paksa dan llama-server tetap hidup.
#
# Yang pertama dicoba adalah job object dengan KILL_ON_JOB_CLOSE -- dan ia
#GAGAL di mesin ini: `SetInformationJobObject` membalas ERROR_BAD_LENGTH (24) untuk
#kelas 9 maupun 2, karena proses Python ini sendiri sudah berada di dalam job
#(`IsProcessInJob` = 1) yang dibuat pembungkus shell. Jadi tidak ada FFI job yang
#disimpan di kode ini; yang tersisa hanya mekanisme yang TERBUKA bekerja:
#
#  1. `hentikan()` untuk jalur berhenti yang wajar (Ctrl+C, keyboard interrupt);
#  2. `sapu_yatim()` saat boot: semua proses llama-server.exe yang benar-benar
#     berasal dari `bin/llama/` milik proyek ini dimatikan lebih dulu, jadi satu
#     pembunuhan paksa paling-paling menahan RAM sampai server dinyalakan lagi.

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED = 0x1000
PROCESS_TERMINATE = 0x0001
INVALID_HANDLE = ctypes.c_void_p(-1).value


class _EntriProses(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def jalur_pid() -> Path:
    return AKAR / "var" / "llama.pid"


def _nama_lengkap(pid: int) -> str:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        ukuran = wintypes.DWORD(260)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(ukuran)):
            return ""
        return buf.value
    finally:
        kernel32.CloseHandle(handle)


def yatim_sejati() -> list[int]:
    """PID llama-server.exe yang berasal dari bin/llama proyek ini, bukan punya orang lain."""
    if os.name != "nt":
        return []
    milik_kita = _exe().resolve()
    snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE or snapshot == 0:
        return []
    hasil: list[int] = []
    entri = _EntriProses()
    entri.dwSize = ctypes.sizeof(_EntriProses)
    kernel32 = ctypes.windll.kernel32
    ada = kernel32.Process32First(snapshot, ctypes.byref(entri))
    try:
        while ada:
            pid = int(entri.th32ProcessID)
            if entri.szExeFile.decode("mbcs", "replace").lower() == "llama-server.exe":
                if pid != (_proses.pid if _proses else -1) and Path(_nama_lengkap(pid)).resolve() == milik_kita:
                    hasil.append(pid)
            ada = kernel32.Process32Next(snapshot, ctypes.byref(entri))
    finally:
        kernel32.CloseHandle(snapshot)
    return hasil


def sapu_yatim() -> list[int]:
    """Matikan llama-server sisa boot sebelumnya. Aman: hanya yang exec-nya milik kita."""
    dibersihkan: list[int] = []
    for pid in yatim_sejati():
        try:
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED | PROCESS_TERMINATE, False, pid
            )
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
                dibersihkan.append(pid)
        except Exception:
            continue
    if dibersihkan:
        jalur_pid().unlink(missing_ok=True)
    return dibersihkan



def _perintah(port: int) -> list[str]:
    from model_lokal import cari_model

    jalur = cari_model(konfig.LOCAL_MODEL_PATH)
    if jalur is None:
        raise ModelLokalError(
            "Tidak ditemukan berkas model .gguf di folder model/.\n"
            "Jalankan: python scripts/unduh_model.py --model llama-3b"
        )
    arg = [
        str(_exe()),
        "-m", str(jalur),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--api-key", _kunci,
        "-c", str(konfig.VULKAN_CTX),
        "-t", str(konfig.LOCAL_MODEL_THREADS),
        "--no-webui",
    ]
    if konfig.VULKAN_NGL >= 0:
        arg += ["-ngl", str(konfig.VULKAN_NGL)]
    if konfig.VULKAN_FA:
        arg += ["-fa", "on"]
    if konfig.VULKAN_SLOT_DIAM:
        # Simpan slot yang menganggur ke prompt cache: persona panjang (ribuan token)
        # tidak perlu dihitung ulang setiap giliran bicara.
        arg += ["--cache-idle-slots"]
    if konfig.VULKAN_PERANGKAT:
        arg += ["--device", konfig.VULKAN_PERANGKAT]
    return arg


def siap() -> bool:
    """Proses hidup dan /health menjawab 200."""
    global _terakhir_galat
    with _lock:
        if _proses is None or _proses.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(_url("/health"), timeout=3) as r:
                return r.status == 200
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            _terakhir_galat = f"llama-server tidak menjawab /health: {err}"
            return False


def _url(jalur: str) -> str:
    return f"{_alamat}{jalur}"


def _kepala() -> dict[str, str]:
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {_kunci}",
    }


def hentikan() -> None:
    """Dipanggil saat server Python mati: anak TIDAK boleh yatim memegang 2 GB RAM."""
    global _proses, _alamat
    with _lock:
        proc, _proses = _proses, None
        _alamat = ""
    if proc is None:
        return
    jalur_pid().unlink(missing_ok=True)
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:  # subprocess macet -> jangan gantung saat shutdown
        try:
            proc.kill()
        except Exception:
            pass


def mulai(paksa: bool = False) -> bool:
    """Nyalakan (atau nyalakan ulang) llama-server. Blocking sampai sehat atau habis waktu."""
    global _proses, _alamat, _kunci, _terakhir_galat, _waktu_muat
    with _lock:
        if _proses is not None and _proses.poll() is None and _alamat and not paksa:
            return True
        hentikan_terkunci = _proses
        if hentikan_terkunci is not None:
            try:
                hentikan_terkunci.terminate()
            except Exception:
                pass

        if not _exe().is_file():
            _terakhir_galat = alasan_tidak_tersedia()
            return False

        _kunci = "".join(
            random.choices(string.ascii_letters + string.digits, k=24)
        )
        port = _port_kosong()
        _alamat = f"http://127.0.0.1:{port}"
        try:
            arg = _perintah(port)
        except ModelLokalError as err:
            _terakhir_galat = err.pesan
            return False

        log_folder = AKAR / "var"
        log_folder.mkdir(exist_ok=True)
        t0 = time.monotonic()
        sisa = sapu_yatim()
        if sisa:
            print(
                f"llama-server yatim dari boot lalu dimatikan lebih dulu (pid {', '.join(map(str, sisa))})",
                file=sys.stderr,
            )
        try:
            with open(log_folder / "llama-server.log", "ab") as log:
                _proses = subprocess.Popen(
                    arg,
                    cwd=str(AKAR),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    ),
                )
        except OSError as err:
            _proses = None
            _terakhir_galat = f"llama-server gagal dimulai: {err}"
            return False

        try:
            jalur_pid().write_text(str(_proses.pid), encoding="utf-8")
        except OSError:
            pass

        # Tunggu sehat di luar _lock? Tidak: dua permintaan chat serentak tidak boleh
        # membangkitkan dua server. Yang boleh menunggu cuma satu, sisanya antre.
        while time.monotonic() - t0 < BATAS_SIAP:
            if _proses.poll() is not None:
                _terakhir_galat = (
                    f"llama-server mati saat boot (kode {_proses.returncode}); "
                    f"lihat var/llama-server.log"
                )
                _proses = None
                return False
            try:
                with urllib.request.urlopen(_url("/health"), timeout=3) as r:
                    if r.status == 200:
                        _waktu_muat = time.monotonic() - t0
                        _terakhir_galat = ""
                        return True
            except urllib.error.HTTPError:
                pass  # sudah listen tapi model belum selesai
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(0.5)

        _terakhir_galat = f"llama-server tidak siap dalam {BATAS_SIAP} dtk"
        return False


atexit.register(hentikan)


def ringkasan() -> str:
    """Satu baris untuk banner + /api/health: angka nyata, bukan klaim."""
    if _proses is None or not _alamat:
        return f"{NAMA}/belum jalan"
    pid = _proses.pid
    return (
        f"{NAMA}/{_alamat.split(':')[-1]} pid={pid} ngl={konfig.VULKAN_NGL} "
        f"fa={'on' if konfig.VULKAN_FA else 'off'} muat={_waktu_muat:.1f}dtk"
    )


def alir(
    pesan: list[dict[str, str]],
    max_tokens: int = 350,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Stream token dari /v1/chat/completions. Bentuk keluaran sama persis dengan
    model_lokal.alir(), jadi sisi streaming app.py tidak perlu tahu mana yang menjawab."""
    if not mulai():
        raise ModelLokalError(_terakhir_galat or "llama-server tidak bisa dimulai")

    tubuh = json.dumps(
        {
            "messages": pesan,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": ["<|eot_id|>", "<|end_of_text|>", "</s>", "User:", "Master:"],
        }
    ).encode("utf-8")

    perm = urllib.request.Request(
        _url("/v1/chat/completions"), data=tubuh, method="POST", headers=_kepala()
    )
    try:
        with urllib.request.urlopen(perm, timeout=300) as jawab:
            for baris in jawab:
                teks = baris.decode("utf-8", "replace").strip()
                if not teks.startswith("data:"):
                    continue
                muatan = teks[5:].strip()
                if muatan == "[DONE]":
                    break
                try:
                    objek = json.loads(muatan)
                except json.JSONDecodeError:
                    continue
                for pilihan in objek.get("choices") or []:
                    isi = (pilihan.get("delta") or {}).get("content")
                    if isi:
                        yield isi
    except urllib.error.HTTPError as err:
        tubuh_galat = err.read().decode("utf-8", "replace")[:300]
        raise ModelLokalError(f"llama-server menolak permintaan ({err.code}): {tubuh_galat}")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise ModelLokalError(f"llama-server hilang di tengah jalan: {err}")
    except Exception as err:  # generator pihak ketiga bisa melempar apa saja
        raise ModelLokalError(f"inferensi vulkan gagal: {err}")
