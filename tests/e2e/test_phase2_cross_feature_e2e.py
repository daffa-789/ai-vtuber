"""Phase 2 E2E Tests: Tier 3 (Cross-Feature Combinations) & Tier 4 (Real-World Application Scenarios).

Strictly runs using system Microsoft Edge (channel="msedge") in headless mode.
Derives expected behavior directly from ORIGINAL_REQUEST.md & PROJECT.md specifications.
Supports Progressive Testability during milestone rollouts.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path
import pytest
from playwright.sync_api import Page, expect

MAIN_SCRIPT = str(Path(__file__).resolve().parents[2] / "main.py")


# =============================================================================
# TIER 3: Cross-Feature Combinations (Pairwise Feature Interactions)
# =============================================================================

def test_t3_mic_toggle_during_chat_typing(page: Page):
    """Tier 3: User types text into chat input, toggles mic button, then submits."""
    chat_input = page.locator("#chat-input")
    send_btn = page.locator("#send-btn")
    speech_bubble = page.locator("#speech-bubble")

    # 1. Type partial message
    partial_text = "Silver Wolf, coba dengarkan ini..."
    chat_input.fill(partial_text)
    expect(chat_input).to_have_value(partial_text)

    # 2. Toggle mic if available
    mic_btn = page.locator("#mic-btn")
    if mic_btn.count() > 0:
        mic_btn.click()
        # Verify input text remains uncorrupted
        expect(chat_input).to_have_value(partial_text)

    # 3. Submit chat message
    send_btn.click()
    expect(chat_input).to_have_value("")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))

    # Verify bridge received message
    bridge_calls = page.evaluate("window.__bridge_calls || []")
    send_calls = [c for c in bridge_calls if c.get("action") == "send_message"]
    assert len(send_calls) >= 1
    assert send_calls[-1]["text"] == partial_text


def test_t3_streaming_bubble_with_continuous_mouth_sync(page: Page):
    """Tier 3: Simultaneous streaming speech bubble updates and lip-sync mouth movements."""
    speech_bubble = page.locator("#speech-bubble")
    bubble_text = page.locator("#bubble-text")
    emotion_tag = page.locator("#emotion-tag")

    # Simulate 3 streaming sentences with interleaved mouth RMS frames
    sentences = [
        ("Halo Master,", "SENYUM", [0.2, 0.5, 0.3]),
        ("hari ini kita mau push rank apa?", "SEMANGAT", [0.4, 0.9, 0.7]),
        ("Aku udah siapin build terbaik!", "GODA", [0.5, 0.8, 0.1, 0.0]),
    ]

    for text, emotion, rms_frames in sentences:
        page.evaluate(f"window.showBubble('{text}', '{emotion}');")
        expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
        expect(bubble_text).to_have_text(text)
        expect(emotion_tag).to_have_text(emotion)

        for rms in rms_frames:
            page.evaluate(f"window.setMouthOpen({rms});")
            time.sleep(0.01)


def test_t3_expression_and_motion_during_speech_stream(page: Page):
    """Tier 3: Triggering expression and motion changes while speech bubble is actively displayed."""
    speech_bubble = page.locator("#speech-bubble")
    bubble_text = page.locator("#bubble-text")

    # 1. Display active speech bubble
    message = "Master jangan cuekin aku dong... Kan aku pengen ditemenin!"
    page.evaluate(f"window.showBubble('{message}', 'SEBAL');")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(bubble_text).to_have_text(message)

    # 2. Change expression to goda (blushing/teasing)
    page.evaluate("window.setExpression('goda');")

    # 3. Trigger motion if supported
    has_set_motion = page.evaluate("typeof window.setMotion === 'function'")
    if has_set_motion:
        page.evaluate("window.setMotion('isyarat', 1);")

    # 4. Assert speech bubble is still visible and intact
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(bubble_text).to_have_text(message)


def test_t3_mic_listening_state_with_incoming_bubble(page: Page):
    """Tier 3: Speech bubble receives incoming text while microphone button is active."""
    speech_bubble = page.locator("#speech-bubble")
    status_badge = page.locator("#status-badge")

    # 1. Activate mic state if available
    mic_btn = page.locator("#mic-btn")
    if mic_btn.count() > 0:
        page.evaluate("window.setVoiceListening(true);")
        expect(mic_btn).to_have_class(re.compile(r"(active|listening)"))

    # 2. Incoming TTS speech bubble arrives
    incoming_text = "Aku dengar suaramu, Master!"
    page.evaluate(f"window.showBubble('{incoming_text}', 'SENYUM');")

    # 3. Assert both UI states coexist harmoniously
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(page.locator("#bubble-text")).to_have_text(incoming_text)


def test_t3_quick_action_interruption_during_streaming(page: Page):
    """Tier 3: User clicks quick action (headpat) while companion is in the middle of streaming speech."""
    speech_bubble = page.locator("#speech-bubble")
    emotion_tag = page.locator("#emotion-tag")
    bubble_text = page.locator("#bubble-text")

    # 1. Start streaming bubble
    page.evaluate("window.showBubble('Sedang menjelaskan strategi game yang rumit...', 'NETRAL');")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))

    # 2. User interrupts with headpat quick action
    headpat_btn = page.locator("button:has-text('💆 Elus Kepala')")
    expect(headpat_btn).to_be_visible()
    headpat_btn.click()

    # 3. Bubble and expression immediately update to interrupted flustered state
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(emotion_tag).to_have_text("KAGET")
    expect(bubble_text).to_have_text("*dielus kepalanya*")

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    assert any(c.get("action") == "touch_head" for c in bridge_calls)


# =============================================================================
# TIER 4: Real-World Application Scenarios (Comprehensive End-to-End Sessions)
# =============================================================================

def test_t4_full_conversation_session(page: Page):
    """Tier 4: Complete end-to-end user conversation flow with streaming responses & lip-sync."""
    chat_input = page.locator("#chat-input")
    send_btn = page.locator("#send-btn")
    speech_bubble = page.locator("#speech-bubble")
    status_badge = page.locator("#status-badge")

    # 1. User enters text prompt
    user_prompt = "Selamat pagi Silver Wolf, siap main game bareng?"
    chat_input.fill(user_prompt)
    send_btn.click()

    # 2. Input clears, temporary speech bubble appears
    expect(chat_input).to_have_value("")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))

    # 3. Simulate backend streaming sentence 1 with lip-sync
    page.evaluate("window.showBubble('Pagi Master! ', 'SENYUM');")
    for r in [0.2, 0.6, 0.4, 0.1]:
        page.evaluate(f"window.setMouthOpen({r});")
        time.sleep(0.01)

    # 4. Simulate backend streaming sentence 2 with lip-sync
    page.evaluate("window.showBubble('Aku udah siap dari tadi lho, yuk login!', 'SEMANGAT');")
    for r in [0.3, 0.8, 0.5, 0.0]:
        page.evaluate(f"window.setMouthOpen({r});")
        time.sleep(0.01)

    # 5. Update Kizuna status badge
    new_status = "⚡ Kizuna: Level 16 • Partner Setia • Sangat Bersemangat"
    page.evaluate(f"window.setKizunaStatus('{new_status}');")
    expect(status_badge).to_have_text(new_status)

    # 6. Verify user can type next message
    chat_input.fill("Ayo kita gasss!")
    expect(chat_input).to_have_value("Ayo kita gasss!")


def test_t4_voice_interaction_session(page: Page):
    """Tier 4: Complete Voice-to-Voice interaction session flow."""
    status_badge = page.locator("#status-badge")
    speech_bubble = page.locator("#speech-bubble")
    mic_btn = page.locator("#mic-btn")

    if mic_btn.count() == 0:
        pytest.skip("Feature F2 (Voice-to-Voice) pending Milestone M2 landing")

    # 1. User toggles microphone
    mic_btn.click()

    # 2. Voice listening active status
    page.evaluate("window.setVoiceListening(true);")
    page.evaluate("window.setVoiceStatus('🎙️ Mendengarkan suara Master...');")
    expect(status_badge).to_have_text("🎙️ Mendengarkan suara Master...")

    # 3. Speech recognition completes and emits text
    recognized = "Kamu lucu banget kalau lagi ngambek"
    page.evaluate(f"""() => {{
        if (typeof window.onSpeechRecognized === 'function') {{
            window.onSpeechRecognized('{recognized}');
        }}
    }}""")

    # 4. Companion responds with flirty tsundere speech & lip sync
    page.evaluate("window.setVoiceStatus('⚡ Memproses respons...');")
    page.evaluate("window.showBubble('Hmph! Siapa yang ngambek sih... Dasar!', 'SEBAL');")
    page.evaluate("window.setExpression('sebal');")
    for r in [0.3, 0.7, 0.2, 0.0]:
        page.evaluate(f"window.setMouthOpen({r});")

    # 5. Return to standby
    page.evaluate("window.setVoiceListening(false);")
    page.evaluate("window.setVoiceStatus('⚡ Kizuna: Siap • Mood: Senang');")
    expect(mic_btn).not_to_have_class(re.compile(r"(active|listening)"))


def test_t4_proactive_idle_and_interruption_session(page: Page):
    """Tier 4: Companion enters proactive idle state, then user interrupts with physical interaction."""
    status_badge = page.locator("#status-badge")
    speech_bubble = page.locator("#speech-bubble")
    emotion_tag = page.locator("#emotion-tag")
    bubble_text = page.locator("#bubble-text")

    # 1. Simulate proactive idle trigger (>10 minutes idle)
    page.evaluate("window.setKizunaStatus('⚡ Kizuna: Idle • Silver Wolf Mengantuk');")
    page.evaluate("window.showBubble('Hoammm... Master sibuk banget ya, aku ngantuk nih...', 'LELAH');")
    page.evaluate("window.setExpression('lelah');")
    has_set_motion = page.evaluate("typeof window.setMotion === 'function'")
    if has_set_motion:
        page.evaluate("window.setMotion('isyarat', 3);")  # tidur motion

    expect(status_badge).to_have_text("⚡ Kizuna: Idle • Silver Wolf Mengantuk")
    expect(emotion_tag).to_have_text("LELAH")
    expect(bubble_text).to_have_text("Hoammm... Master sibuk banget ya, aku ngantuk nih...")

    # 2. User wakes companion with headpat quick action
    headpat_btn = page.locator("button:has-text('💆 Elus Kepala')")
    headpat_btn.click()

    # 3. Companion is startled and switches to awake flustered reaction
    expect(emotion_tag).to_have_text("KAGET")
    expect(bubble_text).to_have_text("*dielus kepalanya*")

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    assert any(c.get("action") == "touch_head" for c in bridge_calls)


def test_t4_full_cli_conversation_session():
    """Tier 4: Full interactive CLI companion session via subprocess."""
    proc = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT, "--cli"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Session script: greeting message, then exit
    session_input = "Halo pacar gamer!\nkeluar\n"
    stdout, stderr = proc.communicate(input=session_input, timeout=30)

    assert proc.returncode == 0, f"CLI session failed with exit code {proc.returncode}. Stderr: {stderr}"
    assert "Silver Wolf // Terminal Companion" in stdout or "Status Ikatan" in stdout
    assert "Sampai jumpa" in stdout
