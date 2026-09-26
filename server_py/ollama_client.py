"""Klien Ollama untuk inferensi LLM lokal offline (Llama 3.2, Qwen, dll).

Stdlib murni tanpa dependensi luar, mendukung streaming JSON-lines dari /api/chat.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterator

TIMEOUT = 45


class OllamaError(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


def alir(model: str, messages: list[dict], url_dasar: str = "http://127.0.0.1:11434") -> Iterator[str]:
    """Mengalirkan potongan teks balasan dari endpoint /api/chat Ollama."""
    url = f"{url_dasar.rstrip('/')}/api/chat"
    data = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.7,
        },
    }
    perm = urllib.request.Request(
        url,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(perm, timeout=TIMEOUT) as resp:
            for baris in resp:
                baris = baris.strip()
                if not baris:
                    continue
                try:
                    obj = json.loads(baris.decode("utf-8"))
                    konten = (obj.get("message") or {}).get("content") or ""
                    if konten:
                        yield konten
                    if obj.get("done"):
                        break
                except ValueError:
                    continue
    except urllib.error.URLError as err:
        raise OllamaError(
            f"Ollama belum aktif di {url_dasar} ({err}). "
            f"Buka aplikasi Ollama atau jalankan: ollama run {model}"
        ) from err
    except Exception as err:
        raise OllamaError(f"Galat streaming Ollama: {err}") from err


def cek_siap(url_dasar: str = "http://127.0.0.1:11434") -> bool:
    """Cek cepat apakah daemon Ollama sedang berjalan di background."""
    try:
        req = urllib.request.Request(f"{url_dasar.rstrip('/')}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False
