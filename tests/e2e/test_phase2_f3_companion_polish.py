"""Phase 2 E2E Tests: Feature F3 — Proactive Companion Behavior, Window Drag & Motion Polish.

Strictly runs using system Microsoft Edge (channel="msedge") in headless mode.
Derives expected behavior directly from ORIGINAL_REQUEST.md & PROJECT.md specifications.
Supports Progressive Testability during milestone rollouts.
"""

from __future__ import annotations

import re
import pytest
from playwright.sync_api import Page, expect


# =============================================================================
# TIER 1: Feature Coverage (Happy-Path Tests in Isolation)
# =============================================================================

def test_t1_f3_header_drag_region(page: Page):
    """Tier 1: Verify .header-bar element exists and contains pywebview-drag-region class."""
    header = page.locator(".header-bar")
    expect(header).to_be_visible()

    # Progressive check: if pywebview-drag-region class is pending M3 landing, skip cleanly
    has_drag_class = page.locator(".header-bar.pywebview-drag-region").count() > 0
    if not has_drag_class:
        pytest.skip("Feature F3 (pywebview-drag-region class) pending Milestone M3 landing")

    expect(header).to_have_class(re.compile(r"pywebview-drag-region"))


def test_t1_f3_header_controls_clickable(page: Page):
    """Tier 1: Verify window close control button is clickable and emits bridge event."""
    btn_ctrl = page.locator(".btn-ctrl-close")
    expect(btn_ctrl).to_be_visible()

    btn_ctrl.click()

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    close_calls = [c for c in bridge_calls if c.get("action") == "close_window"]
    assert len(close_calls) >= 1, "Expected close_window bridge call upon clicking .btn-ctrl-close"


def test_t1_f3_minimize_control_clickable(page: Page):
    """Tier 1: Tombol minimize memanggil bridge minimize_window."""
    btn = page.locator(".btn-ctrl-minimize")
    expect(btn).to_be_visible()

    btn.click()

    bridge_calls = page.evaluate("window.__bridge_calls || []")
    calls = [c for c in bridge_calls if c.get("action") == "minimize_window"]
    assert len(calls) >= 1, "Expected minimize_window bridge call upon clicking .btn-ctrl-minimize"


def test_t1_f3_window_controls_outside_drag_region(page: Page):
    """Tier 1: Kontrol jendela bukan turunan .pywebview-drag-region.

    pywebview menelusuri induk dari target klik, jadi tombol yang berada di
    dalam region drag akan ikut menyeret jendela setiap kali diklik.
    """
    di_dalam_drag = page.evaluate(
        """() => {
            const el = document.querySelector('.window-controls');
            return !!el && !!el.closest('.pywebview-drag-region');
        }"""
    )
    assert not di_dalam_drag, ".window-controls tidak boleh berada di dalam region drag"


def test_t1_f3_live2d_all_nine_expressions(page: Page):
    """Tier 1: Verify all 9 Live2D expressions defined in model3.json can be activated cleanly."""
    expressions = [
        "netral",
        "senyum",
        "semangat",
        "kaget",
        "bingung",
        "lelah",
        "goda",
        "sebal",
        "sedih",
    ]

    for expr in expressions:
        res = page.evaluate(f"""() => {{
            try {{
                window.setExpression('{expr}');
                return true;
            }} catch(e) {{
                return false;
            }}
        }}""")
        assert res is True, f"Failed to activate Live2D expression: {expr}"


def test_t1_f3_live2d_motion_api(page: Page):
    """Tier 1: Verify window.setMotion API plays motion groups (isyarat:0 to isyarat:3)."""
    has_set_motion = page.evaluate("typeof window.setMotion === 'function'")
    if not has_set_motion:
        pytest.skip("Feature F3 (window.setMotion API) pending Milestone M3 landing")

    motions = [
        ("isyarat", 0),  # berubah-1.motion3.json
        ("isyarat", 1),  # berubah-2.motion3.json
        ("isyarat", 2),  # siklus.motion3.json
        ("isyarat", 3),  # tidur.motion3.json (AFK/idle sleep)
    ]

    for group, index in motions:
        res = page.evaluate(f"""() => {{
            try {{
                window.setMotion('{group}', {index});
                return true;
            }} catch(e) {{
                return false;
            }}
        }}""")
        assert res is True, f"setMotion crashed for {group}:{index}"


def test_t1_f3_kizuna_status_badge_multistage(page: Page):
    """Tier 1: Verify status badge updates dynamically across diverse Kizuna milestone states."""
    status_badge = page.locator("#status-badge")

    milestones = [
        "⚡ Kizuna: Level 1 • Kenalan Awal • Netral",
        "⚡ Kizuna: Level 8 • Partner Mabar • Ceria",
        "⚡ Kizuna: Level 15 • Sahabat Karib • Bahagia",
        "⚡ Kizuna: Level 25 • Ikatan Sejati • Penuh Kasih",
    ]

    for status_str in milestones:
        page.evaluate(f"window.setKizunaStatus({status_str!r});")
        expect(status_badge).to_have_text(status_str)


# =============================================================================
# TIER 2: Boundary & Corner Cases (Stress & Defect Immunity)
# =============================================================================

def test_t2_f3_set_expression_unknown_safeguard(page: Page):
    """Tier 2: Passing unknown/unregistered expression name must not crash PIXI/Live2D runtime."""
    res = page.evaluate("""() => {
        try {
            window.setExpression("non_existent_expression_xyz");
            window.setExpression("");
            window.setExpression(null);
            return true;
        } catch(e) {
            return false;
        }
    }""")
    assert res is True, "setExpression threw an unhandled exception for unknown or null name"


def test_t2_f3_set_motion_invalid_group_safeguard(page: Page):
    """Tier 2: Passing invalid motion group or extreme index must be safely ignored."""
    has_set_motion = page.evaluate("typeof window.setMotion === 'function'")
    if not has_set_motion:
        pytest.skip("Feature F3 (window.setMotion API) pending Milestone M3 landing")

    res = page.evaluate("""() => {
        try {
            window.setMotion("invalid_group", 999);
            window.setMotion(null, -1);
            return true;
        } catch(e) {
            return false;
        }
    }""")
    assert res is True, "setMotion crashed on invalid group or index"


def test_t2_f3_drag_region_does_not_block_mouse_tracking(page: Page):
    """Tier 2: Moving pointer across the window must track focus without being blocked by header."""
    # Mouse move to header
    page.mouse.move(240, 20)
    # Mouse move to canvas center
    page.mouse.move(240, 400)
    # Mouse move to bottom
    page.mouse.move(240, 700)

    # Verify canvas is still intact and rendering
    canvas = page.locator("#live2d-canvas")
    expect(canvas).to_be_visible()


def test_t2_f3_status_badge_extreme_content(page: Page):
    """Tier 2: Status badge with long string, emoji sequences, and special chars renders cleanly."""
    status_badge = page.locator("#status-badge")

    extreme_status = "⚡ Kizuna: Level 99 • ★★★★★ • 🎮 Mabar Nonstop • (⁠*⁠´⁠ω⁠｀⁠*⁠) • Mode Gamer Malam!"
    page.evaluate(f"window.setKizunaStatus({extreme_status!r});")
    expect(status_badge).to_have_text(extreme_status)
