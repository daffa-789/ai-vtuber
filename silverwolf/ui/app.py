"""Desktop Companion UI untuk Silver Wolf memakai pywebview.

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

from silverwolf.config import AppConfig, config
from silverwolf.core.kizuna import KizunaEngine
from silverwolf.core.memory import CharacterVault, ChatHistory
from silverwolf.core.mood import Mood
from silverwolf.core.persona_composer import gabung_system
from silverwolf.inference.llama_client import LlamaClient
from silverwolf.voice.pipeline import VoicePipeline

STATIC_DIR = Path(__file__).resolve().parent / "static"


class StaticAndAssetHandler(SimpleHTTPRequestHandler):
    """HTTP Handler yang melayani berkas UI statis sekaligus aset Live2D model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        # Berkas model Live2D dan tekstur diarahkan ke folder aset
        if self.path.startswith("/api/") or self.path.startswith("/models/") or "silverwolf" in self.path:
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
    """Jembatan API dari JavaScript di jendela WebView ke Python."""

    def __init__(
        self,
        vault: CharacterVault,
        kizuna: KizunaEngine,
        llama: LlamaClient,
        voice: VoicePipeline,
        history: ChatHistory,
    ):
        self.vault = vault
        self.kizuna = kizuna
        self.llama = llama
        self.voice = voice
        self.history = history
        self._window: Optional[webview.Window] = None

    def set_window(self, win: webview.Window):
        self._window = win

    def close_window(self):
        if self._window:
            self._window.destroy()

    def send_message(self, text: str):
        """Menerima input pesan pengguna, menghasilkan respons, dan memutar suara."""
        if not text or not text.strip():
            return

        def _process():
            # 1. Catat interaksi di Kizuna
            snap = self.kizuna.record_message(text)

            # 2. Siapkan memori & prompt
            persona = self.vault.baca_persona()
            fakta = self.vault.baca_fakta()
            mood = self.vault.baca_mood() or Mood.awal()
            kizuna_ctx = self.kizuna.get_prompt_context()

            sys_prompt = gabung_system(
                persona=persona,
                fakta=fakta,
                mood=mood,
                lokal=True,
                kizuna_context=kizuna_ctx,
            )

            # Format percakapan
            self.history.tambah("user", text)
            messages = [{"role": "system", "content": sys_prompt}] + self.history.ke_format_llm()

            # 3. Inferensi LLM
            emotion, reply = self.llama.generate(messages)
            self.history.tambah("assistant", f"[{emotion or 'senyum'}] {reply}")

            # 4. Perbarui Mood & Simpan Memori
            mood_baru = Mood.perbarui(mood, emotion)
            self.vault.simpan_mood(mood_baru)
            self.vault.catat_riwayat(text, f"[{emotion or 'senyum'}] {reply}")

            # 5. Tampilkan ke UI
            if self._window:
                # Sanitasi string untuk JS eval
                clean_reply_js = reply.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                emotion_js = (emotion or "senyum").replace("'", "")
                status_text = f"⚡ Kizuna: Level {snap.level} • {mood_baru.suasana()[:20]}..."

                self._window.evaluate_js(f"window.showBubble('{clean_reply_js}', '{emotion_js}');")
                self._window.evaluate_js(f"window.setExpression('{emotion_js}');")
                self._window.evaluate_js(f"window.setKizunaStatus('{status_text}');")

            # 6. Sintesis & pemutaran suara dengan lip-sync
            def on_lip(level: float):
                if self._window:
                    self._window.evaluate_js(f"window.setMouthOpen({level:.3f});")

            try:
                self.voice.speak(reply, on_lip_sync=on_lip, blocking=False)
            except Exception as err:
                print(f"[Companion] Suara: {err}")

        threading.Thread(target=_process, daemon=True).start()

    def touch_head(self):
        """Interaksi sentuh kepala / headpat avatar."""
        snap = self.kizuna.record_touch()
        balasan = "Eh... Master tiba-tiba elus kepalaku?! Rambutku jadi berantakan tahu... Tapi rasanya hangat sih..."
        if self._window:
            self._window.evaluate_js(f"window.showBubble('{balasan}', 'kaget');")
            self._window.evaluate_js("window.setExpression('kaget');")
            self._window.evaluate_js(f"window.setKizunaStatus('⚡ Kizuna: Level {snap.level} • Tersipu');")

        def on_lip(level: float):
            if self._window:
                self._window.evaluate_js(f"window.setMouthOpen({level:.3f});")

        threading.Thread(
            target=lambda: self.voice.speak(balasan, on_lip_sync=on_lip, blocking=False),
            daemon=True,
        ).start()


def start_companion(port: int = 8990):
    """Menjalankan aplikasi companion desktop Silver Wolf."""
    server = ThreadingHTTPServer(("127.0.0.1", port), StaticAndAssetHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[Companion] Server UI statis berjalan di http://127.0.0.1:{port}")

    # Inisialisasi komponen inti
    vault = CharacterVault(config.memory_dir)
    kizuna = KizunaEngine(config.memory_dir / "kizuna" / "silverwolf_kizuna_v1.json")
    llama = LlamaClient()
    voice = VoicePipeline()
    history = ChatHistory()

    api = CompanionApi(vault, kizuna, llama, voice, history)

    # Buat jendela pywebview transparan & frameless
    window = webview.create_window(
        title="Silver Wolf // Desktop Companion",
        url=f"http://127.0.0.1:{port}/index.html",
        width=config.ui_width,
        height=config.ui_height,
        frameless=True,
        transparent=True,
        on_top=True,
        js_api=api,
    )
    api.set_window(window)

    print("[Companion] Membuka jendela desktop Silver Wolf...")
    webview.start(debug=False)
    server.shutdown()
