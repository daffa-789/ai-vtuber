"""RVC inference service — jalan di `rvc-env` (Python 3.10 + fairseq + rvc-python).

Membuat model suara HuoHuo (HuoHuo.pth + .index) SEKALI saat start, lalu melayani
konversi timbre lewat HTTP supaya tiap panggilan cepat (nggak reload model).

Akses:
  GET  /health   -> "ok"
  POST /convert  -> body = bytes WAV sumber,  return = bytes WAV hasil (timbre HuoHuo)

Jalankan:  rvc-env\\Scripts\\python.exe rvc/rvc_service.py
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = Path(os.getenv("VTUBER_RVC_DIR", str(ROOT / "assets" / "rvc" / "HuoHuo")))
MODEL_NAME = os.getenv("VTUBER_RVC_MODEL", "HuoHuo")
VERSION = os.getenv("VTUBER_RVC_VERSI", "v2")
F0_UP = int(os.getenv("VTUBER_RVC_TRANSPOSE", "-3"))
INDEX_RATE = float(os.getenv("VTUBER_RVC_INDEKS_LAJU", "0.6"))
F0_METHOD = os.getenv("VTUBER_RVC_F0", "rmvpe")
FILTER_RADIUS = int(os.getenv("VTUBER_RVC_PENCUCIAN", "3"))
RMS_MIX = float(os.getenv("VTUBER_RVC_CAMPUR_RMS", "0.8"))
PROTECT = float(os.getenv("VTUBER_RVC_PROTEKSI", "0.33"))
PORT = int(os.getenv("VTUBER_RVC_PORT", "8081"))

_rvc = None


def _load():
    global _rvc
    from rvc_python.infer import RVCInference

    model_path = MODEL_DIR / f"{MODEL_NAME}.pth"
    if not model_path.is_file():
        raise FileNotFoundError(f"Model RVC tidak ketemu: {model_path}")

    # NOTE: retrieval index (.index) sengaja TIDAK dipakai — build faiss-cpu di
    # mesin ini crash (segfault) saat faiss.search, dan versi index-nya tidak
    # cocok. Timbre HuoHuo tetap dihasilkan penuh oleh .pth; index hanya
    # penambah kemiripan. index_rate=0.0 + index_path="" melewati faiss.
    print(f"[RVC] Memuat model {model_path.name} (tanpa index, f0={F0_METHOD}) ...", flush=True)
    _rvc = RVCInference(device="cpu", model_path=str(model_path), index_path="", version=VERSION)
    _rvc.set_params(
        f0up_key=F0_UP,
        index_rate=0.0,
        f0method=F0_METHOD,
        filter_radius=FILTER_RADIUS,
        rms_mix_rate=RMS_MIX,
        protect=PROTECT,
        resample_sr=0,
    )
    print("[RVC] Model siap.", flush=True)


def _convert(wav_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fin, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fout:
        in_path, out_path = Path(fin.name), Path(fout.name)
    try:
        in_path.write_bytes(wav_bytes)
        _rvc.infer_file(str(in_path), str(out_path))
        if out_path.is_file() and out_path.stat().st_size > 0:
            return out_path.read_bytes()
        return wav_bytes  # gagal -> kembalikan asli
    finally:
        for p in (in_path, out_path):
            try:
                p.unlink()
            except OSError:
                pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = b"ok" if _rvc is not None else b"loading"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/convert":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        try:
            out = _convert(data)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[RVC] ERROR convert: {exc!r}\n")
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()


def main():
    _load()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[RVC] Layanan konversi suara berjalan di http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
