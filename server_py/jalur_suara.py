"""Rantai suara: teks -> WAV, lewat satu thread pekerja dan satu cache.

Kenapa pekerja tunggal, bukan sekadar Lock di dalam tiap engine: yang dibutuhkan
bukan cuma saling-eksklusif, tapi (a) batas kedalaman antrean -- kalimat ke-9 dari
jawaban panjang tidak boleh menggantung 9xRTF, (b) deadline per pekerjaan supaya
yang terjadi adalah pindah engine, bukan koneksi mati, (c) dedupe pekerjaan identik
yang sedang berjalan, (d) satu tempat jujur untuk mengukur waktu per tahap.

Model RVC dimuat DI DALAM thread pekerja, jadi tidak pernah disentuh thread lain:
aman secara konstruksi, bukan secara konvensi.

Impor berat (piper, rvc_python, torch) semuanya tertunda di dalam modul engine
masing-masing. Sidecar ini harus tetap bisa naik dan menjawab /api/chat di mesin
yang belum `pip install -r requirements.txt`.
"""

from __future__ import annotations

import hashlib
import json
import queue
import statistics
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import tts_piper
import tts_rvc
from konfig import AKAR

# Nilai lain dibaca lewat `konfig.X`, BUKAN diimpor sebagai nama. Bukan gaya:
# `from konfig import TTS_BATAS_DETIK` mengikat ANGKA pada saat impor, sehingga
# tes (dan reload konfigurasi) tidak bisa lagi memvariasikannya -- dan salah satu
# bukti yang diminta Master justru "mengubah .env benar-benar mengganti jalur".
import konfig  # noqa: E402
from wav import AMBANG_DENGAR, WavRusak, pcm_ke_wav, puncak, sudah_wav

SKEMA_CACHE = "suara-v1"
JEJAK_METERIK = "var/meterik-suara.jsonl"


class SemuaEngineGagal(Exception):
    def __init__(self, pesan: str, catatan: list[str]):
        super().__init__(pesan)
        self.catatan = catatan


@dataclass
class Tahap:
    nama: str
    masuk: str  # "teks" atau "wav"
    jalan: object  # callable(masuk, sisa_detik) -> bytes. SELALU dua argumen.
    tersedia: object  # callable() -> bool, murah dan tidak mengimpor yang berat
    patokan: object  # callable() -> str, ikut kunci cache


@dataclass
class Pekerjaan:
    teks: str
    resep: str
    kunci: str
    selesai: threading.Event
    tenggat: float = 0.0  # time.perf_counter() absolut; 0 = tidak ada batas
    hasil: bytes | None = None
    terpakai: str = ""
    galat: str = ""
    detik: dict = field(default_factory=dict)

    def kedaluwarsa(self) -> bool:
        return self.tenggat > 0 and time.perf_counter() > self.tenggat

    def sisa(self) -> float:
        if self.tenggat <= 0:
            return 1e9
        return max(self.tenggat - time.perf_counter(), 0.0)


# Konvensi panggilan SERAGAM: tiap `jalan` menerima (bahan, sisa_detik). Dulu
# masing-masing engine punya tanda sendiri dan `sisa_detik` milik gemini tidak
# pernah diteruskan, sehingga satu pekerjaan cloud bisa memegang pekerja 3 x 25
# detik sementara penunggunya sudah menyerah di 20.
TAHAP: dict[str, Tahap] = {
    "piper": Tahap(
        "piper", "teks",
        lambda teks, sisa: tts_piper.sintesis(teks),
        tts_piper.tersedia, tts_piper.patokan_cache,
    ),
    "rvc": Tahap(
        "rvc", "wav",
        lambda audio, sisa: tts_rvc.ubah(audio, "rvc", sisa),
        tts_rvc.hidup, tts_rvc.patokan_cache,
    ),
}

_antrean: "queue.Queue[Pekerjaan]"
_pekerja: threading.Thread | None = None
_lockmula = threading.Lock()
_peringatan: list[str] = []
_waktu: dict[str, deque] = {}  # tahap -> deque detik
_lock_waktu = threading.Lock()
_in_flight: dict[str, Pekerjaan] = {}
_lock_in_flight = threading.Lock()
_berhenti = threading.Event()
# Resep yang terbukti tidak selesai dalam batas waktu disimpan di sini sebentar.
# Tanpa ini, SETIAP kalimat dari jawaban panjang membayar ulang 20 dtk kegagalan
# yang sama, dan kuota cloud yang seharusnya jadi penahan habis justru terpakai
# untuk menunggu.
_jeda: dict[str, float] = {}


def daftarkan_stub() -> None:
    """Hanya ada saat VTUBER_STUB=1: hening 0,2 detik, tanpa model apa pun."""

    def bikin(teks: str, sisa: float = 0.0) -> bytes:
        return pcm_ke_wav(bytes(4800), 24000, 1)

    TAHAP["stub"] = Tahap("stub", "teks", bikin, lambda: True, lambda: "stub")


# ── rantai ────────────────────────────────────────────────────────────────────
def pecah(resep: str) -> list[str]:
    return [t.strip() for t in reseps(resep).split("+") if t.strip()]


def reseps(resep: str) -> str:
    return (resep or "").strip().lower()


def rantai_aktif(daftar: list[str] | None = None) -> list[str]:
    """Resep yang benar-benar bisa dikerjakan, urutan ikut .env.

    Fungsi murni: tidak menyentuh model, tidak membuka berkas besar. Bisa diuji
    dengan nilai env apa pun, dan itu penting karena 'ganti .env harus benar-benar
    mengganti jalur' adalah salah satu yang diminta Master.
    """
    hasil, catatan = [], []
    for resep in daftar if daftar is not None else konfig.TTS_RANTAI:
        tahap = pecah(resep)
        if not tahap:
            continue
        asing = [t for t in tahap if t not in TAHAP]
        if asing:
            catatan.append(f"resep '{resep}' dibuang: tahap tidak dikenal {asing}")
            continue
        mati = [t for t in tahap if not TAHAP[t].tersedia()]
        if mati:
            alasan = ", ".join(f"{t}: {alasan_tidak_siap(t)}" for t in mati)
            catatan.append(f"resep '{resep}' dilewati ({alasan})")
            continue
        if TAHAP[tahap[0]].masuk != "teks":
            # Rantai selalu dimulai dari teks. `VTUBER_TTS_RANTAI=rvc` bukan
            # konfigurasi yang bisa dipenuhi -- RVC butuh audio sumber, dan error
            # "semua engine gagal" tanpa alasan itu lebih menyesatkan daripada
            # tahap yang jujur bilang ia tidak menerima teks.
            catatan.append(
                f"resep '{resep}' dibuang: tahap pertama '{tahap[0]}' menerima WAV, "
                "bukan teks (tulis piper+rvc)"
            )
            continue
        hasil.append("+".join(tahap))
    # Resep ganda dibuang di sini, bukan di pemanggil: menulis
    # VTUBER_TTS_RANTAI=piper,piper membuat kalimat yang gagal dicoba DUA kali,
    # dan tiap percobaan itu memakan batas detik yang sama.
    hasil = list(dict.fromkeys(hasil))
    _peringatan[:] = catatan
    return hasil


def alasan_tidak_siap(nama: str) -> str:
    if nama == "piper":
        return tts_piper.alasan_tidak_tersedia()
    if nama == "rvc":
        return tts_rvc.alasan_tidak_tersedia()
    if nama == "gemini":
        return "GEMINI_API_KEY kosong"
    return "tidak siap"


def peringatan() -> list[str]:
    return list(_peringatan)


# ── cache ─────────────────────────────────────────────────────────────────────
def folder_cache() -> Path:
    p = Path(konfig.TTS_CACHE_FOLDER)
    return p if p.is_absolute() else AKAR / p


def folder_tmp() -> Path:
    return AKAR / "var" / "tmp-suara"


def normal(teks: str) -> str:
    return " ".join((teks or "").split())


def hitung_kunci(teks: str, resep: str) -> str:
    """Kunci cache. Sengaja PEKA terhadap parameter: ganti model/transpose/f0
    harus miss sendiri, bukan meminta orang membersihkan folder."""
    bagian = [SKEMA_CACHE, resep, normal(teks)]
    for nama in pecah(resep):
        try:
            bagian.append(TAHAP[nama].patokan())
        except Exception as err:
            bagian.append(f"{nama}:patokan-gagal:{err}")
    return hashlib.sha256("|".join(bagian).encode("utf-8")).hexdigest()[:32]


def sunyi(bin: bytes) -> bool:
    """Apakah WAV ini sah tapi isinya tidak akan terdengar sama sekali."""
    try:
        return puncak(bin) <= AMBANG_DENGAR
    except WavRusak:
        return True


def baca_cache(kunci: str) -> bytes | None:
    if not konfig.TTS_CACHE:
        return None
    jalur = folder_cache() / f"{kunci}.wav"
    try:
        byte = jalur.read_bytes()
    except OSError:
        return None
    # Berkas separuh tidak mungkin ada (tulis lewat .part + replace), tapi kalau
    # disk menipu, lebih baik anggap miss daripada kirim WAV rusak ke browser.
    if not sudah_wav(byte) or len(byte) <= 44 or sunyi(byte):
        try:
            jalur.unlink()
        except OSError:
            pass
        return None
    try:
        jalur.touch()  # LRU berdasarkan mtime
    except OSError:
        pass
    return byte


def tulis_cache(kunci: str, wav: bytes) -> None:
    if not konfig.TTS_CACHE or sunyi(wav):
        return
    folder = folder_cache()
    folder.mkdir(parents=True, exist_ok=True)
    jalur = folder / f"{kunci}.wav"
    # Nama .part harus unik: kalau diturunkan dari `kunci` saja, dua penulis dengan
    # kunci sama berbagi satu berkas temp, dan `replace()` di Windows melempar
    # PermissionError saat handle yang lain masih terbuka -- hasilnya dibuang
    # diam-diam lewat except OSError, persis kelas bug yang wav.py perangi.
    separuh = folder / f"{kunci}.{uuid.uuid4().hex}.wav.part"
    try:
        separuh.write_bytes(wav)
        separuh.replace(jalur)
    except OSError:
        try:
            separuh.unlink()
        except OSError:
            pass
        return
    pangkas()


def sapu_yatim() -> int:
    """Buang sisa kerja proses sebelumnya. Dipanggil dari mula(), sebelum pekerja
    aktif, jadi apa pun yang masih ada di sana pasti yatim.

    Ada karena bukti di disk: dua `_masuk.wav` tertinggal dari server yang dipotong
    di tengah infer_file -- `finally` tidak jalan kalau prosesnya dibunuh.
    """
    buang = 0
    for pola, folder in (
        ("*", folder_tmp()),
        ("*.part", folder_cache()),
    ):
        if not folder.is_dir():
            continue
        for p in folder.glob(pola):
            try:
                if p.is_file():
                    p.unlink()
                    buang += 1
            except OSError:
                pass
    return buang


def pangkas(batas_mb: int | None = None) -> int:
    """LRU by mtime sampai di bawah batas. Dipanggil saat boot dan setelah menulis."""
    batas = (batas_mb if batas_mb is not None else konfig.TTS_CACHE_MAKS_MB) * 1024 * 1024
    folder = folder_cache()
    if not folder.is_dir():
        return 0
    isi = sorted(
        (p for p in folder.glob("*.wav") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    total, hapus = 0, 0
    for p in isi:
        try:
            ukuran = p.stat().st_size
        except OSError:
            continue
        if total + ukuran <= batas:
            total += ukuran
            continue
        try:
            p.unlink()
            hapus += 1
        except OSError:
            pass
    return hapus


# ── pekerja ───────────────────────────────────────────────────────────────────
def mula() -> None:
    """Satu pekerja per proses. `mula()` dua kali = dua RVCInference di RAM.

    Penjaga ini bukan formalitas: berhenti() tidak bisa menjamin thread lama sudah
    mati (ia mungkin sedang di tengah infer_file 7 detik), dan dua pekerja yang
    berebut empat core persis hal yang dilarang docstring tts_rvc.
    """
    global _antrean, _pekerja
    with _lockmula:
        if _pekerja is not None and _pekerja.is_alive():
            return
        if konfig.STUB:
            daftarkan_stub()
        sapu_yatim()
        pangkas()
        _antrean = queue.Queue(maxsize=max(konfig.RVC_BATAS_ANTREAN, 1))
        with _lock_in_flight:
            _in_flight.clear()
        _jeda.clear()
        _berhenti.clear()
        _pekerja = threading.Thread(target=_lingkaran, name="penenun-suara", daemon=True)
        _pekerja.start()


def berhenti() -> int:
    """Berhenti dengan jujur: akui semua yang masih mengantre, jangan tinggalkan.

    Tanpa pengurasan ini, tiap penunggu yang sedang wait() menyerah penuh
    TTS_BATAS_DETIK untuk resep yang juga tidak akan pernah dikerjakan (Ctrl-C
    terasa menggantung), dan `_in_flight` menyimpan pekerjaan yatim permanen --
    setiap permintaan untuk kalimat itu lalu menunggu 20 dtk dan gagal selamanya,
    tanpa satu baris kode pun yang bisa mendiagnosisnya.
    """
    global _pekerja
    _berhenti.set()
    diakui = 0
    try:
        while True:
            pekerjaan = _antrean.get_nowait()
            pekerjaan.galat = "pekerja berhenti"
            pekerjaan.selesai.set()
            _antrean.task_done()
            diakui += 1
    except (queue.Empty, NameError):
        pass
    with _lock_in_flight:
        _in_flight.clear()
    pekerja = _pekerja
    if pekerja is not None and pekerja.is_alive():
        pekerja.join(timeout=max(konfig.TTS_BATAS_DETIK, 5) + 2)
        if not pekerja.is_alive():
            _pekerja = None
    else:
        _pekerja = None
    return diakui


def _lingkaran() -> None:
    while not _berhenti.is_set():
        try:
            pekerjaan = _antrean.get(timeout=0.25)
        except queue.Empty:
            continue
        try:
            if pekerjaan.kedaluwarsa():
                # Penunggunya sudah lama menyerah dan pindah engine. Mengerjakan
                # ini cuma membakar CPU yang dibutuhkan kalimat berikutnya.
                pekerjaan.galat = "lewat tenggat di antrean"
            else:
                _kerjakan(pekerjaan)
        finally:
            # Cache ditulis DI SINI, bukan oleh penunggu. Kalau hanya penunggu yang
            # menulis, hasil yang datang telat dibuang dan kalimat yang sama miss
            # selamanya -- RVC butuh ~7 dtk per kalimat, jadi "telat" itu normal.
            if pekerjaan.hasil and not sunyi(pekerjaan.hasil):
                tulis_cache(pekerjaan.kunci, pekerjaan.hasil)
            pekerjaan.selesai.set()
            with _lock_in_flight:
                if _in_flight.get(pekerjaan.kunci) is pekerjaan:
                    _in_flight.pop(pekerjaan.kunci, None)
            _antrean.task_done()


def _kerjakan(pekerjaan: Pekerjaan) -> None:
    """Satu resep utuh: tahap pertama menerima teks, sisanya menerima WAV.

    Tiap tahap mendapat SISA anggaran, bukan angka tetap -- dulu gemini dipanggil
    dengan timeout 25 dtk di dalam pekerjaan yang penunggunya sudah menyerah di 20,
    dan tiga model berurutan bisa memegang pekerja ~75 dtk tanpa ada yang menunggu.
    """
    audio = None
    for nama in pecah(pekerjaan.resep):
        tahap = TAHAP[nama]
        sisa = pekerjaan.sisa()
        if sisa <= 0:
            pekerjaan.galat = f"{nama}: kehabisan waktu sebelum mulai"
            return
        mulai = time.perf_counter()
        # normal() dikirim ke engine, bukan cuma ke kunci: kalau tidak, dua teks
        # berbeda-byte yang berbagi kunci bisa saling menukar hasil.
        bahan = normal(pekerjaan.teks) if tahap.masuk == "teks" else audio
        try:
            audio = tahap.jalan(bahan, sisa)
        except Exception as err:
            pekerjaan.galat = f"{nama}: {err}"
            return
        detik = time.perf_counter() - mulai
        pekerjaan.detik[nama] = detik
        _catat_waktu(nama, detik, audio)
    if audio is None or sunyi(audio):
        # "Suara hilang diam-diam" sudah dua kali menjatuhkan proyek ini (lihat
        # docstring sudah_wav). Keluaran hening = GAGAL, bukan keberhasilan sunyi.
        pekerjaan.galat = "keluaran hening"
        return
    pekerjaan.hasil = audio
    pekerjaan.terpakai = pekerjaan.resep


def _catat_waktu(nama: str, detik: float, wav: bytes | None) -> None:
    with _lock_waktu:
        _waktu.setdefault(nama, deque(maxlen=200)).append(detik)
    if not konfig.TTS_METERIK or wav is None:
        return
    try:
        from wav import baca_header

        _, _, panjang = baca_header(wav)
        jalur = AKAR / JEJAK_METERIK
        jalur.parent.mkdir(parents=True, exist_ok=True)
        baris = {"tahap": nama, "detik": round(detik, 3), "audio": round(panjang, 3)}
        if panjang > 0:
            baris["rtf"] = round(detik / panjang, 3)
        with jalur.open("a", encoding="utf-8") as f:
            f.write(json.dumps(baris, ensure_ascii=False) + "\n")
    except Exception:
        pass  # meterik tidak boleh merusak suara


def bangun(teks: str) -> tuple[bytes, str]:
    """WAV + label engine yang menjawab. Melempar SemuaEngineGagal kalau habis."""
    if konfig.STUB:
        return pcm_ke_wav(bytes(4800), 24000, 1), "stub"

    rantai = rantai_aktif()
    if not rantai:
        raise SemuaEngineGagal(
            "tidak ada engine suara yang siap",
            _peringatan or ["rantai kosong di .env"],
        )

    sekarang = time.perf_counter()
    catatan: list[str] = []
    for resep in rantai:
        sampai = _jeda.get(resep, 0.0)
        if sampai > sekarang:
            catatan.append(f"{resep}: dicoba lagi dalam {sampai - sekarang:.0f} dtk")
            continue

        kunci = hitung_kunci(teks, resep)
        simpanan = baca_cache(kunci)
        if simpanan is not None:
            return simpanan, f"{resep}+cache"

        pekerjaan = _antrekan(kunci, teks, resep)
        if pekerjaan is None:  # antrean penuh -> jangan menggantung
            catatan.append(f"{resep}: antrean penuh")
            continue
        if not pekerjaan.selesai.wait(timeout=konfig.TTS_BATAS_DETIK):
            catatan.append(f"{resep}: lewat {konfig.TTS_BATAS_DETIK} dtk")
            # Resep yang terbukti tidak selesai di beban ini diistirahatkan sebentar,
            # supaya kalimat ke-2..N sebuah jawaban panjang tidak membayar ulang
            # kegagalan yang sama. Hasil yang tetap dikerjakan pekerja masuk cache
            # dan dipakai di percakapan berikutnya.
            _jeda[resep] = time.perf_counter() + max(konfig.TTS_JEDA_RESEP, 0)
            continue
        # Pekerja sudah menulis cache-nya sendiri; di sini cukup pakai byte-nya.
        if pekerjaan.hasil and sudah_wav(pekerjaan.hasil) and not sunyi(pekerjaan.hasil):
            return pekerjaan.hasil, pekerjaan.terpakai or resep
        catatan.append(f"{resep}: {pekerjaan.galat or 'tanpa hasil'}")

    raise SemuaEngineGagal("semua engine suara gagal", catatan)


def _antrekan(kunci: str, teks: str, resep: str) -> Pekerjaan | None:
    """Satu pekerjaan per kunci. Kalimat yang sama dua kali -> satu sintesis."""
    with _lock_in_flight:
        ada = _in_flight.get(kunci)
        if ada is not None:
            return ada
        pekerjaan = Pekerjaan(
            teks=teks,
            resep=resep,
            kunci=kunci,
            selesai=threading.Event(),
            # Tenggat absolut: pekerja memakai ini untuk MEMBUANG pekerjaan yang
            # tidak ada penunggunya lagi, bukan cuma untuk memotong koneksi.
            tenggat=time.perf_counter() + max(konfig.TTS_BATAS_DETIK, 1),
        )
        try:
            _antrean.put_nowait(pekerjaan)
        except queue.Full:
            return None
        _in_flight[kunci] = pekerjaan
        return pekerjaan


# ── meterik untuk banner / health ─────────────────────────────────────────────
def meterik() -> dict:
    with _lock_waktu:
        salin = {k: list(v) for k, v in _waktu.items()}
    keluar = {}
    for nama, daftar in salin.items():
        if not daftar:
            continue
        keluar[nama] = {
            "median": round(statistics.median(daftar), 3),
            "p95": round(sorted(daftar)[max(len(daftar) - 1, int(len(daftar) * 0.95) - 1)], 3),
            "contoh": len(daftar),
        }
    return keluar


def ringkasan() -> dict:
    """Bentuk objek `tts` di /api/health. Sengaja TIDAK menambah kunci level-atas
    -- kontrak lama mengunci daftar kunci itu, dan chat.js membaca h.tts.perKalimat."""
    if konfig.STUB:
        # Mode stub TIDAK lewat rantai apa pun (app.py::tts memulangkan hening
        # sebelum bangun()). Melaporkan "piper,gemini" di sini berarti halaman
        # dan banner saling bertentangan soal siapa yang sedang bicara.
        siap = ["stub"]
        isi = {
            "model": "stub (hening, engine tidak disentuh)",
            "rantai": siap,
            "piper": False,
            "rvc": False,
            "cache": False,
        }
    else:
        siap = rantai_aktif()
        isi = {
            "model": ",".join(siap) or "tidak-ada",
            "rantai": siap,
            "piper": tts_piper.tersedia(),
            "rvc": tts_rvc.hidup(),
            "cache": bool(konfig.TTS_CACHE),
        }
    return {
        **isi,
        "suara": f"rvc/{konfig.RVC_MODEL}" if tts_rvc.hidup() else "piper",
        "perKalimat": bool(konfig.TTS_PER_KALIMAT),
    }
