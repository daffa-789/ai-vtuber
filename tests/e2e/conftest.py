"""Playwright E2E test configuration and fixtures.

Uses system pre-installed Microsoft Edge (channel="msedge").
Runs headlessly without downloading Chromium or blocking GUI windows.
"""

from __future__ import annotations

import socket
import threading
from http.server import ThreadingHTTPServer
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from huohuo.ui.app import StaticAndAssetHandler


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """Launch local ThreadingHTTPServer serving static assets & Live2D model files."""
    port = get_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), StaticAndAssetHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    yield url

    server.shutdown()


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Launch system pre-installed Microsoft Edge headlessly."""
    with sync_playwright() as p:
        # Strictly use channel="msedge" to avoid downloading Playwright Chromium
        browser = p.chromium.launch(channel="msedge", headless=True)
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    context = browser.new_context(viewport={"width": 480, "height": 780})
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext, live_server_url: str) -> Generator[Page, None, None]:
    """Create a page with injected pywebview mock bridge and navigate to index.html."""
    page = context.new_page()
    page.set_default_timeout(3000)

    # Pre-inject pywebview mock bridge before any scripts execute
    page.add_init_script("""
        window.__bridge_calls = [];
        window.pywebview = {
            api: {
                send_message: function(text) {
                    window.__bridge_calls.push({ action: 'send_message', text: text });
                },
                touch_head: function() {
                    window.__bridge_calls.push({ action: 'touch_head' });
                },
                close_window: function() {
                    window.__bridge_calls.push({ action: 'close_window' });
                },
                toggle_voice_input: function() {
                    window.__bridge_calls.push({ action: 'toggle_voice_input' });
                    return { active: true };
                },
                get_voice_state: function() {
                    window.__bridge_calls.push({ action: 'get_voice_state' });
                    return { active: false };
                }
            }
        };
    """)

    page.goto(f"{live_server_url}/index.html", wait_until="domcontentloaded")
    yield page
    page.close()

