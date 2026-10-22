# -*- mode: python ; coding: utf-8 -*-
"""Konfigurasi PyInstaller untuk HuoHuo Desktop Companion (Windows, onedir).

Bangun via `python build_exe.py`. Hasil: dist/huohuo/huohuo.exe (onedir, aset
Live2D & UI dibundel di folder yang sama). Modul berat opsional (torch/whisper/
RVC/fairseq) DIKECUALIKAN agar exe ringan; fitur STT/RVC butuh dependensi itu
terpasang terpisah di lingkungan pengguna.
"""
import os

root = os.path.abspath(os.path.join(SPECPATH, os.pardir))  # dir proyek (induk packaging/)
static_dir = os.path.join(root, "huohuo", "ui", "static")
assets_live2d = os.path.join(root, "assets", "live2d", "huohuo")
icon_path = os.path.join(root, "assets", "ikon", "icon.ico")

datas = []
if os.path.isdir(static_dir):
    datas.append((static_dir, "static"))
if os.path.isdir(assets_live2d):
    datas.append((assets_live2d, os.path.join("assets", "live2d", "huohuo")))

a = Analysis(
    [os.path.join(root, "main.py")],
    pathex=[root],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "webview",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
        "clr",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "torch", "torchaudio", "torchcrepe", "faster_whisper", "fairseq",
        "rvc_python", "pyworld", "numba", "matplotlib", "pytest", "playwright",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="huohuo",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon_path if os.path.isfile(icon_path) else None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="huohuo")
