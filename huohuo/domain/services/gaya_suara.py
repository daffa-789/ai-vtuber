"""Domain Service: PetaGayaSuara.

Menerjemahkan emosi resmi HuoHuo menjadi deskripsi gaya bicara. Adapter
Supertonic mengubahnya menjadi ekspresi dan tempo; adapter Piper mengubahnya
menjadi preset prosodi terbatas dan RVC memberi koreksi pitch ringan.

Kenapa ini penting: keluhan utama suara HuoHuo bukan timbre-nya (itu sudah
dibetulkan RVC) tapi **intonasinya yang datar**. TTS mengatur tempo dan variasi
artikulasi sesuai keterbatasan model. Dengan
memetakan emosi yang SUDAH dihitung LLM, tiap emosi mendapat prosodi yang sesuai.

Peta ini murni logika teks; tidak memerlukan jaringan atau library audio.
Deskripsi berbahasa Inggris dipakai oleh backend yang menerima instruksi gaya.
"""

from __future__ import annotations

from typing import Optional

from huohuo.domain.value_objects.emotion import EmotionTag

# Satu gaya per emosi resmi. Kalau emosi tidak dikenal, NETRAL.
_GAYA = {
    EmotionTag.SENYUM: "warm and gently smiling",
    EmotionTag.GODA: "playful and teasing",
    EmotionTag.SEBAL: "mildly annoyed and pouting",
    EmotionTag.KAGET: "surprised and startled",
    EmotionTag.BINGUNG: "confused and uncertain",
    EmotionTag.LELAH: "tired and sleepy, speaking slowly",
    EmotionTag.SEMANGAT: "excited and energetic",
    EmotionTag.SEDIH: "sad and melancholic",
    EmotionTag.MALU: "embarrassed and hesitant",
    EmotionTag.GUGUP: "nervous and timid, slightly shaky",
    EmotionTag.TAKUT: "frightened and anxious, speaking softly",
    EmotionTag.NETRAL: "calm and natural",
}

# Sifat dasar HuoHuo: gampang gugup dan agak malu. Ditambahkan ke semua gaya
# supaya karakternya konsisten, bukan cuma berubah-ubah ikut emosi.
_WARNA_DASAR = "shy"


class PetaGayaSuara:
    """Pemetaan emosi -> deskripsi gaya bicara."""

    @staticmethod
    def gaya_dari_emosi(emosi: Optional[str], dasar: bool = True) -> str:
        """Kembalikan deskripsi gaya untuk satu tag emosi.

        `dasar=False` membuang sifat pemalu khas HuoHuo, untuk kasus gaya polos
        sudah cukup atau saat warna dasar justru menutupi emosinya.
        """
        tag = EmotionTag.from_str(emosi)
        gaya = _GAYA.get(tag, _GAYA[EmotionTag.NETRAL])
        if dasar and tag is not EmotionTag.NETRAL:
            return f"{_WARNA_DASAR}, {gaya}"
        return gaya

    @staticmethod
    def daftar_gaya() -> dict[str, str]:
        """Peta lengkap untuk dokumentasi dan test."""
        return {tag.value: gaya for tag, gaya in _GAYA.items()}
