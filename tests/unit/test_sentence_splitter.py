"""Unit tests for SentenceSplitterService.

Tests clause splitting, threshold rules, abbreviation/decimal/emoticon preservation,
initial/inline emotion tag extraction, roleplay asterisks, and end-of-stream flush.
"""

from silverwolf.domain.services.sentence_splitter_service import SentenceSplitterService


def test_basic_punctuation_splitting():
    splitter = SentenceSplitterService()
    tokens = ["Halo Master! ", "Apa kabar kamu hari ini? ", "Semoga harimu menyenangkan…"]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 3
    assert results[0] == (None, "Halo Master!")
    assert results[1] == (None, "Apa kabar kamu hari ini?")
    assert results[2] == (None, "Semoga harimu menyenangkan…")


def test_newline_splitting():
    splitter = SentenceSplitterService()
    text = "Baris pertama selesai.\nBaris kedua dimulai!"
    results = list(splitter.split_stream([text]))

    assert len(results) == 2
    assert results[0] == (None, "Baris pertama selesai.")
    assert results[1] == (None, "Baris kedua dimulai!")


def test_comma_threshold_rule():
    splitter = SentenceSplitterService(min_clause_length=15)

    # 1. Short buffer before comma (< 15 chars): comma does NOT split
    short_comma_tokens = ["Halo, ", "Master."]
    res_short = list(splitter.split_stream(short_comma_tokens))
    assert len(res_short) == 1
    assert res_short[0] == (None, "Halo, Master.")

    # 2. Long buffer before comma (>= 15 chars): comma DOES split
    long_comma_tokens = ["Halo Master tersayang, ", "aku kangen banget nih."]
    res_long = list(splitter.split_stream(long_comma_tokens))
    assert len(res_long) == 2
    assert res_long[0] == (None, "Halo Master tersayang,")
    assert res_long[1] == (None, "aku kangen banget nih.")


def test_decimal_number_preservation():
    splitter = SentenceSplitterService()
    tokens = ["Nilai konstanta pi adalah ", "3.14, ", "bukan begitu?"]
    # "Nilai konstanta pi adalah 3.14," >= 15 chars, so splits at comma, but 3.14 does not split on dot!
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert "3.14" in results[0][1]
    assert results[1][1] == "bukan begitu?"


def test_indonesian_abbreviations_preservation():
    splitter = SentenceSplitterService()
    tokens = [
        "Kita bisa beli apel, jeruk, dll. di pasar tradisional. ",
        "Lalu periksa ke dr. Budi di klinik.",
    ]
    results = list(splitter.split_stream(tokens))

    # Should not split at "dll." or "dr."
    assert any("dll." in text for _, text in results)
    assert any("dr. Budi" in text for _, text in results)
    assert not any(text == "dll." for _, text in results)
    assert not any(text == "dr." for _, text in results)


def test_numbered_list_preservation():
    splitter = SentenceSplitterService()
    tokens = ["1. Pertama nyalakan PC.\n", "2. Kedua buka game favorit."]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert results[0][1].startswith("1. Pertama")
    assert results[1][1].startswith("2. Kedua")


def test_roleplay_asterisks_preservation():
    splitter = SentenceSplitterService()
    tokens = ["*tersenyum manis, memeluk Master* ", "Halo Master!"]
    results = list(splitter.split_stream(tokens))

    # Comma inside *...* must not trigger a split
    assert len(results) == 1
    assert "*tersenyum manis, memeluk Master*" in results[0][1]
    assert results[0][1].endswith("Halo Master!")


def test_emoticon_preservation():
    splitter = SentenceSplitterService()
    tokens = ["(*´ω｀*) Halo Master! ", "Semangat terus ya XD!"]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert "(*´ω｀*)" in results[0][1]
    assert "XD!" in results[1][1]


def test_initial_emotion_extraction():
    splitter = SentenceSplitterService()
    tokens = ["[sen", "yum] ", "Halo ", "Master! ", "Aku di sini."]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    # Emotion tag must be extracted and stripped from the sentence text
    assert results[0] == ("senyum", "Halo Master!")
    assert results[1] == ("senyum", "Aku di sini.")
    assert "[senyum]" not in results[0][1]
    assert "[senyum]" not in results[1][1]


def test_midstream_emotion_tag_switch():
    splitter = SentenceSplitterService()
    tokens = ["[kaget] Eh beneran?! ", "[goda] Hehe, bercanda kok Master."]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert results[0] == ("kaget", "Eh beneran?!")
    assert results[1] == ("goda", "Hehe, bercanda kok Master.")


def test_flush_end_of_stream():
    splitter = SentenceSplitterService()
    tokens = ["Halo ", "dunia ", "tanpa tanda baca"]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 1
    assert results[0] == (None, "Halo dunia tanpa tanda baca")


def test_empty_and_whitespace_stream():
    splitter = SentenceSplitterService()
    assert list(splitter.split_stream([])) == []
    assert list(splitter.split_stream(["   ", "\t", "\n"])) == []


def test_split_text_batch_convenience():
    splitter = SentenceSplitterService()
    text = "Satu. Dua! Tiga? Empat."
    sentences = splitter.split_text(text)

    assert sentences == ["Satu.", "Dua!", "Tiga?", "Empat."]
