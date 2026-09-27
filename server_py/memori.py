"""Kebijakan memori: apa yang masuk prompt, bagaimana mood bergeser, kapan fakta
baru diekstrak.
"""

from __future__ import annotations

import json
import re

NILAI_TAG = {
    "senyum": 0.25,
    "semangat": 0.35,
    "goda": 0.2,
    "netral": 0,
    "bingung": -0.05,
    "kaget": 0,
    "lelah": -0.2,
    "sedih": -0.3,
    "sebal": -0.25,
}

MOOD_AWAL = {"valensi": 0.2, "energi": 0.6, "afinitas": 0.3, "pertukaran": 0}


def _jepit(n: float, min_: float, maks: float) -> float:
    return min(maks, max(min_, n))


def perbarui_mood(lama: dict | None, tag: str | None) -> dict:
    """Mood bergeser dari tag yang dia pakai sendiri -- tanpa panggilan API tambahan."""
    dasar = lama or MOOD_AWAL
    delta = NILAI_TAG.get(tag or "", 0)
    return {
        "valensi": _jepit(dasar["valensi"] * 0.8 + delta * 0.5, -1, 1),
        "energi": _jepit(
            dasar["energi"] * 0.95 + (0.1 if tag == "semangat" else 0) - 0.02, 0, 1
        ),
        "afinitas": _jepit(dasar["afinitas"] + 0.03, 0, 1),
        "pertukaran": dasar.get("pertukaran", 0) + 1,
        "alasan": f"tag terakhir: {tag or 'tidak ada'}",
    }


def suasanaku(mood: dict | None) -> str:
    if not mood:
        return ""
    if mood["valensi"] < -0.25:
        return "Kamu lagi agak berat hari ini, jadi jawabanmu lebih pendek dan lebih jujur."
    if mood["valensi"] > 0.3 and mood["energi"] > 0.5:
        return "Kamu lagi ceria, boleh lebih usil sedikit."
    if mood["energi"] < 0.3:
        return "Kamu lagi capek, bicaranya lebih pelan dan pendek."
    return ""


def gabung_system(persona: str, fakta: list[str], mood: dict | None) -> str:
    """Perakitan system instruction: persona + yang dia ingat + suasananya sekarang."""
    bagian = [persona]
    if fakta:
        bagian.append(
            "## Yang saya ingat tentang Master\n" + "\n".join(f"- {f}" for f in fakta)
        )
    suasana = suasanaku(mood)
    if suasana:
        bagian.append(f"## Suasana hati saya sekarang\n{suasana}")
    return "\n\n".join(bagian)


from konfig import AKAR_PERSONA

# Persona BACA DARI BERKAS, bukan ditulis di dalam fungsi ini. Dulu blok
# "Kamu adalah Elaina (18 tahun)..." tertanam di sini, jadi persona.md sama sekali
# tidak dibaca jalur local/vulkan -- hanya jalur ollama yang memakainya. Akibatnya
# menulis ulang persona.md tidak mengubah apa pun yang dijawab model. Sekarang
# keduanya membaca sumber yang sama.
PERSONA = AKAR_PERSONA.read_text(encoding="utf-8")


def _ringkas_persona(teks: str, batas: int = 4200) -> str:
    """Potong persona panjang pada batas paragraf supaya prompt tetap pendek.

    Bawaan 4200 karakter, bukan 1400: pemotongan di batas paragraf membuat angka
    kecil memotong persona SEBELUM bagian "Cara Bicara" dan "Ekspresi" -- persis
    dua bagian yang paling menentukan gaya bicara dan tag wajah. Yang hilang bukan
    lore, tapi instruksi. 4200 menutup seluruh persona.md (7.001 karakter) sehingga
    pemotongan biasanya tidak terpakai sama sekali; kalau persona nanti tumbuh
    lebih besar, yang dipotong tetap bagian contoh/ backstory, bukan aturan.

    Prompt ±4.200 karakter itu ±1.200 token, dan hanya dibayar sekali: slot Vulkan
    yang menganggur menyimpannya di prompt cache (--cache-idle-slots), jadi giliran
    berikutnya tidak menghitung ulang.

    Nama parameter bukan `nilai`: konfig.py mengekspor fungsi `nilai()`, dan memakai
    nama yang sama di sini pernah membuat keduanya bertabrakan -- `len(nilai)` lalu
    membandingkan int dengan str dan membunuh /api/chat dengan 500.
    """
    if len(teks) <= batas:
        return teks
    potong = teks[:batas]
    batas_paragraf = potong.rfind("\n\n")
    if batas_paragraf > batas // 2:
        potong = potong[:batas_paragraf]
    return potong


def gabung_system_lokal(fakta: list[str], mood: dict | None) -> str:
    """System prompt untuk model lokal: persona (dari berkas) + fakta + suasana.

    Bagian yang TIDAK boleh hilang adalah daftar tag emosi: model lokal 3B akan
    melontarkan nama lain kalau tidak diberi daftar tertutup. Tag itu sengaja
    ditulis di sini dan bukan diambil dari persona.md supaya tidak ikut terpotong
    pemangkasan panjang.
    """
    bagian = [
        _ringkas_persona(PERSONA),
        "WAJIB: Awali setiap balasanmu dengan satu tag emosi di paling depan, persis satu dari "
        "[netral], [senyum], [semangat], [kaget], [bingung], [lelah], [goda], [sebal], [sedih]. "
        "Contoh: [senyum] Halo Master, ada yang bisa saya bantu?",
    ]
    if fakta:
        bagian.append("Fakta tentang Master:\n" + "\n".join(f"- {f}" for f in fakta[-5:]))
    suasana = suasanaku(mood)
    if suasana:
        bagian.append(f"Suasana hatimu saat ini: {suasana}")
    return "\n\n".join(bagian)


def ekstrak_fakta(model: str = "", percakapan: list[dict] | None = None, fakta_lama: list[str] | None = None, kunci: str = "") -> list[str]:
    """Ekstraksi fakta offline (stub saat ini agar tidak memanggil API luar)."""
    return []
