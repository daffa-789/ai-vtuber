"""Phase 2 E2E Tests: Feature F2 — Voice-to-Voice Microphone Interaction & Bridge Events.

Strictly runs using system Microsoft Edge (channel="msedge") in headless mode.
Derives expected behavior directly from ORIGINAL_REQUEST.md & PROJECT.md specifications.
Supports Progressive Testability during milestone rollouts.
"""

from __future__ import annotations

import re
import pytest
from playwright.sync_api import Page, expect


def _require_mic_feature(page: Page):
    """Guard for Progressive Testability: skips if Feature F2 has not yet landed in UI."""
    has_mic = page.locator("#mic-btn").count() > 0 or page.evaluate("typeof window.toggleMicrophone === 'function'")
    if not has_mic:
        pytest.skip("Feature F2 (#mic-btn / toggleMicrophone) pending Milestone M2 landing")


# =============================================================================
# TIER 1: Feature Coverage (Happy-Path Tests in Isolation)
# =============================================================================

def test_t1_f2_mic_button_dom_presence(page: Page):
    """Tier 1: Verify presence and visibility of microphone toggle button (#mic-btn)."""
    _require_mic_feature(page)
    mic_btn = page.locator("#mic-btn")
    expect(mic_btn).to_be_visible()
    expect(mic_btn).to_have_class(re.compile(r"mic-btn"))


def test_t1_f2_mic_button_click_bridge_emission(page: Page):
    """Tier 1: Verify clicking #mic-btn emits toggle_voice_input bridge event to Python."""
    _require_mic_feature(page)
    mic_btn = page.locator("#mic-btn")
    mic_btn.click()

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    voice_calls = [c for c in bridge_calls if c.get("action") in ("toggle_voice_input", "start_voice_input")]
    assert len(voice_calls) >= 1, "Expected toggle_voice_input bridge call upon clicking #mic-btn"


def test_t1_f2_mic_active_styling_state(page: Page):
    """Tier 1: Verify setVoiceListening(true) applies active/listening glowing styles."""
    _require_mic_feature(page)
    mic_btn = page.locator("#mic-btn")

    page.evaluate("window.setVoiceListening(true);")
    expect(mic_btn).to_have_class(re.compile(r"(active|listening)"))


def test_t1_f2_mic_inactive_styling_state(page: Page):
    """Tier 1: Verify setVoiceListening(false) clears active/listening glowing styles."""
    _require_mic_feature(page)
    mic_btn = page.locator("#mic-btn")

    page.evaluate("window.setVoiceListening(true);")
    page.evaluate("window.setVoiceListening(false);")
    expect(mic_btn).not_to_have_class(re.compile(r"(active|listening)"))


def test_t1_f2_mic_status_badge_update(page: Page):
    """Tier 1: Verify setVoiceStatus updates status badge to reflect listening/processing."""
    _require_mic_feature(page)
    status_badge = page.locator("#status-badge")

    test_status = "🎙️ Mendengarkan suara Master..."
    page.evaluate(f"window.setVoiceStatus('{test_status}');")
    expect(status_badge).to_have_text(test_status)


# =============================================================================
# TIER 2: Boundary & Corner Cases (Stress & Defect Immunity)
# =============================================================================

def test_t2_f2_mic_rapid_toggle_clicks(page: Page):
    """Tier 2: Rapid successive clicks on #mic-btn must not cause uncaught JS exceptions."""
    _require_mic_feature(page)
    mic_btn = page.locator("#mic-btn")

    for _ in range(5):
        mic_btn.click()

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    voice_calls = [c for c in bridge_calls if c.get("action") in ("toggle_voice_input", "start_voice_input")]
    assert len(voice_calls) >= 5, f"Expected >= 5 bridge calls from rapid clicks, got {len(voice_calls)}"


def test_t2_f2_mic_bridge_missing_fallback(page: Page):
    """Tier 2: Calling toggleMicrophone when pywebview is absent must not throw unhandled errors."""
    _require_mic_feature(page)
    res = page.evaluate("""() => {
        const oldBridge = window.pywebview;
        try {
            window.pywebview = undefined;
            if (typeof window.toggleMicrophone === 'function') {
                window.toggleMicrophone();
            }
            return true;
        } catch (e) {
            return false;
        } finally {
            window.pywebview = oldBridge;
        }
    }""")
    assert res is True, "toggleMicrophone threw an unhandled exception when pywebview bridge was absent"


def test_t2_f2_mic_speech_recognized_callback(page: Page):
    """Tier 2: Verify window.onSpeechRecognized callback populates input or triggers bubble."""
    _require_mic_feature(page)
    recognized_text = "HuoHuo, kamu hebat banget!"

    res = page.evaluate(f"""() => {{
        if (typeof window.onSpeechRecognized === 'function') {{
            window.onSpeechRecognized('{recognized_text}');
            return true;
        }}
        return false;
    }}""")
    if res:
        chat_input = page.locator("#chat-input")
        bubble_text = page.locator("#bubble-text")
        # Either the input is filled, or the bubble receives the recognized text
        input_val = chat_input.input_value()
        bubble_val = bubble_text.text_content()
        assert recognized_text in input_val or recognized_text in bubble_val


def test_t2_f2_mic_error_status_display(page: Page):
    """Tier 2: Verify error status string updates badge gracefully without crashing UI."""
    _require_mic_feature(page)
    status_badge = page.locator("#status-badge")

    error_status = "❌ Mikrofon tidak terdeteksi (PortAudio)"
    page.evaluate(f"window.setVoiceStatus('{error_status}');")
    expect(status_badge).to_have_text(error_status)


def test_t2_f2_mic_status_xss_sanitization(page: Page):
    """Tier 2: Status badge string with HTML tags must be rendered safely as text without script injection."""
    _require_mic_feature(page)
    status_badge = page.locator("#status-badge")

    xss_payload = '<img src="x" onerror="window.__xss_fired=true">'
    page.evaluate(f"window.setVoiceStatus('{xss_payload}');")

    # Verify script did not execute
    xss_fired = page.evaluate("window.__xss_fired === true")
    assert xss_fired is False, "XSS vulnerability detected in setVoiceStatus!"
    # Verify text is rendered literally
    expect(status_badge).to_have_text(xss_payload)
