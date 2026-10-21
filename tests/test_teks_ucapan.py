"""Unit test untuk teks_ucapan dan sentence_splitter."""

from huohuo.core.sentence_splitter import potong_kalimat
from huohuo.core.teks_ucapan import (
    bersihkan,
    bersihkan_per_kalimat,
    buang_narasi,
)


def test_bersihkan_markdown():
    # Menghapus penekanan markdown agar tidak dibacakan "bintang"
    teks = "Halo **Master**, aku *senang* banget hari ini!"
    assert bersihkan(teks) == "Halo Master, aku senang banget hari ini!"


def test_bersihkan_kode_dan_backtick():
    teks = "Ketik perintah `python main.py` di terminal."
    assert bersihkan(teks) == "Ketik perintah python main.py di terminal."


def test_bersihkan_dash_panjang_ke_koma():
    teks = "HuoHuo—waifu kamu—selalu ada."
    assert bersihkan(teks) == "HuoHuo, waifu kamu, selalu ada."


def test_buang_narasi():
    teks = 'Halo Master! "sambil tersenyum manis" Gimana kabarmu?'
    assert buang_narasi(teks) == "Halo Master! Gimana kabarmu?"


def test_potong_kalimat_desimal_tidak_terpotong():
    teks = "Versi 1.0 sudah dirilis. Nilai pi adalah 3.14 ya."
    hasil = potong_kalimat(teks)
    assert len(hasil.kalimat) == 2
    assert "3.14" in hasil.kalimat[1]


def test_bersihkan_per_kalimat():
    teks = "Halo **Master**. *Ini* kalimat kedua!"
    hasil = bersihkan_per_kalimat(teks)
    assert hasil == ["Halo Master.", "Ini kalimat kedua!"]
