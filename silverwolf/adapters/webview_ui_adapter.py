"""Adapter: WebviewUIAdapter.

Implements CompanionUIPort for pywebview desktop window.
Safely translates high-level UI commands into JavaScript evaluation calls in the webview.
"""

from __future__ import annotations

from typing import Any, Optional

from silverwolf.domain.ports.companion_ui_port import CompanionUIPort


class WebviewUIAdapter(CompanionUIPort):
    """Concrete UI adapter communicating with pywebview DOM via JavaScript evaluation."""

    def __init__(self, window: Optional[Any] = None):
        self._window = window

    def set_window(self, window: Any) -> None:
        """Bind the active pywebview Window instance."""
        self._window = window

    def _eval_js(self, js_code: str) -> None:
        """Execute JavaScript in window if window is open and valid."""
        if not self._window:
            return
        try:
            self._window.evaluate_js(js_code)
        except Exception:
            pass

    @staticmethod
    def _sanitize(text: str) -> str:
        """Sanitize text string for safe JavaScript single-quote literal embedding."""
        if not text:
            return ""
        return (
            text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\r", " ")
            .replace("\n", " ")
        )

    def show_bubble(self, text: str, emotion: str = "senyum") -> None:
        """Display dialog subtitle balloon with emotion tag."""
        clean_text = self._sanitize(text)
        clean_emotion = self._sanitize(emotion or "senyum")
        self._eval_js(f"window.showBubble('{clean_text}', '{clean_emotion}');")

    def set_expression(self, emotion: str) -> None:
        """Trigger Live2D facial expression."""
        clean_emotion = self._sanitize(emotion or "senyum")
        self._eval_js(f"window.setExpression('{clean_emotion}');")

    def set_kizuna_status(self, status_text: str) -> None:
        """Update Kizuna status / mood badge in header bar."""
        clean_status = self._sanitize(status_text)
        self._eval_js(f"window.setKizunaStatus('{clean_status}');")

    def set_mouth_open(self, level: float) -> None:
        """Update Live2D mouth opening for lip-sync (0.0 to 1.0)."""
        clamped = max(0.0, min(1.0, float(level)))
        self._eval_js(f"window.setMouthOpen({clamped:.3f});")
