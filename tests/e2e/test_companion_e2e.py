"""Automated Playwright E2E UI Testing for HuoHuo Companion Web Interface.

Strictly runs using system Microsoft Edge (channel="msedge") in headless mode.
Does NOT download or install Playwright Chromium.
"""

from __future__ import annotations

import re
import time

import pytest
from playwright.sync_api import Page, expect

from huohuo.config import config


@pytest.mark.skipif(
    not config.live2d_model_path.is_file(),
    reason="Aset Live2D (proprietary/52MB) tidak disertakan di CI",
)
def test_asset_loading_and_canvas_initialization(page: Page, live_server_url: str):
    """Verify that all core web libraries, model configurations, and the canvas initialize."""
    # 1. Assert core JS libraries loaded into window
    pixi_loaded = page.evaluate("typeof PIXI !== 'undefined'")
    assert pixi_loaded is True, "PIXI library failed to load"

    live2d_plugin_loaded = page.evaluate("typeof PIXI.live2d !== 'undefined'")
    assert live2d_plugin_loaded is True, "pixi-live2d-display plugin failed to load"

    # 2. Check Live2D model config endpoint returns 200 OK
    response = page.request.get(f"{live_server_url}/api/model3.json")
    assert response.status == 200, f"Expected 200 from /api/model3.json, got {response.status}"
    model_json = response.json()
    assert "FileReferences" in model_json or "Version" in model_json, "Invalid model3.json structure"

    # 3. Assert Canvas element exists and is visible
    canvas = page.locator("#live2d-canvas")
    expect(canvas).to_be_visible()

    # 4. Wait briefly for PIXI Application to bind canvas
    time.sleep(0.5)
    canvas_width = page.evaluate("document.getElementById('live2d-canvas').width")
    canvas_height = page.evaluate("document.getElementById('live2d-canvas').height")
    assert canvas_width > 0, f"Canvas width should be > 0, got {canvas_width}"
    assert canvas_height > 0, f"Canvas height should be > 0, got {canvas_height}"


def test_user_chat_interaction(page: Page):
    """Test typing chat input, submitting, speech bubble visibility, and emotion tag updates."""
    chat_input = page.locator("#chat-input")
    send_btn = page.locator("#send-btn")
    speech_bubble = page.locator("#speech-bubble")
    emotion_tag = page.locator("#emotion-tag")
    bubble_text = page.locator("#bubble-text")

    # Initially speech bubble is hidden
    expect(speech_bubble).to_have_class(re.compile(r"hidden"))

    # Type input and click send
    test_message = "Halo pacar gamer tersayang!"
    chat_input.fill(test_message)
    send_btn.click()

    # Chat input is cleared
    expect(chat_input).to_have_value("")

    # Temporary speech bubble appears
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))

    # Verify bridge received message
    bridge_calls = page.evaluate("window.__bridge_calls")
    send_calls = [c for c in bridge_calls if c["action"] == "send_message"]
    assert len(send_calls) >= 1
    assert send_calls[-1]["text"] == test_message

    # Test window.showBubble bridge API directly
    page.evaluate("window.showBubble('Kangen ya sama aku? Mau mabar apa?', 'GODA');")
    expect(speech_bubble).not_to_have_class(re.compile(r"hidden"))
    expect(emotion_tag).to_have_text("GODA")
    expect(bubble_text).to_have_text("Kangen ya sama aku? Mau mabar apa?")


def test_pointer_tracking_and_expression_apis(page: Page):
    """Test window API functions: setExpression, setMouthOpen, setKizunaStatus, and pointer tracking."""
    # 1. setExpression API
    page.evaluate("window.setExpression('kaget');")
    page.evaluate("window.setExpression('senyum');")

    # 2. setMouthOpen API
    page.evaluate("window.setMouthOpen(0.85);")
    page.evaluate("window.setMouthOpen(0.0);")

    # 3. setKizunaStatus API
    status_badge = page.locator("#status-badge")
    new_status = "⚡ Kizuna: Level 15 • Partner Terpercaya • Ceria"
    page.evaluate(f"window.setKizunaStatus('{new_status}');")
    expect(status_badge).to_have_text(new_status)

    # 4. Pointer tracking: Move mouse across screen and verify no uncaught JS errors
    page.mouse.move(100, 200)
    page.mouse.move(240, 390)
    page.mouse.move(400, 600)


def test_head_pat_via_pointer(page: Page):
    """Mengelus kepala pakai pointer (tekan + geser di area kepala) memicu touch_head."""
    canvas = page.locator("#live2d-canvas")
    box = canvas.bounding_box()
    assert box and box["width"] > 0 and box["height"] > 0

    # Pusat kepala = tengah horizontal, CONFIG.headY (0.22) vertikal.
    cx = box["x"] + box["width"] * 0.5
    cy = box["y"] + box["height"] * 0.22

    # Tekan lalu geser turun melewati ambang satu "elus" (strokePx = 44px).
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx, cy + 30)
    page.mouse.move(cx, cy + 60)

    # Feedback: satu hati melayang muncul + gelembung placeholder "...".
    expect(page.locator(".pat-heart").first).to_be_visible()
    expect(page.locator("#bubble-text")).to_have_text("...")

    page.mouse.up()

    bridge_calls = page.evaluate("window.__bridge_calls")
    assert any(c["action"] == "touch_head" for c in bridge_calls), (
        "elus kepala pakai pointer tidak memicu touch_head"
    )


def test_head_pat_ignores_non_head_area(page: Page):
    """Klik/geser di area non-kepala (bawah) tidak memicu touch_head."""
    canvas = page.locator("#live2d-canvas")
    box = canvas.bounding_box()
    cx = box["x"] + box["width"] * 0.5
    low_y = box["y"] + box["height"] * 0.85  # jauh di bawah kepala

    page.mouse.move(cx, low_y)
    page.mouse.down()
    page.mouse.move(cx, low_y + 40)
    page.mouse.up()

    bridge_calls = page.evaluate("window.__bridge_calls")
    assert not any(c["action"] == "touch_head" for c in bridge_calls), (
        "sentuh di luar area kepala tidak seharusnya memicu headpat"
    )
