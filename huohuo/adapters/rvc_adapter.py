"""Adapter: RVCAdapter.

Mengubah timbre audio jadi suara HuoHuo lewat layanan RVC lokal
(`rvc/rvc_service.py` yang jalan di `rvc-env` terpisah, port 8081).

Layanan itu MEMATIKAN DIRI saat menganggur, karena satu-satunya cara yang
terbukti mengembalikan ~1,3 GB memorinya adalah prosesnya berhenti (melepas
model di dalam proses tidak mengembalikan apa pun — diukur 26 Okt). Jadi adapter
ini juga bertugas MENYALAKANNYA KEMBALI saat dibutuhkan, lalu menunggu siap.

Kalau RVC nonaktif, rvc-env tidak ada, atau layanan tidak bisa dinyalakan,
audio asli (Piper) dikembalikan apa adanya supaya TTS tetap jalan — fallback
mulus, bukan error.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import httpx

from huohuo.config import AppConfig, config
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort

# Hanya satu utas boleh mencoba menyalakan layanan pada satu waktu, supaya
# balasan multi-kalimat tidak melahirkan beberapa proses sekaligus.
_gembok_mulai = threading.Lock()


class RVCAdapter(VoiceConversionPort):
    """Klien layanan konversi suara RVC; menyalakan layanan bila perlu."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    # ── keadaan layanan ──────────────────────────────────────────────────────

    def _hidup(self) -> bool:
        try:
            with httpx.Client(timeout=1.5) as client:
                return client.get(self._url("/health")).status_code == 200
        except Exception:
            return False

    def _url(self, akhiran: str) -> str:
        return self.cfg.rvc_service_url.rstrip("/") + akhiran

    def _pastikan_hidup(self) -> bool:
        """True kalau layanan siap menerima /convert."""
        if self._hidup():
            return True
        if not self.cfg.rvc_auto_mulai:
            return False

        python = Path(self.cfg.rvc_python)
        skrip = Path(self.cfg.rvc_skrip)
        if not python.is_file() or not skrip.is_file():
            return False

        with _gembok_mulai:
            # Mungkin utas lain sudah berhasil menyalakan selagi kita menunggu
            # gembok, jadi cek sekali lagi di dalam.
            if self._hidup():
                return True
            try:
                flags = 0
                if sys.platform == "win32":
                    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                    flags = 0x00000008 | 0x00000200
                subprocess.Popen(
                    [str(python), str(skrip)],
                    cwd=str(skrip.parent.parent),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                )
            except Exception:
                return False

            batas = time.monotonic() + max(10, self.cfg.rvc_siap_detik)
            while time.monotonic() < batas:
                if self._hidup():
                    return True
                time.sleep(1.0)
        return False

    # ── konversi ─────────────────────────────────────────────────────────────

    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        """Konversi timbre WAV ke suara HuoHuo; kembalikan audio asli bila gagal."""
        if not wav_bytes or not self.cfg.rvc_aktif:
            return wav_bytes

        if not self._pastikan_hidup():
            return wav_bytes

        url = self._url("/convert")
        for percobaan in (1, 2):
            try:
                with httpx.Client(timeout=self.cfg.rvc_timeout_detik) as client:
                    res = client.post(url, content=wav_bytes,
                                      headers={"Content-Type": "audio/wav"})
                if res.status_code == 200 and len(res.content) > 0:
                    return res.content
                return wav_bytes
            except Exception:
                # Layanan mungkin baru saja berhenti karena idle tepat saat kita
                # memanggil. Coba nyalakan lagi sekali, lalu serahkan ke Piper.
                if percobaan == 1 and self._pastikan_hidup():
                    continue
                return wav_bytes
        return wav_bytes
