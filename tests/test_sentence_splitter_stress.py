"""Adversarial stress test suite for SentenceSplitterService.

Written by Challenger 1 (Milestone M1) to empirically test:
1. Pathological token streams (1 char/token, empty tokens, trailing whitespace, abrupt termination)
2. Japanese Kaomoji and emoticons ((ノ^_^)ノ, (*¯︶¯*), etc.)
3. Complex nested Indonesian abbreviations (s.d. tanggal 5, dr. Daffa dkk. pergi...)
4. Decimal numbers, Indonesian currency (Rp 50.000,00), percentages (99.9%), versions (version 3.14.159)
5. Roleplay asterisks spanning multiple clauses with internal punctuation and unclosed asterisks
6. Unclosed emotion tags and malformed brackets
"""

import sys
from silverwolf.domain.services.sentence_splitter_service import SentenceSplitterService


def test_pathological_single_char_tokens():
    """Streaming 1 character per token should reassemble sentences identically to batch."""
    splitter = SentenceSplitterService()
    text = "Halo Master! Apa kabar kamu hari ini? Semoga baik."
    char_tokens = [c for c in text]
    results = list(splitter.split_stream(char_tokens))

    assert len(results) == 3
    assert results[0] == (None, "Halo Master!")
    assert results[1] == (None, "Apa kabar kamu hari ini?")
    assert results[2] == (None, "Semoga baik.")


def test_pathological_empty_and_whitespace_tokens():
    """Empty strings and random whitespace tokens should not produce ghost clauses."""
    splitter = SentenceSplitterService()
    tokens = ["", "Halo", "", " ", "", "Master!", "", "   ", "\t", "\n", "Lanjut lagi.", ""]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert results[0] == (None, "Halo Master!")
    assert results[1] == (None, "Lanjut lagi.")


def test_pathological_stream_abrupt_termination():
    """Stream ending abruptly without trailing punctuation should flush final clause."""
    splitter = SentenceSplitterService()
    tokens = ["Halo Master tersayang, ", "aku belum selesai ngomong tapi token habis"]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert results[0] == (None, "Halo Master tersayang,")
    assert results[1] == (None, "aku belum selesai ngomong tapi token habis")


def test_indonesian_compound_abbreviation_sd():
    """Abbreviation 's.d.' (sampai dengan) must NOT be split into 's.' and 'd.'."""
    splitter = SentenceSplitterService()
    tokens = ["Acara berlangsung dari tanggal 1 s.d. tanggal 5, dr. Daffa dkk. pergi ke pasar."]
    results = list(splitter.split_stream(tokens))

    split_texts = [text for _, text in results]
    assert not any(t == "s." for t in split_texts), f"Faulty split at 's.': {split_texts}"
    assert not any(t == "d." for t in split_texts), f"Faulty split at 'd.': {split_texts}"
    assert not any(t.startswith("d.") for t in split_texts), f"Faulty split starting with 'd.': {split_texts}"


def test_indonesian_currency_comma_decimals():
    """Indonesian currency 'Rp 50.000,00' uses comma as decimal separator.

    A comma between digits (e.g. '0,00' or '50.000,00') must NOT be split as a clause comma!
    """
    splitter = SentenceSplitterService()
    tokens = ["Total belanjaan Master hari ini adalah Rp 50.000,00 saja, bukan Rp 100.000,00."]
    results = list(splitter.split_stream(tokens))

    split_texts = [text for _, text in results]
    assert not any(t.endswith("50.000,") for t in split_texts), f"Currency cleaved at comma: {split_texts}"
    assert not any(t.startswith("00") for t in split_texts), f"Decimal cleaved at comma: {split_texts}"


def test_percentage_and_version_numbers():
    """Percentages '99.9%' and multi-segment versions 'version 3.14.159' must not split mid-number."""
    splitter = SentenceSplitterService()
    tokens = ["Akurasi model mencapai 99.9% pada dataset pengujian. Gunakan version 3.14.159 sekarang!"]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert "99.9%" in results[0][1]
    assert "version 3.14.159" in results[1][1]


def test_japanese_kaomoji_preservation():
    """Japanese Kaomoji such as (ノ^_^)ノ and (*¯︶¯*) should not trigger premature splits."""
    splitter = SentenceSplitterService()
    tokens = [
        "(ノ^_^)ノ Halo Master tersayang! ",
        "(*¯︶¯*) Senang sekali bertemu denganmu hari ini.",
    ]
    results = list(splitter.split_stream(tokens))

    assert len(results) == 2
    assert "(ノ^_^)ノ" in results[0][1]
    assert "(*¯︶¯*)" in results[1][1]


def test_roleplay_asterisks_with_internal_punctuation():
    """Roleplay asterisks spanning multiple clauses with internal punctuation.

    *tersenyum, lalu melompat ke sofa.* Halo Master!
    Must not split inside the asterisks, and outside text should follow normal splitting.
    """
    splitter = SentenceSplitterService()
    tokens = ["*tersenyum, lalu melompat ke sofa.* Halo Master!"]
    results = list(splitter.split_stream(tokens))

    split_texts = [text for _, text in results]
    assert not any("tersenyum," == t for t in split_texts)
    assert "*tersenyum, lalu melompat ke sofa.*" in results[0][1]


def test_unclosed_roleplay_asterisk_stream_lockup():
    """Unclosed asterisk e.g. '*tersenyum manis dan melompat. Halo Master! Apa kabar?'

    Should NOT lock up the entire stream indefinitely until EOF.
    """
    splitter = SentenceSplitterService()
    tokens = [
        "*tersenyum manis dan melompat. ",
        "Halo Master! ",
        "Apa kabar kamu hari ini?",
    ]
    results = list(splitter.split_stream(tokens))

    # If unclosed '*' causes in_asterisks to remain True forever, no splits occur before EOF!
    assert len(results) >= 2, f"Stream locked up by unclosed asterisk, got {len(results)} chunks: {results}"


def test_unclosed_emotion_tag_stream_latency():
    """Unclosed emotion tag e.g. '[senyum tanpa tutup halo master. Apa kabar?'

    Should NOT lock up the paren_depth parser and prevent subsequent punctuation from splitting.
    """
    splitter = SentenceSplitterService()
    tokens = [
        "[senyum tanpa tutup halo master. ",
        "Apa kabar kamu hari ini? ",
        "Semoga harimu menyenangkan!",
    ]
    results = list(splitter.split_stream(tokens))

    # If unclosed '[' keeps paren_depth > 0 indefinitely, NO clauses will be yielded until EOF!
    assert len(results) >= 2, f"Stream locked up by unclosed bracket, got {len(results)} chunks: {results}"


def run_all_manual():
    """Run tests manually when invoked with `python test_sentence_splitter_stress.py`."""
    tests = [
        ("test_pathological_single_char_tokens", test_pathological_single_char_tokens),
        ("test_pathological_empty_and_whitespace_tokens", test_pathological_empty_and_whitespace_tokens),
        ("test_pathological_stream_abrupt_termination", test_pathological_stream_abrupt_termination),
        ("test_indonesian_compound_abbreviation_sd", test_indonesian_compound_abbreviation_sd),
        ("test_indonesian_currency_comma_decimals", test_indonesian_currency_comma_decimals),
        ("test_percentage_and_version_numbers", test_percentage_and_version_numbers),
        ("test_japanese_kaomoji_preservation", test_japanese_kaomoji_preservation),
        ("test_roleplay_asterisks_with_internal_punctuation", test_roleplay_asterisks_with_internal_punctuation),
        ("test_unclosed_roleplay_asterisk_stream_lockup", test_unclosed_roleplay_asterisk_stream_lockup),
        ("test_unclosed_emotion_tag_stream_latency", test_unclosed_emotion_tag_stream_latency),
    ]

    passed = 0
    failed = 0
    failures = []

    print(f"Running {len(tests)} empirical stress tests on SentenceSplitterService...\n")

    for name, func in tests:
        try:
            func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
            failures.append((name, str(e)))

    print(f"\nSummary: {passed} passed, {failed} failed.")
    return failed == 0


if __name__ == "__main__":
    success = run_all_manual()
    sys.exit(0 if success else 1)
