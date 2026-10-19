"""Unit test untuk emotion_parser dan emotion_tags."""

from silverwolf.core.emotion_parser import (
    add_emotion_tag,
    clean_emotion_tags,
    emotion_to_talk_style,
    extract_emotion,
)
from silverwolf.core.emotion_tags import dikenali, untuk_prompt


def test_extract_emotion_dengan_tag():
    teks = "[goda] Halo Master, kangen ya?"
    hasil = extract_emotion(teks)
    assert hasil.emotion == "goda"
    assert hasil.clean_text == "Halo Master, kangen ya?"


def test_extract_emotion_tanpa_tag():
    teks = "  Halo Master tanpa tag  "
    hasil = extract_emotion(teks)
    assert hasil.emotion is None
    # Tanpa tag, teks TIDAK boleh di-strip (paritas C#)
    assert hasil.clean_text == teks


def test_clean_emotion_tags_membuang_semua_tag():
    teks = "[goda] Halo [prop:tangan-1] Master! [gerak:berubah-1]"
    bersih = clean_emotion_tags(teks)
    assert bersih == "Halo Master!"


def test_clean_emotion_tags_tidak_membuang_link_markdown():
    teks = "Ini link [dokumen](https://example.com) penting."
    bersih = clean_emotion_tags(teks)
    assert bersih == "Ini link [dokumen](https://example.com) penting."


def test_add_emotion_tag():
    assert add_emotion_tag("senyum", "Selamat pagi") == "[senyum] Selamat pagi"


def test_emotion_tags_registry():
    assert dikenali("senyum") is True
    assert dikenali("kaget") is True
    assert dikenali("invalid_tag") is False
    assert "[senyum]" in untuk_prompt()
    assert "[goda]" in untuk_prompt()


def test_emotion_to_talk_style():
    assert emotion_to_talk_style("marah") == "angry"
    assert emotion_to_talk_style("senyum") == "happy"
    assert emotion_to_talk_style("kaget") == "surprised"
    assert emotion_to_talk_style(None) == "neutral"
