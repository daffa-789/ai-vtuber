"""Probe kelayakan: bisakah jendela WebView2 ditanam ke lapisan desktop (WorkerW)?

SEKALI PAKAI. Bukan bagian runtime -- hapus setelah angkanya tercatat di README.

Empat pertanyaan, semuanya dijawab dengan angka, bukan "kelihatannya jalan":

  P1  Jendela masih MENGGAMBAR setelah SetParent ke WorkerW?
  P2  Transparansinya BERTAHAN (wallpaper di luar karakter tetap utuh)?
  P3  Klik benar-benar LEWAT (WindowFromPoint memulangkan desktop, bukan kita)?
  P4  Ia benar-benar DI BAWAH jendela biasa?

Dua pelajaran yang sudah dibayar saat menyusun skrip ini, jangan diulang:

  - `create_window(hidden=True)` MEMATIKAN WebView2-nya diam-diam. Percobaan
    pertama memakai itu untuk menangkap dasar pembanding, dan hasilnya jendela
    tampil sebagai kotak pekat tanpa isi, plus pesan penutup
    "Failed to delete user data folder: 'NoneType' object has no attribute
    'BrowserProcessId'" -- artinya proses browser tidak pernah naik. Karena itu
    di sini SEMUA jendela dibuat dalam keadaan tampil, dan jendela biru penutup
    diletakkan di pojok lalu dipindah dengan SetWindowPos saat gilirannya.
  - Ukuran jendela yang keluar BUKAN angka yang diminta (minta 260x260, dapat
    307x278), jadi kotak merah dideteksi dari gambar, bukan dihitung.

Jalankan:  .venv\\Scripts\\python.exe scripts/probe_desktop.py
"""

from __future__ import annotations

import ctypes
import struct
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# Tanda tangan eksplisit: handle 64-bit yang dipulangkan sebagai int 32-bit akan
# terpotong dan panggilan berikutnya gagal tanpa galat -- pelajaran yang sudah
# dibayar di server_py/model_vulkan.py dan server_py/jendela.py.
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND
user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.SendMessageTimeoutW.restype = ctypes.c_size_t
user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_size_t)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.WindowFromPoint.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]

gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0
SRCCOPY = 0x00CC0020
SPI_GETWORKAREA = 0x0030

LEBAR, TINGGI = 260, 260
SISI_KOTAK = 90
MARJIN = 14

HTML_KARAKTER = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;height:100%;background:transparent;overflow:hidden}}
#kotak{{position:absolute;left:50%;top:50%;width:{SISI_KOTAK}px;height:{SISI_KOTAK}px;
       transform:translate(-50%,-50%);background:#ff0000}}
</style></head><body><div id="kotak"></div></body></html>"""

HTML_TUTUP = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:#0000ff;overflow:hidden}
</style></head><body></body></html>"""

JUDUL_KARAKTER = "PROBE-KARAKTER"
JUDUL_TUTUP = "PROBE-TUTUP"


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


# Argtypes GetDIBits dipasang di sini, bukan di blok atas: argumen keduanya HBITMAP
# (handle), dan tanpa deklarasi itu ctypes mencoba mengonversinya sebagai int 32-bit
# lalu melempar "int too long to convert" -- sudah terjadi pada percobaan pertama.
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                            ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int


# ── ukur layar ───────────────────────────────────────────────────────────────
def area_kerja() -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def skala_dpi() -> float:
    try:
        dpi = user32.GetDpiForSystem()
        if dpi:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


def rect_jendela(hwnd) -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


# ── tangkap layar ────────────────────────────────────────────────────────────
def tangkap(x: int, y: int, w: int, h: int) -> bytes:
    hdc = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    lama = gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, h, hdc, x, y, SRCCOPY)
    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = w
    info.bmiHeader.biHeight = -h  # negatif = baris atas dulu
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0  # BI_RGB
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(info), 0)
    gdi32.SelectObject(mem, lama)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(None, hdc)
    return buf.raw


def banding(a: bytes, b: bytes, lebar: int, tinggi: int,
            kotak: tuple[int, int, int, int] | None = None,
            di_luar: bool = False) -> int:
    n = 0
    for y in range(tinggi):
        dalam_baris = kotak is not None and kotak[1] <= y < kotak[3]
        for x in range(lebar):
            if kotak is not None:
                di_dalam = dalam_baris and kotak[0] <= x < kotak[2]
                if di_luar == di_dalam:
                    continue
            i = (y * lebar + x) * 4
            if a[i] != b[i] or a[i + 1] != b[i + 1] or a[i + 2] != b[i + 2]:
                n += 1
    return n


def hitung_merah(peta: bytes, lebar: int, tinggi: int) -> int:
    n = 0
    for i in range(0, lebar * tinggi * 4, 4):
        if peta[i + 2] > 150 and peta[i + 1] < 100 and peta[i] < 100:
            n += 1
    return n


def hitung_biru(peta: bytes, lebar: int, tinggi: int) -> int:
    n = 0
    for i in range(0, lebar * tinggi * 4, 4):
        if peta[i] > 150 and peta[i + 1] < 100 and peta[i + 2] < 100:
            n += 1
    return n


def kotak_merah(peta: bytes, lebar: int, tinggi: int):
    """Kotak pembatas piksel merah yang SUNGGUH terlihat, dalam koordinat tangkapan."""
    x0 = y0 = 1 << 30
    x1 = y1 = -1
    for y in range(tinggi):
        for x in range(lebar):
            i = (y * lebar + x) * 4
            if peta[i + 2] > 150 and peta[i + 1] < 100 and peta[i] < 100:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
                if y < y0:
                    y0 = y
                if y > y1:
                    y1 = y
    if x1 < 0:
        return None
    return (x0, y0, x1 + 1, y1 + 1)


def peta_ascii(peta: bytes, lebar: int, tinggi: int, kolom: int = 46) -> str:
    """Peta kasar warna, supaya isi tangkapan bisa dibaca langsung di terminal."""
    baris = max(1, kolom * tinggi // max(1, lebar) // 2)
    keluaran = []
    for by in range(baris):
        y0 = by * tinggi // baris
        y1 = max(y0 + 1, (by + 1) * tinggi // baris)
        teks = []
        for bx in range(kolom):
            x0 = bx * lebar // kolom
            x1 = max(x0 + 1, (bx + 1) * lebar // kolom)
            r = g = b = n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    i = (y * lebar + x) * 4
                    b += peta[i]
                    g += peta[i + 1]
                    r += peta[i + 2]
                    n += 1
            r, g, b = r // n, g // n, b // n
            if r > 150 and g < 100 and b < 100:
                teks.append("R")
            elif b > 150 and r < 100 and g < 100:
                teks.append("B")
            elif r > 225 and g > 225 and b > 225:
                teks.append("W")
            elif r < 55 and g < 55 and b < 55:
                teks.append(" ")
            else:
                teks.append(".")
        keluaran.append("".join(teks))
    return "\n".join(keluaran)


def simpan_png(peta: bytes, lebar: int, tinggi: int, jalur) -> None:
    """PNG RGB 8-bit tanpa pustaka gambar: zlib sudah ada di stdlib."""
    import zlib

    mentah = bytearray()
    for y in range(tinggi):
        mentah.append(0)  # filter: none
        off = y * lebar * 4
        for x in range(lebar):
            i = off + x * 4
            mentah += bytes((peta[i + 2], peta[i + 1], peta[i]))

    def chunk(tipe: bytes, data: bytes) -> bytes:
        isi = tipe + data
        return struct.pack(">I", len(data)) + isi + struct.pack(">I", zlib.crc32(isi) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", lebar, tinggi, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(mentah), 6))
           + chunk(b"IEND", b""))
    Path(jalur).parent.mkdir(parents=True, exist_ok=True)
    Path(jalur).write_bytes(png)


def anak_jendela(hwnd, kedalaman: int = 0, maks: int = 2) -> list[str]:
    """Kelas + rect tiap jendela anak. Dipakai untuk melihat seberapa besar
    permukaan WebView2 yang benar-benar terpasang di dalam form."""
    hasil: list[str] = []
    anak = user32.GetWindow(hwnd, 5)  # GW_CHILD
    while anak:
        r = wintypes.RECT()
        user32.GetWindowRect(anak, ctypes.byref(r))
        hasil.append(f"{'  ' * kedalaman}{kelas_jendela(anak)} "
                     f"{r.right - r.left}x{r.bottom - r.top} @({r.left},{r.top})")
        if kedalaman + 1 < maks:
            hasil += anak_jendela(anak, kedalaman + 1, maks)
        anak = user32.GetWindow(anak, 2)  # GW_HWNDNEXT
    return hasil


def kelas_jendela(hwnd) -> str:
    if not hwnd:
        return "(null)"
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value or "(kosong)"


# ── kanvas desktop ───────────────────────────────────────────────────────────
def cari_workerw():
    """WorkerW yang jadi kanvas desktop: yang bersaudara dengan SHELLDLL_DefView.

    Susunannya berbeda antar versi Windows, jadi dua varian ditangani: kalau
    SHELLDLL_DefView masih anak Progman, WorkerW pertama yang ditemukan dipakai.
    """
    progman = user32.FindWindowW("Progman", None)
    hasil = ctypes.c_size_t()
    # 0x052C = pesan tidak resmi yang membuat Progman melahirkan WorkerW.
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0002, 1000, ctypes.byref(hasil))

    temuan: list[int] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            w = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if w:
                temuan.append(w)
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if temuan:
        return temuan[0], "WorkerW (bersaudara SHELLDLL_DefView)"
    w = user32.FindWindowExW(None, None, "WorkerW", None)
    if w:
        return w, "WorkerW (varian tanpa SHELLDLL_DefView)"
    return progman, "Progman (tidak ada WorkerW -- jalur cadangan)"


def tanam(hwnd, workerw, w_area: int, h_area: int) -> bool:
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    ex = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
    if not user32.SetParent(hwnd, workerw):
        return False
    return bool(user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, w_area, h_area,
                                    SWP_NOACTIVATE | SWP_SHOWWINDOW))


# ── probe ────────────────────────────────────────────────────────────────────
def jalankan_probe() -> int:
    import webview

    kiri, atas, w_area, h_area = area_kerja()
    print(f"layar           : {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)} px | "
          f"area kerja {w_area}x{h_area} pada ({kiri},{atas}) | GetDpiForSystem={skala_dpi():.2f}")
    print("catatan: area kerja dibaca SEBELUM jendela pertama, dan proses ini baru "
          "menjadi DPI-aware setelah webview.start().")

    faktor = skala_dpi()
    x = int((w_area - LEBAR) / 2 / faktor)
    y = int((h_area - TINGGI) / 2 / faktor)

    # Semua jendela dibuat TAMPIL: hidden=True mematikan WebView2 diam-diam.
    # Yang penutup diletakkan jauh di pojok supaya tidak menutupi karakter.
    jendela = webview.create_window(
        JUDUL_KARAKTER, html=HTML_KARAKTER, x=x, y=y, width=LEBAR, height=TINGGI,
        frameless=True, transparent=True, on_top=True, easy_drag=False, shadow=False,
        focus=False,
    )
    tutup = webview.create_window(
        JUDUL_TUTUP, html=HTML_TUTUP, x=8, y=8, width=200, height=200,
        frameless=True, transparent=False, on_top=True, easy_drag=False, shadow=False,
        focus=False,
    )

    siap = threading.Event()
    jendela.events.loaded += lambda *_: siap.set()
    putusan: dict[str, object] = {}

    def kerja():
        try:
            if not siap.wait(25):
                print("GAGAL: halaman karakter tidak pernah memicu event loaded.", file=sys.stderr)
                return
            time.sleep(1.2)

            hwnd = user32.FindWindowW(None, JUDUL_KARAKTER)
            hwnd_tutup = user32.FindWindowW(None, JUDUL_TUTUP)
            if not hwnd:
                print("GAGAL: jendela karakter tidak ketemu lewat FindWindowW.", file=sys.stderr)
                return
            r = rect_jendela(hwnd)
            putusan["rect"] = r
            print(f"jendela diminta : {LEBAR}x{TINGGI} di ({x},{y}) logis")
            print(f"jendela nyata   : {r[2]}x{r[3]} pada ({r[0]},{r[1]}) px  "
                  f"-> rasio {r[2]/LEBAR:.3f} x {r[3]/TINGGI:.3f}")

            x0 = max(0, r[0] - MARJIN)
            y0 = max(0, r[1] - MARJIN)
            wl = min(user32.GetSystemMetrics(0) - x0, r[2] + 2 * MARJIN)
            wh = min(user32.GetSystemMetrics(1) - y0, r[3] + 2 * MARJIN)
            print(f"wilayah ukur    : {wl}x{wh} pada ({x0},{y0})")

            def snap(nama: str) -> bytes:
                peta = tangkap(x0, y0, wl, wh)
                putusan[nama] = peta
                return peta

            px, py = r[0] + r[2] // 2, r[1] + r[3] // 2

            # B -- keadaan acuan: jendela tampil normal (transparan, on_top).
            B = snap("B")
            merah_B = hitung_merah(B, wl, wh)
            putusan["P3_B"] = kelas_jendela(user32.WindowFromPoint(wintypes.POINT(px, py)))
            print(f"\nB tampil        : merah={merah_B}  WindowFromPoint={putusan['P3_B']}")
            print("pohon jendela   :")
            for baris_anak in anak_jendela(hwnd):
                print(f"   {baris_anak}")
            simpan_png(B, wl, wh, "var/probe/B.png")
            print("--- peta B ---")
            print(peta_ascii(B, wl, wh))
            if merah_B < 200:
                print("\nBERHENTI: kotak merah tidak tergambar walau WebView2 sudah memicu "
                      "loaded. Ini bukan soal penanaman.", file=sys.stderr)
                return

            dasar = kotak_merah(B, wl, wh)
            kotak = (dasar[0] - 4, dasar[1] - 4, dasar[2] + 4, dasar[3] + 4)
            putusan["kotak"] = (dasar, kotak)
            print(f"kotak merah     : {dasar[2]-dasar[0]}x{dasar[3]-dasar[1]} px di "
                  f"({dasar[0]},{dasar[1]})  [diminta {SISI_KOTAK} px CSS]")

            # A -- dasar pembanding: jendela disembunyikan, lalu ditampilkan lagi.
            jendela.hide()
            time.sleep(1.2)
            A = snap("A")
            merah_A = hitung_merah(A, wl, wh)
            jendela.show()
            time.sleep(1.6)
            B2 = snap("B2")
            merah_B2 = hitung_merah(B2, wl, wh)
            print(f"A sembunyi      : merah={merah_A} (harus 0)")
            print(f"B2 tampil lagi  : merah={merah_B2} "
                  f"({'hide/show aman' if merah_B2 > 200 else 'HIDE/SHOW MERUSAK GAMBAR'})")
            if merah_A != 0 or merah_B2 < 200:
                print("\nBERHENTI: dasar pembanding tidak bisa dipercaya.", file=sys.stderr)
                simpan_png(A, wl, wh, "var/probe/A.png")
                simpan_png(B2, wl, wh, "var/probe/B2.png")
                return

            luar_B = banding(A, B2, wl, wh, kotak, di_luar=True)
            dalam_B = banding(A, B2, wl, wh, kotak)
            print(f"   P2  di luar kotak berubah vs A : {luar_B} piksel")
            print(f"       di dalam kotak berubah     : {dalam_B} piksel")

            # C -- ditanam ke WorkerW.
            workerw, ket = cari_workerw()
            print(f"\nkanvas desktop  : {ket} (0x{workerw:x})")
            ok = tanam(hwnd, workerw, w_area, h_area)
            putusan["tanam_ok"] = ok
            time.sleep(1.8)
            r2 = rect_jendela(hwnd)
            putusan["rect_setelah"] = r2
            print(f"SetParent       : {'berhasil' if ok else 'GAGAL'}")
            print(f"rect sesudahnya : {r2[2]}x{r2[3]} pada ({r2[0]},{r2[1]})")
            C = snap("C")
            merah_C = hitung_merah(C, wl, wh)
            beda_BC = banding(B2, C, wl, wh)
            luar_C = banding(A, C, wl, wh, kotak, di_luar=True)
            putusan["P3_C"] = kelas_jendela(user32.WindowFromPoint(wintypes.POINT(px, py)))
            print(f"C ditanam       : merah={merah_C}  WindowFromPoint={putusan['P3_C']}")
            print(f"   P1  beda vs B2 (menggambar?)   : {beda_BC} piksel")
            print(f"   P2  di luar kotak berubah vs A : {luar_C} piksel")
            if merah_C < 200:
                simpan_png(C, wl, wh, "var/probe/C.png")
                print("\n--- C ---", file=sys.stderr)
                print(peta_ascii(C, wl, wh), file=sys.stderr)

            # D -- jendela biru dipindah tepat di atas karakter.
            if hwnd_tutup:
                user32.SetWindowPos(hwnd_tutup, HWND_TOP, r[0], r[1], r[2], r[3],
                                    SWP_NOACTIVATE | SWP_SHOWWINDOW)
            time.sleep(1.4)
            D = snap("D")
            merah_d = hitung_merah(D, wl, wh)
            biru_d = hitung_biru(D, wl, wh)
            putusan["P3_D"] = kelas_jendela(user32.WindowFromPoint(wintypes.POINT(px, py)))
            print(f"\nD ditutup biru  : merah={merah_d} biru={biru_d}  "
                  f"WindowFromPoint={putusan['P3_D']}")
            print(f"   P4  karakter tertutup?         : {'YA' if merah_d == 0 else 'TIDAK'}")
            if merah_d != 0:
                simpan_png(D, wl, wh, "var/probe/D.png")

            # E -- biru disingkirkan lagi, karakter harus muncul kembali.
            if hwnd_tutup:
                user32.SetWindowPos(hwnd_tutup, HWND_TOP, 8, 8, 200, 200,
                                    SWP_NOACTIVATE | SWP_SHOWWINDOW)
            time.sleep(1.4)
            E = snap("E")
            merah_E = hitung_merah(E, wl, wh)
            print(f"\nE biru disingkir: merah={merah_E}")
            print(f"   P1  karakter kembali?          : {'YA' if merah_E > 200 else 'TIDAK'}")

            # ── putusan ──────────────────────────────────────────────────────
            p1 = merah_C > 200 and beda_BC < merah_B2 * 0.25
            p2 = luar_C < merah_B2 * 0.25
            p3 = any(k in str(putusan["P3_C"]) for k in
                     ("DefView", "SysListView", "WorkerW", "Progman"))
            p4 = merah_d == 0

            print("\n" + "=" * 62)
            print("PUTUSAN")
            print("=" * 62)
            print(f"P1 menggambar setelah ditanam : {'LULUS' if p1 else 'GAGAL'}  "
                  f"(merah {merah_B2} -> {merah_C}, beda {beda_BC} px)")
            print(f"P2 transparansi bertahan      : {'LULUS' if p2 else 'GAGAL'}  "
                  f"(luar kotak berubah {luar_B} -> {luar_C} px)")
            print(f"P3 klik lewat ke desktop      : {'LULUS' if p3 else 'GAGAL'}  "
                  f"(WindowFromPoint={putusan['P3_C']})")
            print(f"P4 di bawah jendela biasa     : {'LULUS' if p4 else 'GAGAL'}  "
                  f"(merah saat ditutup {merah_d})")
            putusan["putusan"] = (p1, p2, p3, p4)
            for nama in ("A", "B2", "C", "D", "E"):
                simpan_png(putusan[nama], wl, wh, f"var/probe/{nama}.png")
        except Exception as err:
            import traceback
            traceback.print_exc()
            print(f"probe gagal: {err}", file=sys.stderr)
        finally:
            for j in (tutup, jendela):
                try:
                    j.destroy()
                except Exception:
                    pass

    webview.start(kerja, gui="edgechromium", debug=False)
    hasil = putusan.get("putusan")
    if not hasil:
        print("\nprobe tidak sampai ke putusan -- lihat galat di atas.", file=sys.stderr)
        return 2
    return 0 if all(hasil) else 1


if __name__ == "__main__":
    sys.exit(jalankan_probe())
