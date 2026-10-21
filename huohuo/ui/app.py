"""Desktop Companion UI untuk HuoHuo memakai pywebview.

Menjalankan jendela transparan, frameless, dan always-on-top yang merender
avatar Live2D Cubism Web dengan pelacakan kursor, sinkronisasi bibir (lip-sync),
reaksi ekspresi emosi, dan gelembung chat interaktif.
"""

from __future__ import annotations

import mimetypes
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import webview

from huohuo.application.dtos.interaction_dto import UserInteractionRequest
from huohuo.config import config
from huohuo.infrastructure.container import Container, create_container

STATIC_DIR = Path(__file__).resolve().parent / "static"


class StaticAndAssetHandler(SimpleHTTPRequestHandler):
    """HTTP Handler yang melayani berkas UI statis sekaligus aset Live2D model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        # Berkas model Live2D dan tekstur diarahkan ke folder aset
        if self.path.startswith("/api/") or self.path.startswith("/models/") or "huohuo" in self.path:
            clean_name = self.path.split("?")[0].replace("/api/", "").replace("/models/", "").lstrip("/")
            if clean_name.endswith(".model3.json") or clean_name == "model3.json":
                target = config.live2d_model_path
            else:
                target = config.live2d_model_path.parent / clean_name

            if target.is_file():
                self.send_response(200)
                mime, _ = mimetypes.guess_type(str(target))
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(target.stat().st_size))
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return

        return super().do_GET()

    def log_message(self, format, *args):
        # Senyapkan log akses HTTP agar konsol tetap bersih
        pass


class CompanionApi:
    """Jembatan API dari JavaScript di jendela WebView ke Python Use Cases."""

    def __init__(
        self,
        container: Optional[Container] = None,
        vault=None,
        kizuna=None,
        llama=None,
        voice=None,
        history=None,
    ):
        self.container = container or create_container()
        self._window: Optional[webview.Window] = None
        # Voice-to-Voice (F2) state
        self._voice_active = False
        self._voice_thread: Optional[threading.Thread] = None
        self._voice_stop = threading.Event()
        self._voice_lock = threading.Lock()

    @staticmethod
    def _js_str(text: str) -> str:
        """Sanitize text untuk literal JS single-quote."""
        if not text:
            return ""
        return (
            text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\r", " ")
            .replace("\n", " ")
        )

    def _eval_js(self, code: str) -> None:
        if not self._window:
            return
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass

    def set_window(self, win: webview.Window):
        self._window = win
        if hasattr(self.container.ui_port, "set_window"):
            self.container.ui_port.set_window(win)

    def close_window(self):
        if self._window:
            self._window.destroy()

    def send_message(self, text: str):
        """Menerima input pesan pengguna, menghasilkan respons via use case."""
        if not text or not text.strip():
            return

        def _worker():
            req = UserInteractionRequest(text=text, play_audio=True, blocking_audio=False)
            self.container.process_interaction_use_case.execute(req)

        threading.Thread(target=_worker, daemon=True).start()

    def touch_head(self):
        """Interaksi sentuh kepala / headpat avatar via use case."""
        def _worker():
            self.container.touch_headpat_use_case.execute(play_audio=True, blocking_audio=False)

        threading.Thread(target=_worker, daemon=True).start()

    # ── Voice-to-Voice (F2) ──────────────────────────────────────────────────

    def toggle_voice_input(self):
        """Nyalakan/matikan loop mikrofon dari tombol mic UI. Mengembalikan status baru."""
        with self._voice_lock:
            if self._voice_active:
                self._voice_stop.set()
                self._voice_active = False
                worker = self._voice_thread
                self._voice_thread = None
            else:
                self._voice_stop.clear()
                self._voice_active = True
                worker = threading.Thread(
                    target=self._voice_worker, daemon=True, name="VoiceInputLoop"
                )
                self._voice_thread = worker
                worker.start()
            active = self._voice_active
        if worker is not None and not active:
            try:
                worker.join(timeout=0.2)
            except Exception:
                pass
        self._set_voice_listening(active)
        return {"active": active}

    def get_voice_state(self):
        """Status mikrofon saat ini untuk sinkronisasi ulang UI."""
        return {"active": self._voice_active}

    def _set_voice_listening(self, active: bool) -> None:
        status = "🎙️ Mendengarkan suara Master..." if active else "🔇 Input suara nonaktif"
        self._eval_js(f"window.setVoiceListening({'true' if active else 'false'});")
        self._eval_js(f"window.setVoiceStatus('{self._js_str(status)}');")

    def _voice_worker(self) -> None:
        """Loop: dengar satu ujaran -> transkripsi -> siarkan ke UI -> respons streaming."""
        voice = self.container.voice_interaction_use_case
        voice.reset()
        while not self._voice_stop.is_set():
            try:
                text = voice.transcribe_utterance(timeout_seconds=8.0)
            except Exception as exc:
                self._eval_js(
                    f"window.setVoiceStatus('❌ Mikrofon tidak terdeteksi ({self._js_str(str(exc))})');"
                )
                break
            if self._voice_stop.is_set():
                break
            if text:
                self._eval_js(f"window.onSpeechRecognized('{self._js_str(text)}');")
                voice.process_utterance(text, play_audio=True)


def start_companion(port: int = 8990, container: Optional[Container] = None):
    """Menjalankan aplikasi companion desktop HuoHuo."""
    server = ThreadingHTTPServer(("127.0.0.1", port), StaticAndAssetHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[Companion] Server UI statis berjalan di http://127.0.0.1:{port}")

    app_container = container or create_container()
    api = CompanionApi(container=app_container)

    # Buat jendela pywebview transparan & frameless
    window = webview.create_window(
        title="HuoHuo // Desktop Companion",
        url=f"http://127.0.0.1:{port}/index.html",
        width=config.ui_width,
        height=config.ui_height,
        frameless=True,
        transparent=True,
        on_top=True,
        js_api=api,
    )
    api.set_window(window)

    print("[Companion] Membuka jendela desktop HuoHuo...")
    webview.start(debug=False)
    server.shutdown()
