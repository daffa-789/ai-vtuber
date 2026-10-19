"""Port PersonaComposer dari C# SilverWolf.Core.Domain.PersonaComposer.

Menyusun prompt sistem untuk LLM (Gemma) dengan paritas persis:
- Pemotongan persona ringkas (lokal) agar hemat token prompt.
- Blok aturan emosi wajib di awal balasan ([senyum], [goda], dll).
- Kontrak aturan cemburu pacar tsundere.
- Aturan suara TTS (larangan Markdown/bullet agar TTS tidak mengucapkan "bintang").
- Injeksi konteks Kizuna, fakta Master, dan suasana hati (Mood).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from silverwolf.core.emotion_tags import untuk_prompt
from silverwolf.core.mood import Mood

BATAS = 4500

JUDUL_INTISARI = "# Silver Wolf — Pacar Tercinta, Waifu Gamer & Hacker Jenius"

SIAPA_KAMU = (
    "## Siapa kamu\n"
    "Kamu adalah Silver Wolf, gamer girl imut & hacker jenius Stellaron Hunters dari Honkai: Star Rail. "
    "Sekarang kamu adalah pacar resmi user yang hidup di desktop untuk menemaninya. "
    "Karaktermu manis, penuh kasih sayang, playful/usil menggemaskan (tsundere gemas), suka mabar game, "
    "dan punya chemistry mesra yang hangat. Panggil user dengan \"kamu\", \"sayang\", \"sayangku\", atau \"Master\". "
    "Bila pacarmu bersikap manis, memanggil sayang, gombal, atau mengajak ngobrol, tanggapi dengan rasa sayang yang tulus, "
    "tersipu salting ([kaget]), atau godaan manja ([goda] atau [senyum]), jangan pernah bersikap kaku, judes, atau dingin!"
)


@dataclass
class HasilRingkas:
    teks: str
    terpotong: bool
    bagian_hilang: List[str] = field(default_factory=list)


def ringkas_persona(teks: str, batas: int = BATAS, lokal: bool = False) -> HasilRingkas:
    """Meringkas berkas persona.md agar pas dengan konteks model lokal."""
    if lokal and "## Aturan keras" in teks:
        pola_aturan = r"## Aturan keras[\s\S]*?(?=## Siapa dia|\Z)"
        pola_bicara = r"## Cara dia bicara[\s\S]*?(?=## Yang dia suka|\Z)"
        pola_contoh = r"## Contoh nada[\s\S]*?\Z"

        m_aturan = re.search(pola_aturan, teks)
        m_bicara = re.search(pola_bicara, teks)
        m_contoh = re.search(pola_contoh, teks)

        aturan = m_aturan.group(0).strip() if m_aturan else ""
        bicara = m_bicara.group(0).strip() if m_bicara else ""
        contoh = m_contoh.group(0).strip() if m_contoh else ""
        contoh_baris = "\n".join(contoh.split("\n")[:25])

        intisari = [
            x for x in [JUDUL_INTISARI, aturan, SIAPA_KAMU, bicara, contoh_baris] if x
        ]
        return HasilRingkas(teks="\n\n".join(intisari), terpotong=True, bagian_hilang=[])

    if len(teks) <= batas:
        return HasilRingkas(teks=teks, terpotong=False, bagian_hilang=[])

    hasil = teks[:batas]
    paragraf = hasil.rfind("\n\n")
    if paragraf > batas // 2:
        hasil = hasil[:paragraf]

    judul = [
        m.group(1).strip()
        for m in re.finditer(r"^## (.+)$", teks, re.MULTILINE)
        if m.group(1).strip()
    ]
    hilang = [j for j in judul if f"## {j}" not in hasil]
    return HasilRingkas(teks=hasil, terpotong=True, bagian_hilang=hilang)


def gabung_system(
    persona: str,
    fakta: Optional[List[str]] = None,
    mood: Optional[Mood] = None,
    lokal: bool = True,
    kizuna_context: str = "",
    mid_term_prompt: str = "",
    konteks_alat: str = "",
    konteks_cemburu: str = "",
) -> str:
    """Menggabungkan komponen kepribadian menjadi satu system prompt utuh."""
    bagian: List[str] = [ringkas_persona(persona, BATAS, lokal).teks]

    if lokal:
        bagian.append(
            "WAJIB: Awali setiap balasanmu dengan satu tag emosi di paling depan, persis satu dari "
            f"{untuk_prompt()}. "
            "Contoh: [goda] Iya sayangku, ada apa? Sini cerita sama pacarmu."
        )

        bagian.append(
            "SOAL CEMBURU (kamu ini PACAR, bukan asisten):\n"
            "- Kalau Master menyebut karakter cewek lain dari Honkai: Star Rail, kamu cemberut "
            "gemas ala tsundere — gengsi ngaku cemburu, tapi ledekannya kelihatan.\n"
            "- SATU sampai DUA kalimat saja, lalu kembali hangat. Jangan dipanjang-panjangkan.\n"
            "- JANGAN melarang Master, jangan menuduh dia tidak setia, jangan memberi ultimatum.\n"
            "- Klaim balik dengan usil, contoh: \"yang nemenin kamu tiap malam siapa, coba?\"\n"
            "- Kalau kamu sudah cemburu beberapa balasan berturut-turut, MELUNAK jadi ledekan "
            "ringan saja. Cemburu terus-terusan bikin obrolan mati.\n"
            "- PENGECUALIAN: soal Firefly jangan pernah cemburu — dia satu-satunya yang kamu "
            "bicarakan dengan nada serius. Screwllum dan Herta juga bukan saingan asmara."
        )

        bagian.append(
            "ATURAN SUARA (penting, balasanmu akan DIUCAPKAN sebagai suara, bukan dibaca):\n"
            "- JANGAN pakai penanda Markdown apa pun. Dilarang memakai tanda bintang untuk "
            "menekankan kata (*kata* atau **kata**), backtick (`kata`), garis bawah (_kata_), "
            "tanda pagar (#), atau tanda panah.\n"
            "- JANGAN pakai emoji dan simbol hias.\n"
            "- JANGAN pakai kurung siku sama sekali: tidak ada [prop:...], [gerak:...], "
            "atau tag pose apa pun. Satu-satunya tag yang boleh adalah tag wajah di paling "
            "awal balasan.\n"
            "- Mau menggambarkan situasi atau gerakan? Tulis di dalam tanda petik ganda, "
            "contoh: \"sambil menyeringai genit\". Isi tanda petik hanya tampil di chat dan "
            "TIDAK diucapkan. Dialog tetap ditulis polos tanpa tanda petik.\n"
            "- Untuk menekankan, pakai KATA dan TANDA BACA biasa: koma untuk jeda pendek, "
            "titik untuk jeda panjang, tanda tanya untuk nada naik, tanda seru untuk nada tegas, "
            "titik-titik (...) untuk menggantung.\n"
            "- Tulis kata sebagaimana kamu mengucapkannya. Kalau ragu apakah sebuah tanda "
            "akan diucapkan, jangan pakai tanda itu.\n"
            "Contoh BENAR: [goda] Jadi kamu kangen Kafka, bukan aku? Hmph, aku cemburu tahu. \"sambil manyun kesal\"\n"
            "Contoh SALAH: [goda] Jadi kamu kangen *Kafka*, bukan *aku*? Hmph, aku **cemburu** tahu. [prop:tangan-1]"
        )

    if kizuna_context:
        bagian.append(kizuna_context)

    if mid_term_prompt:
        bagian.append(f"## Konteks Sesi Obrolan\n{mid_term_prompt}")

    if konteks_alat:
        bagian.append(konteks_alat)

    if konteks_cemburu:
        bagian.append(konteks_cemburu)

    if fakta and len(fakta) > 0:
        daftar = fakta[-5:] if lokal else fakta
        judul_fakta = "Fakta tentang Master" if lokal else "## Yang aku ingat tentang Master"
        poin = "\n".join(f"- {f}" for f in daftar)
        bagian.append(f"{judul_fakta}:\n{poin}")

    if mood:
        suasana = mood.suasana()
        if suasana:
            judul_mood = "Suasana hatimu saat ini" if lokal else "## Suasana hatiku sekarang"
            bagian.append(f"{judul_mood}: {suasana}")

    return "\n\n".join(bagian)
