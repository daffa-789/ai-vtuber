"""Desktop Companion UI untuk HuoHuo memakai pywebview.

Menjalankan jendela transparan, frameless, dan always-on-top yang merender
avatar Live2D Cubism Web dengan pelacakan kursor, sinkronisasi bibir (lip-sync),
reaksi ekspresi emosi, dan gelembung chat interaktif.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple

import webview

from huohuo.application.dtos.interaction_dto import UserInteractionRequest
from huohuo.config import config
from huohuo.domain.services.proactive_idle_service import ProactiveIdleService
from huohuo.infrastructure.container import Container, create_container

if getattr(sys, "frozen", False):
    STATIC_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)) / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"


def _load_window_position(path) -> Tuple[Optional[int], Optional[int]]:
    """Baca koordinat jendela terakhir; kembalikan (None, None) bila tidak ada/invalid."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        x, y = int(data["x"]), int(data["y"])
        return (x, y) if x >= 0 and y >= 0 else (None, None)
    except Exception:
        return (None, None)


def _save_window_position(path, x, y) -> None:
    """Simpan koordinat jendela terakhir ke berkas konfigurasi lokal."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"x": int(x), "y": int(y)}), encoding="utf-8")
    except Exception:
        pass


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
        # Proactive idle (F3) state
        self._last_interaction = time.monotonic()
        self._idle_stop = threading.Event()
        self._idle_thread: Optional[threading.Thread] = None

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
        self._start_idle_timer()

    def close_window(self):
        if self._window:
            self._window.destroy()

    def send_message(self, text: str):
        """Menerima input pesan pengguna, menghasilkan respons via use case."""
        self._signal_interaction()
        if not text or not text.strip():
            return

        def _worker():
            req = UserInteractionRequest(text=text, play_audio=True, blocking_audio=False)
            self.container.process_interaction_use_case.execute(req)

        threading.Thread(target=_worker, daemon=True).start()

    def touch_head(self):
        """Interaksi sentuh kepala / headpat avatar via use case."""
        self._signal_interaction()

        def _worker():
            self.container.touch_headpat_use_case.execute(play_audio=True, blocking_audio=False)

        threading.Thread(target=_worker, daemon=True).start()

    # ── Voice-to-Voice (F2) ──────────────────────────────────────────────────

    def toggle_voice_input(self):
        """Nyalakan/matikan loop mikrofon dari tombol mic UI. Mengembalikan status baru."""
        self._signal_interaction()
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

    # ── Proactive Companion (F3) ─────────────────────────────────────────────

    def _signal_interaction(self) -> None:
        """Catat aktivitas Master agar timer idle direset."""
        self._last_interaction = time.monotonic()

    def _start_idle_timer(self) -> None:
        if not getattr(self.container.cfg, "proactive_aktif", True):
            return
        if self._idle_thread and self._idle_thread.is_alive():
            return
        self._idle_stop.clear()
        self._idle_thread = threading.Thread(
            target=self._idle_loop, daemon=True, name="ProactiveIdleTimer"
        )
        self._idle_thread.start()

    def _idle_loop(self) -> None:
        threshold = max(
            ProactiveIdleService.MIN_IDLE_SECONDS,
            int(getattr(self.container.cfg, "idle_threshold_detik", 300)),
        )
        while not self._idle_stop.wait(5.0):
            if self._voice_active:
                continue
            idle = time.monotonic() - self._last_interaction
            if idle < threshold:
                continue
            self._last_interaction = time.monotonic()
            try:
                level = self.container.kizuna_repo.load().level
            except Exception:
                level = 1
            picked = ProactiveIdleService.pick_proactive(
                idle_seconds=idle, kizuna_level=level, hour=datetime.now().hour
            )
            if not picked:
                continue
            emotion, text = picked
            self._eval_js(
                f"window.showBubble('{self._js_str(text)}', '{self._js_str(emotion)}');"
            )
            self._eval_js(f"window.setExpression('{self._js_str(emotion)}');")
            threading.Thread(
                target=self._speak, args=(text,), daemon=True, name="ProactiveSpeak"
            ).start()

    def _speak(self, text: str) -> None:
        try:
            self.container.synthesize_voice_use_case.speak(text, blocking=True)
        except Exception:
            pass


def start_companion(port: int = 8990, container: Optional[Container] = None):
    """Menjalankan aplikasi companion desktop HuoHuo."""
    server = ThreadingHTTPServer(("127.0.0.1", port), StaticAndAssetHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[Companion] Server UI statis berjalan di http://127.0.0.1:{port}")

    app_container = container or create_container()
    api = CompanionApi(container=app_container)

    # Pulihkan posisi jendela terakhir (Window Drag & Position Memory - F3)
    saved_x, saved_y = _load_window_position(config.window_position_file)

    # Buat jendela pywebview transparan & frameless
    window = webview.create_window(
        title="HuoHuo // Desktop Companion",
        url=f"http://127.0.0.1:{port}/index.html",
        width=config.ui_width,
        height=config.ui_height,
        x=saved_x,
        y=saved_y,
        frameless=True,
        transparent=True,
        on_top=True,
        js_api=api,
    )
    api.set_window(window)

    # Persistensi posisi: simpan saat jendela dipindah (drag) dan saat ditutup.
    def _persist_position(*_args):
        try:
            if window.x is not None and window.y is not None:
                _save_window_position(config.window_position_file, window.x, window.y)
        except Exception:
            pass

    try:
        window.events.moved += _persist_position
        window.events.closing += _persist_position
    except Exception:
        pass

    print("[Companion] Membuka jendela desktop HuoHuo...")
    webview.start(debug=False)
    server.shutdown()
