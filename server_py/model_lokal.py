"""Penyedia inferensi LLM offline lokal menggunakan llama-cpp-python (GGUF).

Memuat berkas model GGUF dari folder model/ atau jalur di .env.
Mendukung streaming token (generator) yang cocok dengan rantai antrean server.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

AKAR = Path(__file__).resolve().parent.parent
FOLDER_MODEL = AKAR / "model"

# Singleton instance agar model tidak dimuat ulang di setiap panggilan chat
_LLM_INSTANCE = None
_MODEL_DIMUAT: str | None = None


class ModelLokalError(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


def cari_model(jalur_kandidat: str | None = None) -> Path | None:
    """Cari berkas .gguf di jalur kandidat atau pindai isi folder model/."""
    if jalur_kandidat:
        p = Path(jalur_kandidat)
        if not p.is_absolute():
            p = AKAR / p
        if p.is_file() and p.suffix.lower() == ".gguf":
            return p

    if FOLDER_MODEL.is_dir():
        # Prioritaskan berkas gguf yang ada
        berkas = sorted(FOLDER_MODEL.glob("*.gguf"), key=lambda f: f.stat().st_size)
        if berkas:
            return berkas[0]

    return None


def tersedia(jalur_kandidat: str | None = None) -> bool:
    """Apakah berkas model GGUF tersedia di disk."""
    return cari_model(jalur_kandidat) is not None


def muat_model(jalur_kandidat: str | None = None, threads: int = 4, n_ctx: int = 8192):
    """Muat model GGUF ke memori jika belum dimuat."""
    global _LLM_INSTANCE, _MODEL_DIMUAT

    jalur = cari_model(jalur_kandidat)
    if jalur is None:
        raise ModelLokalError(
            "Tidak ditemukan berkas model .gguf di folder model/.\n"
            "Jalankan: python scripts/unduh_model.py atau letakkan berkas .gguf ke folder model/."
        )

    if _LLM_INSTANCE is not None and _MODEL_DIMUAT == str(jalur):
        try:
            if _LLM_INSTANCE.n_ctx() >= n_ctx:
                return _LLM_INSTANCE
            del _LLM_INSTANCE
            _LLM_INSTANCE = None
        except Exception:
            return _LLM_INSTANCE

    try:
        from llama_cpp import Llama
    except ImportError:
        raise ModelLokalError(
            "Paket llama-cpp-python belum terpasang. Pasang jalur dependensi proyek:\n"
            "  .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
            "(baris torch/CPU-nya harus lebih dulu -- lihat catatan di bagian atas berkas itu)"
        )

    print(f"Memuat model lokal GGUF: {jalur.name} ({threads} threads, ctx={n_ctx})...")
    try:
        _LLM_INSTANCE = Llama(
            model_path=str(jalur),
            n_ctx=n_ctx,
            n_threads=threads,
            n_batch=512,
            verbose=False,
        )
        _MODEL_DIMUAT = str(jalur)
        print(f"Model lokal {jalur.name} berhasil dimuat ke memori.")
        return _LLM_INSTANCE
    except Exception as err:
        _LLM_INSTANCE = None
        _MODEL_DIMUAT = None
        raise ModelLokalError(f"Gagal memuat model GGUF {jalur.name}: {err}")


def alir(
    pesan: list[dict[str, str]],
    jalur_kandidat: str | None = None,
    threads: int = 4,
    n_ctx: int = 8192,
    max_tokens: int = 350,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Stream token respons dari model lokal GGUF."""
    llm = muat_model(jalur_kandidat=jalur_kandidat, threads=threads, n_ctx=n_ctx)

    # Tidak ada suntikan prompt di sini: isi system prompt adalah urusan
    # memori.gabung_system_lokal(), supaya penyedia mana pun (CPU maupun vulkan)
    # membaca pesan yang SAMA. Dulu blok "[PANDUAN EKSPRESI WAJAH LIVE2D]" ditambahkan
    # di sini dan instruksi yang sama sudah ada di system prompt -- dua sumber
    # kebenaran, dan yang kedua hanya menambah token prompt yang harus dihitung ulang.
    pesan_terformat = pesan

    try:
        respon = llm.create_chat_completion(
            messages=pesan_terformat,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|eot_id|>", "<|end_of_text|>", "</s>", "User:", "Master:"],
        )

        for chunk in respon:
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            teks = delta.get("content", "")
            if teks:
                yield teks
    except Exception as err:
        raise ModelLokalError(f"Kesalahan inferensi model lokal: {err}")
