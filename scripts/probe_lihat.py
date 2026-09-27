"""Tangkap satu wilayah layar ke PNG, lalu cetak warna & petanya.

Perkakas diagnosa, SEKALI PAKAI. Dipakai untuk melihat dengan mata sendiri apa
yang benar-benar tergambar di layar -- karena "kotak merah tidak terdeteksi" bisa
berarti dua hal yang sangat berbeda: jendelanya tidak menggambar, atau yang
menggambar bukan itu.

Jalankan:  .venv\\Scripts\\python.exe scripts/probe_lihat.py [x y w h] [keluaran.png]
Tanpa argumen: seluruh area kerja.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_desktop as pd  # noqa: E402

# Skrip ini tidak pernah membuat jendela, jadi prosesnya tetap DPI-unaware dan
# koordinat BitBlt-nya akan tervirtualisasi (terukur: GetSystemMetrics menjawab
# 1536x864 di layar 1920x1080). Dinyatakan sadar-DPI di sini supaya koordinat yang
# kita minta sama dengan koordinat piksel fisik.
try:
    pd.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:
    try:
        pd.user32.SetProcessDPIAware()
    except Exception:
        pass


def print_jendela(hwnd, w: int, h: int) -> bytes:
    """Minta jendela menggambar DIRINYA ke DC kita, termasuk isi DirectComposition.

    BitBlt dari screen DC tidak bisa melihat isi WebView2 -- ia menggambar lewat
    DirectComposition, bukan GDI, dan yang tertangkap cuma latar form-nya. Itu
    sebabnya seluruh probe pertama melaporkan "kotak merah tidak tergambar".
    PW_RENDERFULLCONTENT (0x2) meminta jendelanya sendiri yang merender.
    """
    u = pd.user32
    g = pd.gdi32
    u.PrintWindow.argtypes = [pd.wintypes.HWND, pd.wintypes.HDC, pd.wintypes.UINT]
    u.PrintWindow.restype = pd.wintypes.BOOL
    g.PatBlt.argtypes = [pd.wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, pd.wintypes.DWORD]

    hdc = u.GetDC(None)
    mem = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    lama = g.SelectObject(mem, bmp)
    # WHITENESS: isi dulu dengan putih, supaya bagian yang TIDAK tergambar
    # kelihatan sebagai putih, bukan sebagai sampah memori.
    g.PatBlt(mem, 0, 0, w, h, 0x00FF0062)
    u.PrintWindow(hwnd, mem, 0x00000002)

    info = pd.BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(pd.BITMAPINFOHEADER)
    info.bmiHeader.biWidth = w
    info.bmiHeader.biHeight = -h
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(info), 0)
    g.SelectObject(mem, lama)
    g.DeleteObject(bmp)
    g.DeleteDC(mem)
    u.ReleaseDC(None, hdc)
    return buf.raw


def main() -> int:
    arg = sys.argv[1:]
    cara_print = False
    if arg and arg[0] == "--print":
        cara_print = True
        arg = arg[1:]
    judul = ""
    if arg and not arg[0].lstrip("-").isdigit():
        # Argumen pertama berupa nama jendela: tangkap rect jendela itu, dilebihkan
        # sedikit supaya tepinya ikut terlihat.
        judul = arg[0]
        hwnd = pd.user32.FindWindowW(None, judul)
        if not hwnd:
            print(f"jendela '{judul}' tidak ketemu")
            return 1
        rx, ry, rw, rh = pd.rect_jendela(hwnd)
        m = 12
        x, y, w, h = max(0, rx - m), max(0, ry - m), rw + 2 * m, rh + 2 * m
        print(f"jendela '{judul}' 0x{hwnd:x} rect {rw}x{rh} @({rx},{ry})")
        arg = arg[1:]
    elif len(arg) >= 4:
        x, y, w, h = (int(v) for v in arg[:4])
        arg = arg[4:]
    else:
        x, y, w, h = 0, 0, pd.user32.GetSystemMetrics(0), pd.user32.GetSystemMetrics(1)
    keluaran = arg[0] if arg else "var/probe/lihat.png"

    peta = print_jendela(hwnd, w, h) if (cara_print and judul) else pd.tangkap(x, y, w, h)
    pd.simpan_png(peta, w, h, keluaran)
    print(f"{'PrintWindow' if (cara_print and judul) else 'BitBlt'} "
          f"{w}x{h} pada ({x},{y}) -> {keluaran}")
    print(f"merah={pd.hitung_merah(peta, w, h)} biru={pd.hitung_biru(peta, w, h)}")
    from collections import Counter
    c: Counter = Counter()
    for i in range(0, w * h * 4, 4):
        c[(peta[i + 2], peta[i + 1], peta[i])] += 1
    print("warna terbanyak:")
    for warna, n in c.most_common(8):
        print(f"   {warna}  {n}")
    print(pd.peta_ascii(peta, w, h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
