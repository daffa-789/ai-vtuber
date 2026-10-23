"""Adapter: RVCAdapter.

Mengubah timbre audio jadi suara HuoHuo lewat layanan RVC lokal
(`rvc/rvc_service.py` yang jalan di `rvc-env` terpisah, port 8081).

Kalau RVC nonaktif atau layanan tidak tersedia, audio asli (Piper) dikembalikan
apa adanya supaya TTS tetap jalan — fallback mulus.
"""

from __future__ import annotations

from typing import Optional

import httpx

from huohuo.config import AppConfig, config
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort


class RVCAdapter(VoiceConversionPort):
    """Concrete adapter that calls the local RVC HTTP service."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        """Convert timbre of WAV audio into HuoHuo voice via the RVC service."""
        if not wav_bytes or not self.cfg.rvc_aktif:
            return wav_bytes

        url = self.cfg.rvc_service_url.rstrip("/") + "/convert"
        try:
            with httpx.Client(timeout=self.cfg.rvc_timeout_detik) as client:
                res = client.post(
                    url,
                    content=wav_bytes,
                    headers={"Content-Type": "audio/wav"},
                )
                if res.status_code == 200 and len(res.content) > 0:
                    return res.content
        except Exception:
            # Layanan mati / timeout -> pakai suara Piper asli, jangan macet.
            return wav_bytes
        return wav_bytes
