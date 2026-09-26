"""Ukur jalur suara sebelum ada yang mengklaim apa pun.

Aturan proyek ini: angka latensi hanya boleh masuk README kalau ada berkas yang
membangkitkannya, bercap tanggal. Skrip inilah berkas itu.

    python scripts/uji_latensi.py --resep piper --kalimat 10
    python scripts/uji_latensi.py --resep piper+rvc --f0 pm,rmvpe --kalimat 10
    python scripts/uji_latensi.py --resep rvc --audio "E:/Asset RVC/Model/Furina Model/furina1.wav"
    python scripts/uji_latensi.py --resep piper+rvc --mendiagnosa

`--audio` melompati Piper: berguna untuk mengadili RVC saja, termasuk sebelum
voice Piper sempat diunduh.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "server_py"))

import konfig  # noqa: E402
import tts_piper  # noqa: E402
import tts_rvc  # noqa: E402
import wav as wav_mod  # noqa: E402

# Kalimat nyata dari log percakapan, bukan lorem ipsum: panjangnya yang menentukan
# RTF, dan jawaban Elaina biasanya 2-4 kalimat pendek.
KALIMAT = [
    "Selamat malam, Master.",
    "Apa kabar hari ini?",
    "Saya sedang tidak ingin mengurus perkara orang lain.",
    "Kalau Master minta tolong, saya bantu, tapi saya protes dulu.",
    "Ada untungnya tidak untuk saya?",
    "Master sudah makan belum?",
    "Saya hanya lewat, kebetulan saja mampir.",
    "Itu keputusan Master, bukan keputusan saya.",
    "Capek juga jadi yang paling waras di sini.",
    "Lima menit lagi, setelah itu saya pergi.",
    "Jangan sentuh tas saya.",
    "Baik, saya kerjakan. Sekali ini saja.",
]


def rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


def statistik(isi: list[float]) -> tuple[float, float]:
    if not isi:
        return (0.0, 0.0)
    urut = sorted(isi)
    p95 = urut[min(len(urut) - 1, int(round(0.95 * (len(urut) - 1))))]
    return (statistics.median(isi), p95)


def ukur_piper(banyak: int) -> list[dict]:
    hasil = []
    for i in range(banyak):
        teks = KALIMAT[i % len(KALIMAT)]
        t0 = time.perf_counter()
        try:
            audio = tts_piper.sintesis(teks)
        except Exception as err:
            print(f"  piper GALAT: {err}", file=sys.stderr)
            return hasil
        detik = time.perf_counter() - t0
        _, _, panjang = wav_mod.baca_header(audio)
        hasil.append({"tahap": "piper", "detik": detik, "audio": panjang})
    return hasil


def ukur_rvc(banyak: int, sumber: bytes | None) -> list[dict]:
    hasil = []
    for i in range(banyak):
        if sumber is None:
            teks = KALIMAT[i % len(KALIMAT)]
            try:
                sumber_kalimat = tts_piper.sintesis(teks)
            except Exception as err:
                print(f"  piper GALAT (sumber RVC): {err}", file=sys.stderr)
                return hasil
        else:
            sumber_kalimat = sumber
        t0 = time.perf_counter()
        try:
            audio = tts_rvc.ubah(sumber_kalimat, f"uji-{i}")
        except Exception as err:
            print(f"  rvc GALAT: {str(err)[:200]}", file=sys.stderr)
            raise
        detik = time.perf_counter() - t0
        _, _, panjang = wav_mod.baca_header(audio)
        hasil.append({"tahap": f"rvc/{konfig.RVC_F0}", "detik": detik, "audio": panjang})
    return hasil


def tampil(baris: list[dict]) -> tuple[float, float]:
    per_tahap: dict[str, list[float]] = {}
    per_rtf: dict[str, list[float]] = {}
    audio_total = 0.0
    detik_total = 0.0
    for b in baris:
        per_tahap.setdefault(b["tahap"], []).append(b["detik"])
        if b["audio"] > 0:
            per_rtf.setdefault(b["tahap"], []).append(b["detik"] / b["audio"])
        audio_total += b["audio"]
        detik_total += b["detik"]
    print(f"  {'tahap':<12} {'median':>8} {'p95':>8} {'RTF':>7} {'n':>4}")
    for nama in sorted(per_tahap):
        med, p95 = statistik(per_tahap[nama])
        rtf = statistik(per_rtf.get(nama, [0.0]))[0]
        print(f"  {nama:<12} {med:7.2f}s {p95:7.2f}s {rtf:6.2f}  {len(per_tahap[nama]):4}")
    return (detik_total, audio_total)


def keputusan(rtf: float, kalimat_pertama: float) -> str:
    """Salinan harfiah tabel gerbang di berkas rencana -- supaya yang memutuskan
    angka, bukan siapa yang sedang memegang keyboard."""
    if rtf <= 1.0:
        return f"RTF {rtf:.2f} <= 1.0: Real-time aman, rekomendasi default: piper+rvc"
    if rtf <= 2.0:
        return f"RTF {rtf:.2f}: Sedikit di atas real-time, rekomendasi: piper+rvc dengan cache atau fallback piper"
    return f"RTF {rtf:.2f} > 2.0: Rekomendasi pakai piper murni untuk latensi cepat atau nyalakan VTUBER_TTS_CACHE"


def utama() -> int:
    urai = argparse.ArgumentParser(description="ukur latensi jalur suara")
    urai.add_argument("--resep", default="piper+rvc")
    urai.add_argument("--kalimat", type=int, default=10)
    urai.add_argument("--f0", default="pm,rmvpe")
    urai.add_argument("--audio", default="", help="WAV sumber; melompati Piper")
    urai.add_argument("--index", default="", help="mis. 0,0.5 untuk mengadu index")
    urai.add_argument("--mendiagnosa", action="store_true")
    arg = urai.parse_args()

    sumber = None
    if arg.audio:
        jalur = Path(arg.audio)
        if not jalur.is_file():
            print(f"berkas audio tidak ada: {jalur}", file=sys.stderr)
            return 2
        sumber = jalur.read_bytes()

    mau_piper = "piper" in arg.resep
    mau_rvc = "rvc" in arg.resep

    print(f"mesin: {AKAR} | RSS awal {rss_mb():.0f} MB")
    if mau_piper:
        t0 = time.perf_counter()
        if not tts_piper.muat():
            print(f"piper tidak siap: {tts_piper.alasan_tidak_tersedia()}", file=sys.stderr)
            return 2
        print(f"muat piper {time.perf_counter() - t0:.2f} s")

    semua: list[dict] = []
    angka = []
    for f0 in (arg.f0.split(",") if mau_rvc else ["-"]):
        if mau_rvc:
            konfig.RVC_F0 = f0.strip()
        baris = []
        if mau_piper:
            baris += ukur_piper(arg.kalimat)
        if mau_rvc:
            t0 = time.perf_counter()
            try:
                tts_rvc.muat()
                print(f"muat rvc (f0={konfig.RVC_F0}) {time.perf_counter() - t0:.1f} s")
                baris += ukur_rvc(arg.kalimat, sumber)
            except Exception as err:
                print(f"  rvc f0={konfig.RVC_F0} gagal: {str(err)[:160]}", file=sys.stderr)
                if arg.mendiagnosa:
                    bahan = sumber or (baris[-1].get("_wav") if baris else None)
                    if bahan is None and tts_piper.tersedia():
                        bahan = tts_piper.sintesis(KALIMAT[0])
                    if bahan:
                        print(tts_rvc.diagnostik(bahan), file=sys.stderr)
                continue
        print(f"\nresep={arg.resep} f0={konfig.RVC_F0} kalimat={arg.kalimat}")
        detik, audio = tampil(baris)
        rtf = detik / audio if audio else 0.0
        pertama = next((b["detik"] for b in baris), 0.0)
        print(f"  total {detik:.2f} s untuk {audio:.2f} s audio | RTF {rtf:.2f} | RSS {rss_mb():.0f} MB")
        print(f"  {keputusan(rtf, pertama)}")
        angka.append((konfig.RVC_F0, rtf))
        semua += baris

    if len(angka) > 1:
        angka.sort(key=lambda x: x[1])
        print(f"\nUSULAN: f0={angka[0][0]} (RTF {angka[0][1]:.2f}) mengalahkan "
              + ", ".join(f"{n}={r:.2f}" for n, r in angka[1:]))
        print("  tapi kualitas tetap harus didengar -- lihat langkah telinga Master.")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
