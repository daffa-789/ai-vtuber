"""Penyedia aset jalur suara: voice Piper, model dasar RVC, checkpoint Furina.

Tanpa berkas-berkas ini tidak ada yang bisa bersuara, dan tidak semuanya bisa
diunduh (checkpoint Furina sudah ada di disk Master). Skrip ini satu-satunya
tempat yang tahu LETaknya, dan patuh pada dua aturan:

  1. JANGAN PERNAH menulis ke E: (18 GB bebas, 86% penuh). Baca dari sana boleh.
  2. JANGAN menimpa berkas yang ukurannya sudah cocok -- menyalin 507 MB ulang
     karena seseorang mengetik flag yang salah itu bukan pembersihan.

Cara pakai:
    python scripts/sedia_suara.py --periksa
    python scripts/sedia_suara.py --piper
    python scripts/sedia_suara.py --model-dasar
    python scripts/sedia_suara.py --furina [--dengan-index]
    python scripts/sedia_suara.py --semua
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "server_py"))

import konfig  # noqa: E402
import wav as wav_mod  # noqa: E402

# ── lokasi ───────────────────────────────────────────────────────────────────
PIPER = AKAR / "aset" / "suara" / "piper"
RVC = AKAR / "aset" / "suara" / "rvc"
DASAR = AKAR / "aset" / "suara" / "model-dasar"
CACHE = AKAR / "var" / "cache-suara"
TMP = AKAR / "var" / "tmp-suara"

# Sumber yang terbukti: venv proyek lama yang dependensinya sudah terpasang dan
# sudah diuji bisa memuat rvc_python + fairseq di mesin ini.
VENV_TERBUKTI = Path(
    r"C:/Users/Daffa/Desktop/Folder Space AI/Folder Space Semester 6"
    r"/voice changer3 glm/venv/Lib/site-packages/rvc_python/base_model"
)
FURINA_SUMBER = Path("E:/Asset RVC/Model/Furina Model")

# hubert_base.pt TIDAK sama dengan contentvec/pytorch_model.bin milik Applio,
# jadi sumbernya venv terbukti (atau unduhan paket), bukan Applio.
BERKAS_DASAR = {
    "hubert_base.pt": 189_507_909,
    "rmvpe.pt": 181_184_272,
    "rmvpe.onnx": 361_688_443,
}
MD5_RMVPE = "059b08cb99737850741ba9d20298533d"  # identik dengan punyak Applio


def md5(jalur: Path, blok: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with jalur.open("rb") as f:
        while True:
            data = f.read(blok)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def dilarang_ke_e(jalur: Path) -> None:
    """Tolak menulis di luar proyek. E: tinggal 18 GB dan aset ini ratusan MB."""
    teks = str(jalur).replace("\\", "/").upper()
    if teks.startswith("E:/"):
        raise SystemExit(f"GALAT: menolak menulis ke {jalur} -- E: tinggal sedikit")
    if not _di_dalam_proyek(jalur):
        raise SystemExit(f"GALAT: menolak menulis di luar proyek: {jalur}")


def _di_dalam_proyek(jalur: Path) -> bool:
    try:
        jalur.resolve().relative_to(AKAR.resolve())
        return True
    except (ValueError, OSError):
        return False


def baris(status: str, pesan: str) -> None:
    print(f"{status:<6} {pesan}")


def cocok(jalur: Path, ukuran: int) -> bool:
    return jalur.is_file() and jalur.stat().st_size == ukuran


def salin(sumber: Path, tujuan: Path, ukuran: int | None = None, paksa: bool = False) -> str:
    """Salin kalau perlu. Mengembalikan 'OK' / 'Lewat' / 'GALAT'."""
    if not sumber.is_file():
        baris("GALAT", f"sumber tidak ada: {sumber}")
        return "GALAT"
    dilarang_ke_e(tujuan)
    uk = ukuran or sumber.stat().st_size
    if cocok(tujuan, uk) and not paksa:
        baris("Lewat", f"{tujuan.relative_to(AKAR)} sudah ada ({uk:,} B)")
        return "Lewat"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tmp = tujuan.with_suffix(tujuan.suffix + ".part")
    shutil.copy2(sumber, tmp)
    if not cocok(tmp, uk):
        tmp.unlink(missing_ok=True)
        baris("GALAT", f"salinan ukuran tidak cocok: {sumber} -> {tujuan}")
        return "GALAT"
    tmp.replace(tujuan)
    baris("OK", f"{tujuan.relative_to(AKAR)} <- {sumber.name} ({uk:,} B)")
    return "OK"


def folder_site_packages() -> Path:
    """Tempat rvc_python mencari base_model-nya (ia membaca f'{lib_dir}/base_model')."""
    import importlib.util

    spec = importlib.util.find_spec("rvc_python")
    if spec is None or not spec.origin:
        return Path("<rvc_python belum diinstal>")
    return Path(spec.origin).parent


# ── tindakan ──────────────────────────────────────────────────────────────────
def aksi_piper(paksa: bool = False) -> str:
    nama = konfig.PIPER_SUARA
    tujuan = PIPER / f"{nama}.onnx"
    if tujuan.is_file() and tujuan.stat().st_size > 1024 * 1024 and not paksa:
        baris("Lewat", f"voice {nama} sudah ada ({tujuan.stat().st_size:,} B)")
        return "Lewat"
    from piper.download_voices import download_voice

    PIPER.mkdir(parents=True, exist_ok=True)
    dilarang_ke_e(PIPER)
    try:
        download_voice(nama, PIPER, force_redownload=paksa)
    except Exception as err:
        baris("GALAT", f"unduh {nama} gagal: {err}")
        return "GALAT"
    baris("OK", f"voice {nama} -> {PIPER}")
    return "OK"


def aksi_model_dasar(sumber: Path, paksa: bool = False) -> str:
    hasil = "OK"
    for nama, ukuran in BERKAS_DASAR.items():
        tujuan = DASAR / nama
        if cocok(tujuan, ukuran):
            baris("Lewat", f"{nama} sudah ada di {DASAR.relative_to(AKAR)}")
            continue
        if tidak_ada(sumber / nama):
            baris(
                "GALAT",
                f"{nama} tidak ada di {sumber} -- unduh sekali (rvc_python akan "
                "mengunduh sendiri saat muat, tapi itu masuk RAM sekaligus)",
            )
            hasil = "GALAT"
            continue
        hasil = min_rank(hasil, salin(sumber / nama, tujuan, ukuran, paksa))

    # rvc_python TIDAK bisa diarahkan ke luar paketnya: ia membuka
    # f"{lib_dir}/base_model/..." dengan lib_dir = direktori paket. Jadi salinan
    # proyek ini dipasang ke site-packages -- dan itulah sebabnya membuat ulang
    # .venv berarti menjalankan skrip ini lagi (lihat --periksa).
    dipasang = folder_site_packages() / "base_model"
    if tidak_ada(dipasang.parent / "infer.py"):
        baris("GALAT", "rvc_python belum terinstal, tidak bisa memasang base_model")
        return "GALAT"
    dipasang.mkdir(parents=True, exist_ok=True)
    for nama, ukuran in BERKAS_DASAR.items():
        dari = DASAR / nama
        if cocok(dari, ukuran):
            hasil = min_rank(hasil, salin(dari, dipasang / nama, ukuran, paksa))
    return hasil


def tidak_ada(p: Path) -> bool:
    try:
        return not p.is_file()
    except OSError:
        return True


def min_rank(a: str, b: str) -> str:
    urutan = {"OK": 0, "Lewat": 1, "GALAT": 2}
    return a if urutan[a] >= urutan[b] else b


def aksi_furina(sumber: Path, dengan_index: bool, paksa: bool = False) -> str:
    folder = RVC / konfig.RVC_MODEL
    pth = sorted(sumber.glob("*.pth"))
    if not pth:
        baris("GALAT", f"tidak ada .pth di {sumber}")
        return "GALAT"
    hasil = salin(pth[0], folder / f"{konfig.RVC_MODEL}.pth", paksa=paksa)
    if dengan_index:
        idx = sorted(sumber.glob("*.index"))
        if not idx:
            baris("GALAT", f"tidak ada .index di {sumber}")
            hasil = "GALAT"
        else:
            salin(idx[0], folder / f"{konfig.RVC_MODEL}.index", paksa=paksa)
            baris(
                "OK",
                "index dipasang, TAPI default VTUBER_RVC_INDEKS_LAJU=0 membatasinya: "
                "rvc_python membacanya ulang per kalimat (+/-1 GB puncak RAM)",
            )
    else:
        baris(
            "OK",
            "index TIDAK disalin (sengaja): tanpa index suara tetap jalan; "
            "tambah --dengan-index kalau mau mencoba perbedaannya",
        )
    return hasil


def aksi_fixture() -> str:
    TMP.mkdir(parents=True, exist_ok=True)
    tujuan = TMP / "fixture.wav"
    dilarang_ke_e(tujuan)
    byte = wav_mod.pcm_ke_wav(bytes(22050 // 2), 22050, 1)
    tujuan.write_bytes(byte)
    baris("OK", f"fixture {tujuan.relative_to(AKAR)} ({len(byte)} B, 0,5 dtk hening)")
    return "OK"


# ── pemeriksaan ───────────────────────────────────────────────────────────────
def aksi_periksa() -> int:
    """Lapor tanpa menulis apa pun. Keluar bukan-0 kalau ada yang kurang."""
    masalah = 0
    print(f"target tulis   : {AKAR}  (C: -- tidak pernah ke E:)")
    print(f".venv          : {Path(sys.executable)}")
    print(f"base_model     : {folder_site_packages() / 'base_model'}")

    voice = PIPER / f"{konfig.PIPER_SUARA}.onnx"
    if voice.is_file():
        baris("OK", f"piper voice {voice.stat().st_size:,} B")
    else:
        baris("GALAT", f"piper voice belum ada: {voice}")
        baris(" ", "  -> python scripts/sedia_suara.py --piper")
        masalah += 1

    dipasang = folder_site_packages() / "base_model"
    for nama, ukuran in BERKAS_DASAR.items():
        if cocok(dipasang / nama, ukuran):
            baris("OK", f"base_model/{nama} {ukuran:,} B")
        elif cocok(DASAR / nama, ukuran):
            baris("GALAT", f"{nama} ada di proyek tapi belum terpasang ke paket")
            baris(" ", "  -> python scripts/sedia_suara.py --model-dasar")
            masalah += 1
        else:
            jejak = " (sumber: venv terbukti)" if sumber_dasar_ada() else ""
            baris("GALAT", f"{nama} tidak ada di mana pun{jejak}")
            masalah += 1

    pth, idx, nama = _cari_furina()
    if pth:
        baris("OK", f"rvc/{nama} checkpoint {pth.stat().st_size:,} B")
        if idx:
            baris("OK", f"rvc/{nama} index {idx.stat().st_size:,} B (dipakai hanya kalau INDEKS_LAJU>0)")
        else:
            baris(" ", f"rvc/{nama} tanpa index -- itu memang default")
    else:
        baris("GALAT", f"checkpoint rvc '{nama}' belum ada di {RVC}")
        baris(" ", "  -> python scripts/sedia_suara.py --furina")
        masalah += 1

    if VT_RVC_tidak_siap():
        baris("GALAT", "rvc_python belum terinstal (pip install -r requirements.txt)")
        masalah += 1

    if masalah:
        print(f"\n{masalah} hal belum siap.")
    else:
        print("\nsemua aset jalur suara siap.")
    return 1 if masalah else 0


def sumber_dasar_ada() -> bool:
    return (VENV_TERBUKTI / "hubert_base.pt").is_file()


def VT_RVC_tidak_siap() -> bool:
    import importlib.util

    return importlib.util.find_spec("rvc_python") is None


def _cari_furina():
    folder = RVC / konfig.RVC_MODEL
    if not folder.is_dir():
        return (None, None, konfig.RVC_MODEL)
    pth = sorted(folder.glob("*.pth"))
    idx = sorted(folder.glob("*.index"))
    return (pth[0] if pth else None, idx[0] if idx else None, konfig.RVC_MODEL)


def utama() -> int:
    urai = argparse.ArgumentParser(description="sediakan aset jalur suara Elaina")
    urai.add_argument("--periksa", action="store_true", help="lapor tanpa menulis")
    urai.add_argument("--piper", action="store_true", help="unduh voice id_ID")
    urai.add_argument("--model-dasar", action="store_true", help="salin hubert + rmvpe")
    urai.add_argument("--furina", action="store_true", help="salin checkpoint Furina")
    urai.add_argument("--dengan-index", action="store_true", help="sertakan .index 507 MB")
    urai.add_argument("--fixture", action="store_true", help="buat WAV uji tanpa API")
    urai.add_argument("--semua", action="store_true", help="piper + model-dasar + furina")
    urai.add_argument("--paksa", action="store_true", help="salin ulang walau ukuran cocok")
    urai.add_argument("--sumber-dasar", default=str(VENV_TERBUKTI))
    urai.add_argument("--sumber-furina", default=str(FURINA_SUMBER))
    arg = urai.parse_args()

    if not any(
        (arg.periksa, arg.piper, arg.model_dasar, arg.furina, arg.fixture, arg.semua)
    ):
        arg.periksa = True

    hasil = 0
    if arg.piper or arg.semua:
        aksi_piper(arg.paksa)
    if arg.model_dasar or arg.semua:
        aksi_model_dasar(Path(arg.sumber_dasar), arg.paksa)
    if arg.furina or arg.semua:
        aksi_furina(Path(arg.sumber_furina), arg.dengan_index, arg.paksa)
    if arg.fixture:
        aksi_fixture()
    if arg.periksa:
        hasil = aksi_periksa()
    return hasil


if __name__ == "__main__":
    sys.exit(utama())
