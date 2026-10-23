"""Adapter: LlamaServerAdapter.

Implements LLMInferencePort for llama-server / OpenAI-compatible endpoints.
Includes health check, streaming, and graceful in-character fallback.
"""

from __future__ import annotations

import json
from typing import Generator, List, Optional, Tuple

import httpx

from huohuo.config import AppConfig, config
from huohuo.domain.ports.llm_port import LLMInferencePort
from huohuo.domain.services.emotion_service import EmotionParserService


class LlamaServerAdapter(LLMInferencePort):
    """Adapter for interacting with llama-server HTTP API."""

    def __init__(self, cfg: Optional[AppConfig] = None, endpoint: Optional[str] = None):
        self.cfg = cfg or config
        raw_endpoint = endpoint or self.cfg.llama_endpoint
        self.endpoint = raw_endpoint.rstrip("/")
        self.timeout = float(self.cfg.llama_timeout_detik)

    def is_healthy(self, timeout_detik: float = 3.0) -> bool:
        """Checks if llama-server is healthy and ready to accept inference requests."""
        try:
            with httpx.Client(timeout=timeout_detik) as client:
                res = client.get(f"{self.endpoint}/models")
                if res.status_code == 200:
                    return True
                if res.status_code == 503:
                    return False
        except Exception:
            return False
        return False

    def stream_chat(
        self,
        messages: List[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> Generator[str, None, None]:
        """Stream token-by-token completion from llama-server."""
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            # Pertahankan cache KV (prompt system HuoHuo) antar-permintaan supaya
            # pesan berikutnya tidak perlu prefill ulang -> latensi jauh lebih rendah.
            "keep_alive": -1,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield f"[kaget] Maaf Master, server inferensi sedang sibuk (status {response.status_code})."
                        return

                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception:
            # Fallback to in-character mock if offline
            yield from self._fallback_response(messages)

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """Stream token-by-token completion from llama-server."""
        yield from self.stream_chat(messages)

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        """Generate complete reply and extract emotion tag."""
        full_tokens = []
        for token in self.stream_chat(messages):
            full_tokens.append(token)

        full_text = "".join(full_tokens).strip()
        emotion, clean_text = EmotionParserService.parse(full_text)
        return emotion, clean_text

    def _fallback_response(self, messages: List[dict[str, str]]) -> Generator[str, None, None]:
        """In-character fallback when llama-server is offline."""
        last_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_msg = m.get("content", "").lower()
                break

        if any(w in last_msg for w in ("halo", "hai", "pagi", "siang", "malam")):
            balasan = (
                "[senyum] H-halo Master tersayang... aku HuoHuo. "
                "Kangen ya sama aku? Mau ngobrol apa hari ini?"
            )
        elif any(w in last_msg for w in ("sayang", "cinta", "waifu")):
            balasan = (
                "[goda] Hehe, gombal terus deh pacarku ini. Tapi aku suka kok. "
                "Sini peluk dulu biar tambah semangat."
            )
        elif any(w in last_msg for w in ("kafka", "firefly", "herta", "ruan mei")):
            balasan = (
                "[sebal] Hmph! Kenapa malah nyebut cewek lain sih? Kan yang nemenin kamu tiap malam di sini itu aku, Master! "
                "Jangan bikin pacarmu cemburu dong."
            )
        elif any(w in last_msg for w in ("headpat", "elus", "rambut")):
            balasan = (
                "[kaget] Eh... Master tiba-tiba elus kepalaku?! Rambutku jadi berantakan tahu... "
                "Tapi... rasanya hangat sih..."
            )
        else:
            balasan = (
                "[senyum] H-halo Master... A-aku HuoHuo. Ada yang bisa aku bantu, atau... "
                "kita ngobrol santai aja ya? D-dingin kalau sendirian..."
            )

        words = balasan.split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")
