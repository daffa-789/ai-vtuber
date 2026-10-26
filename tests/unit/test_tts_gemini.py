"""Test pemetaan emosi->gaya bicara dan rantai fallback TTS.

Tidak ada jaringan di sini: Gemini diuji lewat httpx yang ditambal, dan rantai
TTS diuji dengan backend palsu. Yang dijamin adalah kontraknya -- gaya ikut
terkirim, dan kegagalan Gemini tidak membuat HuoHuo bisu.
"""

from __future__ import annotations

import base64
from typing import Optional

import pytest

from huohuo.adapters import gemini_tts_adapter
from huohuo.adapters.gemini_tts_adapter import GeminiTTSAdapter, _cari_audio, _rapikan_wav
from huohuo.adapters.tts_bertingkat import TTSBertingkat
from huohuo.domain.services.gaya_suara import PetaGayaSuara
from huohuo.domain.value_objects.emotion import EmotionTag


# ── pemetaan gaya ────────────────────────────────────────────────────────────

def test_setiap_emosi_resmi_punya_gaya():
    for tag in EmotionTag:
        gaya = PetaGayaSuara.gaya_dari_emosi(tag.value)
        assert gaya and isinstance(gaya, str), f"{tag.value} tidak punya gaya"


def test_emosi_berbeda_menghasilkan_gaya_berbeda():
    gaya = {PetaGayaSuara.gaya_dari_emosi(t.value) for t in EmotionTag}
    assert len(gaya) == len(EmotionTag), "beberapa emosi pakai gaya yang sama"


def test_emosi_tidak_dikenal_jatuh_ke_netral():
    assert PetaGayaSuara.gaya_dari_emosi("euforia") == PetaGayaSuara.gaya_dari_emosi(None)
    assert PetaGayaSuara.gaya_dari_emosi("") == PetaGayaSuara.gaya_dari_emosi("netral")


def test_emosi_kuat_membawa_warna_dasar_huohuo():
    gaya = PetaGayaSuara.gaya_dari_emosi("goda")
    assert "shy" in gaya
    assert "teasing" in gaya
    # netral tidak dobel: cukup "calm and natural"
    assert PetaGayaSuara.gaya_dari_emosi("netral") == "calm and natural"


def test_daftar_gaya_terbuka_untuk_dokumentasi():
    assert set(PetaGayaSuara.daftar_gaya()) == {t.value for t in EmotionTag}


# ── parsing respons Gemini ───────────────────────────────────────────────────

def test_cari_audio_menemukan_di_struktur_sebenarnya():
    """Dokumentasi menyebut jalur lain; ini bentuk respons yang sungguh datang."""
    respons = {
        "id": "x", "status": "completed",
        "steps": [{"type": "model_output", "content": [
            {"type": "audio", "data": base64.b64encode(b"RIFF" + b"\0" * 5000).decode()}
        ]}],
    }
    assert _cari_audio(respons) is not None


def test_cari_audio_mengabaikan_string_pendek():
    assert _cari_audio({"steps": [{"content": [{"text": "halo"}]}]}) is None


def test_wav_dipertahankan_dan_pcm_dibungkus():
    wav = b"RIFF" + b"\0" * 100
    assert _rapikan_wav(wav) == wav
    pcm = _rapikan_wav(b"\x01\x02" * 2000)
    assert pcm is not None and pcm[:4] == b"RIFF"
    assert _rapikan_wav(b"") is None


# ── adapter Gemini ───────────────────────────────────────────────────────────

class Cfg:
    def __init__(self, key="kunci-palsu", model="gemini-3.8-flash-tts", voice="Kore"):
        self.gemini_api_key = key
        self.gemini_tts_model = model
        self.gemini_tts_voice = voice
        self.gemini_tts_gaya = "calm and natural"
        self.gemini_timeout_detik = 5


def test_tanpa_key_tidak_menyentuh_jaringan(monkeypatch):
    def dilarang(*a, **k):
        raise AssertionError("tidak boleh HTTP tanpa key")

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", dilarang)
    ad = GeminiTTSAdapter(cfg=Cfg(key=""))
    assert ad.tersedia is False
    assert ad.synthesize("halo") is None


def test_gaya_terkirim_dalam_permintaan(monkeypatch):
    terkirim = {}

    class Respons:
        status_code = 200

        def json(self):
            return {"steps": [{"content": [{"data": base64.b64encode(
                b"RIFF" + b"\0" * 5000).decode()}]}]}

    class Klien:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            terkirim["body"] = json
            terkirim["headers"] = headers
            return Respons()

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", Klien)
    hasil = GeminiTTSAdapter(cfg=Cfg()).synthesize("[goda] halo", gaya="playful and teasing")
    assert hasil and hasil[:4] == b"RIFF"

    anotasi = terkirim["body"]["input"][0]["content"][0]["annotations"][0]
    assert anotasi["type"] == "speech_metadata"
    assert anotasi["style"] == "playful and teasing"
    assert terkirim["body"]["generation_config"]["speech_config"][0]["voice"] == "Kore"
    # key hanya lewat header, tidak pernah masuk body
    assert "kunci-palsu" not in str(terkirim["body"])
    assert terkirim["headers"]["x-goog-api-key"] == "kunci-palsu"


def test_tag_emosi_tidak_ikut_dibaca_oleh_tts(monkeypatch):
    """Tag [goda] untuk wajah, bukan untuk dibacakan."""
    terkirim = {}

    class Respons:
        status_code = 200

        def json(self):
            return {"steps": [{"content": [{"data": base64.b64encode(
                b"RIFF" + b"\0" * 5000).decode()}]}]}

    class Klien:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            terkirim["teks"] = json["input"][0]["content"][0]["text"]
            return Respons()

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", Klien)
    GeminiTTSAdapter(cfg=Cfg()).synthesize("[goda] halo Master")
    assert "[goda]" not in terkirim["teks"]
    assert "halo Master" in terkirim["teks"]


def test_http_error_kembalikan_none_bukan_exception(monkeypatch):
    class Respons:
        status_code = 403

        def json(self):
            return {}

    class Klien:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return Respons()

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", Klien)
    assert GeminiTTSAdapter(cfg=Cfg()).synthesize("halo") is None


def test_error_jaringan_ditangkap(monkeypatch):
    class Klien:
        def __init__(self, *a, **k):
            raise ConnectionError("offline")

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", Klien)
    assert GeminiTTSAdapter(cfg=Cfg()).synthesize("halo") is None


def test_pesan_error_tidak_menyebut_key(monkeypatch, capsys):
    class Klien:
        def __init__(self, *a, **k):
            raise RuntimeError("boom rahasia")

    monkeypatch.setattr(gemini_tts_adapter.httpx, "Client", Klien)
    GeminiTTSAdapter(cfg=Cfg()).synthesize("halo")
    keluar = capsys.readouterr().out
    assert "kunci-palsu" not in keluar


# ── rantai fallback ──────────────────────────────────────────────────────────

class TTSSelalu:
    def __init__(self, hasil: bytes, nama="ok"):
        self.hasil, self.nama, self.dipanggil = hasil, nama, []

    def synthesize(self, text, gaya=None):
        self.dipanggil.append(gaya)
        return self.hasil


class TTSGagal:
    def __init__(self, exception=None):
        self.exception = exception
        self.dipanggil = 0

    def synthesize(self, text, gaya=None):
        self.dipanggil += 1
        if self.exception:
            raise self.exception
        return None


def test_rantai_pakai_yang_pertama_berhasil():
    utama = TTSSelalu(b"RIFFgemini")
    cadangan = TTSSelalu(b"RIFFpiper")
    rantai = TTSBertingkat([utama, cadangan])
    assert rantai.synthesize("halo") == b"RIFFgemini"
    assert cadangan.dipanggil == []


def test_cadangan_dipakai_saat_utama_kosong():
    utama = TTSGagal()
    cadangan = TTSSelalu(b"RIFFpiper")
    rantai = TTSBertingkat([utama, cadangan])
    assert rantai.synthesize("halo") == b"RIFFpiper"
    assert utama.dipanggil == 1


def test_cadangan_dipakai_saat_utama_melempar():
    utama = TTSGagal(exception=RuntimeError("meledak"))
    cadangan = TTSSelalu(b"RIFFpiper")
    assert TTSBertingkat([utama, cadangan]).synthesize("halo") == b"RIFFpiper"


def test_gaya_diteruskan_ke_setiap_backend():
    utama = TTSGagal()
    cadangan = TTSSelalu(b"RIFFpiper")
    TTSBertingkat([utama, cadangan]).synthesize("halo", gaya="playful")
    assert cadangan.dipanggil == ["playful"]


def test_semua_gagal_mengembalikan_none():
    assert TTSBertingkat([TTSGagal(), TTSGagal()]).synthesize("halo") is None


def test_backend_lama_tanpa_param_gaya_tetap_jalan():
    """Simulasi adapter pihak ketiga yang belum tahu soal `gaya`."""
    class Kuno:
        def synthesize(self, text):
            return b"RIFFkuno"

    assert TTSBertingkat([Kuno()]).synthesize("halo", gaya="x") == b"RIFFkuno"
