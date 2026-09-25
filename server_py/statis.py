"""Sajian berkas statis: web/ (halaman + modul) lalu public/ (model, core, aset).

Menggantikan Vite dev server. Yang dulu dikerjakan Vite dan harus ditiru di sini:
  * `?import` pada berkas .mjs (onnxruntime-web memakainya) -- cukup dibuang,
    karena berkasnya sendiri sudah benar adanya di disk;
  * MIME `.wasm` dan `.moc3` -- salah tipe bikin Cubism menolak memuat model;
  * kunci VITE_* dari .env disuntik ke index.html, karena `import.meta.env`
    milik Vite dan bundler sudah tidak ada.
"""

from __future__ import annotations

import json
from pathlib import Path

from konfig import AKAR, env_web

AKAR_WEB = AKAR / "web"
AKAR_PUBLIK = AKAR / "public"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".model3.json": "application/json",
    ".exp3.json": "application/json",
    ".motion3.json": "application/json",
    ".physics3.json": "application/json",
    ".cdi3.json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".wasm": "application/wasm",
    ".moc3": "application/octet-stream",
    ".onnx": "application/octet-stream",
    ".wav": "audio/wav",
}


def tipe(berkas: Path) -> str:
    # model3.json / exp3.json punya dua ekstensi -- ambil yang paling panjang dulu.
    for akhir in sorted(MIME, key=len, reverse=True):
        if berkas.name.endswith(akhir):
            return MIME[akhir]
    return MIME.get(berkas.suffix, "application/octet-stream")


def cari(url_path: str) -> Path | None:
    """Selesaikan URL ke berkas di dalam web/ atau public/, tolak yang keluar."""
    bersih = url_path.lstrip("/") or "index.html"
    for akar in (AKAR_WEB, AKAR_PUBLIK):
        calon = (akar / bersih).resolve()
        if not str(calon).startswith(str(akar.resolve())):
            continue  # percobaan path traversal
        if calon.is_file():
            return calon
    return None


def isi(berkas: Path) -> bytes:
    """Isi berkas; index.html dibubuhi konfigurasi .env lebih dulu."""
    mentah = berkas.read_bytes()
    if berkas.name != "index.html":
        return mentah
    suntikan = (
        "<script>window.__VTUBER_ENV__ = "
        + json.dumps(env_web(), ensure_ascii=False)
        + ";</script>"
    )
    return mentah.replace(b"<!--VTUBER_ENV-->", suntikan.encode("utf-8"))


def tanda(berkas: Path) -> str:
    """ETap dari ukuran + mtime: cukup untuk tahu berkas berganti tanpa membacanya.

    index.html dapat pengecualian: isinya berubah lewat .env, bukan lewat berkasnya
    sendiri, jadi tanda .env ikut dicampur -- kalau tidak, mengedit .env akan
    membalas 304 dan halaman tetap memakai nilai lama.
    """
    st = berkas.stat()
    dasar = f"{st.st_size:x}-{int(st.st_mtime):x}"
    if berkas.name == "index.html":
        dasar += f"-{hash(json.dumps(env_web(), sort_keys=True, ensure_ascii=False)) & 0xffffff:x}"
    return f'"{dasar}"'


def kebijakan(berkas: Path) -> str:
    """Header Cache-Control per jenis berkas.

    `no-store` di semua berkas membuat 43 MB model dibaca ulang setiap muat ulang
    (terukur: transfer sama besar pada muat dingin dan hangat). Model dan pustaka
    tidak berubah sendiri, jadi boleh awet; kode sumber dan halaman harus selalu
    ditanya ulang, kalau tidak Master mengedit .js lalu melihat versi lama.
    """
    teks = str(berkas).replace("\\", "/")
    if "/models/" in teks or "/lib/" in teks:
        return "public, max-age=31536000, immutable"
    return "no-cache"
