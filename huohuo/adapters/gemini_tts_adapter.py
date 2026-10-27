"""Adapter: GeminiTTSAdapter.

Sintesis suara opsional lewat Gemini native TTS. Backend ini masih dapat dipilih
manual; konfigurasi bawaan proyek memakai Piper lokal agar tetap offline.

Aturan penting:
  * Key dibaca dari environment, TIDAK PERNAH masuk log maupun pesan error.
  * Kegagalan apa pun mengembalikan None, bukan exception, supaya rantai TTS
    boleh jatuh ke Piper dan suara tetap keluar.
  * Respons diambil dengan menelusuri struktur JSON, bukan satu jalur tetap:
    dokumentasi resmi menyebut `interaction.output_audio.data` tapi yang
    actually datang `steps[0].content[0].data` (diverifikasi 26 Okt).
"""

from __future__ import annotations

import base64
from typing import Any, Optional

import httpx

from huohuo.config import AppConfig, config
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.services.text_speech_service import TextSpeechService

_ENDPOIN = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _cari_audio(o: Any) -> Optional[str]:
    """Cari string base64 audio di dalam respons, di kedalaman berapa pun."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and len(v) > 2048 and k in ("data", "audio", "bytes"):
                return v
            ketemu = _cari_audio(v)
            if ketemu:
                return ketemu
    elif isinstance(o, list):
        for v in o:
            ketemu = _cari_audio(v)
            if ketemu:
                return ketemu
    return None


def _rapikan_wav(raw: bytes) -> Optional[bytes]:
    """Gemini mengirim WAV, tapi kalau yang datang PCM mentah kita beri header."""
    if not raw:
        return None
    if raw[:4] == b"RIFF":
        return raw
    import io
    import wave

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(raw)
    return out.getvalue()


class GeminiTTSAdapter(TTSPort):
    """Sintesis TTS lewat API Gemini; gagal diam-diam supaya bisa fallback."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    @property
    def tersedia(self) -> bool:
        """True kalau key dan model terkonfigurasi. Tidak menyentuh jaringan."""
        return bool(self.cfg.gemini_api_key) and bool(self.cfg.gemini_tts_model)

    def _tubuh_permintaan(self, teks: str, gaya: Optional[str]) -> dict:
        bagian_teks: dict = {"type": "text", "text": teks}
        if gaya:
            bagian_teks["annotations"] = [
                {"type": "speech_metadata", "style": gaya}
            ]
        tubuh = {
            "model": self.cfg.gemini_tts_model,
            "input": [{"type": "user_input", "content": [bagian_teks]}],
            "response_format": {"type": "audio"},
        }
        if self.cfg.gemini_tts_voice:
            tubuh["generation_config"] = {
                "speech_config": [{"voice": self.cfg.gemini_tts_voice}]
            }
        return tubuh

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        """WAV bytes dari teks, atau None kalau kunci/api/jaringan bermasalah."""
        if not self.tersedia:
            return None

        cleaned = TextSpeechService.bersihkan_untuk_tts(text)
        if not cleaned:
            return None

        try:
            with httpx.Client(timeout=self.cfg.gemini_timeout_detik) as client:
                res = client.post(
                    _ENDPOIN,
                    json=self._tubuh_permintaan(cleaned, gaya or self.cfg.gemini_tts_gaya),
                    headers={"x-goog-api-key": self.cfg.gemini_api_key},
                )
                if res.status_code != 200:
                    # Jangan pernah tampilkan isi error mentah-mentah: respons
                    # Google kadang menyertakan ulang permintaan, termasuk header.
                    print(f"[GeminiTTS] HTTP {res.status_code}; pakai fallback")
                    return None
                data = res.json()
        except Exception as galat:  # noqa: BLE001
            print(f"[GeminiTTS] gagal ({type(galat).__name__}); pakai fallback")
            return None

        b64 = _cari_audio(data)
        if not b64:
            print("[GeminiTTS] tidak ada audio di respons; pakai fallback")
            return None
        try:
            return _rapikan_wav(base64.b64decode(b64))
        except Exception:  # noqa: BLE001
            return None
