"""Adapter: TTSBertingkat.

Menjalankan beberapa backend TTS berurutan dan memakai yang pertama berhasil.

Kenapa perlu: Gemini memberi intonasi yang jauh lebih hidup, tapi ia layanan
internet. Tanpa lapisan ini, koneksi putus berarti HuoHuo diam total -- padahal
sudah ada Piper yang offline dan selalu jalan. Urutan dibaca dari
`VTUBER_TTS_RANTAI` (bawaan "gemini,piper").

Ini juga tempat yang tepat untuk menambah backend baru nanti: cukup daftarkan
pabriknya di _CALON, tidak perlu menyentuh use case atau container.
"""

from __future__ import annotations

from typing import Callable, Optional

from huohuo.config import AppConfig, config
from huohuo.domain.ports.tts_port import TTSPort


class TTSBertingkat(TTSPort):
    """Coba tiap backend bergiliran; kembalikan hasil pertama yang bukan None."""

    def __init__(self, tingkatan: list[TTSPort], nama: Optional[list[str]] = None):
        self.tingkatan = [t for t in tingkatan if t is not None]
        self.nama = nama or [type(t).__name__ for t in self.tingkatan]

    @property
    def tersedia(self) -> bool:
        return bool(self.tingkatan)

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        for indeks, tts in enumerate(self.tingkatan):
            try:
                hasil = tts.synthesize(text, gaya=gaya)
            except TypeError:
                # Backend pihak ketiga yang signature-nya belum mengenal `gaya`.
                hasil = tts.synthesize(text)
            except Exception as galat:  # noqa: BLE001
                print(f"[TTS] {self.nama[indeks]} error ({type(galat).__name__})")
                hasil = None
            if hasil:
                return hasil
            if len(self.tingkatan) > 1:
                print(f"[TTS] {self.nama[indeks]} gagal, coba berikutnya")
        return None


# Backend yang dikenal. Menambah yang baru cukup satu entri di sini.
_CALON: dict[str, Callable[[AppConfig], Optional[TTSPort]]] = {}


def _daftarkan_calon() -> None:
    """Import malas supaya adapter yang tidak dipakai tidak ikut dimuat."""
    if _CALON:
        return
    from huohuo.adapters.gemini_tts_adapter import GeminiTTSAdapter
    from huohuo.adapters.piper_tts_adapter import PiperTTSAdapter

    def _gemini(cfg: AppConfig) -> Optional[TTSPort]:
        ad = GeminiTTSAdapter(cfg=cfg)
        return ad if ad.tersedia else None

    _CALON["gemini"] = _gemini
    _CALON["piper"] = lambda cfg: PiperTTSAdapter(cfg=cfg)


def buat_tts(cfg: Optional[AppConfig] = None) -> TTSPort:
    """Rakit rantai TTS sesuai konfigurasi, tanpa backend yang tidak siap."""
    cfg = cfg or config
    _daftarkan_calon()

    # VTUBER_TTS_BACKEND tunggal tetap dihormati ("piper" saja, "gemini" saja).
    rantai = cfg.tts_rantai or cfg.tts_backend
    tingkatan: list[TTSPort] = []
    dipakai: list[str] = []
    for nama in [h.strip().lower() for h in rantai.split(",") if h.strip()]:
        pabrik = _CALON.get(nama)
        if pabrik is None:
            print(f"[TTS] backend tidak dikenal: {nama}")
            continue
        ad = pabrik(cfg)
        if ad is None:
            print(f"[TTS] {nama} tidak siap (key/model belum ada), dilewati")
            continue
        tingkatan.append(ad)
        dipakai.append(nama)

    if not tingkatan:
        # Jangan pernah mengembalikan rantai kosong: Piper selalu jadi jaring
        # pengaman terakhir, bahkan tanpa key.
        from huohuo.adapters.piper_tts_adapter import PiperTTSAdapter

        tingkatan = [PiperTTSAdapter(cfg=cfg)]
        dipakai = ["piper"]

    return TTSBertingkat(tingkatan, nama=dipakai)
