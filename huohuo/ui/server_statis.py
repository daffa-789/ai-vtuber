"""Server statis UI + penyaji aset model Live2D.

Dipisah dari `huohuo/ui/app.py` karena berkas ini tidak butuh pywebview sama
sekali. Sebelumnya test e2e harus mengimpor `huohuo.ui.app` hanya untuk
mendapat handler HTTP, dan impor itu ikut menarik `webview` — sekarang tidak.
"""

from __future__ import annotations

import mimetypes
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from huohuo.config import config

if getattr(sys, "frozen", False):
    # Bekuan PyInstaller: aset ditaruh di folder _MEIPASS.
    STATIC_DIR = Path(
        getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
    ) / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"


class StaticAndAssetHandler(SimpleHTTPRequestHandler):
    """Layani berkas UI statis sekaligus aset Live2D model dari luar folder static."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        # Berkas model Live2D dan tekstur diarahkan ke folder aset
        if (
            self.path.startswith("/api/")
            or self.path.startswith("/models/")
            or "huohuo" in self.path
        ):
            clean_name = (
                self.path.split("?")[0]
                .replace("/api/", "")
                .replace("/models/", "")
                .lstrip("/")
            )
            if clean_name.endswith(".model3.json") or clean_name == "model3.json":
                target = config.live2d_model_path
            else:
                target = config.live2d_model_path.parent / clean_name

            if target.is_file():
                self.send_response(200)
                mime, _ = mimetypes.guess_type(str(target))
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(target.stat().st_size))
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return

        return super().do_GET()

    def log_message(self, format, *args):
        # Senyapkan log akses HTTP agar konsol tetap bersih
        pass
