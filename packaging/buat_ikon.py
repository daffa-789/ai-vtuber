"""Bangun assets/ikon/icon.{png,ico} dari render avatar HuoHuo.

Dipakai ulang saat model Live2D berganti atau ingin mengubah bingkai wajah:

    python main.py                 # jalankan companion dulu (server statis :8990)
    python packaging/buat_ikon.py  # render ulang avatar lalu tulis ikon

Butuh: playwright (deps dev, sama seperti tests/e2e) + Pillow.
Hasil render mentah disimpan di tmp-ukur/ (gitignored) supaya bisa diperiksa.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MENTAH = ROOT / "tmp-ukur" / "avatar_render.png"
TUJUAN = ROOT / "assets" / "ikon"
URL = "http://127.0.0.1:8990/index.html"

# Kepala + topi, wajah terpusat; koordinat untuk render 2000x3250.
BOX = (720, 383, 1300, 963)
UKURAN_ICO = (256, 128, 64, 48, 32, 24, 16)
SISI = 512


def render():
    """Ambil tangkapan avatar resolusi tinggi berlatar transparan."""
    from playwright.sync_api import sync_playwright

    MENTAH.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(
            viewport={"width": 1000, "height": 1625}, device_scale_factor=2
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        # Model butuh beberapa detik untuk muncul penuh.
        page.wait_for_timeout(8000)
        page.evaluate(
            """() => {
                document.querySelectorAll('.header-bar, .dialog-overlay, .chat-panel')
                    .forEach(el => { el.style.display = 'none'; });
            }"""
        )
        page.wait_for_timeout(600)
        page.screenshot(path=str(MENTAH), omit_background=True)
        browser.close()
    print(f"render mentah: {MENTAH}")


def latar():
    """Persegi gradasi vertikal dengan sudut membulat."""
    g = Image.new("RGBA", (SISI, SISI))
    d = ImageDraw.Draw(g)
    atas, bawah = (26, 34, 52), (18, 74, 84)
    for y in range(SISI):
        t = y / (SISI - 1)
        warna = tuple(int(a + (b - a) * t) for a, b in zip(atas, bawah)) + (255,)
        d.line([(0, y), (SISI, y)], fill=warna)
    topeng = Image.new("L", (SISI, SISI), 0)
    ImageDraw.Draw(topeng).rounded_rectangle(
        [0, 0, SISI - 1, SISI - 1], radius=int(SISI * 0.22), fill=255
    )
    g.putalpha(topeng)
    return g


def bangun():
    if not MENTAH.is_file():
        sys.exit(f"tidak ada render di {MENTAH} — jalankan tanpa --lewati-render")

    kepala = Image.open(MENTAH).convert("RGBA").crop(BOX)
    sisi = max(kepala.size)
    kotak = Image.new("RGBA", (sisi, sisi), (0, 0, 0, 0))
    kotak.paste(kepala, ((sisi - kepala.width) // 2, 0), kepala)

    pas = int(SISI * 1.06)
    kotak = kotak.resize((pas, pas), Image.LANCZOS)

    kanvas = latar()
    kanvas.paste(kotak, ((SISI - pas) // 2, int(SISI * 0.06)), kotak)
    kanvas.putalpha(latar().split()[-1])

    TUJUAN.mkdir(parents=True, exist_ok=True)
    kanvas.save(TUJUAN / "icon.png")
    kanvas.save(TUJUAN / "icon.ico", format="ICO", sizes=[(n, n) for n in UKURAN_ICO])
    print(f"ditulis {TUJUAN / 'icon.png'} dan {TUJUAN / 'icon.ico'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--lewati-render",
        action="store_true",
        help="pakai render mentah yang sudah ada di tmp-ukur/",
    )
    args = ap.parse_args()
    if not args.lewati_render:
        render()
    bangun()
