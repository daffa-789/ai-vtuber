"""Jendela pet: Elaina melayang di desktop, tanpa bingkai, tembus pandang.

Dijalankan lewat pywebview + WebView2 (runtime Edge sudah ada di mesin ini, v153).
Kenapa bukan render Live2D langsung dari Python: SDK Cubism tidak punya jalur
Native untuk Python, dan build Cubism Native butuh compiler C++ yang tidak ada di
mesin ini (cl/cmake/gcc nol). Jadi JS tetap ada -- tapi terkubur di dalam jendela,
dan Master tidak pernah membuka browser atau menyentuh berkasnya.

Fakta yang diukur sebelum modul ini ditulis (probe 27 Sep, 240x240, sampling grid):
hanya 1351 dari 29929 titik yang berubah saat jendela transparan ditampilkan, dan
kotak merahnya sendiri menyumbang 1445 -- artinya desktop benar-benar tembus.
Frameless + transparent + on_top bekerja di WebView2 pada mesin ini.

Satu hal yang TIDAK boleh diulang dari probe pertama: koordinat yang kita kirim ke
pywebview bukan koordinat piksel fisik. Layar ini berskala DPI >100%, jadi posisi
harus dihitung dari work area lalu dibagi faktor skala -- kalau tidak, "pojok kanan
bawah" mendarat di tengah layar dan taskbar tertutup.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import konfig  # satu sumber kebenaran untuk knob perilaku (.env)
except Exception:  # dijalankan lepas dari proyek pun harus tetap hidup
    konfig = None


class _Persegi(ctypes.Structure):
    _fields_ = [("kiri", ctypes.c_long), ("atas", ctypes.c_long),
                ("kanan", ctypes.c_long), ("bawah", ctypes.c_long)]


SPI_GETWORKAREA = 0x0030


def area_kerja() -> tuple[int, int, int, int]:
    """Work area piksel fisik: layar dikurangi taskbar. Bukan full screen."""
    try:
        r = _Persegi()
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
            return r.kiri, r.atas, r.kanan - r.kiri, r.bawah - r.atas
    except Exception:
        pass
    return 0, 0, ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)


def skala_dpi() -> float:
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


def tunggu_siap(base: str, url: str | None = None, pelayan=None, batas: float = 240.0) -> bool:
    """Jangan tampilkan dia sebelum /api/health menjawab -- jendela kosong dengan
    avatar yang belum tergambar terlihat seperti aplikasi rusak, bukan sedang memuat.

    `pelayan` (thread Flask) ikut dipantau: kalau dia mati lebih dulu, menunggu
    sampai habis batas hanya menyembunyikan penyebab aslinya. Persis itu yang
    terjadi pada percobaan pertama (TypeError dari parameter run() yang tidak ada),
    dan tanpa pemeriksaan ini gejalanya cuma "jendela tidak muncul".
    """
    t0 = time.monotonic()
    while time.monotonic() - t0 < batas:
        if pelayan is not None and not pelayan.is_alive():
            return False
        try:
            with urlopen(url or base.rstrip("/") + "/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def tempel_ke_dasar(judul: str, tunggu: float = 12.0) -> bool:
    """Geser jendela yang SUDAH jadi supaya dasar fisiknya pas di garis taskbar.

    Menghitung y dari tinggi yang kita MINTA itu salah: pywebview/WinForms memotong
    bingkai tak-klien (terukur di mesin ini: minta 430x650, jadi 415x612 -- bukan
    rasio skala, jadi tidak bisa dikoreksi dengan perkalian). Satu-satunya angka yang
    jujur adalah rect asli jendela, jadi diambil dari sana lalu digeser.

    Area kerja dihitung ULANG di dalam thread ini, bukan diwarisi dari pemanggil.
    Sebabnya terukur 27 Sep: sebelum webview.start(), prosesnya masih DPI-unaware,
    jadi SPI_GETWORKAREA menjawab satuan virtual -- 1536x816 di layar 1920x1080
    berskala 125%. Dipakai apa adanya, "dasar" itu mendarat di y=816 padahal taskbar
    ada di y=1020, dan karakternya melayang 204 px di atas taskbar.
    """
    if os.name != "nt":
        return False
    try:
        from ctypes import wintypes

        u = ctypes.WinDLL("user32", use_last_error=True)
        u.FindWindowW.restype = wintypes.HWND
        u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]

        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                        ("r", ctypes.c_long), ("b", ctypes.c_long)]

        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
        u.GetWindowRect.restype = wintypes.BOOL
        u.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wintypes.BOOL]
        u.MoveWindow.restype = wintypes.BOOL

        t0 = time.monotonic()
        while time.monotonic() - t0 < tunggu:
            h = u.FindWindowW(None, judul)
            if h:
                _kiri, _atas, _lebar, _tinggi = area_kerja()
                batas_bawah = _atas + _tinggi
                r = RECT()
                if u.GetWindowRect(h, ctypes.byref(r)) and (r.b - r.t) > 40:
                    geser = batas_bawah - r.b
                    if abs(geser) <= 1:
                        return True
                    u.MoveWindow(h, r.l, r.t + geser, r.r - r.l, r.b - r.t, True)
                    # pywebview masih menyelesaikan ukuran jendelanya SETELAH start()
                    # berjalan, jadi satu kali geser bisa tertimpa: pada percobaan
                    # pertama thread ini menemukan jendela saat tingginya masih 941,
                    # menggeser -125, lalu jendela dikecilkan ke 612 dan mendarat
                    # setengah jalan ke atas. Diulang sampai rect-nya tidak bergerak
                    # lagi -- dua putaran identik dianggap stabil.
                    time.sleep(1.2)
                    r2 = RECT()
                    u.GetWindowRect(h, ctypes.byref(r2))
                    if abs((batas_bawah - r2.b)) <= 1:
                        return True
            time.sleep(0.4)
        return False
    except Exception:
        return False


GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
LWA_COLORKEY = 0x00000001
SWP_FRAMECHANGED = 0x0020
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def tembuskan(jendela, judul: str, tunggu: float = 20.0) -> bool:
    """Bikin jendela pet benar-benar tembus pandang, dan buang dari taskbar.

    INI BUKAN PENYEMPURNAAN. pywebview 6.2.1 menyalakan transparansi di WebView2-nya
    (platforms/edgechromium.py:114: DefaultBackgroundColor = Color.Transparent) TAPI
    tidak pernah menyentuh form WinForms induknya: BackColor tetap Control, dan
    seluruh paket itu tidak sekali pun memakai TransparencyKey maupun
    SetLayeredWindowAttributes. Akibatnya, terukur 27 Sep di mesin ini:

      - exstyle jendela = 0x50008 -- TIDAK ada WS_EX_LAYERED, jadi mustahil tembus;
      - PrintWindow dengan PW_RENDERFULLCONTENT memulangkan 397035 piksel
        (240,240,240) seragam, yaitu BackColor form menutupi seluruh jendela;
      - WS_EX_APPWINDOW ikut terpasang, jadi jendelanya muncul di taskbar dan Alt+Tab.

    Obatnya color key: WS_EX_LAYERED + LWA_COLORKEY dengan warna latar form sebagai
    kunci. Semua piksel yang persis sewarna itu jadi tembus, dan karakter yang
    digambar di atasnya tetap. Terukur pada probe yang sama: setelah dikunci, sudut
    jendela berubah dari (240,240,240) menjadi warna wallpaper desktop.

    Harga yang harus diketahui: tepi karakter yang berantialias bercampur dengan
    warna latar itu, jadi ada rim tipis sewarna latar di sekeliling siluet. Itu
    batas teknik color key, bukan bug yang bisa dihilangkan dengan penyetelan.
    """
    if os.name != "nt":
        return False
    try:
        from ctypes import wintypes

        u = ctypes.WinDLL("user32", use_last_error=True)
        u.FindWindowW.restype = wintypes.HWND
        u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        u.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                 ctypes.c_ubyte, wintypes.DWORD]
        u.SetLayeredWindowAttributes.restype = wintypes.BOOL
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.UINT]
        u.SetWindowPos.restype = wintypes.BOOL

        t0 = time.monotonic()
        hwnd = None
        while time.monotonic() - t0 < tunggu:
            hwnd = u.FindWindowW(None, judul)
            if hwnd:
                break
            time.sleep(0.3)
        if not hwnd:
            print("  ! tembuskan: jendela tidak ketemu, latar tetap pekat", file=sys.stderr)
            return False

        # Warna kunci diambil dari form-nya sendiri, bukan ditulis 240,240,240:
        # nilainya bisa berbeda kalau tema Windows berubah.
        merah, hijau, biru = 240, 240, 240
        try:
            from webview.platforms import winforms as wf

            form = None
            for _coba in range(12):
                peta = getattr(wf.BrowserView, "instances", {}) or {}
                # Kunci menurut uid dulu; kalau belum terdaftar (jendelanya sudah
                # punya HWND tapi pendaftarannya belum jalan -- terukur: KeyError
                # 'master'), pakai satu-satunya isi peta itu. Jangan berhenti di
                # nilai cadangan 240,240,240: itu kebetulan benar untuk tema terang
                # bawaan, dan akan salah begitu temanya berganti.
                form = peta.get(jendela.uid) or (next(iter(peta.values())) if len(peta) == 1 else None)
                if form is not None:
                    break
                time.sleep(0.25)
            if form is None:
                raise LookupError("form tidak terdaftar di BrowserView.instances")
            merah, hijau, biru = form.BackColor.R, form.BackColor.G, form.BackColor.B
        except Exception as err:
            print(f"  ! tembuskan: BackColor form tidak terbaca ({err}); "
                  f"pakai 240,240,240", file=sys.stderr)

        ex = u.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_LAYERED | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        u.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
        u.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                       SWP_FRAMECHANGED | SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE)
        ref = (biru << 16) | (hijau << 8) | merah  # COLORREF = BGR
        ok = u.SetLayeredWindowAttributes(hwnd, ref, 0, LWA_COLORKEY)
        print(
            f"  pet: tembus pandang {'aktif' if ok else 'GAGAL'} "
            f"(kunci {merah},{hijau},{biru}) | exstyle 0x{u.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF:x}",
            file=sys.stderr,
            flush=True,
        )
        return bool(ok)
    except Exception as err:
        print(f"  ! tembuskan gagal: {err}", file=sys.stderr)
        return False


# ── perilaku: "biar tidak terasa seperti jendela" ────────────────────────────
# Menanam jendela ke lapisan desktop SUDAH DICOBA DAN GAGAL di mesin ini (lihat
# RENCANA-DESKTOP.md, Fase 1: tidak ada kanvas WorkerW, dan memaksa tanam membuat
# permukaan WebView2-nya mati). Jadi kesan itu dikejar lewat PERILAKU, bukan lewat
# lapisan: dia minggir saat memang tidak muat di layar, dan Master selalu punya
# jalan kembali lewat ikon tray + hotkey. Tanpa dua jalan kembali itu, fitur
# sembunyi-otomatis cuma cara kehilangan karakternya tanpa pesan.

SW_HIDE = 0
SW_SHOW = 5
HWND_TOPMOST = -1
VK_CTRL, VK_SHIFT, VK_ALT, VK_WIN = 0x11, 0x10, 0x12, 0x5B

# Jendela-jendela ini bukan "aplikasi yang menutupi layar", jadi tidak boleh
# memicu sembunyi: desktop itu sendiri, taskbar, dan Start Menu.
BUKAN_APLIKASI = {"Progman", "WorkerW", "ShellDLL_DefView", "SysListView32",
                  "Shell_TrayWnd", "Windows.UI.Core.CoreWindow", "XamlExplorerHostIslandWindow"}


def _kelas(hwnd) -> str:
    if not hwnd:
        return "(null)"
    buf = ctypes.create_unicode_buffer(256)
    ctypes.WinDLL("user32").GetClassNameW(hwnd, buf, 256)
    return buf.value or "(kosong)"


def _siapkan_user32():
    """Semua tanda tangan yang dipakai blok ini, dinyatakan eksplisit.

    Bukan kerapian: handle 64-bit yang dipulangkan sebagai int 32-bit akan
    terpotong dan panggilan berikutnya gagal tanpa galat. Pelajaran itu sudah
    dibayar dua kali di proyek ini (model_vulkan.py, dan bagian _induk_hidup di
    berkas ini).
    """
    from ctypes import wintypes

    u = ctypes.WinDLL("user32", use_last_error=True)
    u.GetForegroundWindow.restype = wintypes.HWND
    u.GetForegroundWindow.argtypes = []
    u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetClassNameW.restype = ctypes.c_int
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsWindowVisible.restype = wintypes.BOOL
    u.IsZoomed.argtypes = [wintypes.HWND]
    u.IsZoomed.restype = wintypes.BOOL
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetWindowRect.restype = wintypes.BOOL
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.ShowWindow.restype = wintypes.BOOL
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u.SetWindowPos.restype = wintypes.BOOL
    u.GetAsyncKeyState.argtypes = [ctypes.c_int]
    u.GetAsyncKeyState.restype = ctypes.c_short
    return u


def hotkey_vk(teks: str):
    """'ctrl+shift+s' -> ([VK_CTRL, VK_SHIFT], VK_S). None kalau tidak bisa dibaca."""
    bagian = [b.strip() for b in teks.replace(" ", "").split("+") if b.strip()]
    if not bagian:
        return None
    utama = bagian[-1]
    if len(utama) == 1 and utama.isalnum():
        vk_utama = ord(utama.upper())
    else:
        return None
    penahan = []
    for nama in bagian[:-1]:
        if nama == "ctrl":
            penahan.append(VK_CTRL)
        elif nama == "shift":
            penahan.append(VK_SHIFT)
        elif nama == "alt":
            penahan.append(VK_ALT)
        elif nama in ("win", "super"):
            penahan.append(VK_WIN)
        else:
            return None
    # WAJIB ada penahan. Tanpa ini, `VTUBER_PET_HOTKEY=s` akan menyambar setiap
    # huruf s yang Master ketik di aplikasi mana pun -- dan yang muncul adalah
    # kotak obrolan yang membuka sendiri, bukan hotkey.
    if not penahan:
        return None
    return penahan, vk_utama


def _depan(u):
    """(kelas, rasio_lebar, rasio_tinggi) jendela depan terhadap seluruh layar."""
    from ctypes import wintypes

    depan = u.GetForegroundWindow()
    if not depan:
        return "(tidak ada)", 0.0, 0.0
    r = wintypes.RECT()
    if not u.GetWindowRect(depan, ctypes.byref(r)):
        return _kelas(depan), 0.0, 0.0
    sw = u.GetSystemMetrics(0) or 1
    sh = u.GetSystemMetrics(1) or 1
    return _kelas(depan), (r.right - r.left) / sw, (r.bottom - r.top) / sh


def _layar_penuh(u, hwnd):
    """Jendela depan menutupi SELURUH monitor, termasuk pita taskbar.

    Ambangnya 0,98 dan itu dipilih, bukan ditebak: jendela yang hanya dimaksimalkan
    tetap menyisakan pita taskbar, jadi rasionya sekitar 0,94 di mesin ini -- dan
    kalau ambangnya diturunkan sampai situ, karakternya akan sembunyi hampir
    sepanjang waktu karena jendela maksimal itu keadaan kerja sehari-hari.
    """
    depan = u.GetForegroundWindow()
    if not depan or depan == hwnd:
        return False
    if _kelas(depan) in BUKAN_APLIKASI:
        return False
    if not u.IsWindowVisible(depan):
        return False
    _k, rw, rh = _depan(u)
    return rw >= 0.98 and rh >= 0.98


def _maksimal(u, hwnd) -> bool:
    depan = u.GetForegroundWindow()
    if not depan or depan == hwnd or _kelas(depan) in BUKAN_APLIKASI:
        return False
    return bool(u.IsZoomed(depan))


def sembunyikan(hwnd) -> bool:
    """True hanya kalau jendelanya benar-benar jadi tersembunyi.

    Tidak pernah melempar: dulu `tampilkan()` meledak karena satu konstanta yang
    lupa didefinisikan (SWP_SHOWWINDOW), dan akibatnya karakternya tertinggal
    sembunyi sementara keadaan di memori mengira dia sudah tampil -- pengintai lalu
    berhenti mencoba menampilkan lagi. Jadi keadaan di memori harus mengikuti
    hasil panggilannya, bukan ditebak sebelum panggilannya.
    """
    try:
        u = _siapkan_user32()
        u.ShowWindow(hwnd, SW_HIDE)
        return True
    except Exception as err:
        print(f"  ! sembunyikan gagal: {err}", file=sys.stderr, flush=True)
        return False


def tampilkan(hwnd) -> bool:
    try:
        u = _siapkan_user32()
        u.ShowWindow(hwnd, SW_SHOW)
        # SW_SHOW tidak menjamin dia kembali ke depan tumpukan; topmost-nya dipasang ulang.
        u.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        return True
    except Exception as err:
        print(f"  ! tampilkan gagal: {err}", file=sys.stderr, flush=True)
        return False


def pantau(jendela, judul: str, aturan: str, hotkey: str, tunggu: float = 25.0) -> None:
    """Thread pengintai: sembunyi-otomatis + hotkey kotak obrolan.

    Satu thread untuk dua pekerjaan, bukan dua, karena keduanya menyentuh keadaan
    yang sama (jendela ini terlihat atau tidak) dan dua thread yang mengurus satu
    keadaan adalah cara paling cepat membuatnya saling menimpa.

    `paksa` = kehendak Master dari ikon tray. Selama terisi, aturan otomatis tidak
    menang -- kalau tidak, menyembunyikan lewat tray akan langsung dibatalkan
    pengintai pada putaran berikutnya. `paksa` dilepas begitu keadaan layar penuh
    berubah, supaya karakternya tidak terjebak sembunyi selamanya.
    """
    from ctypes import wintypes  # noqa: F401  (dipakai lewat _siapkan_user32)

    u = _siapkan_user32()
    hwnd = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < tunggu and not hwnd:
        hwnd = ctypes.WinDLL("user32").FindWindowW(None, judul)
        time.sleep(0.3)
    if not hwnd:
        print("  ! pantau: jendela tidak ketemu, perilaku otomatis mati", file=sys.stderr)
        return

    pasangan = hotkey_vk(hotkey) if hotkey else None
    if hotkey and not pasangan:
        print(f"  ! hotkey '{hotkey}' tidak bisa dibaca (contoh yang benar: ctrl+shift+s)",
              file=sys.stderr)
    penahan_hotkey = False
    sembunyi = False
    paksa = None
    terakhir_penuh = False
    galat_terakhir = ""
    while True:
        try:
            penuh = _layar_penuh(u, hwnd)
            if penuh != terakhir_penuh:
                terakhir_penuh = penuh
                paksa = None  # keadaan layar berubah -> kehendak manual dilepas

            if paksa is not None:
                harus = paksa
            elif aturan == "layar-penuh":
                harus = penuh
            elif aturan == "maksimal":
                harus = penuh or _maksimal(u, hwnd)
            else:
                harus = False

            if harus != sembunyi:
                if harus:
                    kl, rw, rh = _depan(u)
                    print(f"  pet: minggir -- depan '{kl}' {rw:.2f}x{rh:.2f} dari layar",
                          file=sys.stderr, flush=True)
                    # Keadaan mengikuti hasil panggilan, bukan sebaliknya: kalau
                    # menyembunyikan gagal, `sembunyi` tetap False dan putaran
                    # berikutnya mencoba lagi.
                    sembunyi = sembunyikan(hwnd)
                else:
                    if tampilkan(hwnd):
                        print("  pet: kembali tampil", file=sys.stderr, flush=True)
                        sembunyi = False
                    else:
                        sembunyi = True

            if pasangan:
                penahan, utama = pasangan
                turun = bool(u.GetAsyncKeyState(utama) & 0x8000)
                semua = all(bool(u.GetAsyncKeyState(v) & 0x8000) for v in penahan)
                if turun and semua and not penahan_hotkey:
                    penahan_hotkey = True
                    if sembunyi:
                        sembunyi = False
                        paksa = False
                        tampilkan(hwnd)
                    try:
                        jendela.evaluate_js(
                            "window.__vtuberPanel && window.__vtuberPanel()")
                    except Exception as err:
                        print(f"  ! hotkey: panel tidak bisa dibuka ({err})", file=sys.stderr)
                elif not (turun and semua):
                    penahan_hotkey = False
        except Exception as err:
            # Dicetak sekali per pesan, bukan tiap 350 ms: satu galat yang bertahan
            # akan membanjiri log dan menyembunyikan galat berikutnya.
            pesan = f"  ! pantau: {err}"
            if pesan != galat_terakhir:
                galat_terakhir = pesan
                print(pesan, file=sys.stderr, flush=True)
        time.sleep(0.35)


def pasang_tray(jendela, judul: str) -> bool:
    """Ikon tray: Tampilkan / Sembunyikan / Keluar.

    Ini bukan hiasan. Sembunyi-otomatis tanpa jalan kembali berarti karakternya
    bisa hilang dan Master tidak punya cara memanggilnya lagi selain membunuh
    prosesnya.

    Dijalankan di thread .NET ber-apartment STA dengan Application.Run() sendiri,
    bukan di thread Python biasa: NotifyIcon butuh message loop, dan menu klik
    kanannya butuh STA. pywebview sendiri membuat thread UI-nya dengan cara yang
    sama (platforms/winforms.py).
    """
    def kerja():
        # Thread Python biasa, tapi dinyatakan STA lewat CoInitializeEx. Cara ini
        # dipilih supaya seluruh pemuatan .NET (import clr + AddReference) terjadi
        # DI DALAM thread ini, SETELAH jendelanya hidup -- bukan di thread utama
        # sebelum webview.start(). Kalau WinForms dimuat lebih dulu di thread utama,
        # ia ikut menyetel DPI awareness dan Application context, dan itu wilayah
        # yang sudah terbukti rapuh di mesin ini (lihat catatan storage_path).
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
        except Exception:
            pass

        def cari():
            return ctypes.WinDLL("user32").FindWindowW(None, judul)

        t0 = time.monotonic()
        while time.monotonic() - t0 < 30 and not cari():
            time.sleep(0.3)
        if not cari():
            print("  ! tray: jendela tidak pernah muncul, ikon tidak dipasang", file=sys.stderr)
            return

        try:
            import clr  # noqa: F401
            from System import EventHandler
            from System.Drawing import Bitmap, Color as Warna, Graphics, Icon, SolidBrush
            from System.Windows.Forms import (Application, ContextMenuStrip, NotifyIcon,
                                              ToolStripMenuItem, ToolStripSeparator)

            bmp = Bitmap(32, 32)
            g = Graphics.FromImage(bmp)
            g.Clear(Warna.Transparent)
            g.FillEllipse(SolidBrush(Warna.FromArgb(255, 232, 182, 115)), 4, 4, 24, 24)

            def ke_tampil(_s=None, _e=None):
                h = cari()
                if h:
                    tampilkan(h)

            def ke_sembunyi(_s=None, _e=None):
                h = cari()
                if h:
                    sembunyikan(h)

            def ke_keluar(_s=None, _e=None):
                try:
                    jendela.destroy()
                except Exception:
                    pass
                Application.Exit()

            # Item dibuat lewat teksnya saja, lalu handler dipasang terpisah.
            # Bentuk tiga-argumen ToolStripMenuItem(str, Image, EventHandler) TIDAK
            # bisa diselesaikan pythonnet -- `None` pada posisi Image membuat
            # pemilihan overload gagal ("No method matches given arguments"), dan
            # ikon tray-nya tidak pernah muncul. Sudah terjadi, jangan diulang.
            def item(teks, aksi):
                it = ToolStripMenuItem(teks)
                it.Click += EventHandler(aksi)
                return it

            menu = ContextMenuStrip()
            menu.Items.Add(item("Tampilkan", ke_tampil))
            menu.Items.Add(item("Sembunyikan", ke_sembunyi))
            menu.Items.Add(ToolStripSeparator())
            menu.Items.Add(item("Keluar", ke_keluar))

            ikon = NotifyIcon()
            ikon.Icon = Icon.FromHandle(bmp.GetHicon())
            ikon.Text = judul
            ikon.ContextMenuStrip = menu
            ikon.Visible = True
            print("  pet: ikon tray terpasang (Tampilkan / Sembunyikan / Keluar)",
                  file=sys.stderr, flush=True)
            Application.Run()
        except Exception as err:
            print(f"  ! tray gagal: {err}", file=sys.stderr, flush=True)

    threading.Thread(target=kerja, daemon=True).start()
    return True


def buka(base: str, lebar: int = 430, tinggi: int = 650, judul: str = "Silver Wolf",
         siap: str | None = None, pelayan=None, induk: int = 0) -> int:
    """Blokir sampai jendela ditutup. Kode proses dikembalikan.

    `induk` = PID proses server kalau jendela ini dijalankan sebagai anak darinya;
    kalau induk mati (dibunuh paksa, jadi tidak ada atexit), jendela ikut ditutup
    dalam 2 dtk supaya tidak tertinggal sebagai kartu hantu di desktop.
    """
    try:
        import webview
    except ImportError:
        print(
            "pywebview tidak terpasang -- jalankan: .venv\\Scripts\\python.exe -m pip install pywebview\n"
            "Sementara waktu, buka saja " + base + " di browser (mode biasa).",
            file=sys.stderr,
        )
        return 1

    if not tunggu_siap(base, url=siap, pelayan=pelayan):
        pesan = "thread sisi web mati" if (pelayan is not None and not pelayan.is_alive()) else "batas waktu habis"
        print(
            f"server tidak siap ({pesan}); jendela TIDAK dibuka. "
            f"Padahal dia akan menunjukkannya sendiri: {base}",
            file=sys.stderr,
        )
        return 1
    kiri, atas, w, h = area_kerja()
    faktor = skala_dpi()
    # pywebview/WinForms memakai satuan LOGIS; work area fisik. Bagi dulu, baru
    # tempel. Dasar jendela MEMPELEK ke garis bawah area kerja (bukan +24): dengan
    # VITE_AVATAR_JANGKAR=1 model digantung di dasar kanvas, jadi kaki dia
    # "injak" taskbar persis seperti desktop pet sungguhan.
    x = int(kiri + w - lebar / faktor - 8)
    y = int(atas + h - tinggi / faktor)

    jendela = webview.create_window(
        judul,
        url=base.rstrip("/") + "/?tampak=pet",
        x=x,
        y=y,
        width=lebar,
        height=tinggi,
        frameless=True,
        transparent=True,
        on_top=True,
        easy_drag=True,
        # background_color TIDAK dikirim: pywebview hanya menerima hex triplet
        # 6 digit, dan '#00000000' ditolak dengan ValueError. Transparansi sudah
        # jadi tugas transparent=True (dibuktikan probe: 1351/29929 titik berubah,
        # dan 1445 di antaranya adalah kotak merahnya sendiri).
    )
    if induk and os.environ.get("VTUBER_PET_JAGA_INDUK", "tidak").strip().lower() in ("ya", "1", "true", "on"):
        # MATI sebagai bawaan, dan itu pilihan sadar. Penjaga ini menutup jendela
        # dalam 2 dtk kalau ia menyimpulkan induk sudah mati -- dan satu pembacaan
        # yang salah simpul membuat pet hilang SEKETIKA tanpa pesan, jauh lebih
        # buruk daripada satu jendela tertinggal. (Terjadi pada pengujian 27 Sep:
        # varian dengan flag QUERY_LIMITED membuat jendela tak pernah muncul.)
        # Nyalakan lewat VTUBER_PET_JAGA_INDUK=ya kalau jendela hantu lebih
        # mengganggu daripada proses sisa.
        _jaga_induk(induk, jendela)
    # Jendela dibuat oleh thread ini juga, tapi rect-nya baru ada setelah WebView2
    # sempat naik -- makanya penempelan ke garis taskbar dijalankan sebagai thread
    # pendamping yang menunggu rect-nya nyata (lihat docstring tempel_ke_dasar).
    threading.Thread(target=tempel_ke_dasar, args=(judul,), daemon=True).start()
    # Transparansi dan pembuangan dari taskbar juga menunggu jendelanya nyata, dan
    # urutannya setelah penempelan supaya SetWindowPos di dalamnya tidak membatalkan
    # posisi yang baru saja dipasang.
    threading.Thread(target=tembuskan, args=(jendela, judul), daemon=True).start()

    # Perilaku "biar tidak terasa seperti jendela". Diambil dari konfig kalau ada,
    # supaya .env tetap satu-satunya tempat menyetel.
    aturan = getattr(konfig, "PET_SEMBUNYI", "layar-penuh") if konfig else "layar-penuh"
    hotkey = getattr(konfig, "PET_HOTKEY", "") if konfig else ""
    tray = bool(getattr(konfig, "PET_TRAY", True)) if konfig else True
    print(f"  pet: sembunyi otomatis='{aturan}' | tray={'ya' if tray else 'tidak'} | "
          f"hotkey='{hotkey or 'mati'}'", file=sys.stderr, flush=True)
    threading.Thread(target=pantau, args=(jendela, judul, aturan, hotkey),
                     daemon=True).start()
    if tray:
        pasang_tray(jendela, judul)
    # gui eksplisit: di Windows ada juga backend mshtml (IE) yang tidak bisa
    # transparan dan tidak sanggup menjalankan pixi/WebGL.
    #
    # storage_path SENGAJA tidak dipakai. Ia dicoba pada 27 Sep untuk menghindari
    # profil WebView2 terkunci dari instance yang dibunuh paksa, dan hasilnya
    # justru regresi sunyi: webview.start() kembali seketika tanpa satu baris pun
    # dicetak, dan jendela tidak pernah ada. Tanpa parameter itu jendela muncul
    # (terverifikasi dua kali). Jadi biarkan pywebview memilih foldernya sendiri.
    webview.start(gui="edgechromium", debug=False)
    return 0


# ── dijalankan sebagai PROSES TERSENDIRI ─────────────────────────────────────
# Ini bukan gaya-gayaan, dan penyebabnya terukur 27 Sep dengan tiga varian A/B:
#
#   vulkan + sapuan, tanpa RVC   -> jendela MUNCUL
#   RVC dimuat di proses yang sama -> webview.start() kembali seketika, nol error
#   tanpa sapuan (sapu_yatim=[]) -> jendela MUNCUL (sebelum bug handle diperbaiki)
#
# WinForms/pywebview menuntut thread utama ber-apartment STA. Tumpukan RVC
# (torch + fairseq + onnxruntime + praat) sudah menyetel COM di thread utama proses
# server, dan setelah itu WebView2 tidak mau hidup -- tanpa pesan galat apa pun.
# Memisahkan jendela ke proses anak memberinya thread utama yang bersih, dan itu
# satu-satunya susunan yang terbukti jalan di mesin ini.
def _induk_hidup(pid: int) -> bool:
    """False HANYA kalau induk pasti sudah mati. Ragu = anggap hidup.

    Ini ulangan pelajaran dari model_vulkan: `OpenProcess` tanpa `restype = HANDLE`
    memulangkan int 32 bit, handle 64-bit terpotong, `GetExitCodeProcess` gagal,
    kode tetap 0, dan 0 != STILL_ACTIVE dibaca sebagai "induk mati" -- sehingga
    pengawas ini justru MENUTUP jendela yang harusnya dijaganya. Semua tanda tangan
    di bawah karena itu dinyatakan eksplisit, dan setiap cabang gagal mengembalikan
    True.
    """
    if pid <= 0 or os.name != "nt":
        return True
    try:
        from ctypes import wintypes

        # WinDLL(use_last_error=True), bukan windll: tanpa itu ctypes.get_last_error()
        # selalu 0 dan "proses tidak ada" tidak bisa dibedakan dari "akses ditolak".
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not getattr(k32, "_jendela_ditandatangani", False):
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            k32.GetExitCodeProcess.restype = wintypes.BOOL
            k32.CloseHandle.argtypes = [wintypes.HANDLE]
            k32._jendela_ditandatangani = True

        SYNCHRONIZE = 0x00100000
        PROSES_QUERY_LIMITED = 0x1000
        STILL_ACTIVE = 259
        ACCESS_DENIED = 5
        # QUERY_LIMITED WAJIB ikut diminta: dengan SYNCHRONIZE saja,
        # GetExitCodeProcess membalas False (terukur: handle valid, err 5 sisa
        # lama, kode 0 tapi tidak terbaca) dan jendela tidak akan pernah tertutup.
        h = k32.OpenProcess(SYNCHRONIZE | PROSES_QUERY_LIMITED, False, pid)
        if not h:
            # NULL + ACCESS_DENIED = masih hidup tapi tidak boleh dibuka (jarang
            # untuk proses milik sendiri). NULL dengan sebab lain = PID sudah tidak
            # ada -> induk mati.
            return ctypes.get_last_error() == ACCESS_DENIED
        try:
            kode = wintypes.DWORD()
            if not k32.GetExitCodeProcess(h, ctypes.byref(kode)):
                return True
            return kode.value == STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    except Exception:
        return True


def _jaga_induk(pid: int, jendela) -> None:
    def loop():
        while True:
            time.sleep(2.0)
            if not _induk_hidup(pid):
                try:
                    jendela.destroy()
                except Exception:
                    pass
                return

    threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("pemakaian: python server_py/jendela.py <url-dasar> [pid-induk]", file=sys.stderr)
        sys.exit(2)
    pid_induk = 0
    if len(sys.argv) > 2:
        try:
            pid_induk = int(sys.argv[2])
        except ValueError:
            pid_induk = 0
    sys.exit(buka(sys.argv[1], induk=pid_induk))
