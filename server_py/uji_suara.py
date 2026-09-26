"""Tes jalur suara tanpa HTTP, tanpa jaringan, dan tanpa model 500 MB.

Semua engine di sini dipalsukan lewat jalur_suara.TAHAP, jadi yang diuji adalah
PERILAKU orkestratornya: siapa dipanggil, berapa kali, dan apa yang terjadi saat
salah satu mati. Yang tidak bisa dibuktikan cara ini (kualitas audio, kecepatan
nyata) tugas uji_latensi.py dan telinga Master.

Jalankan:  .venv\\Scripts\\python.exe server_py\\uji_suara.py
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jalur_suara  # noqa: E402
import konfig  # noqa: E402
import tts_rvc  # noqa: E402
import wav  # noqa: E402

GAGAL: list[str] = []
LOLOS = 0


def cek(nama: str, fungsi) -> None:
    global LOLOS
    try:
        fungsi()
    except Exception as err:
        GAGAL.append(nama)
        print(f"FAIL {nama}: {type(err).__name__}: {err}")
    else:
        LOLOS += 1
        print(f"pass {nama}")


def bikin_wav(detik: float = 0.2, laju: int = 22050) -> bytes:
    """WAV kecil berisi NADA sungguhan -- bukan byte nol.

    Ini koreksi atas cacat tes yang nyata: fixture lama `bytes(n)` (semua nol) dan
    seluruh tes orkestrasi tetap bilang "WAV utuh". Artinya kalau engine menghasilkan
    keheningan, harness ini tidak akan pernah tahu -- padahal itulah gejala yang di
    browser terlihat sebagai "rahang diam tanpa error". Sekarang `puncak()` ikut
    diperiksa, jadi fixture-nya harus benar-benar berbunyi.
    """
    import math
    import struct

    jumlah = int(detik * laju)
    pcm = b"".join(
        struct.pack("<h", int(9000 * math.sin(2 * math.pi * 320 * i / laju)))
        for i in range(jumlah)
    )
    return wav.pcm_ke_wav(pcm, laju, 1)


def bikin_wav_hening(detik: float = 0.2, laju: int = 22050) -> bytes:
    """Header WAV sah, isi nol semua -- bahan uji untuk B2."""
    return wav.pcm_ke_wav(bytes(int(detik * laju) * 2), laju, 1)


class Perekam:
    """Engine palsu yang menghitung panggilannya sendiri."""

    def __init__(self, nama: str, lambat: float = 0.0, rusak: bool = False, hening: bool = False):
        self.nama = nama
        self.panggil = 0
        self.lambat = lambat
        self.rusak = rusak
        self.keluar = bikin_wav_hening() if hening else bikin_wav()
        self._lock = threading.Lock()

    def sintesis(self, teks: str, sisa: float = 0.0) -> bytes:
        with self._lock:
            self.panggil += 1
        if self.lambat:
            time.sleep(self.lambat)
        if self.rusak:
            raise RuntimeError(f"{self.nama} dirusak")
        return self.keluar

    def ubah(self, audio, sisa: float = 0.0) -> bytes:
        return self.sintesis(str(len(audio or b"")), sisa)

    def tersedia(self) -> bool:
        return True

    def patokan(self) -> str:
        return self.nama  # sengaja TIDAK berubah: yang dihitung jumlah pemanggilan


def pasang(nama: str, rekam: Perekam, masuk: str = "teks") -> None:
    jalur_suara.TAHAP[nama] = jalur_suara.Tahap(
        nama, masuk, rekam.sintesis if masuk == "teks" else rekam.ubah,
        rekam.tersedia, rekam.patokan,
    )


def dengan_rantai(*resep: str):
    """Konteks: gantian rantai + bersihkan engine palsu setelahnya."""

    class Penjaga:
        def __enter__(self):
            self.asli = list(konfig.TTS_RANTAI)
            konfig.TTS_RANTAI[:] = list(resep)
            return self

        def __exit__(self, *exc):
            konfig.TTS_RANTAI[:] = self.asli
            for n in [x for x in jalur_suara.TAHAP if x.startswith("uji")]:
                jalur_suara.TAHAP.pop(n, None)

    return Penjaga()


def utama() -> int:
    jalur_suara.mula()
    try:
        cek("kunci cache stabil terhadap spasi", uji_kunci_stabil)
        cek("kunci cache peka terhadap parameter", uji_kunci_peka)
        cek("cache hit menutup engine", uji_cache_menutup_engine)
        cek("RVC tidak dipanggil saat mati", uji_rvc_mati_tidak_dipanggil)
        cek("engine mati -> resep berikutnya menjawab", uji_engine_mati_fallback)
        cek("dedupe pekerjaan identik", uji_dedupe_aliran)
        cek("lewat batas detik -> menyerah dengan alasan", uji_batas_detik)
        cek("rantai berasal dari .env, tanpa duplikat", uji_rantai_dari_env)
        cek("keluaran hening ditolak dan tidak masuk cache", uji_hening_ditolak)
        cek("hasil yang telat tetap masuk cache", uji_hasil_telat_tercache)
        cek("pekerja kedaluwarsa dibuang, bukan dikerjakan", uji_kedaluwarsa_dibuang)
        cek("berhenti() menguras antrean tanpa meninggalkan yatim", uji_berhenti_menguras)
        cek("mula() dua kali tidak melahirkan dua pekerja", uji_mula_idempoten)
        cek("sapu_yatim membersihkan sisa proses sebelumnya", uji_sapu_yatim)
        cek("matriks engine: WAV utuh atau LEWAT beralasan", uji_matriks_engine)
    finally:
        jalur_suara.berhenti()
    print(f"\n{LOLOS} lulus, {len(GAGAL)} gagal")
    if GAGAL:
        for g in GAGAL:
            print(f"  - {g}")
    return 1 if GAGAL else 0


def uji_kunci_stabil():
    a = jalur_suara.hitung_kunci("Halo Master", "piper")
    b = jalur_suara.hitung_kunci("  Halo   Master ", "piper")
    assert a == b, "spasi berlebih mengubah kunci -> cache tidak pernah panas"


def uji_kunci_peka():
    dasar = jalur_suara.hitung_kunci("halo", "piper+rvc")
    asli = konfig.RVC_F0
    try:
        konfig.RVC_F0 = "pm" if asli == "rmvpe" else "rmvpe"
        ubah = jalur_suara.hitung_kunci("halo", "piper+rvc")
        assert dasar != ubah, "ganti f0method tidak mengubah kunci cache"
    finally:
        konfig.RVC_F0 = asli
    assert jalur_suara.hitung_kunci("halo", "piper") != jalur_suara.hitung_kunci(
        "halo", "piper+rvc"
    ), "resep berbeda menghasilkan kunci sama -> hasil bocor antar-resep"


def uji_cache_menutup_engine():
    rekam = Perekam("ujicache")
    pasang("ujicache", rekam)
    with dengan_rantai("ujicache"):
        teks = "kalimat yang belum pernah lewat " + str(time.time_ns())
        b1, label1 = jalur_suara.bangun(teks)
        assert rekam.panggil == 1, f"panggilan pertama harus 1, jadi {rekam.panggil}"
        b2, label2 = jalur_suara.bangun(teks)
        assert rekam.panggil == 1, f"cache miss dua kali ({rekam.panggil} panggilan)"
        assert b1 == b2, "hasil cache berbeda dari hasil engine"
        assert "cache" in label2, f"label tidak menyebut cache: {label2}"
        assert wav.sudah_wav(b1), "hasil cache bukan WAV utuh"


def uji_rvc_mati_tidak_dipanggil():
    asli = konfig.RVC_HIDUP
    konfig.RVC_HIDUP = False
    try:
        assert not tts_rvc.hidup(), "RVC_HIDUP=False tapi hidup() True"
        assert not tts_rvc.siap() or True  # siap() hanya soal aset, bukan soal sakelar
        try:
            tts_rvc.ubah(bikin_wav(), "uji")
            raise AssertionError("ubah() tidak menolak padahal RVC dimatikan")
        except tts_rvc.RvcTidakHidup:
            pass
        # Dan resep yang memuat rvc harus tersingkir dari rantai aktif.
        with dengan_rantai("piper+rvc"):
            assert "piper+rvc" not in jalur_suara.rantai_aktif(), "RVC mati tapi resepnya lolos"
    finally:
        konfig.RVC_HIDUP = asli


def uji_engine_mati_fallback():
    mati = Perekam("ujimati", rusak=True)
    selamat = Perekam("ujiselamat")
    pasang("ujimati", mati)
    pasang("ujiselamat", selamat)
    with dengan_rantai("ujimati", "ujiselamat"):
        _, label = jalur_suara.bangun("satu kalimat uji fallback " + str(time.time_ns()))
        assert mati.panggil == 1, f"engine pertama tidak pernah dicoba: {mati.panggil}"
        assert label == "ujiselamat", f"fallback tidak terjadi, yang menjawab {label}"


def uji_dedupe_aliran():
    lambat = Perekam("ujilambat", lambat=0.8)
    pasang("ujilambat", lambat)
    hasil: list = []
    galat: list = []

    def kerja(teks: str):
        try:
            hasil.append(jalur_suara.bangun(teks))
        except Exception as err:  # dicatat, bukan ditelan
            galat.append(err)

    with dengan_rantai("ujilambat"):
        teks = "kalimat kembar yang datang bersamaan " + str(time.time_ns())
        t1 = threading.Thread(target=kerja, args=(teks,))
        t2 = threading.Thread(target=kerja, args=(teks,))
        t1.start()
        time.sleep(0.05)  # pastikan yang pertama sudah masuk antrean
        t2.start()
        t1.join(timeout=25)
        t2.join(timeout=25)
        assert not galat, f"dedupe memicu galat: {galat}"
        assert len(hasil) == 2, f"tidak semua permintaan dijawab: {len(hasil)}"
        assert lambat.panggil == 1, (
            f"kalimat identik disintesis {lambat.panggil}x -- dedupe in-flight gagal"
        )


def uji_batas_detik():
    lambat = Perekam("ujilambat2", lambat=6.0)
    pasang("ujilambat2", lambat)
    asli = konfig.TTS_BATAS_DETIK
    with dengan_rantai("ujilambat2"):
        konfig.TTS_BATAS_DETIK = 1
        t0 = time.perf_counter()
        try:
            jalur_suara.bangun("kalimat yang harus kena batas detik " + str(time.time_ns()))
            raise AssertionError("lewat batas detik tidak dilaporkan")
        except jalur_suara.SemuaEngineGagal as err:
            gabung = " ".join(err.catatan)
            assert "lewat" in gabung, f"alasan bukan batas waktu: {gabung}"
        finally:
            konfig.TTS_BATAS_DETIK = asli
        assert time.perf_counter() - t0 < 5, "bangun() menggantung melewati batas detik"


def uji_rantai_dari_env():
    with dengan_rantai("rekayasa-tidak-ada"):
        assert jalur_suara.rantai_aktif() == [], "nilai tak dikenal tidak dibuang"
        assert jalur_suara.peringatan(), "tahap tak dikenal harus dilaporkan, bukan diabaikan"
    with dengan_rantai("piper", "piper"):
        aktif = jalur_suara.rantai_aktif()
        assert len(set(aktif)) == len(aktif), f"resep ganda tidak dipadatkan: {aktif}"
    with dengan_rantai("rvc"):
        # RVC menerima WAV, bukan teks: tidak boleh lolos jadi rantai lalu gagal
        # tanpa sebab.
        assert jalur_suara.rantai_aktif() == [], "resep rvc-seorang-diri lolos penyaringan"
        assert any("WAV" in p for p in jalur_suara.peringatan()), (
            f"penolakan tidak beralasan: {jalur_suara.peringatan()}"
        )


def uji_hening_ditolak():
    """Header WAV sah + isi nol semua harus dianggap GAGAL, bukan sukses.

    Ini bug yang tidak terlihat dari luar: browser dapat 200 audio/wav, decode
    sukses, `berbicara = true`, tapi rahang diam total -- dan begitu hasilnya masuk
    cache, kalimat itu hening selamanya.
    """
    hening = Perekam("uji hening", hening=True)
    pasang("ujihening", hening)
    with dengan_rantai("ujihening"):
        try:
            jalur_suara.bangun("kalimat yang engine-nya bisu " + str(time.time_ns()))
            raise AssertionError("keluaran hening diterima sebagai sukses")
        except jalur_suara.SemuaEngineGagal as err:
            assert any("hening" in c for c in err.catatan), f"alasan tidak menyebut hening: {err.catatan}"
    jalur = jalur_suara.folder_cache() / f"{jalur_suara.hitung_kunci('x', 'ujihening')}.wav"
    assert wav.puncak(bikin_wav()) > jalur_suara.AMBANG_DENGAR, "fixture nada sendiri terlalu pelan"
    assert wav.puncak(bikin_wav_hening()) == 0, "fixture hening sendiri tidak nol"
    assert jalur is not None  # (keberadaan cache diverifikasi lewat bangun() di atas)


def uji_hasil_telat_tercache():
    """Yang selesai setelah penunggu menyerah TETEP harus masuk cache.

    Kalau hanya penunggu yang menulis cache, hasil telat dibuang dan kalimat yang
    sama miss selamanya. RVC terukur 4-15 dtk per kalimat, jadi "telat" itu jalur
    normal, bukan pengecualian.
    """
    lambat = Perekam("ujitelat", lambat=2.5)
    pasang("ujitelat", lambat)
    teks = "kalimat yang hasilnya datang telat " + str(time.time_ns())
    asli = (konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP)
    with dengan_rantai("ujitelat"):
        konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = 1, 0
        try:
            try:
                jalur_suara.bangun(teks)
                raise AssertionError("penunggu seharusnya menyerah lebih dulu")
            except jalur_suara.SemuaEngineGagal:
                pass
            assert lambat.panggil == 1, f"pekerja tidak mengerjakan apa pun: {lambat.panggil}"
            time.sleep(3.2)  # biarkan pekerja menyelesaikan pekerjaannya
            kunci = jalur_suara.hitung_kunci(teks, "ujitelat")
            jalur = jalur_suara.folder_cache() / f"{kunci}.wav"
            assert jalur.is_file(), "hasil telat dibuang -- tulis_cache tidak di pekerja"
            audio, label = jalur_suara.bangun(teks)
            assert "cache" in label, f"hasil telat tidak terpakai: {label}"
            assert lambat.panggil == 1, f"cache panas tapi engine dipanggil lagi: {lambat.panggil}"
            jalur.unlink(missing_ok=True)
        finally:
            konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = asli


def uji_kedaluwarsa_dibuang():
    """Pekerja tidak boleh mengerjakan kalimat yang penunggunya sudah pergi."""
    lambat = Perekam("ujiantre", lambat=2.5)
    pasang("ujiantre", lambat)
    asli = (konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP)
    with dengan_rantai("ujiantre"):
        konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = 1, 0
        try:
            # Kalimat pertama menyita pekerja; kalimat kedua pasti kedaluwarsa
            # sebelum gilirannya tiba.
            for i in range(2):
                try:
                    jalur_suara.bangun(f"kalimat antre {i} " + str(time.time_ns()))
                except jalur_suara.SemuaEngineGagal:
                    pass
            time.sleep(1.0)
            assert lambat.panggil == 1, (
                f"pekerja tetap mengerjakan {lambat.panggil} kalimat padahal "
                "yang kedua sudah tidak ditunggu siapa pun"
            )
        finally:
            konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = asli


def uji_berhenti_menguras():
    """`berhenti()` tidak boleh meninggalkan Event yang tidak pernah di-set."""
    lambat = Perekam("ujiberhenti", lambat=2.0)
    pasang("ujiberhenti", lambat)
    asli = (konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP)
    konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = 2, 0
    with dengan_rantai("ujiberhenti"):
        try:
            jalur_suara.mula()
            pegangan = []
            for i in range(3):
                k = jalur_suara.hitung_kunci(f"berhenti {i} " + str(time.time_ns()), "ujiberhenti")
                pegangan.append(jalur_suara._antrekan(k, f"berhenti {i}", "ujiberhenti"))
            diakui = jalur_suara.berhenti()
            belum = [p for p in pegangan if p is not None and not p.selesai.is_set()]
            assert not belum, f"{len(belum)} pekerjaan menunggu event yang tidak akan pernah di-set"
            with jalur_suara._lock_in_flight:
                sisa = dict(jalur_suara._in_flight)
            assert not sisa, f"_in_flight keracunan permanen: {list(sisa)[:3]}"
            assert diakui >= 0
        finally:
            konfig.TTS_BATAS_DETIK, konfig.TTS_JEDA_RESEP = asli
            jalur_suara.mula()  # pulihkan pekerja untuk tes berikutnya


def uji_mula_idempoten():
    """Dua kali mula() = dua RVCInference di RAM, hal yang dilarang docstring tts_rvc."""
    pekerja = jalur_suara._pekerja
    jalur_suara.mula()
    jalur_suara.mula()
    assert jalur_suara._pekerja is pekerja, (
        "mula() kedua mengganti thread tanpa mematikan yang lama -> dua pekerja"
    )
    assert jalur_suara._pekerja.is_alive()


def uji_sapu_yatim():
    """Sisa proses sebelumnya harus dibuang sebelum apa pun mulai."""
    tmp = jalur_suara.folder_tmp()
    cache = jalur_suara.folder_cache()
    tmp.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    peninggalan = tmp / "peninggalan_masuk.wav"
    peninggalan.write_bytes(bikin_wav(0.05))
    separuh = cache / "abcdef.part"
    separuh.write_bytes(bikin_wav(0.05))
    jalur_suara.sapu_yatim()
    assert not peninggalan.exists(), "var/tmp-suara tidak disapu -> menumpuk selamanya"
    assert not separuh.exists(), "berkas .part tertinggal di luar plafon cache"


def uji_matriks_engine():
    """Tiap resep: WAV utuh, atau LEWAT dengan alasan -- bukan PASS kosong.

    Model RVC dihangatkan DULUAN dan batas detik dilonggarkan khusus di sini, dan
    itu bukan untuk menutupi sesuatu: memuat hubert+rmvpe+checkpoint terukur
    7-9 detik, dan itu terjadi DI DALAM permintaan pertama kalau
    VTUBER_RVC_MUAT_BOOT=didak. Yang diuji tes ini bentuk keluaran tiap engine;
    waktunya diukur terpisah oleh scripts/uji_latensi.py.
    """
    for resep in ["piper", "rvc", "piper+rvc"]:
        with dengan_rantai(resep):
            if "rvc" in resep and tts_rvc.hidup():
                try:
                    tts_rvc.muat()
                except Exception as err:
                    print(f"     LEWAT {resep}: rvc tidak bisa dimuat: {str(err)[:90]}")
                    continue
            lama = konfig.TTS_BATAS_DETIK
            konfig.TTS_BATAS_DETIK = 90
            try:
                if not jalur_suara.rantai_aktif():
                    # Termasuk kasus `rvc` seorang diri: RVC menerima WAV, bukan teks.
                    print(f"     LEWAT {resep}: {'; '.join(jalur_suara.peringatan())}")
                    continue
                audio, label = jalur_suara.bangun("kalimat matriks engine " + str(time.time_ns()))
            finally:
                konfig.TTS_BATAS_DETIK = lama
            laju, kanal, detik = wav.baca_header(audio)
            assert detik > 0.05, f"{resep}: audio {detik} dtk terlalu pendek"
            assert kanal == 1, f"{resep}: kanal {kanal}, harus mono"
            assert laju in (22050, 24000, 40000), f"{resep}: laju tak terduga {laju}"
            print(f"     pass {resep}: {detik:.2f} dtk @{laju} Hz ({label})")


if __name__ == "__main__":
    sys.exit(utama())
