"""Bukti bahwa server BISA naik, bukan hanya bisa dikompilasi.

Lahir dari kecelakaan nyata: `py_compile` LULUS tapi banner memakai nama variabel
yang salah, jadi server mode normal mati saat boot dan semua laporan hijau
sebelumnya ternyata menguji proses lama. Karena itu baris banner dipisah jadi
fungsi murni, dan berkas inilah yang memanggilnya di DUA mode.

Yang dijaga di sini, urut dari yang paling sering diam-diam rusak:
  1. setiap modul bisa diimpor TANPA paket audio terinstal (impor tertunda benar)
  2. banner tercetak di mode stub dan mode normal
  3. rantai engine tersaring benar untuk empat kombinasi konfigurasi
  4. bungkusan WAV mondar-mandir (header yang kita tulis bisa dibaca kembali)

Jalankan:  .venv\\Scripts\\python.exe server_py\\uji_jalan.py
"""

from __future__ import annotations

import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GAGAL: list[str] = []
LOLOS = 0


def cek(nama: str, fungsi) -> None:
    global LOLOS
    try:
        fungsi()
    except Exception as err:
        GAGAL.append(f"{nama}: {type(err).__name__}: {err}")
        print(f"FAIL {nama}: {type(err).__name__}: {err}")
    else:
        LOLOS += 1
        print(f"pass {nama}")


def utama() -> int:
    # ── 1. impor semua modul sisi server ────────────────────────────────────
    def impor_semua():
        import jalur_suara  # noqa: F401
        import konfig  # noqa: F401
        import memori  # noqa: F401
        import statis  # noqa: F401
        import tts_piper  # noqa: F401
        import tts_rvc  # noqa: F401
        import vault  # noqa: F401
        import wav  # noqa: F401

    cek("impor semua modul server", impor_semua)

    import app
    import jalur_suara
    import wav

    # ── 2. modul engine tidak mengimpor paket berat di level modul ──────────
    def tanpa_paket_berat():
        # torch/onnxruntime adalah bukti terberat: kalau ada impor level-modul
        # yang menyeretnya, nama ini sudah ada di sys.modules setelah `import app`.
        for terlarang in ("torch", "piper", "rvc_python", "faiss", "numba"):
            if terlarang in sys.modules:
                raise AssertionError(
                    f"'{terlarang}' sudah termuat hanya karena mengimpor server -- "
                    "impor berat harus tertunda di dalam fungsi"
                )

    cek("server tidak menyeret torch/piper/rvc_python", tanpa_paket_berat)

    # ── 3. banner dua mode ──────────────────────────────────────────────────
    def banner_dua_mode():
        import konfig

        asli = konfig.STUB
        try:
            # Yang dimutasi adalah konfig.STUB, BUKAN app.STUB: app.py sekarang
            # membaca atribut itu juga. Dulu app.py mengimpor STUB sebagai nama,
            # jadi tes yang menyetel app.STUB menguji bindings yang tidak dipakai
            # runtime -- hijau palsu, dan jalur_suara tetap mengira ini mode normal.
            konfig.STUB = True
            stub = app.baris_banner(9999)
            assert "9999" in stub, f"nomor port tidak muncul: {stub}"
            assert "stub" in stub.lower(), f"mode stub tidak mengaku: {stub}"
            konfig.STUB = False
            normal = app.baris_banner(9999)
            assert "stub" not in normal.split("memori=")[0].lower(), (
                f"banner normal mengaku stub: {normal}"
            )
            assert normal != stub, "kedua mode menghasilkan baris yang sama"
        finally:
            konfig.STUB = asli

    cek("banner mode stub dan mode normal", banner_dua_mode)

    # ── 4. rantai engine tersaring benar ────────────────────────────────────
    def rantai_disaring():
        import konfig

        asli = (list(konfig.TTS_RANTAI), konfig.RVC_HIDUP)
        try:
            konfig.TTS_RANTAI[:] = ["piper+rvc", "gemini"]
            konfig.RVC_HIDUP = False
            hasil = jalur_suara.rantai_aktif()
            assert "piper+rvc" not in hasil, f"RVC mati tapi resepnya lolos: {hasil}"
            assert "gemini" in hasil or konfig.KUNCI == "", f"gemini hilang: {hasil}"

            konfig.TTS_RANTAI[:] = ["rekayasa-total"]
            assert jalur_suara.rantai_aktif() == [], "nilai tak dikenal tidak dibuang"
            assert jalur_suara.peringatan(), "tahap tak dikenal harus dilaporkan, bukan diabaikan"
        finally:
            konfig.TTS_RANTAI[:] = asli[0]
            konfig.RVC_HIDUP = asli[1]

    cek("rantai_aktif menyaring & memperingatkan", rantai_disaring)

    # ── 5. WAV mondar-mandir ────────────────────────────────────────────────
    def wav_roundtrip():
        pcm = bytes(22050 * 2)  # 16-bit mono: 2 byte per sampel -> tepat 1,0 detik
        byte = wav.pcm_ke_wav(pcm, 22050, 1)
        assert wav.sudah_wav(byte), "hasil sendiri tidak diakui sebagai WAV"
        laju, kanal, detik = wav.baca_header(byte)
        assert (laju, kanal) == (22050, 1), f"header salah: {laju} {kanal}"
        assert 0.99 < detik < 1.01, f"durasi salah: {detik}"
        with wave.open(io.BytesIO(byte), "rb") as w:
            assert len(w.readframes(w.getnframes())) == len(pcm), "isi PCM berubah panjang"
        assert not wav.sudah_wav(bytes(100)), "PCM mentah tidak boleh lolos"
        try:
            wav.baca_header(b"RIFF" + bytes(40))
            raise AssertionError("header palsu tidak ditolak")
        except wav.WavRusak:
            pass

    cek("pcm_ke_wav / sudah_wav / baca_header", wav_roundtrip)

    # ── 5b. puncak() harus membaca SELURUH berkas, bukan kepalanya saja ──────
    def puncak_bukan_sepotong():
        import math
        import struct

        senyap = bytes(40000)  # 0,5 detik sunyi di depan -- persis ramp RVC
        nada = b"".join(
            struct.pack("<h", int(20000 * math.sin(2 * math.pi * 300 * i / 40000)))
            for i in range(80000)
        )
        berkas = wav.pcm_ke_wav(senyap + nada, 40000, 1)
        _, _, detik = wav.baca_header(berkas)
        assert 2.2 < detik < 2.6, f"durasi salah: {detik}"
        assert wav.puncak(berkas) > 10000, (
            f"audiobersuara nyaring dinilai bisu: puncak={wav.puncak(berkas)} "
            "-- ini persis bug yang membuat semua kalimat RVC ditolak"
        )
        assert wav.puncak(wav.pcm_ke_wav(bytes(40000), 40000, 1)) == 0, "hening sungguhan tidak bernilai 0"

    cek("puncak() membaca seluruh berkas", puncak_bukan_sepotong)

    # ── 6. env_web tetap membatasi bocoran ke browser ───────────────────────
    def pagar_browser():
        import konfig

        bocor = [k for k in konfig.env_web() if not k.startswith("VITE_")]
        assert not bocor, f"kunci server bocor ke browser: {bocor[:5]}"

    cek("env_web hanya meloloskan VITE_*", pagar_browser)

    print(f"\n{LOLOS} lulus, {len(GAGAL)} gagal")
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(utama())
