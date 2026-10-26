"""RVC inference service — jalan di `rvc-env` (Python 3.10 + fairseq + rvc-python).

Melayani konversi timbre suara HuoHuo lewat HTTP (HuoHuo.pth + .index).

Model makan ~1,3-2,5 GB RAM dan mesin ini hanya punya 16 GB tanpa GPU diskrit.
Melepas model dari dalam proses TIDAK mengembalikan memori (sudah diukur: gc +
trim working set hanya memulihkan 0,06 GB), jadi yang dilakukan adalah layanan
INI BERHENTI SENDIRI setelah menganggur `VTUBER_RVC_IDLE_HAPUS` detik -- hanya
proses yang mati benar-benar mengembalikan RAM. `RVCAdapter` di sisi aplikasi
menyalakannya kembali saat dibutuhkan, jadi tidak ada yang perlu dinyalakan
tangan. Selama ngobrol beruntun layanan tetap hidup dan konversi tetap cepat.

Akses:
  GET  /health   -> selalu 200 selama proses hidup; body "siap" kalau model sudah
                    terpasang, "muat" kalau belum (permintaan pertama lebih lambat)
  GET  /status   -> JSON: model_termuat, idle_hapus_detik, muat_boot, idle_terakhir_detik
  POST /convert  -> body = bytes WAV sumber,  return = bytes WAV hasil (timbre HuoHuo)

Jalankan:  rvc-env\\Scripts\\python.exe rvc/rvc_service.py
"""

from __future__ import annotations

import gc
import io
import json
import os
import sys
import tempfile
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# Skrip ini dijalankan sebagai `python rvc/rvc_service.py`, jadi sys.path[0]
# adalah folder rvc/, bukan root repo. Tanpa baris ini `import rvc.*` gagal.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _muat_env() -> None:
    """Isi os.environ dari .env di root repo.

    Layanan ini sengaja tidak memakai python-dotenv (rvc-env tidak punya), tapi
    tanpa ini semua `os.getenv` di bawah jatuh ke default dalam kode — artinya
    mengubah .env tidak berdampak apa pun pada suara, padahal .env adalah satu-satunya
    sumber kebenaran profil suara. Nilai yang sudah ada di environment menang,
    supaya `start_rvc.bat` tetap bisa menimpa.
    """
    jalur = ROOT / ".env"
    if not jalur.is_file():
        return
    for baris in jalur.read_text(encoding="utf-8", errors="replace").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, _, nilai = baris.partition("=")
        nilai = nilai.strip().strip('"').strip("'")
        os.environ.setdefault(kunci.strip(), nilai)


_muat_env()

# Default dibaca dari huohuo/profil_suara.py — modul yang sama dipakai
# huohuo/config.py. `huohuo/__init__.py` sengaja kosong, jadi impor ini aman
# di rvc-env walau huohuo/config.py sendiri tidak bisa dimuat di sana.
from huohuo import profil_suara as suara  # noqa: E402

MODEL_DIR = Path(
    os.getenv("VTUBER_RVC_DIR", str(ROOT / "assets" / "rvc" / suara.MODEL_NAMA))
)
MODEL_NAME = os.getenv("VTUBER_RVC_MODEL", suara.MODEL_NAMA)
VERSION = os.getenv("VTUBER_RVC_VERSI", suara.VERSI)
F0_UP = int(os.getenv("VTUBER_RVC_TRANSPOSE", str(suara.TRANSPOSE)))
INDEX_RATE = float(os.getenv("VTUBER_RVC_INDEKS_LAJU", str(suara.INDEKS_LAJU)))
F0_METHOD = os.getenv("VTUBER_RVC_F0", suara.METODE_F0)
FILTER_RADIUS = int(os.getenv("VTUBER_RVC_PENCUCIAN", str(suara.PENCUCIAN)))
RMS_MIX = float(os.getenv("VTUBER_RVC_CAMPUR_RMS", str(suara.CAMPUR_RMS)))
PROTECT = float(os.getenv("VTUBER_RVC_PROTEKSI", str(suara.PROTEKSI)))
PORT = int(os.getenv("VTUBER_RVC_PORT", str(suara.PORT)))

# ── Koreksi nada keluaran ────────────────────────────────────────────────────
# Keluaran RVC menaikkan energi >6 kHz dari ~0,13% (sumber Piper) jadi ~2%
# — itulah "cempreng"/logam yang terdengar. Shelf di bawah menurunkannya lagi.
EQ_AKTIF = suara.ya(os.getenv("VTUBER_RVC_EQ"), suara.EQ_AKTIF)
EQ_TINGGI_HZ = float(os.getenv("VTUBER_RVC_EQ_TINGGI_HZ", str(suara.EQ_TINGGI_HZ)))
EQ_TINGGI_DB = float(os.getenv("VTUBER_RVC_EQ_TINGGI_DB", str(suara.EQ_TINGGI_DB)))
EQ_RENDAH_HZ = float(os.getenv("VTUBER_RVC_EQ_RENDAH_HZ", str(suara.EQ_RENDAH_HZ)))
EQ_RENDAH_DB = float(os.getenv("VTUBER_RVC_EQ_RENDAH_DB", str(suara.EQ_RENDAH_DB)))

# ── Pengaturan muat/bongkar model (hemat RAM) ────────────────────────────────
# Muat saat boot? Kalau tidak, model baru dimuat pada permintaan pertama.
MUAT_BOOT = suara.ya(os.getenv("VTUBER_RVC_MUAT_BOOT"), suara.MUAT_BOOT)
# Bongkar model setelah menganggur sekian detik. 0 = jangan pernah bongkar
# (perilaku lama: model menempel terus dan memakan 2,4 GB).
IDLE_HAPUS_DETIK = float(os.getenv("VTUBER_RVC_IDLE_HAPUS", str(suara.IDLE_HAPUS_DETIK)))

_rvc = None
# ThreadingHTTPServer melayani tiap koneksi di utas sendiri, sedangkan modelnya
# satu dan tidak tahan dipakai serentak. Lock ini juga mencegah watchdog
# membongkar model di tengah konversi.
_gembok = threading.RLock()
# Dimulai dari "sekarang", bukan 0. Kalau mulai dari 0, kombinasi
# MUAT_BOOT=ya + IDLE_HAPUS>0 akan langsung membongkar model yang baru dimuat
# karena selisih waktunya terlihat sangat besar.
_aktivitas_akhir = time.time()


def _muat_model():
    """Muat RVCInference. Panggil hanya dengan `_gembok` tergenggam."""
    global _rvc
    if _rvc is not None:
        return

    from rvc_python.infer import RVCInference

    model_path = MODEL_DIR / f"{MODEL_NAME}.pth"
    if not model_path.is_file():
        raise FileNotFoundError(f"Model RVC tidak ketemu: {model_path}")

    # Index retrieval dulu dilewati karena faiss-cpu 1.8.0 segfault saat
    # index.search() pada berkas .index milik proyek ini. rvc/indeks_brute.py
    # mengambil vektor penyimpanannya (IVF*,Flat menyimpan vektor mentah) lalu
    # mencari tetangga terdekat dengan numpy, jadi index bisa dipakai lagi.
    indeks = next(iter(sorted(MODEL_DIR.glob(f"*{MODEL_NAME}_{VERSION}.index"))), None)
    if indeks is None:
        print("[RVC] Index tidak ketemu; timbre hanya dari .pth.", flush=True)

    from rvc.indeks_brute import pasang

    pasang()
    print(
        f"[RVC] Memuat model {model_path.name} "
        f"(index={'ada' if indeks else 'tidak'}, f0={F0_METHOD}) ...",
        flush=True,
    )
    awal = time.time()
    _rvc = RVCInference(
        device=suara.SUBFER,
        model_path=str(model_path),
        index_path=str(indeks) if indeks else "",
        version=VERSION,
    )
    _rvc.set_params(
        f0up_key=F0_UP,
        index_rate=INDEX_RATE if indeks else 0.0,
        f0method=F0_METHOD,
        filter_radius=FILTER_RADIUS,
        rms_mix_rate=RMS_MIX,
        protect=PROTECT,
        resample_sr=0,
    )
    print(f"[RVC] Model siap dalam {time.time() - awal:.1f} dtk.", flush=True)


def _bongkar_model():
    """Lepas model dari RAM.

    PENTING — ini TIDAK cukup untuk mengembalikan memori, dan itu sudah diukur
    (26 Okt, tmp-ukur/uji_trim2.py): setelah dua kali konversi jejak layanan
    1,33 GB; `del` + `gc.collect()` memulihkan -0,02 GB (nol), dan
    `SetProcessWorkingSetSizeEx` hanya menambah 0,35 GB. Halaman torch/CRT tetap
    dikandung proses. Satu-satunya cara yang terbukti mengembalikan SELURUHNYA
    adalah prosesnya benar-benar berhenti (RAM bebas naik dari 3,82 ke 6,18 GB).

    Karena itu watchdog memanggil `_berhenti()` yang keluar dari proses, bukan
    fungsi ini. Fungsi ini dipertahankan hanya untuk jalur darurat (mis. model
    rusak dan kita ingin mencoba memuat ulang di dalam proses yang sama).
    """
    global _rvc
    if _rvc is None:
        return
    _rvc = None
    gc.collect()
    print("[RVC] Model dilepas dari memori (proses tetap hidup).", flush=True)


def _berhenti(pesan: str) -> None:
    """Keluar dari proses supaya OS mengambil kembali seluruh memorinya."""
    print(f"[RVC] {pesan} — layanan berhenti.", flush=True)
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(0)


def _penjaga_idle():
    """Utas watchdog: berhenti total kalau lama tidak ada permintaan.

    Berhenti = proses exit, bukan sekadar melepas model. RVCAdapter akan
    menyalakan ulang layanan ini saat butuh, jadi dari sisi aplikasi tidak
    ada yang berubah kecuali kalimat pertama setelah idle lebih lambat.
    """
    while True:
        time.sleep(min(15.0, max(1.0, IDLE_HAPUS_DETIK / 4)))
        if IDLE_HAPUS_DETIK <= 0:
            continue
        if time.time() - _aktivitas_akhir < IDLE_HAPUS_DETIK:
            continue
        with _gembok:
            if time.time() - _aktivitas_akhir >= IDLE_HAPUS_DETIK:
                _berhenti(f"menganggur {IDLE_HAPUS_DETIK:.0f} dtk")


def _baca_wav(b: bytes):
    with wave.open(io.BytesIO(b), "rb") as w:
        sr, n_ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    tipe = {1: np.uint8, 2: np.int16, 4: np.int32}.get(sw)
    if tipe is None:
        return None
    y = np.frombuffer(raw, dtype=tipe).astype(np.float64)
    if tipe is np.uint8:  # unsigned: geser ke tengah
        y -= 128.0
    if n_ch > 1:
        y = y.reshape(-1, n_ch).mean(axis=1)
    return y, sr, tipe


def _tulis_wav(y: np.ndarray, sr: int, tipe) -> bytes:
    if tipe is np.uint8:
        data = np.clip(y + 128.0, 0, 255).astype(np.uint8)
    else:
        batas = float(np.iinfo(tipe).max)
        data = np.clip(y, -batas, batas - 1).astype(tipe)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(np.dtype(tipe).itemsize)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return out.getvalue()


def _perbaiki_nada(b: bytes) -> bytes:
    """Turunkan kembali energi frekuensi tinggi yang ditambahkan RVC.

    Shelf tinggi memotong zona 'cempreng' (di atas EQ_TINGGI_HZ), shelf rendah
    mengembalikan badan suara yang hilang. Level akhir disamakan dengan sebelum
    EQ supaya volume tidak berubah setelah pemotongan.
    """
    dari_sci = _baca_wav(b)
    if dari_sci is None:
        return b
    y, sr, tipe = dari_sci
    if sr <= 0 or y.size == 0:
        return b

    from scipy.signal import butter, sosfilt

    rms_sebelum = float(np.sqrt(np.mean(y ** 2))) + 1e-9
    nyq = sr / 2.0

    def shelf(fc: float, db: float, tinggi: bool):
        if not (0 < fc < nyq) or abs(db) < 0.01:
            return y
        sos = butter(2, fc / nyq, btype="low", output="sos")
        rendah = sosfilt(sos, y)
        lin = 10.0 ** (db / 20.0)
        return rendah + lin * (y - rendah) if tinggi else lin * rendah + (y - rendah)

    y = shelf(EQ_TINGGI_HZ, EQ_TINGGI_DB, tinggi=True)
    y = shelf(EQ_RENDAH_HZ, EQ_RENDAH_DB, tinggi=False)

    # Ganti rugi level supaya pemotongan shelf tidak membuat suara mengecil.
    y *= rms_sebelum / (float(np.sqrt(np.mean(y ** 2))) + 1e-9)

    puncak = float(np.max(np.abs(y)))
    batas = float(np.iinfo(tipe).max) if tipe is not np.uint8 else 127.0
    if puncak > batas:
        y *= batas / puncak
    return _tulis_wav(y, sr, tipe)


def _convert(wav_bytes: bytes) -> bytes:
    global _aktivitas_akhir
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fin, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fout:
        in_path, out_path = Path(fin.name), Path(fout.name)
    # Jam aktivitas dipasang di awal DAN di akhir: konversi panjang tidak boleh
    # dianggap "menganggur" lalu modelnya dibongkar di tengah jalan.
    with _gembok:
        _aktivitas_akhir = time.time()
        _muat_model()
        try:
            in_path.write_bytes(wav_bytes)
            _rvc.infer_file(str(in_path), str(out_path))
            if out_path.is_file() and out_path.stat().st_size > 0:
                hasil = out_path.read_bytes()
                return _perbaiki_nada(hasil) if EQ_AKTIF else hasil
            return wav_bytes  # gagal -> kembalikan asli
        finally:
            _aktivitas_akhir = time.time()
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
            # Selalu 200 selama proses hidup. "muat" berarti siap menerima tapi
            # model belum terpasang, jadi /convert pertama akan lebih lambat.
            body = b"siap" if _rvc is not None else b"muat"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/status":
            body = json.dumps(
                {
                    "model_termuat": _rvc is not None,
                    "idle_hapus_detik": IDLE_HAPUS_DETIK,
                    "muat_boot": MUAT_BOOT,
                    "idle_terakhir_detik": round(time.time() - _aktivitas_akhir, 1),
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
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
    if MUAT_BOOT:
        with _gembok:
            _muat_model()
    else:
        print("[RVC] Model akan dimuat pada permintaan pertama.", flush=True)
    if IDLE_HAPUS_DETIK > 0:
        print(f"[RVC] Model dibongkar kalau menganggur > {IDLE_HAPUS_DETIK:.0f} dtk.", flush=True)
    threading.Thread(target=_penjaga_idle, daemon=True).start()

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[RVC] Layanan konversi suara berjalan di http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
