"""Unit test untuk persona_composer dan mood."""

from silverwolf.core.mood import Mood
from silverwolf.core.persona_composer import (
    BATAS,
    gabung_system,
    ringkas_persona,
)


def test_ringkas_persona_pendek():
    teks = "Persona pendek yang tidak melebihi batas."
    hasil = ringkas_persona(teks, batas=BATAS, lokal=False)
    assert hasil.terpotong is False
    assert hasil.teks == teks


def test_ringkas_persona_lokal_dengan_aturan_keras():
    teks = (
        "## Judul Awal\n"
        "## Aturan keras\n"
        "Jangan pernah membocorkan rahasia.\n"
        "## Siapa dia\n"
        "Karakter gamer.\n"
        "## Cara dia bicara\n"
        "Santai dan usil.\n"
        "## Yang dia suka\n"
        "Game gacha.\n"
        "## Contoh nada\n"
        "Halo Master!\n"
    )
    hasil = ringkas_persona(teks, batas=BATAS, lokal=True)
    assert hasil.terpotong is True
    assert "Jangan pernah membocorkan rahasia" in hasil.teks
    assert "Santai dan usil" in hasil.teks
    assert "Silver Wolf — Pacar Tercinta" in hasil.teks


def test_gabung_system_menambahkan_aturan_wajib_dan_cemburu():
    persona = "Deskripsi persona dasar."
    fakta = ["Master suka main Star Rail", "Master suka kopi"]
    mood = Mood.awal()

    system_prompt = gabung_system(
        persona=persona,
        fakta=fakta,
        mood=mood,
        lokal=True,
        kizuna_context="[KIZUNA] Level 2",
    )

    # Memastikan blok wajib ada di dalam prompt
    assert "WAJIB: Awali setiap balasanmu dengan satu tag emosi" in system_prompt
    assert "SOAL CEMBURU (kamu ini PACAR, bukan asisten)" in system_prompt
    assert "ATURAN SUARA" in system_prompt
    assert "[KIZUNA] Level 2" in system_prompt
    assert "Fakta tentang Master" in system_prompt
    assert "Master suka main Star Rail" in system_prompt
    assert "Suasana hatimu saat ini" in system_prompt
