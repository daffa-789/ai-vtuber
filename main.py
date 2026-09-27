"""Satu titik masuk untuk Silver Wolf: `python main.py`.

Flask memegang sisi HTTP (halaman + /api/*), dan SEMUA kerja berat tetap di modul
yang sudah ada di `server_py/` -- `model_lokal` / `model_vulkan` untuk chat,
`jalur_suara` untuk suara, `stt_whisper` untuk mic, `vault` untuk memori, `statis`
untuk sajian berkas. Berkas ini tidak meniru logika mereka; kalau ada yang perlu
berubah di salah satu jalur itu, cukup diubah di satu tempat.

Dibanding server stdlib `http.server` yang lama: rute dan statusnya identik, jadi
`web/*.js` di browser tidak disentuh sedikit pun. Yang dapat dari Flask cuma bentuk
kodenya -- dekorator rute, bukan if/elif pada self.path.

Port dibaca dari VTUBER_PORT. 0 berarti cari port bebas sendiri: mesin ini dipakai
banyak proyek sekaligus, jadi tidak ada nomor port yang dipatok di kode ini.

Jalankan:  .venv\\Scripts\\python.exe main.py      lalu buka http://127.0.0.1:8787/
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

AKAR = Path(__file__).resolve().parent
if str(AKAR / "server_py") not in sys.path:
    sys.path.insert(0, str(AKAR / "server_py"))

warnings.filterwarnings("ignore", category=FutureWarning)
for _sunyi in ("faiss", "fairseq", "rvc_python", "httpx", "huggingface_hub"):
    logging.getLogger(_sunyi).setLevel(logging.WARNING)
# Werkzeug berisik dua kali (banner "development server" + satu baris per permintaan).
# Untuk jendela pet itu hanya sampah di bawah ikon; peredaman lewat logger karena
# app.run() tidak lagi menerima parameter min_level di Werkzeug 3.
logging.getLogger("werkzeug").setLevel(logging.ERROR)

from flask import Flask, Response, abort, request  # noqa: E402

import jalur_suara  # noqa: E402
import jendela  # noqa: E402
import konfig  # noqa: E402
import memori  # noqa: E402
import model_lokal  # noqa: E402
import model_vulkan  # noqa: E402
import ollama_client  # noqa: E402
import statis  # noqa: E402
import stt_whisper  # noqa: E402
import tts_rvc  # noqa: E402
import vault  # noqa: E402
from konfig import (  # noqa: E402
    AKAR_PERSONA,
    MAKS_AUDIO,
    MAKS_BODY,
    MAKS_KARAKTER,
    MAKS_PESAN,
    PORT,
)
from wav import pcm_ke_wav  # noqa: E402

PERSONA = AKAR_PERSONA.read_text(encoding="utf-8")

# Aliran kalengan untuk VTUBER_STUB=1. Sengaja dipecah di tengah tag ('[se' +
# 'nyum]') supaya pengupas tag di web/ekspresi.js ikut terpakai, bukan hanya jalur
# yang rapi.
POTONGAN_STUB = ["[se", "nyum] Halo ", "Master.", " [sebal] kok", " diam sih"]

# Pesan "GPU tidak dipakai" terakhir yang sudah diberitakan. Sekali per perubahan,
# supaya log tidak berteriak 20 kali untuk satu jawaban panjang.
PERINGATAN_JATUH = ""

app = Flask(__name__, static_folder=None)


# ── pembantu ─────────────────────────────────────────────────────────────────
def _pacu(aliran):
    """Paksa token pertama keluar SEBELUM status 200 dikirim.

    `model_lokal.alir()` dan `model_vulkan.alir()` sama-sama generator: memanggilnya
    tidak menjalankan apa pun, jadi `try` di sekitar pemanggilan itu tidak pernah
    menangkap galat boot. Tanpa fungsi ini, model yang hilang menghasilkan jawaban
    kosong ber-status 200 dan 503 yang ditulis kode tidak pernah tercapai.
    """
    pertama = next(aliran, None)
    if pertama is None:
        return iter(())

    def lanjut():
        yield pertama
        yield from aliran

    return lanjut()


def rapikan_riwayat(raw) -> list[dict]:
    """Peran dibatasi ke dua nilai yang dikenali engine, isi dipotong pendek."""
    if not isinstance(raw, list):
        return []
    hasil = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        isi = m.get("content")
        if not isinstance(isi, str) or not isi.strip():
            continue
        hasil.append(
            {
                "role": "model" if m.get("role") == "assistant" else "user",
                "parts": [{"text": isi[:MAKS_KARAKTER]}],
            }
        )
    return hasil[-MAKS_PESAN:]


def _body(batas: int) -> bytes:
    """Baca badan permintaan dengan plafon nyata, bukan hanya dari header."""
    panjang = request.content_length or 0
    if panjang > batas:
        abort(413)
    data = request.get_data(cache=False)
    if len(data) > batas:
        abort(413)
    return data


def _json(data: dict, kode: int = 200, **kepala) -> Response:
    jawab = Response(
        json.dumps(data, ensure_ascii=False),
        status=kode,
        mimetype="application/json",
    )
    for k, v in kepala.items():
        jawab.headers[k] = v
    return jawab


def port_bebas() -> int:
    """VTUBER_PORT=0: kernel yang memilih. Ada balapan kecil (dilepas lalu dipakai
    lagi) -- harganya murah dibanding menabrak port proyek lain di mesin ini."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── halaman & aset statis ────────────────────────────────────────────────────
@app.after_request
def _cors(jawab: Response) -> Response:
    # Halaman dan API asalnya sama (127.0.0.1:port), jadi ini hanya menjaga agar
    # /perkakas.html dan pembuka tab lain di mesin yang sama tidak ditolak browser.
    jawab.headers.setdefault("Access-Control-Allow-Origin", "*")
    jawab.headers.setdefault("Access-Control-Allow-Headers", "content-type")
    jawab.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return jawab


def _saji(berkas: Path) -> Response:
    tanda = statis.tanda(berkas)
    jawab = Response(
        statis.isi(berkas),
        mimetype=statis.tipe(berkas).split(";")[0] or None,
        headers={"Cache-Control": statis.kebijakan(berkas)},
    )
    # HTML harus persis charset-nya seperti yang dipakai server lama.
    if berkas.suffix == ".html":
        jawab.headers["Content-Type"] = statis.tipe(berkas)
    jawab.headers["ETag"] = tanda
    # make_conditional(): Werkzeug yang membandingkan If-None-Match (dan If-Range /
    # HEAD / metode). Mencocokkan string sendiri di sini pernah salah -- `request.
    # if_none_match` itu objek ETags, bukan string, dan percobaan pertama melempar
    # AttributeError yang membuat SEMUA berkas statis balas 500.
    return jawab.make_conditional(request)


@app.get("/")
def halaman():
    berkas = statis.cari("/index.html")
    if berkas is None:
        abort(404)
    return _saji(berkas)


@app.get("/<path:jalur>")
def aset(jalur: str):
    if jalur.startswith("api/"):
        abort(404)  # API hanya punya rute tersurat di bawah; jangan samar-samar
    berkas = statis.cari("/" + jalur)
    if berkas is None:
        abort(404)
    return _saji(berkas)


# ── health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    if konfig.STUB:
        model_info = "stub"
    elif konfig.LLM_PROVIDER == "vulkan":
        model_info = (
            model_vulkan.ringkasan()
            if model_vulkan.siap()
            else f"vulkan/tidak-jalan ({model_vulkan.alasan_tidak_tersedia()})"
        )
    elif konfig.LLM_PROVIDER in ("local", "llama_cpp"):
        berkas_m = model_lokal.cari_model(konfig.LOCAL_MODEL_PATH)
        model_info = f"local/{berkas_m.name}" if berkas_m else "local/belum-ada-model"
    elif konfig.LLM_PROVIDER == "ollama":
        model_info = f"ollama/{konfig.OLLAMA_MODEL}"
    else:
        model_info = konfig.LLM_PROVIDER

    return _json(
        {
            "ok": True,
            "model": model_info,
            "cadangan": [PERINGATAN_JATUH] if PERINGATAN_JATUH else [],
            "key": True,
            "tts": jalur_suara.ringkasan(),
            "stt": {
                "hidup": konfig.STT_HIDUP,
                "model": konfig.STT_MODEL,
                "siap": stt_whisper.tersedia(),
                "alasan": stt_whisper.alasan_tidak_tersedia(),
            },
            "memori": "vault Obsidian" if vault.tersedia() else vault.alasan_tidak_tersedia(),
            "sisi": "python",
        }
    )


# ── chat ─────────────────────────────────────────────────────────────────────
def _siapkan_aliran(riwayat: list[dict], fakta: list, mood):
    """Bangun pesan + pacu token pertama. (aliran, nama, galat) -- galat masih bisa
    muncul di tengah aliran, dan itu tidak bisa lagi diubah jadi status HTTP."""
    if konfig.LLM_PROVIDER in ("local", "llama_cpp", "vulkan"):
        pesan = [{"role": "system", "content": memori.gabung_system_lokal(fakta, mood)}]
        for m in riwayat:
            peran = "assistant" if m.get("role") in ("assistant", "model") else "user"
            isi = (
                " ".join(p.get("text", "") for p in m.get("parts", []))
                if "parts" in m
                else m.get("content", "")
            )
            pesan.append({"role": peran, "content": isi})

        berkas = model_lokal.cari_model(konfig.LOCAL_MODEL_PATH)
        nama_model = berkas.name if berkas else "gguf"

        if konfig.LLM_PROVIDER == "vulkan":
            global PERINGATAN_JATUH
            try:
                return _pacu(model_vulkan.alir(pesan)), f"vulkan/{nama_model}", None
            except model_lokal.ModelLokalError as err:
                # Jatuh ke CPU masih offline, jadi boleh -- TAPI harus berisik:
                # dicetak, dan dilaporkan lewat x-model + /api/health.
                if PERINGATAN_JATUH != err.pesan:
                    PERINGATAN_JATUH = err.pesan
                    print(f"GPU tidak dipakai, kembali ke CPU: {err.pesan}", file=sys.stderr)

        def cpu():
            yield from model_lokal.alir(
                pesan,
                jalur_kandidat=konfig.LOCAL_MODEL_PATH,
                threads=konfig.LOCAL_MODEL_THREADS,
                n_ctx=konfig.LOCAL_MODEL_CTX,
            )

        try:
            return _pacu(cpu()), f"local/{nama_model}", None
        except model_lokal.ModelLokalError as err:
            return None, "", err

    if konfig.LLM_PROVIDER == "ollama":
        pesan = [{"role": "system", "content": memori.gabung_system(PERSONA, fakta, mood)}]
        for m in riwayat:
            peran = "assistant" if m["role"] == "assistant" else "user"
            isi = (
                " ".join(p.get("text", "") for p in m.get("parts", []))
                if "parts" in m
                else m.get("content", "")
            )
            pesan.append({"role": peran, "content": isi})
        try:
            aliran = ollama_client.alir(konfig.OLLAMA_MODEL, pesan, konfig.OLLAMA_URL)
            return _pacu(aliran), f"ollama/{konfig.OLLAMA_MODEL}", None
        except ollama_client.OllamaError as err:
            return None, "", err

    return (
        None,
        "",
        model_lokal.ModelLokalError(
            f"Provider '{konfig.LLM_PROVIDER}' tidak dikenal. Sistem berjalan offline: "
            "gunakan 'local', 'vulkan', atau 'ollama'."
        ),
    )


@app.post("/api/chat")
def chat():
    if konfig.STUB:
        return _chat_stub()

    try:
        riwayat = rapikan_riwayat(json.loads(_body(MAKS_BODY).decode("utf-8")).get("messages"))
    except json.JSONDecodeError:
        return _json({"error": "body harus JSON: { messages: [{role, content}] }"}, 400)

    if not riwayat:
        return _json({"error": "riwayat kosong"}, 400)

    # Memori dibaca lebih dulu supaya yang dia ingat ikut membentuk jawaban ini.
    fakta, mood = [], None
    if vault.tersedia():
        try:
            fakta, mood = vault.baca_fakta(), vault.baca_mood()
        except Exception as err:
            print(f"memori tidak terbaca: {err}", file=sys.stderr)

    aliran, terpakai, galat = _siapkan_aliran(riwayat, fakta, mood)
    if galat is not None:
        kode = 400 if "tidak dikenal" in galat.pesan else 503
        return _json({"error": galat.pesan}, kode)

    def tubuh_jawaban():
        mentah = ""
        try:
            for potong in aliran:
                mentah += potong
                # direct_passthrough=True melompati konversi str->bytes Flask, jadi
                # generator ini WAJIB menulis byte. Bukti: tanpa .encode(), server
                # menjawab "applications must write bytes" dan aliran keluar kosong.
                yield potong.encode("utf-8")
            # Setelah byte pertama terkirim status tidak bisa diubah lagi, jadi
            # kegagalan di tengah aliran cukup menutupnya; frontend menampilkan parsial.
            threading.Thread(
                target=simpan_memori, args=(riwayat, mentah, fakta, mood), daemon=True
            ).start()
        except ConnectionError:
            print("halaman menutup aliran", file=sys.stderr)
        except Exception as err:
            print(f"aliran terputus: {err}", file=sys.stderr)

    return Response(
        tubuh_jawaban(),
        mimetype="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "x-model": terpakai,
        },
        direct_passthrough=True,
    )


@app.get("/api/chat")
def chat_metode_salah():
    return _json({"error": "gunakan POST untuk /api/chat"}, 405)


def _chat_stub() -> Response:
    """Aliran kalengan: menguji rantai stream -> tag -> wajah tanpa model apa pun."""

    def tubuh():
        for potong in POTONGAN_STUB:
            yield potong.encode("utf-8")  # direct_passthrough: harus byte
            time.sleep(0.12)

    return Response(
        tubuh(),
        mimetype="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "x-model": "stub"},
        direct_passthrough=True,
    )


# ── tts ──────────────────────────────────────────────────────────────────────
@app.post("/api/tts")
def tts():
    if konfig.STUB:
        return Response(
            pcm_ke_wav(bytes(4800), 24000, 1),
            mimetype="audio/wav",
            headers={"x-tts-model": "stub", "Cache-Control": "no-store"},
        )

    try:
        teks = str(json.loads(_body(MAKS_BODY).decode("utf-8")).get("text") or "")[:MAKS_KARAKTER]
    except json.JSONDecodeError:
        return _json({"error": "body harus JSON: { text }"}, 400)

    if not teks.strip():
        return _json({"error": "teks kosong"}, 400)

    # Seluruh engine suara lokal (Piper + RVC) berjalan 100% offline tanpa API key.
    try:
        wav, terpakai = jalur_suara.bangun(teks)
    except jalur_suara.SemuaEngineGagal as err:
        for catatan in err.catatan:
            print(f"TTS: {catatan}", file=sys.stderr)
        return _json({"error": str(err)}, 503)

    return Response(
        wav,
        mimetype="audio/wav",
        headers={"x-tts-model": terpakai, "Cache-Control": "no-store"},
    )


# ── stt ──────────────────────────────────────────────────────────────────────
@app.post("/api/stt")
def stt():
    """WAV dari browser -> teks, dibuat di mesin ini (tidak ada yang naik ke cloud).

    Engine yang tidak ada dijawab 503 dengan cara memasang -- BUKAN {"teks": ""}
    seperti dulu, karena "transkripsi kosong" tidak bisa dibedakan dari "tidak ada
    engine" dan itu membuat orang menyalahkan mikrofonnya sendiri.
    """
    if not konfig.STT_HIDUP:
        return _json({"error": "STT dimatikan (VTUBER_STT=tidak)"}, 503)
    if not stt_whisper.tersedia():
        return _json({"error": stt_whisper.alasan_tidak_tersedia()}, 503)

    body = _body(MAKS_AUDIO)
    if len(body) < 100:
        return _json({"error": "audio terlalu pendek"}, 400)

    try:
        teks = stt_whisper.transkripsi(body)
    except stt_whisper.GalatSTT as err:
        print(f"STT: {err.pesan}", file=sys.stderr)
        return _json({"error": err.pesan}, 503)

    return _json({"teks": teks, "mesin": f"whisper/{konfig.STT_MODEL}"})


# ── memori karakter ──────────────────────────────────────────────────────────
def simpan_memori(riwayat: list, mentah: str, fakta_lama: list, mood_lama: dict | None) -> None:
    """Ditulis SETELAH balasan terkirim: vault mati tidak boleh merusak percakapan
    yang sudah terjawab."""
    if konfig.STUB or not vault.tersedia() or not mentah.strip():
        return  # STUB: percakapan uji tidak boleh menodai riwayat karakter
    try:
        tag_cocok = re.match(r"\s*[`'\"“”]*\s*\[([^\]]{1,20})\]", mentah)
        tag = tag_cocok.group(1).lower() if tag_cocok else None
        isi = re.sub(r"^\s*[`'\"“”]*\s*\[[^\]]{1,20}\][`'\"“”]*\s*", "", mentah).strip()
        tanya = ""
        if riwayat and isinstance(riwayat[-1], dict):
            if "parts" in riwayat[-1] and riwayat[-1]["parts"]:
                tanya = riwayat[-1]["parts"][0].get("text", "")
            else:
                tanya = riwayat[-1].get("content", "")

        mood = memori.perbarui_mood(mood_lama, tag)
        vault.catat_hari(f"**Master:** {tanya} → **Silver Wolf:** {isi} _({tag or 'tanpa tag'})_")
        vault.simpan_mood(mood)
    except Exception as err:
        print(f"memori gagal ditulis: {err}", file=sys.stderr)


# ── boot ─────────────────────────────────────────────────────────────────────
def baris_banner(nomor: int) -> str:
    """Satu baris "siap" saat server naik. FUNGSI MURNI: tidak menyalakan proses apa
    pun -- yang memanas-manas ada di utama()."""
    if konfig.STUB:
        model_chat = "stub"
    elif konfig.LLM_PROVIDER == "vulkan":
        berkas_m = model_lokal.cari_model(konfig.LOCAL_MODEL_PATH)
        nama = berkas_m.name if berkas_m else "belum ada di folder model/"
        if model_vulkan.tersedia():
            model_chat = (
                f"vulkan/{nama} ngl={konfig.VULKAN_NGL} "
                f"fa={'on' if konfig.VULKAN_FA else 'off'}"
            )
        else:
            # Diakui di baris pertama, bukan di log yang tidak dibaca siapa-siapa.
            model_chat = f"CPU/{nama} (GPU: {model_vulkan.alasan_tidak_tersedia()})"
    elif konfig.LLM_PROVIDER in ("local", "llama_cpp"):
        berkas_m = model_lokal.cari_model(konfig.LOCAL_MODEL_PATH)
        model_chat = f"local/{berkas_m.name if berkas_m else 'belum ada di folder model/'}"
    elif konfig.LLM_PROVIDER == "ollama":
        model_chat = f"ollama/{konfig.OLLAMA_MODEL}"
    else:
        model_chat = konfig.LLM_PROVIDER

    memori_baris = "vault Obsidian" if vault.tersedia() else vault.alasan_tidak_tersedia()
    if konfig.STUB:
        memori_baris += " (diam, tidak ditulis)"
    siap = jalur_suara.rantai_aktif()
    tts_baris = "stub (hening 0,2 dtk)" if konfig.STUB else (",".join(siap) or "TIDAK ADA")
    if konfig.STUB or not konfig.STT_HIDUP:
        stt_baris = "mati"
    elif stt_whisper.tersedia():
        stt_baris = f"whisper/{konfig.STT_MODEL}"
    else:
        stt_baris = f"TIDAK ADA ({stt_whisper.alasan_tidak_tersedia()})"

    baris = (
        f"silverwolf http://127.0.0.1:{nomor} | mode=100% OFFLINE | "
        f"chat={model_chat} | tts={tts_baris} | stt={stt_baris} | memori={memori_baris}"
    )
    if konfig.STUB:
        return baris
    for catatan in jalur_suara.peringatan():
        baris += f"\n  ! {catatan}"
    return baris


def utama(argumen: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Silver Wolf -- AI Qoder desktop Live2D, 100% offline.",
    )
    p.add_argument("--browser", action="store_true",
                   help="tanpa jendela pet: Flask saja, buka sendiri di browser")
    p.add_argument("--pet", action="store_true",
                   help="paksa jendela pet melayang di desktop")
    args = p.parse_args(argumen)

    tampak = konfig.TAMPAK
    if args.browser:
        tampak = "browser"
    if args.pet:
        tampak = "pet"

    jalur_suara.mula()
    nomor = PORT or port_bebas()
    base = f"http://127.0.0.1:{nomor}"
    try:
        print(baris_banner(nomor), flush=True)

        # Panaskan sebelum permintaan pertama: membaca 1,9 GB GGUF + kompilasi shader
        # Vulkan itu 5-15 dtk, dan kalau terjadi DI DALAM /api/chat, kalimat pertama
        # melewati batas waktunya dan yang didengar bukan hasilnya.
        if konfig.LLM_PROVIDER == "vulkan" and not konfig.STUB and konfig.VULKAN_MUAT_BOOT:
            t0 = time.monotonic()
            if model_vulkan.mulai():
                print(
                    f"  vulkan: llama-server siap dalam {time.monotonic() - t0:.1f} dtk",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                print(
                    f"  ! vulkan tidak jalan, chat jatuh ke CPU: {model_vulkan.alasan_tidak_tersedia()}",
                    file=sys.stderr,
                    flush=True,
                )
        if konfig.RVC_MUAT_BOOT and not konfig.STUB and tts_rvc.hidup():
            try:
                tts_rvc.muat()
                print("  rvc: model dimuat saat boot", file=sys.stderr, flush=True)
            except Exception as err:
                print(f"  ! rvc tidak bisa dimuat: {err}", file=sys.stderr, flush=True)
        if konfig.STT_MUAT_BOOT and not konfig.STUB and stt_whisper.tersedia():
            stt_whisper.muat()

        if tampak == "pet":
            # Flask di thread samping; JENDELA di proses ANAK, bukan di sini.
            #
            # Alasannya terukur, bukan dugaan: dengan RVC (torch + fairseq +
            # onnxruntime) dimuat di proses ini, `webview.start()` kembali seketika
            # tanpa satu baris galat pun -- WinForms/WebView2 menuntut thread utama
            # ber-apartment STA dan COM-nya sudah disetel lebih dulu oleh tumpukan
            # audio. Tanpa RVC di proses yang sama, jendela muncul dengan benar.
            # Jadi: server + engine tetap di sini, GUI dapat proses sendiri yang
            # bersih. Anak mengawasi PID induknya dan menutup diri kalau induk mati.
            #
            # CATATAN: `app.run(min_level=...)` TIDAK ADA di Werkzeug 3 dan melempar
            # TypeError yang membunuh thread ini dalam sekejap, sehingga /api/health
            # tidak pernah menjawab dan jendela tidak pernah muncul. Peredaman log
            # dilakukan lewat logger 'werkzeug', bukan lewat parameter run().
            galat_serve: list[BaseException] = []

            def serve():
                try:
                    app.run(
                        host="127.0.0.1", port=nomor, threaded=True,
                        debug=False, use_reloader=False,
                    )
                except BaseException as err:  # jangan sampai mati tanpa jejak
                    galat_serve.append(err)

            pelayan = threading.Thread(target=serve, daemon=True)
            pelayan.start()
            if not jendela.tunggu_siap(base, pelayan=pelayan):
                pesan = galat_serve[0] if galat_serve else "batas waktu habis"
                print(f"  ! sisi web tidak siap ({pesan}); jendela tidak dibuka", file=sys.stderr, flush=True)
                return 1

            print(f"  pet: {base}/?tampak=pet  (klik kanan pada dia untuk ngobrol)", flush=True)
            anak = subprocess.Popen(
                [sys.executable, str(AKAR / "server_py" / "jendela.py"), base, str(os.getpid())],
                cwd=str(AKAR),
            )
            kode = anak.wait()
            if galat_serve:
                print(f"  ! sisi web mati: {galat_serve[0]}", file=sys.stderr, flush=True)
                kode = 1
            return kode

        # Mode browser: satu proses, satu blokir.
        #
        # Peramban dibuka SENDIRI begitu servernya benar-benar menjawab, bukan
        # sebelum app.run() -- warmup Vulkan di mesin ini 10-15 dtk, dan membuka
        # lebih dulu hanya memunculkan "tidak bisa terhubung" selama itu.
        def buka_peramban():
            if not jendela.tunggu_siap(base, batas=180.0):
                print(f"  ! server belum menjawab; buka sendiri: {base}/", file=sys.stderr, flush=True)
                return
            import webbrowser

            try:
                webbrowser.open(base + "/")
                print(f"  web: {base}/ (dibuka di peramban bawaan)", flush=True)
            except Exception as err:
                print(f"  ! tidak bisa membuka peramban ({err}); buka sendiri: {base}/",
                      file=sys.stderr, flush=True)

        threading.Thread(target=buka_peramban, daemon=True).start()
        app.run(
            host="127.0.0.1",
            port=nomor,
            threaded=True,
            debug=False,
            use_reloader=False,
        )
        return 0
    except KeyboardInterrupt:
        pass
    finally:
        jalur_suara.berhenti()
        model_vulkan.hentikan()  # anak tidak boleh yatim memegang 2 GB
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    sys.exit(utama())
