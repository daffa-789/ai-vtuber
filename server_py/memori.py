"""Kebijakan memori: apa yang masuk prompt, bagaimana mood bergeser, kapan fakta
baru diekstrak.
"""

from __future__ import annotations

import json
import re
import sys

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
            "## Yang aku ingat tentang Master\n" + "\n".join(f"- {f}" for f in fakta)
        )
    suasana = suasanaku(mood)
    if suasana:
        bagian.append(f"## Suasana hatiku sekarang\n{suasana}")
    return "\n\n".join(bagian)


from konfig import AKAR_PERSONA

# Persona BACA DARI BERKAS, bukan ditulis di dalam fungsi ini. Dulu blok
# "Kamu adalah Elaina (18 tahun)..." tertanam di sini, jadi persona.md sama sekali
# tidak dibaca jalur local/vulkan -- hanya jalur ollama yang memakainya. Akibatnya
# menulis ulang persona.md tidak mengubah apa pun yang dijawab model. Sekarang
# keduanya membaca sumber yang sama.
PERSONA = AKAR_PERSONA.read_text(encoding="utf-8")


def _ringkas_persona(teks: str, batas: int = 9000) -> str:
    """Potong persona panjang pada batas paragraf supaya prompt tetap pendek.

    Angka ini pernah 4200 dengan komentar "menutup seluruh persona.md" -- dan
    komentar itu SALAH, terukur 28 Sep: persona.md 7.206 karakter, hasilnya prompt
    4.164 dan tiga bagian hilang seluruhnya: "Batas", "Contoh Nada", "Aturan Emoji".
    Yang terbuang justru bagian paling menentukan -- contoh dialog adalah senjata
    terbesar persona ini, dan aturan tanpa-emoji itu satu-satunya tempat ia ditulis
    untuk jalur lokal. Gejalanya bukan error, cuma karakter yang pelan-pelan lupa
    caranya bicara.

    Karena itu batasnya sekarang 9000 (persona + ruang tumbuh), dan kalau nanti
    tetap terpotong, bagian yang hilang DICEPRINT -- pemangkasan senyap tidak boleh
    terjadi dua kali pada berkas yang sama.

    Prompt ±7.200 karakter itu ±1.900 token, dan hanya dibayar sekali: slot Vulkan
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
    hilang = [h.strip() for h in re.findall(r"(?m)^## (.+)$", teks) if f"## {h.strip()}" not in potong]
    print(
        f"  ! persona terpotong: {len(potong)} dari {len(teks)} karakter masuk prompt. "
        f"Bagian yang HILANG: {', '.join(hilang) or '(tanpa judul)'}",
        file=sys.stderr,
        flush=True,
    )
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
        "Contoh: [senyum] Beres, Master. Tinggal bilang bagian mana yang macet.",
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
