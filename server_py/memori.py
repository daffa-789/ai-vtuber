"""Kebijakan memori: apa yang masuk prompt, bagaimana mood bergeser, kapan fakta
baru diekstrak. Terjemahan langsung dari server/memori.mjs -- angkanya sengaja
tidak diubah supaya kedua sisi menghasilkan state yang sama.
"""

from __future__ import annotations

import json
import re

import gemini

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


def ekstrak_fakta(model: str, percakapan: list[dict], fakta_lama: list[str], kunci: str) -> list[str]:
    """Satu panggilan API tambahan, jadi pemanggilnya menyetel kapan ini layak."""
    instruksi = "\n".join(
        [
            "Dari percakapan di bawah, tuliskan FAKTA BARU yang layak diingat lama tentang Master:",
            "pekerjaan, kebiasaan, orang, tanggal, preferensi, proyek, kondisi hari ini.",
            "Abaikan basa-basi dan hal yang sudah ada di daftar fakta lama.",
            "Balas HANYA array JSON berisi string pendek berbahasa Indonesia. [] kalau tidak ada.",
            "",
            f"Fakta lama: {json.dumps(fakta_lama, ensure_ascii=False)}",
            "",
            "Percakapan:",
            "\n".join(
                f"{'Master' if m['role'] == 'user' else 'Elaina'}: {m['content']}" for m in percakapan
            ),
        ]
    )

    hasil = gemini.generate(
        model,
        {
            "contents": [{"role": "user", "parts": [{"text": instruksi}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 500},
        },
        kunci,
    )
    teks = gemini.teks_dari(hasil)
    potongan = re.search(r"\[.*\]", teks, re.S)
    if not potongan:
        return []
    try:
        data = json.loads(potongan.group(0))
    except ValueError:
        return []
    return [s.strip() for s in data if isinstance(s, str) and s.strip()]
