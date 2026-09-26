"""Engine TTS cloud: Gemini generateContent dengan responseModalities AUDIO.

Isinya loop failover yang dulu hidup di app.py::tts, dipindah apa adanya. Yang
berubah hanya rumahnya -- "400 tidak layak dicoba ke model lain" dan urutan
utama -> cadangan -> model lama dipertahankan karena keduanya lahir dari kegagalan
yang terukur, bukan selera.

Engine ini satu-satunya yang butuh GEMINI_API_KEY. Kuota tingkat gratis 20
permintaan/HARI untuk semua model, jadi punya engine lokal di sampingnya itu
bukan kemewahan.
"""

from __future__ import annotations

import base64
import sys

import gemini
import konfig
from wav import laju_kanal, pcm_ke_wav, sudah_wav

NAMA = "gemini"


def daftar_model() -> list[str]:
    # Model lama masih dilayani di belakang dua model 3.8: kalau keduanya 503,
    # lebih baik terdengar suara daripada tidak sama sekali.
    return list(dict.fromkeys([konfig.TTS_MODEL, *konfig.TTS_CADANGAN, "gemini-2.5-flash-preview-tts"]))


def tersedia() -> bool:
    return bool(konfig.KUNCI)


def butuh_kunci() -> bool:
    return True


def label() -> str:
    return f"{konfig.TTS_MODEL}/{konfig.TTS_SUARA}"


def sintesis(teks: str, sisa: float = 0.0) -> bytes:
    """WAV utuh. Melempar gemini.Ditolak terakhir kalau semua model gagal.

    `sisa` = detik anggaran yang masih dimiliki pekerjaan ini (diteruskan
    jalur_suara). SATU panggilan harus selesai di dalam sisa itu, bukan memakai
    angka sendiri: dulu timeout-nya 25 dtk sementara penunggunya menyerah di 20, dan
    tiga model berurutan bisa memegang satu-satunya pekerja ~75 dtk untuk hasil yang
    sudah tidak ditunggu siapa pun.
    """
    galat_terakhir = ""
    anggaran = int(min(sisa or 15, 15)) or 15
    for model in daftar_model():
        try:
            hasil = gemini.generate(
                model, gemini.body_tts(teks, konfig.TTS_SUARA), konfig.KUNCI, timeout=anggaran
            )
            audio = gemini.audio_dari(hasil)
            if not audio:
                galat_terakhir = f"{model}: tidak ada audio"
                continue
            bin = base64.b64decode(audio[1])
            laju, kanal = laju_kanal(audio[0])
            # Jangan membungkus ulang yang sudah berheader -- itulah penyebab
            # "suara hilang diam-diam saat model diganti" yang dicatat di wav.py.
            return bin if sudah_wav(bin) else pcm_ke_wav(bin, laju, kanal)
        except gemini.Ditolak as err:
            galat_terakhir = err.pesan
            if not err.layak_dicoba:
                raise  # 400 = permintaannya yang salah, bukan modelnya
            print(f"TTS {model} ditolak: {err.pesan[:90]}", file=sys.stderr)

    raise gemini.Ditolak(galat_terakhir or "semua model TTS gagal")
