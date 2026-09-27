"""Uji tanam: bisakah jendela WebView2 jadi bagian desktop (lapisan WorkerW)?

SEKALI PAKAI. Menjawab satu pertanyaan yang tidak bisa dijawab dari dokumentasi:
apakah WebView2 tetap hidup dan menggambar setelah jendelanya di-SetParent ke
WorkerW -- lapisan yang sama dengan wallpaper, di BELAKANG ikon desktop.

Susunannya sengaja persis seperti server_py/jendela.py: frameless, transparan,
on_top, lalu dikunci warnanya lewat WS_EX_LAYERED + LWA_COLORKEY. Kalau langkah
itu tidak dibawa, hasil ujinya tidak mewakili keadaan sebenarnya.

Yang diukur skrip ini: struktur. Induk jendelanya benar-benar WorkerW, jendelanya
masih terlihat, permukaan WebView2-nya masih ada, dan klik benar-benar lewat ke
desktop. Yang TIDAK bisa diukur skrip: apakah isinya benar-benar tergambar --
BitBlt dan PrintWindow dua-duanya buta pada DirectComposition. Itu bagian mata
Master, dan jendelanya sengaja dibiarkan hidup supaya bisa dilihat.

Jalankan:  .venv\\Scripts\\python.exe scripts/probe_tanam.py
Hentikan:  Ctrl+C, atau tutup prosesnya.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_desktop as pd  # noqa: E402

JUDUL = "UJI-TANAM"
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
LWA_COLORKEY = 0x00000001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
HWND_TOP = 0

# Halaman uji: latar transparan, satu pita magenta besar di tengah. Magenta dipilih
# karena tidak mungkin tertukar dengan apa pun di desktop.
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:transparent;overflow:hidden}
#pita{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
      width:70%;height:34%;background:#ff00ff;color:#111;
      font:700 30px/1.3 Segoe UI,sans-serif;display:flex;align-items:center;
      justify-content:center;text-align:center;border-radius:18px}
</style></head><body>
<div id="pita">KALAU INI TERLIHAT DI DESKTOP,<br>BERARTI BISA</div>
</body></html>"""


# GetParent belum ada di probe_desktop, dan tanpa restype eksplisit handle 64-bit-nya
# terpotong jadi int 32-bit -- kelas induknya lalu terbaca dari alamat yang salah.
pd.user32.GetParent.restype = wintypes.HWND
pd.user32.GetParent.argtypes = [wintypes.HWND]


def cari_workerw():
    """Kanvas desktop: WorkerW yang bersaudara tepat SESUDAH jendela pemilik
    SHELLDLL_DefView -- dan kandidatnya wajib TERLIHAT serta selebar layar.

    Susunan di mesin ini, terukur 27 Sep (baca-saja, bukan dugaan):

        Progman 1536x864 vis=True judul=15
          SHELLDLL_DefView 1536x864 vis=True
            SysListView32 1536x864 vis=True      <- ikon desktop
        WorkerW 133x38 vis=False  (x15, semua kosong)

    Dua akibatnya. Pertama, SHELLDLL_DefView menempel di Progman, bukan di WorkerW,
    jadi varian ini harus ditangani sendiri. Kedua, lima belas WorkerW kecil dan
    tak terlihat itu membuat pencarian yang longgar salah sasaran: percobaan pertama
    memilih salah satunya, dan SetParent ke jendela tak terlihat berakhir dengan
    induk (null). Karena itu sekarang ada syarat bentuk, bukan cuma nama kelas.
    """
    progman = pd.user32.FindWindowW("Progman", None)
    hasil = ctypes.c_size_t()
    # 0x052C: minta Progman melahirkan WorkerW di belakang ikon.
    pd.user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0002, 1000, ctypes.byref(hasil))
    time.sleep(0.8)

    layar_w = pd.user32.GetSystemMetrics(0)
    layar_h = pd.user32.GetSystemMetrics(1)
    pemilik: list[int] = []
    kandidat: list[int] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if pd.user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            pemilik.append(hwnd)
            w = pd.user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if w:
                kandidat.append(w)
        return True

    pd.user32.EnumWindows(WNDENUMPROC(cb), 0)

    print(f"    layar {layar_w}x{layar_h} | pemilik SHELLDLL_DefView: "
          f"{[hex(h) for h in pemilik]}")
    for w in kandidat:
        r = pd.rect_jendela(w)
        vis = bool(pd.user32.IsWindowVisible(w))
        print(f"    kandidat WorkerW 0x{w:x} {r[2]}x{r[3]} vis={vis}")
        if vis and r[2] >= layar_w * 0.9 and r[3] >= layar_h * 0.9:
            return w, "WorkerW kanvas (tervalidasi bentuk)"
    # Varian kedua: DefView memang anak WorkerW, bukan anak Progman.
    for h in pemilik:
        if bool(pd.user32.IsWindowVisible(h)):
            return h, f"{kelas(h)} -- pemilik SHELLDLL_DefView (varian kedua)"
    return progman, "Progman (cadangan: ditanam sebagai saudara SHELLDLL_DefView)"


def kelas(hwnd) -> str:
    return pd.kelas_jendela(hwnd)


def main() -> int:
    import webview

    jendela = webview.create_window(
        JUDUL, html=HTML, width=900, height=420, frameless=True, transparent=True,
        on_top=True, easy_drag=False, shadow=False, focus=False,
    )
    siap = threading.Event()
    jendela.events.loaded += lambda *_: siap.set()

    def kerja():
        try:
            if not siap.wait(25):
                print("GAGAL: halaman tidak pernah memicu loaded", file=sys.stderr)
                return
            time.sleep(1.5)
            hwnd = pd.user32.FindWindowW(None, JUDUL)
            if not hwnd:
                print("GAGAL: jendela tidak ketemu", file=sys.stderr)
                return
            print(f"[1] jendela lahir    : {pd.rect_jendela(hwnd)} "
                  f"exstyle 0x{pd.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF:x}")

            # Kunci warna latar form, sama seperti server_py/jendela.py.
            merah = hijau = biru = 240
            try:
                from webview.platforms import winforms as wf

                form = wf.BrowserView.instances[jendela.uid]
                merah, hijau, biru = form.BackColor.R, form.BackColor.G, form.BackColor.B
            except Exception as err:
                print(f"    (BackColor tidak terbaca: {err})", file=sys.stderr)
            ex = pd.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            ex = (ex | WS_EX_LAYERED | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            pd.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
            pd.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                   SWP_FRAMECHANGED | SWP_NOACTIVATE | 0x0002 | 0x0001)
            pd.user32.SetLayeredWindowAttributes(hwnd, (biru << 16) | (hijau << 8) | merah,
                                                 0, LWA_COLORKEY)
            print(f"[2] warna dikunci    : {merah},{hijau},{biru} | "
                  f"exstyle 0x{pd.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF:x}")

            # ── TANAM ────────────────────────────────────────────────────────
            workerw, ket = cari_workerw()
            print(f"[3] kanvas desktop   : {ket} (0x{workerw:x})")
            # SetParent memulangkan induk LAMA. NULL di sini artinya "sebelumnya tidak
            # punya induk" -- yaitu keadaan normal jendela puncak, BUKAN kegagalan.
            # Keberhasilannya dibaca dari GetParent sesudahnya, bukan dari nilai balik.
            sebelum = pd.user32.SetParent(hwnd, workerw)
            galat = ctypes.get_last_error()
            induk_baru = pd.user32.GetParent(hwnd)
            cocok = induk_baru == workerw
            print(f"[4] SetParent        : induk lama "
                  f"{'(tidak ada)' if not sebelum else hex(sebelum)} -> "
                  f"induk baru {kelas(induk_baru)} [{'COCOK' if cocok else 'TIDAK COCOK'}]")
            print(f"    GetLastError     : {galat} "
                  f"({ctypes.FormatError(galat) if galat else 'tidak ada galat'})")
            print(f"    gaya jendela     : WS_CHILD={'ya' if pd.user32.GetWindowLongPtrW(hwnd, -16) & 0x40000000 else 'tidak'} "
                  f"WS_POPUP={'ya' if pd.user32.GetWindowLongPtrW(hwnd, -16) & 0x80000000 else 'tidak'}")
            print(f"    pemilik jendela  : {kelas(pd.user32.GetWindow(hwnd, 4))}")  # GW_OWNER

            # Percobaan kedua: SetParent kadang menolak jendela puncak yang masih
            # ber-WS_POPUP. Gaya WS_CHILD dipasang dulu, baru ditanam ulang.
            if not cocok:
                gaya = pd.user32.GetWindowLongPtrW(hwnd, -16)
                pd.user32.SetWindowLongPtrW(hwnd, -16, (gaya | 0x40000000) & ~0x80000000)
                sebelum2 = pd.user32.SetParent(hwnd, workerw)
                galat2 = ctypes.get_last_error()
                induk2 = pd.user32.GetParent(hwnd)
                cocok = induk2 == workerw
                print(f"[4b] SetParent+WS_CHILD: induk baru {kelas(induk2)} "
                      f"[{'COCOK' if cocok else 'TIDAK COCOK'}] "
                      f"| GetLastError {galat2} "
                      f"({ctypes.FormatError(galat2) if galat2 else 'tidak ada galat'})")

            if not cocok:
                # JANGAN dibesarkan ke seluruh layar: itu menutupi desktop Master
                # tanpa memberi jawaban apa pun. Gagal = berhenti bersih di sini.
                print("\nGAGAL menanam: induknya tidak berubah. Jendela ditutup, "
                      "layar tidak disentuh.", file=sys.stderr)
                jendela.destroy()
                return

            # Kalau yang dipakai Progman (varian tanpa WorkerW), jendela harus
            # diletakkan di DASAR tumpukan supaya berada di bawah SHELLDLL_DefView.
            _k, _a, lebar, tinggi = pd.area_kerja()
            pd.user32.SetWindowPos(hwnd, 1 if workerw == pd.user32.FindWindowW("Progman", None)
                                   else HWND_TOP, 0, 0, lebar, tinggi,
                                   SWP_NOACTIVATE | SWP_SHOWWINDOW)
            time.sleep(2.0)

            r = pd.rect_jendela(hwnd)
            px, py = r[0] + r[2] // 2, r[1] + r[3] // 2
            terlihat = bool(pd.user32.IsWindowVisible(hwnd))
            atas_kursor = kelas(pd.user32.WindowFromPoint(wintypes.POINT(px, py)))
            print(f"[5] sesudah tanam    : rect {r[2]}x{r[3]} @({r[0]},{r[1]})")
            print(f"[6] masih terlihat?  : {terlihat}")
            print(f"[7] permukaan webview: "
                  f"{pd.anak_jendela(hwnd, maks=4) or 'TIDAK ADA ANAK'}")
            print(f"[8] WindowFromPoint  : {atas_kursor}")
            print(f"[9] induk            : {kelas(pd.user32.GetParent(hwnd))}")

            print("\n" + "=" * 60)
            print("BACAAN")
            print("=" * 60)
            print(f"induk = WorkerW        : "
                  f"{'YA' if 'WorkerW' in kelas(pd.user32.GetParent(hwnd)) else 'TIDAK'}")
            print(f"klik lewat ke desktop  : "
                  f"{'YA' if any(k in atas_kursor for k in ('DefView', 'SysListView', 'WorkerW', 'Progman')) else 'TIDAK'}")
            print(f"permukaan masih hidup  : "
                  f"{'YA' if pd.anak_jendela(hwnd) else 'TIDAK'}")
            print("\nJendela ini DIBIARKAN HIDUP supaya bisa dilihat mata.")
            print("Tekan Win+D (tampilkan desktop) -- pita magenta harus terlihat")
            print("DI BELAKANG ikon desktop. Ctrl+C untuk menghentikan.")
        except Exception:
            import traceback
            traceback.print_exc()

    webview.start(kerja, gui="edgechromium", debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
