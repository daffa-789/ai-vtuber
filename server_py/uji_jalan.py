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
  5. tidak ada alamat/API non-loopback di kode yang dijalankan -- klaim "offline"
     diuji, bukan ditulis
  6. konfigurasi tidak menyimpan cadangan cloud yang bisa dipakai diam-diam

Jalankan:  .venv\\Scripts\\python.exe server_py\\uji_jalan.py
"""

from __future__ import annotations

import io
import re
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
        for terlarang in ("torch", "piper", "rvc_python", "faiss", "numba", "faster_whisper", "ctranslate2"):
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
            konfig.TTS_RANTAI[:] = ["piper+rvc", "piper"]
            konfig.RVC_HIDUP = False
            hasil = jalur_suara.rantai_aktif()
            assert "piper+rvc" not in hasil, f"RVC mati tapi resepnya lolos: {hasil}"
            assert "piper" in hasil, f"piper hilang: {hasil}"

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

    # ── 7. tidak ada satu pun alamat non-loopback di kode yang DIJALANKAN ────
    # Klaim "100% offline" dulu cuma ada di README dan sudah dua kali bohong:
    # Gemini sempat hilang dari kode tapi labelnya tertinggal, dan mic diam-diam
    # masih naik ke server Google. Skrip pengunduh (scripts/) sengaja tidak
    # diperiksa -- itu alat instalasi, bukan runtime. `web/lib/` juga tidak:
    # pustaka vendored penuh URL lisensi di komentar.
    IZIN: dict[str, str] = {
        # berkas -> ALASAN sah ia masih menyentuh luar mesin. KOSONG = "offline
        # total" TERBUKTI, dan itu keadaan yang ingin kita pertahankan. Tiap baris
        # baru di sini adalah keputusan sadar untuk mengirim sesuatu ke cloud;
        # tanpa baris itu, tes ini yang berteriak.
        #
        # Riwayat: dulu berisi "mikrofon.js" (Web Speech API = server Google/MS) dan
        # "model_lokal.py" (URL indeks pip di pesan galat). Keduanya sudah hilang --
        # mic pindah ke Whisper lokal, dan pesan instal sekarang menunjuk
        # requirements.txt, bukan ke alamat.
    }
    POLA_ALAMAT = re.compile(r"https?://([^/\s\"'`<>)]+)", re.I)
    LOOPBACK = ("127.0.0.1", "localhost", "0.0.0.0", "::1", "[::1]")

    def tanpa_alamat_luar():
        akar_web = Path(__file__).resolve().parent.parent / "web"
        target = sorted((Path(__file__).resolve().parent).glob("*.py"))
        target += [p for p in sorted(akar_web.rglob("*")) if p.suffix in (".js", ".html")]
        target = [p for p in target if "lib" not in p.parts and "uji_" not in p.name]
        pelanggar: list[str] = []
        menyentuh_luar: set[str] = set()

        def catat(nama: str, temuan: str) -> None:
            menyentuh_luar.add(nama)
            if nama not in IZIN:
                pelanggar.append(temuan)

        for berkas in target:
            for baris, teks in enumerate(berkas.read_text(encoding="utf-8").splitlines(), 1):
                for host in POLA_ALAMAT.findall(teks):
                    if not host.startswith(LOOPBACK):
                        catat(berkas.name, f"{berkas.name}:{baris} -> {host}")
        # nama API cloud yang tidak meninggalkan URL, tapi sama saja keluar mesin
        for berkas in sorted(akar_web.rglob("*.js")):
            if "lib" in berkas.parts:
                continue
            teks = berkas.read_text(encoding="utf-8")
            for tanda in ("webkitSpeechRecognition", "SpeechRecognition"):
                if tanda in teks:
                    catat(berkas.name, f"{berkas.name} -> {tanda} (STT cloud browser)")
        for nama, alasan in IZIN.items():
            if nama not in menyentuh_luar:
                raise AssertionError(
                    f"{nama} tidak lagi menyentuh luar mesin -- izinkannya masih "
                    f"tertulis: {alasan}. Hapus dari IZIN."
                )
        assert not pelanggar, f"jalur keluar mesin baru: {pelanggar[:6]}"

    cek("kode runtime tidak menyentuh alamat luar", tanpa_alamat_luar)

    # ── 8. tidak ada cadangan cloud yang tersisa di konfigurasi ──────────────
    def tanpa_cadangan_cloud():
        import konfig

        for nama in ("MODEL_CADANGAN", "TTS_CADANGAN"):
            assert getattr(konfig, nama) == [], f"{nama} harus kosong: {getattr(konfig, nama)}"
        assert konfig.LLM_PROVIDER in ("local", "llama_cpp", "vulkan", "ollama"), (
            f"provider chat di luar yang offline: {konfig.LLM_PROVIDER}"
        )
        for resep in konfig.TTS_RANTAI:
            assert re.fullmatch(r"(piper|rvc|piper\+rvc|stub)", resep), (
                f"resep TTS tak dikenal (mungkin sisa cloud): {resep}"
            )

    cek("konfigurasi tidak punya cadangan cloud", tanpa_cadangan_cloud)

    # ── 9. parser .env: komentar sebaris tidak boleh menelan nilainya ────────
    # Dulu `VTUBER_VULKAN_NGL=99  # semua lapis` terbaca utuh sampai komentar,
    # `int()` gagal, dan nilainya diam-diam diganti bawaan -- bug kelas "resep
    # diabaikan tanpa pesan" yang sudah lebih dari sekali terjadi di proyek ini.
    def parser_env():
        import tempfile

        import konfig

        isi = "\n".join(
            [
                "KANG_NUM=99  # semua lapis",
                'KANG_QUOT="#fff"',
                "KANG_MERGE=merah #f00",
                "KANG_NO_SPASI=a#b",
                "KANG_QUOT_SPASI=  'x y'  # catatan",
                "KANG_Bulat=ya  # nyalakan",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            jalur = Path(td) / ".env"
            jalur.write_text(isi, encoding="utf-8")
            hasil = konfig.baca_env(jalur)
        assert hasil["KANG_NUM"] == "99", hasil["KANG_NUM"]
        assert hasil["KANG_QUOT"] == "#fff", hasil["KANG_QUOT"]
        assert hasil["KANG_MERGE"] == "merah", hasil["KANG_MERGE"]
        assert hasil["KANG_NO_SPASI"] == "a#b", hasil["KANG_NO_SPASI"]
        assert hasil["KANG_QUOT_SPASI"] == "x y", hasil["KANG_QUOT_SPASI"]
        # lewat pembaca bertipe juga: di sinilah nilai cacat dulu jadi bawaan diam-diam
        asli = dict(konfig._ENV)
        try:
            konfig._ENV = hasil
            assert konfig.angka("KANG_NUM", -1) == 99
            assert konfig.bool_("KANG_Bulat", False) is True
        finally:
            konfig._ENV = asli

    cek("parser .env memotong komentar tanpa membunuh nilai", parser_env)

    # ── 10. pembaca WAV sisi STT: tolak yang bukan audio, jangan sampai muat model ──
    def pembatas_stt():
        import struct

        import stt_whisper

        wav_sunyi = wav.pcm_ke_wav(bytes(16000 * 2), 16000, 1)  # 1,0 detik hening
        data, laju = stt_whisper.baca_wav(wav_sunyi)
        assert laju == 16000, laju
        assert abs(len(data) / 16000 - 1.0) < 0.01, len(data)

        # Bukan WAV sama sekali.
        for buruk, nama in ((b"RIFF" + bytes(60), "header palsu"), (b"", "kosong")):
            try:
                stt_whisper.baca_wav(buruk)
                raise AssertionError(f"{nama} tidak ditolak")
            except stt_whisper.GalatSTT:
                pass

        # 8-bit: tidak didukung, dan harus bilang begitu -- bukan salah transkrip.
        delapan = (
            b"RIFF"
            + struct.pack("<I", 36 + 100)
            + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8)
            + b"data"
            + struct.pack("<I", 100)
            + bytes(100)
        )
        try:
            stt_whisper.baca_wav(delapan)
            raise AssertionError("WAV 8-bit lolos -- harusnya ditolak, bukan disalahtranskrip")
        except stt_whisper.GalatSTT:
            pass

        # Resample: 22,05 kHz -> 16 kHz harus memendek dengan rasio yang benar.
        data22, _ = stt_whisper.baca_wav(wav.pcm_ke_wav(bytes(22050 * 2), 22050, 1))
        hasil = stt_whisper.resample(data22, 22050)
        assert abs(len(hasil) / 16000 - 1.0) < 0.02, len(hasil)
        assert len(stt_whisper.resample(data22, 16000)) == len(data22), "16k tidak boleh diubah"

    cek("stt_whisper menolak audio buruk & resample benar", pembatas_stt)

    print(f"\n{LOLOS} lulus, {len(GAGAL)} gagal")
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(utama())
