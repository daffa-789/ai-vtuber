"""Sidecar Python: penyaji backend dengan kontrak HTTP.

Frontend tidak diubah sedikit pun -- /api/health, /api/chat (aliran teks),
/api/tts (WAV), /api/stt (body WAV mentah) punya bentuk permintaan dan jawaban
yang identik, jadi proxy Vite dan halaman ini tetap bekerja.

Jalankan:  python server_py/app.py
Port dibaca dari VTUBER_PORT; 0 berarti kernel pilihkan port bebas dan nomornya
dicetak saat mulai, karena mesin ini dipakai banyak proyek sekaligus.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import logging
import threading
import time
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("faiss").setLevel(logging.WARNING)
logging.getLogger("fairseq").setLevel(logging.WARNING)
logging.getLogger("rvc_python").setLevel(logging.WARNING)

import jalur_suara
import konfig
import memori
import model_lokal
import model_vulkan
import ollama_client
import statis
import stt_whisper
import tts_rvc
import vault
from konfig import (
    AKAR_PERSONA,
    JEDA_FAKTA,
    MAKS_AUDIO,
    MAKS_BODY,
    MAKS_KARAKTER,
    MAKS_PESAN,
    PORT,
    STT_MODEL,
)
from wav import laju_kanal, pcm_ke_wav, sudah_wav

PERSONA = AKAR_PERSONA.read_text(encoding="utf-8")

# Aliran kalengan untuk VTUBER_STUB=1. Sengaja dipecah di tengah tag ('[se' +
# 'nyum]') supaya pengupas tag ikut diuji, bukan hanya jalur yang rapi.
POTONGAN_STUB = ["[se", "nyum] Halo ", "Master.", " [sebal] kok", " diam sih"]

# stdout di-buffer penuh saat dialihkan ke berkas, jadi nomor port hasil
# VTUBER_PORT=0 tidak muncul dan orang mengira servernya tidak naik.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


def rapikan_riwayat(raw) -> list[dict]:
    """Peran dibatasi ke dua nilai yang dikenali API, isi dipotong pendek."""
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


# Pesan jatuh-from-GPU terakhir yang sudah diberitakan. Sekali per perubahan, supaya
# log tidak berteriak 20 kali untuk satu jawaban panjang.
PERINGATAN_JATUH = ""


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


class Sidecar(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # tanpa keep-alive: aliran diakhiri oleh close

    # ── helpers ─────────────────────────────────────────────────────────────
    def _tambah_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, Authorization")

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._tambah_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, kode: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(kode)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self._tambah_cors()
            self.end_headers()
            self.wfile.write(body)
        except ConnectionError as err:
            # ConnectionError adalah induk dari BrokenPipeError, ConnectionResetError,
            # DAN ConnectionAbortedError -- yang terakhir inilah yang Windows lempar
            # saat browser menutup tab di tengah permintaan (terukur 27 Sep di /api/stt,
            # dan karena hanya dua subclass pertama yang ditangkap, klien yang pergi
            # dicatat sebagai 500 + traceback penuh). Klien yang menutup diri bukan
            # kesalahan server.
            print(f"klien menutup sebelum jawaban {kode} sampai: {err}", file=sys.stderr)

    def _tubuh(self, batas: int) -> bytes:
        try:
            panjang = int(self.headers.get("content-length") or 0)
        except ValueError:
            raise ValueError("content-length tidak dikenali")
        if panjang > batas:
            raise ValueError("body terlalu besar")
        return self.rfile.read(panjang)

    def log_message(self, bentuk, *isi):  # noqa: N802 - dipanggil BaseHTTPRequestHandler
        print(f"{self.command} {self.path} -> {isi[1] if len(isi) > 1 else isi}")

    # ── routes ─────────────────────────────────────────────────────────────
    def do_GET(self):  # noqa: N802
        if self.path == "/api/health":
            if konfig.STUB:
                model_info = "stub"
            elif konfig.LLM_PROVIDER == "vulkan":
                # "hidup" hanya kalau proses anak benar-benar menjawab /health.
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
                model_info = MODEL

            is_offline = konfig.LLM_PROVIDER in ("local", "llama_cpp", "vulkan", "ollama")
            return self._json(
                200,
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
                },
            )
        return self._statis()

    def _statis(self) -> None:
        """Ganti peran dev server: sajikan web/ dan public/ dari disk."""
        # Query dibuang sebelum mencari berkas: onnxruntime-web mengimpor glue-nya
        # dengan akhiran `?import`, dan Vite dulu menanggapi query itu dengan 500.
        jalur = statis.cari(self.path.split("?", 1)[0])
        if jalur is None:
            return self._json(404, {"error": f"tidak ada berkas untuk {self.path}"})
        etag = statis.tanda(jalur)
        kendali = statis.kebijakan(jalur)
        if self.headers.get("if-none-match") == etag:
            self.send_response(304)
            self.send_header("etag", etag)
            self.send_header("cache-control", kendali)
            self.end_headers()
            return
        isi = statis.isi(jalur)
        self.send_response(200)
        self.send_header("content-type", statis.tipe(jalur))
        self.send_header("content-length", str(len(isi)))
        self.send_header("cache-control", kendali)
        self.send_header("etag", etag)
        self._tambah_cors()
        self.end_headers()
        self.wfile.write(isi)

    def do_POST(self):  # noqa: N802
        rute = {"/api/chat": self.chat, "/api/tts": self.tts, "/api/stt": self.stt}.get(self.path)
        if rute is None:
            return self._json(404, {"error": "tidak ada endpoint itu"})
        try:
            rute()
        except ValueError as err:
            self._json(400, {"error": str(err)})
        except Exception as err:  # satu permintaan tidak boleh mematikan server
            print(f"galat {self.path}: {err}", file=sys.stderr)
            self._json(500, {"error": str(err)})

    # ── chat ────────────────────────────────────────────────────────────────
    def chat(self) -> None:
        if konfig.STUB:
            return self._chat_stub()
        try:
            riwayat = rapikan_riwayat(json.loads(self._tubuh(MAKS_BODY).decode("utf-8")).get("messages"))
        except json.JSONDecodeError:
            return self._json(400, {"error": "body harus JSON: { messages: [{role, content}] }"})

        if not riwayat:
            return self._json(400, {"error": "riwayat kosong"})

        # Memori dibaca lebih dulu supaya yang dia ingat ikut membentuk jawaban ini.
        fakta, mood = [], None
        if vault.tersedia():
            try:
                fakta, mood = vault.baca_fakta(), vault.baca_mood()
            except Exception as err:
                print(f"memori tidak terbaca: {err}", file=sys.stderr)

        aliran, terpakai = None, ""
        if konfig.LLM_PROVIDER in ("local", "llama_cpp", "vulkan"):
            pesan_lokal = [{"role": "system", "content": memori.gabung_system_lokal(fakta, mood)}]
            for m in riwayat:
                peran = "assistant" if m.get("role") in ("assistant", "model") else "user"
                isi_pesan = " ".join(p.get("text", "") for p in m.get("parts", [])) if "parts" in m else m.get("content", "")
                pesan_lokal.append({"role": peran, "content": isi_pesan})

            berkas_terpakai = model_lokal.cari_model(konfig.LOCAL_MODEL_PATH)
            nama_model = berkas_terpakai.name if berkas_terpakai else "gguf"

            if konfig.LLM_PROVIDER == "vulkan":
                try:
                    # Token pertama DIPAKSA di sini. `alir()` itu generator: kalau hanya
                    # disimpan, tubuh fungsi belum jalan sama sekali dan galat boot
                    # (binary hilang, model tidak ada, server mati) baru muncul SETELAH
                    # status 200 terkirim -- sehingga jawaban bolong dan 503 tidak pernah
                    # terjadi. `_pacu()` menutup lubang itu untuk kedua penyedia.
                    aliran = _pacu(model_vulkan.alir(pesan_lokal))
                    terpakai = f"vulkan/{nama_model}"
                except model_lokal.ModelLokalError as err:
                    # Jatuh ke CPU masih offline, jadi boleh -- TAPI harus berisik:
                    # dicetak, dan dilaporkan lewat x-model + /api/health.
                    global PERINGATAN_JATUH
                    if PERINGATAN_JATUH != err.pesan:
                        PERINGATAN_JATUH = err.pesan
                        print(f"GPU tidak dipakai, kembali ke CPU: {err.pesan}", file=sys.stderr)
                    try:
                        aliran = _pacu(
                            model_lokal.alir(
                                pesan_lokal,
                                jalur_kandidat=konfig.LOCAL_MODEL_PATH,
                                threads=konfig.LOCAL_MODEL_THREADS,
                                n_ctx=konfig.LOCAL_MODEL_CTX,
                            )
                        )
                        terpakai = f"local/{nama_model}"
                    except model_lokal.ModelLokalError as err2:
                        return self._json(503, {"error": err2.pesan})
            else:
                try:
                    aliran = _pacu(
                        model_lokal.alir(
                            pesan_lokal,
                            jalur_kandidat=konfig.LOCAL_MODEL_PATH,
                            threads=konfig.LOCAL_MODEL_THREADS,
                            n_ctx=konfig.LOCAL_MODEL_CTX,
                        )
                    )
                    terpakai = f"local/{nama_model}"
                except model_lokal.ModelLokalError as err:
                    return self._json(503, {"error": err.pesan})

        elif konfig.LLM_PROVIDER == "ollama":
            pesan_ollama = [{"role": "system", "content": memori.gabung_system(PERSONA, fakta, mood)}]
            for m in riwayat:
                peran = "assistant" if m["role"] == "assistant" else "user"
                isi_pesan = " ".join(p.get("text", "") for p in m.get("parts", [])) if "parts" in m else m.get("content", "")
                pesan_ollama.append({"role": peran, "content": isi_pesan})

            try:
                aliran = ollama_client.alir(konfig.OLLAMA_MODEL, pesan_ollama, konfig.OLLAMA_URL)
                terpakai = f"ollama/{konfig.OLLAMA_MODEL}"
            except ollama_client.OllamaError as err:
                return self._json(503, {"error": err.pesan})
        else:
            return self._json(
                400,
                {"error": f"Provider '{konfig.LLM_PROVIDER}' tidak dikenal. Sistem berjalan offline: gunakan 'local', 'vulkan', atau 'ollama'."},
            )

        self.send_response(200)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("x-accel-buffering", "no")
        self.send_header("x-model", terpakai)
        self._tambah_cors()
        self.end_headers()

        # Setelah byte pertama terkirim status tidak bisa diubah lagi, jadi
        # kegagalan di tengah aliran cukup menutupnya; frontend menampilkan parsial.
        mentah = ""
        try:
            for potong in aliran:
                mentah += potong
                self.wfile.write(potong.encode("utf-8"))
                self.wfile.flush()
        except ConnectionError:
            print("halaman menutup aliran", file=sys.stderr)
        except Exception as err:
            print(f"aliran terputus: {err}", file=sys.stderr)

        threading.Thread(
            target=simpan_memori,
            args=(riwayat, mentah, fakta, mood),
            daemon=True,
        ).start()

    def _chat_stub(self) -> None:
        """Aliran kalengan: menguji rantai stream -> tag -> wajah tanpa kuota."""
        self.send_response(200)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("x-model", "stub")
        self._tambah_cors()
        self.end_headers()
        try:
            for potong in POTONGAN_STUB:
                self.wfile.write(potong.encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.12)
        except ConnectionError:
            pass  # klien menutup tab di tengah aliran kalengan

    # ── tts ────────────────────────────────────────────────────────────────
    def tts(self) -> None:
        if konfig.STUB:
            return self._audio(pcm_ke_wav(bytes(4800), 24000, 1), "stub")
        try:
            teks = str(json.loads(self._tubuh(MAKS_BODY).decode("utf-8")).get("text") or "")[
                :MAKS_KARAKTER
            ]
        except json.JSONDecodeError:
            return self._json(400, {"error": "body harus JSON: { text }"})

        if not teks.strip():
            return self._json(400, {"error": "teks kosong"})

        # Seluruh engine suara lokal (Piper + RVC) berjalan 100% offline tanpa API key.
        try:
            wav, terpakai = jalur_suara.bangun(teks)
        except jalur_suara.SemuaEngineGagal as err:
            for catatan in err.catatan:
                print(f"TTS: {catatan}", file=sys.stderr)
            return self._json(503, {"error": str(err)})

        self._audio(wav, terpakai)

    def _audio(self, wav: bytes, terpakai: str) -> None:
        """Satu tempat menulis WAV ke socket. Browser yang menutup tab saat audio
        40 kHz masih terkirim bukan kesalahan server -- dan tanpa penangkap ini
        kejadian itu naik sebagai traceback + 500."""
        try:
            self.send_response(200)
            self.send_header("content-type", "audio/wav")
            self.send_header("content-length", str(len(wav)))
            self.send_header("cache-control", "no-store")
            self.send_header("x-tts-model", terpakai)
            self._tambah_cors()
            self.end_headers()
            self.wfile.write(wav)
        except ConnectionError:
            print("halaman menutup sebelum audio sampai", file=sys.stderr)

    # ── stt ─────────────────────────────────────────────────────────────────
    def stt(self) -> None:
        """WAV dari browser -> teks, dibuat di mesin ini (tidak ada yang naik ke cloud).

        Dulu metode ini hanya mengembalikan {"teks": ""} dan itu berbahaya: halaman
        mengira transkripsi kosong karena Master diam, padahal tidak ada engine sama
        sekali. Sekarang engine yang tidak ada dijawab 503 dengan cara memasang.
        """
        if not konfig.STT_HIDUP:
            return self._json(503, {"error": "STT dimatikan (VTUBER_STT=tidak)"})
        if not stt_whisper.tersedia():
            return self._json(503, {"error": stt_whisper.alasan_tidak_tersedia()})

        panjang = int(self.headers.get("content-length", 0) or 0)
        if panjang > MAKS_AUDIO:
            return self._json(413, {"error": f"audio melebihi {MAKS_AUDIO // 1024} KB"})
        body = self.rfile.read(panjang) if panjang > 0 else b""
        if len(body) < 100:
            return self._json(400, {"error": "audio terlalu pendek"})

        try:
            teks = stt_whisper.transkripsi(body)
        except stt_whisper.GalatSTT as err:
            print(f"STT: {err.pesan}", file=sys.stderr)
            return self._json(503, {"error": err.pesan})

        return self._json(200, {"teks": teks, "mesin": f"whisper/{konfig.STT_MODEL}"})


def simpan_memori(
    riwayat: list, mentah: str, fakta_lama: list, mood_lama: dict | None
) -> None:
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
        vault.catat_hari(f"**Master:** {tanya} → **Elaina:** {isi} _({tag or 'tanpa tag'})_")
        vault.simpan_mood(mood)
    except Exception as err:
        print(f"memori gagal ditulis: {err}", file=sys.stderr)


def baris_banner(nomor: int) -> str:
    """Satu baris "siap" yang dicetak saat server naik -- mode 100% offline.

    FUNGSI MURNI: tidak boleh menyalakan proses apa pun. `uji_jalan.py` memanggilnya
    untuk membuktikan bentuk baris ini, dan banner yang membangunkan llama-server
    akan membuat tes mencetak proses 2 GB.
    """
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

    memori = "vault Obsidian" if vault.tersedia() else vault.alasan_tidak_tersedia()
    if konfig.STUB:
        memori += " (diam, tidak ditulis)"
    siap = jalur_suara.rantai_aktif()
    tts = "stub (hening 0,2 dtk)" if konfig.STUB else (",".join(siap) or "TIDAK ADA")
    if konfig.STUB or not konfig.STT_HIDUP:
        stt = "mati"
    elif stt_whisper.tersedia():
        stt = f"whisper/{konfig.STT_MODEL}"
    else:
        stt = f"TIDAK ADA ({stt_whisper.alasan_tidak_tersedia()})"
    baris = (
        f"sidecar python http://127.0.0.1:{nomor} | mode=100% OFFLINE | "
        f"chat={model_chat} | tts={tts} | stt={stt} | memori={memori}"
    )
    kalau = jalur_suara.peringatan()
    if konfig.STUB:
        return baris
    for catatan in kalau:
        baris += f"\n  ! {catatan}"
    return baris


def utama() -> int:
    jalur_suara.mula()
    try:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", PORT), Sidecar)
        except OSError as err:
            # Jangan pernah merebut port milik proyek lain: lapor lalu berhenti.
            print(f"port {PORT or 'acak'} tidak bisa dipakai: {err}", file=sys.stderr)
            return 1

        print(baris_banner(server.server_address[1]))
        # Panaskan sebelum permintaan pertama: membaca 1,9 GB GGUF + kompilasi shader
        # Vulkan pernah terukur 8-15 dtk, dan kalau itu terjadi DI DALAM /api/chat,
        # kalimat pertama lewat batas waktu dan yang didengar Master bukan hasilnya.
        if konfig.LLM_PROVIDER == "vulkan" and not konfig.STUB and konfig.VULKAN_MUAT_BOOT:
            import time as _waktu

            t0 = _waktu.monotonic()
            if model_vulkan.mulai():
                print(f"  vulkan: llama-server siap dalam {_waktu.monotonic() - t0:.1f} dtk", file=sys.stderr)
            else:
                print(f"  ! vulkan tidak jalan, chat jatuh ke CPU: {model_vulkan.alasan_tidak_tersedia()}", file=sys.stderr)
        # Muat RVC saat boot kalau diminta: pekerjaan pertama tidak dingin.
        if konfig.RVC_MUAT_BOOT and not konfig.STUB and tts_rvc.hidup():
            try:
                tts_rvc.muat()
                print("  rvc: model dimuat saat boot", file=sys.stderr)
            except Exception as err:
                print(f"  ! rvc tidak bisa dimuat: {err}", file=sys.stderr)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        jalur_suara.berhenti()
        # Anak tidak boleh yatim: llama-server memegang 2 GB dan tidak akan mati
        # sendiri setelah induknya pergi (atexit hanya jaminan kedua).
        model_vulkan.hentikan()
    return 0


if __name__ == "__main__":
    sys.exit(utama())
