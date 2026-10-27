"""Port SentenceSplitter dari C# HuoHuo.Core.Text.SentenceSplitter.

Memecah balasan LLM menjadi kalimat-kalimat utuh secara streaming untuk
disintesis oleh pipeline suara (Supertonic/Piper + RVC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from huohuo.core.emotion_parser import clean_emotion_tags

PENUTUP = ".!?…。！？"
EKOR = "\"'”’)]}»"


@dataclass
class HasilPotong:
    kalimat: List[str]
    sisa: str


def buang_tag(teks: Optional[str]) -> str:
    """Bersihkan tag emosi lalu padatkan spasi ganda."""
    bersih = clean_emotion_tags(teks)
    # Padatkan 2+ spasi/tab menjadi satu spasi
    import re
    return re.sub(r"[ \t]{2,}", " ", bersih)


def _bukan_akhir_kalimat(teks: str, i: int) -> bool:
    """Mendeteksi apakah tanda baca adalah desimal atau penomoran (bukan akhir kalimat)."""
    if i - 1 < 0 or not ('0' <= teks[i - 1] <= '9'):
        return False

    if i + 1 < len(teks) and ('0' <= teks[i + 1] <= '9'):
        return True

    if i - 2 < 0:
        return True

    dua_sebelum = teks[i - 2]
    return dua_sebelum in (' ', '\n', '(')


def potong_kalimat(teks: Optional[str], minimal: int = 12) -> HasilPotong:
    """Pecah teks menjadi daftar kalimat yang siap diucapkan dan sisa yang belum lengkap."""
    if not teks:
        return HasilPotong(kalimat=[], sisa="")

    teks_bersih = buang_tag(teks)
    kalimat: List[str] = []
    awal = 0
    panjang = len(teks_bersih)

    for i in range(panjang):
        c = teks_bersih[i]
        if c not in PENUTUP:
            continue

        if _bukan_akhir_kalimat(teks_bersih, i):
            continue

        j = i + 1
        while j < panjang and teks_bersih[j] in EKOR:
            j += 1

        if j < panjang and not teks_bersih[j].isspace():
            continue

        potongan = teks_bersih[awal:j].strip()
        if len(potongan) >= minimal or any(ch.isspace() for ch in potongan):
            kalimat.append(potongan)
            awal = j

    sisa = teks_bersih[awal:].lstrip()
    return HasilPotong(kalimat=kalimat, sisa=sisa)
