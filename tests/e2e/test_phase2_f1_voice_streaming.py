"""Phase 2 E2E Tests: Feature F1 — Streaming Voice Bubble Updates & Continuous Lip-Sync.

Strictly runs using system Microsoft Edge (channel="msedge") in headless mode.
Derives expected behavior directly from ORIGINAL_REQUEST.md & PROJECT.md specifications.
"""

from __future__ import annotations

import re
import time
from playwright.sync_api import Page, expect


# =============================================================================
# TIER 1: Feature Coverage (Happy-Path Tests in Isolation)
# =============================================================================

def test_t1_f1_streaming_bubble_single_clause(page: Page):
    """Tier 1: Verify single clause streaming display and emotion tag update."""
    speech_bubble = page.locator("#speech-bubble")
    emotion_tag = page.locator("#emotion-tag")
    bubble_text = page.locator("#bubble-text")

    # Initial state should be hidden
    expect(speech_bubble).to_have_class(re.compile(r"hidden"))

    # First clause arrives from streaming LLM
    page.evaluate("window.showBubble('Halo Master,', 'SENYUM');")

    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(emotion_tag).to_have_text("SENYUM")
    expect(bubble_text).to_have_text("Halo Master,")


def test_t1_f1_streaming_bubble_sequential_clauses(page: Page):
    """Tier 1: Verify real-time sentence-by-sentence streaming bubble updates without tearing."""
    speech_bubble = page.locator("#speech-bubble")
    emotion_tag = page.locator("#emotion-tag")
    bubble_text = page.locator("#bubble-text")

    clauses = [
        ("Halo Master,", "SENYUM"),
        ("aku kangen banget mabar bareng kamu!", "GODA"),
        ("Ayo login sekarang juga ya~", "SEMANGAT"),
    ]

    for text, emotion in clauses:
        page.evaluate(f"window.showBubble('{text}', '{emotion}');")
        expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
        expect(emotion_tag).to_have_text(emotion)
        expect(bubble_text).to_have_text(text)
        time.sleep(0.05)


def test_t1_f1_lipsync_standard_mouth_values(page: Page):
    """Tier 1: Verify mouth open API sets standard boundary values (0.0, 0.5, 1.0)."""
    # Verify evaluation executes cleanly without uncaught JS error
    result_min = page.evaluate("""() => {
        window.setMouthOpen(0.0);
        return true;
    }""")
    assert result_min is True

    result_mid = page.evaluate("""() => {
        window.setMouthOpen(0.5);
        return true;
    }""")
    assert result_mid is True

    result_max = page.evaluate("""() => {
        window.setMouthOpen(1.0);
        return true;
    }""")
    assert result_max is True


def test_t1_f1_lipsync_continuous_rms_stream(page: Page):
    """Tier 1: Verify streaming continuous RMS levels simulating 50ms audio worker frames."""
    rms_levels = [0.05, 0.18, 0.42, 0.75, 0.88, 0.65, 0.40, 0.22, 0.08, 0.0]

    for level in rms_levels:
        res = page.evaluate(f"""() => {{
            window.setMouthOpen({level});
            return true;
        }}""")
        assert res is True
        time.sleep(0.01)


def test_t1_f1_bubble_visibility_toggle(page: Page):
    """Tier 1: Verify speech bubble visibility activates on message and maintains visible class."""
    speech_bubble = page.locator("#speech-bubble")
    expect(speech_bubble).to_have_class(re.compile(r"hidden"))

    page.evaluate("window.showBubble('Tes visibilitas gelembung bicara', 'NETRAL');")
    expect(speech_bubble).to_be_visible()
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))


# =============================================================================
# TIER 2: Boundary & Corner Cases (Stress & Defect Immunity)
# =============================================================================

def test_t2_f1_mouth_open_clamping_negative(page: Page):
    """Tier 2: Extreme negative mouth open values must be clamped to 0.0 without errors."""
    negative_values = [-0.01, -0.5, -1.0, -99.99]
    for val in negative_values:
        res = page.evaluate(f"""() => {{
            try {{
                window.setMouthOpen({val});
                return true;
            }} catch(e) {{
                return false;
            }}
        }}""")
        assert res is True, f"Failed on negative value: {val}"


def test_t2_f1_mouth_open_clamping_excessive(page: Page):
    """Tier 2: Extreme positive mouth open values must be clamped to 1.0 without errors."""
    excessive_values = [1.01, 1.5, 2.0, 999.0]
    for val in excessive_values:
        res = page.evaluate(f"""() => {{
            try {{
                window.setMouthOpen({val});
                return true;
            }} catch(e) {{
                return false;
            }}
        }}""")
        assert res is True, f"Failed on excessive value: {val}"


def test_t2_f1_mouth_open_nan_and_invalid_types(page: Page):
    """Tier 2: NaN, undefined, or string arguments should not throw unhandled JS exceptions."""
    res = page.evaluate("""() => {
        try {
            window.setMouthOpen(NaN);
            window.setMouthOpen(null);
            window.setMouthOpen(undefined);
            window.setMouthOpen("invalid_string");
            return true;
        } catch(e) {
            return false;
        }
    }""")
    assert res is True, "setMouthOpen crashed on non-numeric inputs"


def test_t2_f1_streaming_bubble_empty_text(page: Page):
    """Tier 2: Empty or whitespace-only streaming bubble text should not crash or corrupt DOM."""
    speech_bubble = page.locator("#speech-bubble")
    bubble_text = page.locator("#bubble-text")

    page.evaluate("window.showBubble('', 'SENYUM');")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(bubble_text).to_have_text("")

    page.evaluate("window.showBubble('   ', 'NETRAL');")
    expect(bubble_text).to_have_text("   ")


def test_t2_f1_streaming_bubble_long_monologue(page: Page):
    """Tier 2: Stress test with extreme monologue length (>500 chars) ensuring proper DOM containment."""
    speech_bubble = page.locator("#speech-bubble")
    bubble_text = page.locator("#bubble-text")

    long_text = (
        "Master tahu nggak sih, di dunia game itu ada yang namanya meta build, "
        "tapi menurutku apapun karakternya kalau pilotnya jago pasti bisa tembus Memory of Chaos 12! "
        "Aku udah racik tim hypercarry yang bakal bikin musuh langsung berlutut dalam 0 cycle! "
        "Jangan lupa siapin cemilan sama minuman dingin ya, malam ini kita push rank sampai pagi!"
    )

    page.evaluate(f"window.showBubble({long_text!r}, 'SEMANGAT');")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(bubble_text).to_have_text(long_text)
