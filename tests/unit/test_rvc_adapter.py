"""Test kontrak aman RVCAdapter.

Adapter ini boleh MENYALAKAN proses layanan RVC, jadi risiko terbesarnya adalah
membuat aplikasi menggantung atau crash. Yang diuji di sini adalah kontrak
fallback-nya, bukan kualitas suaranya. Tidak ada proses nyata atau jaringan
yang disentuh.
"""

from pathlib import Path

import pytest

from huohuo.adapters import rvc_adapter
from huohuo.adapters.rvc_adapter import RVCAdapter


class Cfg:
    """Stub AppConfig; adapter hanya membaca atribut, tidak menulis."""

    def __init__(self, **over):
        self.rvc_aktif = over.get("rvc_aktif", True)
        self.rvc_service_url = "http://127.0.0.1:1/"  # port mustahil -> selalu mati
        self.rvc_timeout_detik = 2
        self.rvc_auto_mulai = over.get("rvc_auto_mulai", True)
        self.rvc_siap_detik = over.get("rvc_siap_detik", 3)
        self.rvc_python = Path(over.get("rvc_python", "tidak-ada/python.exe"))
        self.rvc_skrip = Path("rvc/rvc_service.py")


MASUKAN = b"wav-asli-piper"


def test_rvc_nonaktif_mengembalikan_audio_asli_tanpa_http(monkeypatch):
    def dilarang(*a, **k):
        raise AssertionError("tidak boleh menyentuh HTTP saat RVC nonaktif")

    monkeypatch.setattr(rvc_adapter.httpx, "Client", dilarang)
    assert RVCAdapter(Cfg(rvc_aktif=False)).convert(MASUKAN) == MASUKAN


def test_audio_kosong_dilewatkan():
    assert RVCAdapter(Cfg()).convert(b"") == b""


def test_layanan_mati_dan_auto_mulai_off_tanpa_mencoba_spawn(monkeypatch):
    dipanggil = {"spawn": 0}

    def pseudo_popen(*a, **k):
        dipanggil["spawn"] += 1
        raise AssertionError("tidak boleh menyalakan proses saat AUTO_MULAI=tidak")

    monkeypatch.setattr(rvc_adapter.subprocess, "Popen", pseudo_popen)
    ad = RVCAdapter(Cfg(rvc_auto_mulai=False))
    assert ad.convert(MASUKAN) == MASUKAN
    assert dipanggil["spawn"] == 0


def test_rvc_env_tidak_ada_fallback_cepat_tanpa_menggantung(monkeypatch):
    """Python rvc-env tidak ditemukan -> harus langsung menyerah, bukan menunggu."""
    monkeypatch.setattr(
        rvc_adapter.subprocess, "Popen",
        lambda *a, **k: pytest.fail("tidak boleh spawn kalau python tidak ada"),
    )
    ad = RVCAdapter(Cfg(rvc_auto_mulai=True, rvc_python="tidak-ada/python.exe"))
    assert ad.convert(MASUKAN) == MASUKAN


def test_spawn_gagal_ditangkap_dan_fallback(monkeypatch, tmp_path):
    """Python & skrip ADA, tapi Popen gagal -> harus fallback, bukan raise."""
    python_palsu = tmp_path / "python.exe"
    python_palsu.write_bytes(b"")
    skrip = tmp_path / "rvc_service.py"
    skrip.parent.mkdir(parents=True, exist_ok=True)
    skrip.write_text("", encoding="utf-8")

    def gagal(*a, **k):
        raise OSError("akses ditolak")

    monkeypatch.setattr(rvc_adapter.subprocess, "Popen", gagal)
    ad = RVCAdapter(Cfg(rvc_siap_detik=2))
    ad.cfg.rvc_python = python_palsu
    ad.cfg.rvc_skrip = skrip
    assert ad.convert(MASUKAN) == MASUKAN


def test_konversi_berhasil_memakai_hasil_layanan(monkeypatch):
    class Respons:
        status_code = 200
        content = b"wav-timbre-huohuo"

    class Klien:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return Respons()

        def post(self, url, content=None, headers=None):
            return Respons()

    monkeypatch.setattr(rvc_adapter.httpx, "Client", Klien)
    hasil = RVCAdapter(Cfg()).convert(MASUKAN)
    assert hasil == b"wav-timbre-huohuo"
    assert hasil != MASUKAN


def test_gagal_post_dikembalikan_audio_asli(monkeypatch):
    class Klien:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            raise ConnectionError("layanan mati")

        def post(self, url, content=None, headers=None):
            raise ConnectionError("layanan mati di tengah jalan")

    monkeypatch.setattr(rvc_adapter.httpx, "Client", Klien)
    monkeypatch.setattr(rvc_adapter.subprocess, "Popen",
                        lambda *a, **k: pytest.fail("tidak boleh spawn di test ini"))
    ad = RVCAdapter(Cfg(rvc_auto_mulai=False))
    assert ad.convert(MASUKAN) == MASUKAN
