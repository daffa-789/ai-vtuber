"""Pemanggil Gemini API lewat REST, tanpa SDK.

Sengaja stdlib-only: tidak ada yang perlu di-install, dan bentuk permintaannya
persis yang dikirim @google/genai di sisi Node, jadi kedua implementasi bisa
dibandingkan apel-per-apel.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from typing import Iterator

ALAMAT = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 15


class Ditolak(Exception):
    """Penolakan API, sudah dibersihkan dari tumpukan JSON Google."""

    def __init__(self, pesan: str, status: int = 0):
        super().__init__(pesan)
        self.pesan = pesan
        self.status = status

    @property
    def layak_dicoba(self) -> bool:
        """503/429 itu antrean sementara -> layak dicoba ke model lain.

        400 berarti permintaannya yang salah, jadi berpindah model cuma membuang
        satu panggilan lagi.
        """
        return bool(
            re.search(r"503|429|timeout|timed out|UNAVAILABLE|RESOURCE_EXHAUSTED|high demand|rate", self.pesan, re.I)
        )


def bersihkan_error(pesan: str) -> str:
    """Google menumpuk JSON error di dalam string message, sampai dua lapis."""
    for _ in range(3):
        try:
            dalam = json.loads(pesan).get("error")
        except (ValueError, AttributeError):
            break
        if not dalam:
            break
        pesan = dalam if isinstance(dalam, str) else (dalam.get("message") or pesan)
    return re.sub(r"\s+", " ", pesan).strip()


def _kirim(model: str, aksi: str, body: dict, key: str, query: str = "", timeout: int = TIMEOUT):
    url = f"{ALAMAT}/{model}:{aksi}?key={key}{query}"
    perm = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        return urllib.request.urlopen(perm, timeout=timeout)
    except urllib.error.HTTPError as err:
        raise Ditolak(bersihkan_error(err.read().decode("utf-8", "replace")), err.code) from err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise Ditolak(f"{model} tidak bisa dihubungi: {err}") from err


def generate(model: str, body: dict, key: str) -> dict:
    with _kirim(model, "generateContent", body, key) as resp:
        return json.loads(resp.read().decode("utf-8"))


def alir(model: str, body: dict, key: str) -> Iterator[str]:
    """Buka aliran SEKARANG juga dan kembalikan iterator potongan teks.

    Ini bukan generator: kalau dipanggil sebagai generator, koneksi baru terbuka
    saat iterasi pertama, jadi kegagalan model pertama tidak tertangkap di
    percobaan pertama dan fallback model cadangan tidak pernah jalan.
    """
    return _potongan(_kirim(model, "streamGenerateContent", body, key, query="&alt=sse"), model)


def _potongan(resp, model: str) -> Iterator[str]:
    """`chunk.text` di SDK cuma menggabungkan semua part, jadi begitu juga di sini."""
    with resp:
        for baris in resp:
            baris = baris.decode("utf-8", "replace").strip()
            if not baris.startswith("data:"):
                continue
            try:
                chunk = json.loads(baris[5:].strip())
            except ValueError:
                continue
            for calon in chunk.get("candidates") or []:
                for part in (calon.get("content") or {}).get("parts") or []:
                    teks = part.get("text")
                    if teks:
                        yield teks
                # Saat kuota harian habis, Google menutup aliran TANPA event error:
                # status HTTP sudah 200, jadi satu-satunya tandanya finishReason.
                # Tanpa ini jawaban setengah kalimat tampil seolah memang begitu.
                akhir = calon.get("finishReason")
                if akhir and akhir != "STOP":
                    print(f"aliran {model} berhenti lebih awal: {akhir}", file=sys.stderr)


def teks_dari(hasil: dict) -> str:
    for calon in hasil.get("candidates") or []:
        gabung = "".join(
            p.get("text", "") for p in (calon.get("content") or {}).get("parts") or []
        )
        if gabung:
            return gabung
    return ""


def audio_dari(hasil: dict):
    """Inline data pertama, biasanya (mimeType, bytes). Model transcribe tidak punya."""
    for calon in hasil.get("candidates") or []:
        for part in (calon.get("content") or {}).get("parts") or []:
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return data.get("mimeType", ""), data["data"]
    return None


def transkrip_dari(hasil: dict) -> str:
    """Model transcribe menaruh hasilnya di audioTranscription, BUKAN di .text."""
    for calon in hasil.get("candidates") or []:
        for part in (calon.get("content") or {}).get("parts") or []:
            t = (part.get("audioTranscription") or {}).get("text")
            if t:
                return t.strip()
            if part.get("text"):
                return part["text"].strip()
    return ""


def body_chat(riwayat: list, system: str, suhu: float = 0.9, maks_token: int = 1200) -> dict:
    # maks_token harus JAUH lebih besar dari teks yang diinginkan: model berpikir dulu
    # (thoughtsTokenCount terukur 450 untuk satu sapaan pendek persona Elaina), dan kalau
    # plafonnya 400 balasan terpotong di tengah kalimat dengan finishReason tetap STOP.
    return {
        "contents": [{"role": r["role"], "parts": r["parts"]} for r in riwayat],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"temperature": suhu, "maxOutputTokens": maks_token},
    }


def body_tts(teks: str, suara: str) -> dict:
    return {
        "contents": [{"role": "user", "parts": [{"text": teks}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": suara}}},
        },
    }


def body_audio(b64: str, mime: str = "audio/wav") -> dict:
    return {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": mime, "data": b64}}]}]}
