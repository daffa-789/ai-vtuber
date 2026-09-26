"""Engine pengubah WARNA suara: RVC v2 dengan checkpoint Furina.

Bukan TTS. RVC butuh audio sumber -- ia tidak menyusun teks jadi suara. Di sini
sumbernya keluaran Piper (lafal + irama bahasa Indonesia), dan RVC hanya
mengganti timbrenya. Karena itu engine ini boleh mati (VTUBER_RVC=tidak) tanpa
membisukan apa pun.

Satu-satunya pemegang RVCInference di proyek ini, dan hanya boleh disentuh dari
thread pekerja jalur_suara: muat model 190-370 MB ke RAM dan bukan sesuatu yang
aman dipakai dua thread sekaligus.

Catatan DLL yang terukur di mesin ini (2026-09-26): `import faiss` sebelum
`import torch` membuat torch gagal dengan WinError 1114 pada c10.dll. Jalur
rvc_python.infer kebetulan sudah aman (modules.py memuat torch di baris 8,
pipeline.py baru memuat faiss di baris 11), tapi itu bergantung pada urutan
berkas pihak ketiga -- makanya `import torch` ditulis eksplisit lebih dulu.
"""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

import konfig
from konfig import AKAR
from wav import AMBANG_DENGAR, baca_header, puncak, sudah_wav

NAMA = "rvc"

# Konversi RVC terukur 4-15 dtk per kalimat di mesin ini. Di bawah angka ini,
# menolak lebih murah daripada memulai kerja yang pasti tidak akan ditunggu.
WAKTU_MINIMUM = 3.0

_rvc = None
_lock = threading.Lock()
_galat_terakhir = ""


class RvcTidakHidup(Exception):
    """RVC dimatikan atau asetnya belum ada -- bukan kegagalan, jangan diadu."""


class RvcGagal(Exception):
    """Percobaan konversi benar-benar gagal."""


def folder_model() -> Path:
    p = Path(konfig.RVC_FOLDER)
    return p if p.is_absolute() else AKAR / p


def berkas_rncunan() -> tuple[Path | None, Path | None, str]:
    """(pth, index, nama) untuk model terpilih, mengikuti cara rvc_python memindai.

    rvc_python._load_available_models() men-scan models_dir/*/ dan mengambil
    *.pth + *.index pertama, jadi bentuk folder inilah kontraknya -- nama model
    di .env adalah nama SUBFOLDER, bukan nama berkas.
    """
    folder = folder_model() / konfig.RVC_MODEL
    if not folder.is_dir():
        return (None, None, konfig.RVC_MODEL)
    pth = sorted(folder.glob("*.pth"))
    idx = sorted(folder.glob("*.index"))
    return (pth[0] if pth else None, idx[0] if idx else None, konfig.RVC_MODEL)


def siap() -> bool:
    """Murah: cek berkas + modul bisa diimpor. TIDAK menyentuh konstruktor."""
    pth, _, _ = berkas_rncunan()
    return pth is not None and _rvc_terpasang()


def hidup() -> bool:
    return konfig.RVC_HIDUP and siap()


def _rvc_terpasang() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("rvc_python") is not None
    except Exception:
        return False


def izinkan_global_torch() -> None:
    """Daftar putih kelas yang ada di dalam checkpoint HuBERT/RMVPE.

    PyTorch >= 2.6 membalik bawaan `torch.load` menjadi weights_only=True.
    checkpoint fairseq menyimpan objek `fairseq.data.dictionary.Dictionary` dan
    `argparse.Namespace`, jadi muatnya ditolak -- bukan karena berkasnya rusak,
    tapi karena sandbox-nya sekarang ketat. rvc_python memanggil torch.load tanpa
    menyebut weights_only, jadi kita TIDAK menutup sandbox itu (opsi yang lebih
    gampang tapi berarti berkas .pth pihak ketiga bisa mengeksekusi kode apa pun
    di meja Master); kita hanya membuka dua pintu yang memang dibutuhkan.

    Kalau kelak muncul "Unsupported global: GLOBAL x.y.Z", itu bukan kegagalan
    yang harus disweep di bawah karpet: tambah nama kelasnya ke sini supaya
    daftar yang dipercaya tetap terbaca dan bisa diaudit.
    """
    import torch

    calon: list = []
    try:
        from fairseq.data.dictionary import Dictionary

        calon.append(Dictionary)
    except Exception:
        pass
    import argparse

    calon.append(argparse.Namespace)
    try:
        torch.serialization.add_safe_globals(calon)
    except Exception:
        pass  # torch lama tanpa add_safe_globals -> bawaannya sudah weights_only=False


def muat() -> None:
    """Idempoten. Hanya boleh dipanggil dari thread pekerja jalur_suara."""
    global _rvc, _galat_terakhir
    with _lock:
        if _rvc is not None:
            return
        if not konfig.RVC_HIDUP:
            raise RvcTidakHidup("VTUBER_RVC=tidak")
        pth, idx, nama = berkas_rncunan()
        if pth is None:
            raise RvcTidakHidup(
                f"checkpoint tidak ada di {folder_model() / nama} "
                "(jalankan scripts/sedia_suara.py --furina)"
            )
        if not _rvc_terpasang():
            raise RvcTidakHidup("rvc_python belum diinstal (pip install -r requirements.txt)")

        import torch  # noqa: F401  -- WAJIB sebelum rvc_python, lihat docstring modul

        izinkan_global_torch()
        from rvc_python.infer import RVCInference

        try:
            rvc = RVCInference(
                models_dir=str(folder_model()),
                device="cpu:0",  # tidak ada NVIDIA di mesin ini; jangan ditulis cuda
            )
            rvc.load_model(nama, version=konfig.RVC_VERSI, index_path="")
            rvc.set_params(**param_aktif())
        except Exception as err:
            _galat_terakhir = f"muat RVC gagal: {err}"
            raise RvcGagal(_galat_terakhir) from err
        _rvc = rvc
        # Index sengaja TIDAK dimuat lewat load_model: kalau RVC_INDEKS_LAJU=0 ia
        # cuma akan dibaca (507 MB) lalu dibuang.
        if konfig.RVC_INDEKS_LAJU > 0 and idx is not None:
            _rvc.models[nama]["index"] = str(idx)


def param_aktif() -> dict:
    """Peta kunci kita -> nama parameter rvc_python (namanya tidak bisa ditebak)."""
    return {
        "f0method": konfig.RVC_F0,
        "f0up_key": konfig.RVC_TRANSPOSE,
        "index_rate": konfig.RVC_INDEKS_LAJU,
        "filter_radius": konfig.RVC_PENCUCIAN,
        "resample_sr": konfig.RVC_RESAMPLE,
        "rms_mix_rate": konfig.RVC_CAMPUR_RMS,
        "protect": konfig.RVC_PROTEKSI,
    }


def patokan_cache() -> str:
    """Dipakai kunci cache: ganti checkpoint/parameter -> miss sendiri, tanpa bersih manual."""
    pth, idx, nama = berkas_rncunan()

    def tanda(p: Path | None) -> str:
        if p is None:
            return "tidak-ada"
        st = p.stat()
        return f"{st.st_size}:{int(st.st_mtime)}"

    p = param_aktif()
    return "|".join(
        [
            "rvc",
            nama,
            konfig.RVC_VERSI,
            str(p["f0method"]),
            str(p["f0up_key"]),
            str(p["index_rate"]),
            tanda(pth),
            tanda(idx) if p["index_rate"] else "tanpa-index",
        ]
    )


def ubah(wav_masuk: bytes, label: str = "", sisa: float = 0.0) -> bytes:
    """WAV masuk -> WAV keluar dengan timbre model. Lewat berkas, karena itu
    satu-satunya antarmuka yang disediakan rvc_python (infer_file/infer_dir).

    `sisa` (detik anggaran yang masih ada) dipakai sebagai pagar masuk, bukan
    pembatal di tengah jalan -- infer_file tidak bisa dihentikan. Kalau waktunya
    sudah tidak cukup untuk mengerjakan apa pun, lebih baik menolak sekarang dan
    membiarkan rantai pindah engine daripada memegang pekerja 7 detik untuk hasil
    yang tidak akan ditunggu siapa pun.
    """
    if not konfig.RVC_HIDUP:
        raise RvcTidakHidup("VTUBER_RVC=tidak")
    if sisa and sisa < WAKTU_MINIMUM:
        raise RvcGagal(
            f"anggaran tinggal {sisa:.1f} dtk, di bawah {WAKTU_MINIMUM:.0f} dtk yang "
            "dibutuhkan satu konversi -- lewati resep ini"
        )
    muat()

    # Nama berkas temp WAJIB unik per permintaan. Dua alasan yang sama-sama sunyi:
    # cache_harvest_f0 di rvc_python di-lru_cache berdasarkan PATH berkas (nama
    # sama = F0 kalimat sebelumnya dipulangkan), dan input_audio_path2wav global.
    folder_tmp = AKAR / "var" / "tmp-suara"
    folder_tmp.mkdir(parents=True, exist_ok=True)
    alias = uuid.uuid4().hex
    masuk = folder_tmp / f"{alias}_masuk.wav"
    keluar = folder_tmp / f"{alias}_keluar.wav"

    try:
        masuk.write_bytes(wav_masuk)
        _rvc.set_params(**param_aktif())
        try:
            _rvc.infer_file(str(masuk), str(keluar))
        except Exception as err:
            # vc_single MENELAN semua exception dan mengembalikan string traceback,
            # lalu infer_file meledak di dalam wavfile.write. Galat yang sampai ke
            # sini biasanya tidak menjelaskan apa pun.
            #
            # `sebab asli` dijalankan di sini berarti konversi KEDUA yang utuh
            # (4-15 dtk lagi) sambil memegang satu-satunya pekerja -- tepat saat
            # rantai sedang gagal. Jadi hanya atas permintaan, lewat diagnostik().
            sebab = (
                _telusuri(str(masuk))
                if konfig.TTS_METERIK
                else "sebab asli hanya dipakai saat VTUBER_TTS_METERIK=ya "
                     "atau lewat scripts/uji_latensi.py --mendiagnosa"
            )
            raise RvcGagal(f"{err} | {sebab}") from err

        if not keluar.is_file():
            raise RvcGagal(f"RVC tidak menulis berkas keluaran ({label})")
        byte = keluar.read_bytes()
        if not sudah_wav(byte) or len(byte) <= 44:
            raise RvcGagal(f"keluaran RVC bukan WAV utuh ({len(byte)} byte, {label})")
        _, _, detik = baca_header(byte)
        if detik <= 0.02:
            raise RvcGagal(f"keluaran RVC terlalu pendek ({detik:.3f} dtk, {label})")
        # Durasi BUKAN bukti ada suaranya. Keluaran 40 kHz penuh nol lolos
        # baca_header, lolos decodeAudioData browser, dan menghasilkan rahang yang
        # diam seribu bahasa -- lalu masuk cache dan membisukan kalimat itu selamanya.
        if puncak(byte) <= AMBANG_DENGAR:
            raise RvcGagal(f"keluaran RVC hening ({detik:.2f} dtk, {label})")
        return byte
    finally:
        for p in (masuk, keluar):
            try:
                os.remove(p)
            except OSError:
                pass


def _telusuri(jalur_masuk: str) -> str:
    """Panggil vc_single langsung supaya traceback yang ditelan paket kelihatan."""
    try:
        nama = _rvc.current_model
        hasil = _rvc.vc.vc_single(
            sid=0,
            input_audio_path=jalur_masuk,
            f0_up_key=konfig.RVC_TRANSPOSE,
            f0_method=konfig.RVC_F0,
            file_index=_rvc.models[nama].get("index") or "",
            file_index2="",
            index_rate=konfig.RVC_INDEKS_LAJU,
            filter_radius=konfig.RVC_PENCUCIAN,
            resample_sr=konfig.RVC_RESAMPLE,
            rms_mix_rate=konfig.RVC_CAMPUR_RMS,
            protect=konfig.RVC_PROTEKSI,
            f0_file="",
        )
        if isinstance(hasil, tuple) and isinstance(hasil[0], str):
            return hasil[0].strip()
        return "vc_single tampak berhasil; kegagalan ada di penulisan berkas"
    except Exception as err:
        return str(err)


def diagnostik(wav_masuk: bytes) -> str:
    """Untuk scripts/uji_latensi.py --mendiagnosa: kembalikan laporan, bukan byte."""
    if not hidup():
        return "RVC mati atau asetnya belum ada"
    muat()
    folder_tmp = AKAR / "var" / "tmp-suara"
    folder_tmp.mkdir(parents=True, exist_ok=True)
    masuk = folder_tmp / f"diagnostik_{uuid.uuid4().hex}.wav"
    try:
        masuk.write_bytes(wav_masuk)
        pesan = _telusuri(str(masuk))
        sr = getattr(getattr(_rvc, "vc", None), "tgt_sr", "?")
        return f"tgt_sr={sr} | f0={konfig.RVC_F0} | transpose={konfig.RVC_TRANSPOSE}\n{pesan}"
    finally:
        try:
            os.remove(masuk)
        except OSError:
            pass


def alasan_tidak_tersedia() -> str:
    if not konfig.RVC_HIDUP:
        return "VTUBER_RVC=tidak"
    pth, _, nama = berkas_rncunan()
    if pth is None:
        return f"checkpoint {nama} belum ditaruh di {folder_model()}"
    if not _rvc_terpasang():
        return "rvc_python belum diinstal"
    return _galat_terakhir or "rvc siap"
