"""Klien inferensi LLM untuk Silver Wolf (llama-server / OpenAI-compatible API).

Mendukung:
- Pemantauan kesehatan (health check) dengan deteksi status 503 ("Loading model").
- Batas waktu tunggu respons 120 detik (sesuai invarian proyek M8/M11).
- Streaming token balasan dengan ekstraksi tag emosi secara realtime.
- Mode fallback mandiri (in-character mock) bila server lokal belum dinyalakan.
"""

from __future__ import annotations

import json
from typing import Generator, List, Optional, Tuple

import httpx

from silverwolf.config import AppConfig, config
from silverwolf.core.emotion_parser import extract_emotion


class LlamaClient:
    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config
        self.endpoint = self.cfg.llama_endpoint.rstrip("/")
        self.timeout = float(self.cfg.llama_timeout_detik)

    def is_healthy(self, timeout_detik: float = 3.0) -> bool:
        """Memeriksa apakah server lokal aktif dan siap melayani permintaan."""
        try:
            # Coba endpoint /health bawaan llama-server atau /v1/models
            with httpx.Client(timeout=timeout_detik) as client:
                res = client.get(f"{self.endpoint}/models")
                if res.status_code == 200:
                    return True
                if res.status_code == 503:
                    # Model masih dalam proses pemuatan ke RAM/VRAM
                    return False
        except Exception:
            return False
        return False

    def stream_chat(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> Generator[str, None, None]:
        """Streaming chat completion token demi token dari llama-server."""
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
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
        except Exception as e:
            # Fallback ke balasan karakter jika llama-server offline
            yield from self._fallback_response(messages)

    def generate(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> Tuple[Optional[str], str]:
        """Menghasilkan balasan utuh dan mengekstrak tag emosi ([senyum], [goda], dll)."""
        full_tokens = []
        for token in self.stream_chat(messages, temperature=temperature, max_tokens=max_tokens):
            full_tokens.append(token)

        full_text = "".join(full_tokens).strip()
        hasil = extract_emotion(full_text)
        return hasil.emotion, hasil.clean_text

    def _fallback_response(self, messages: List[dict]) -> Generator[str, None, None]:
        """Balasan fallback in-character Silver Wolf saat server lokal offline."""
        last_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_msg = m.get("content", "").lower()
                break

        if any(w in last_msg for w in ("halo", "hai", "pagi", "siang", "malam")):
            balasan = (
                "[senyum] Halo Master tersayang! Aku Silver Wolf, pacar gamer kamu. "
                "Kangen ya sama aku? Mau ngobrol atau mabar game apa hari ini? \"sambil tersenyum manis\""
            )
        elif any(w in last_msg for w in ("sayang", "cinta", "waifu")):
            balasan = (
                "[goda] Hehe, gombal terus deh pacarku ini. Tapi aku suka kok. "
                "Sini peluk dulu biar tambah semangat. \"sambil menatap manja\""
            )
        elif any(w in last_msg for w in ("kafka", "firefly", "herta", "ruan mei")):
            balasan = (
                "[sebal] Hmph! Kenapa malah nyebut cewek lain sih? Kan yang nemenin kamu tiap malam di sini itu aku, Master! "
                "Jangan bikin pacarmu cemburu dong. \"sambil cemberut lucu\""
            )
        else:
            balasan = (
                "[goda] Aku dengar kok Master. Mau hacking sesuatu bareng atau lanjut main game? "
                "Apa pun yang kamu mau, aku temani sampai tamat!"
            )

        # Simulasikan streaming pendek
        words = balasan.split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")


# Singleton client bawaan
llama = LlamaClient()
