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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gemini
import jalur_suara
import konfig
import memori
import statis
import tts_rvc
import vault
from konfig import (
    AKAR_PERSONA,
    JEDA_FAKTA,
    MAKS_AUDIO,
    MAKS_BODY,
    MAKS_KARAKTER,
    MAKS_PESAN,
    MODEL,
    MODEL_CADANGAN,
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
        self.send_response(kode)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self._tambah_cors()
        self.end_headers()
        self.wfile.write(body)

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
            return self._json(
                200,
                {
                    "ok": True,
                    "model": "stub" if konfig.STUB else MODEL,
                    "cadangan": MODEL_CADANGAN,
                    "key": bool(konfig.KUNCI),
                    "tts": jalur_suara.ringkasan(),
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
        if not konfig.KUNCI:
            return self._json(
                501,
                {"error": "GEMINI_API_KEY belum diisi. Salin .env.example jadi .env lalu isi."},
            )

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

        body = gemini.body_chat(riwayat, memori.gabung_system(PERSONA, fakta, mood))

        # Jawaban pertama yang datang menang. Antrean 503 berpindah-pindah antar
        # model, jadi pindah kursi lebih murah daripada menunggu bangku.
        aliran, terpakai, error_terakhir = None, "", ""
        for model in dict.fromkeys([MODEL, *MODEL_CADANGAN]):
            try:
                aliran = gemini.alir(model, body, konfig.KUNCI)
                terpakai = model
                break
            except gemini.Ditolak as err:
                error_terakhir = err.pesan
                if not err.layak_dicoba:
                    break  # 400 = permintaannya yang salah, model lain percuma
                print(f"chat {model} sedang penuh: {err.pesan[:70]}", file=sys.stderr)

        if aliran is None:
            return self._json(503, {"error": error_terakhir or "Gemini menolak permintaan"})

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
        except gemini.Ditolak as err:
            print(f"aliran terputus: {err.pesan}", file=sys.stderr)
        except (BrokenPipeError, ConnectionResetError):
            print("halaman menutup aliran", file=sys.stderr)

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
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ── tts ────────────────────────────────────────────────────────────────
    def tts(self) -> None:
        if konfig.STUB:
            wav = pcm_ke_wav(bytes(4800), 24000, 1)
            self.send_response(200)
            self.send_header("content-type", "audio/wav")
            self.send_header("content-length", str(len(wav)))
            self.end_headers()
            self.wfile.write(wav)
            return
        try:
            teks = str(json.loads(self._tubuh(MAKS_BODY).decode("utf-8")).get("text") or "")[
                :MAKS_KARAKTER
            ]
        except json.JSONDecodeError:
            return self._json(400, {"error": "body harus JSON: { text }"})

        if not teks.strip():
            return self._json(400, {"error": "teks kosong"})

        # Tidak ada lagi "501 kalau GEMINI_API_KEY kosong" di sini. Dahulu syarat
        # itu mutlak; sekarang engine lokal (piper/rvc) tidak butuh kunci sama
        # sekali, jadi menolak tanpa kunci akan membisukan halaman yang sebenarnya
        # bisa bicara. Kewajiban kunci milik tiap engine sendiri.
        try:
            wav, terpakai = jalur_suara.bangun(teks)
        except jalur_suara.SemuaEngineGagal as err:
            for catatan in err.catatan:
                print(f"TTS: {catatan}", file=sys.stderr)
            return self._json(503, {"error": str(err)})

        self.send_response(200)
        self.send_header("content-type", "audio/wav")
        self.send_header("content-length", str(len(wav)))
        self.send_header("cache-control", "no-store")
        self.send_header("x-tts-model", terpakai)
        self._tambah_cors()
        self.end_headers()
        self.wfile.write(wav)

    # ── stt ─────────────────────────────────────────────────────────────────
    def stt(self) -> None:
        if not konfig.KUNCI:
            return self._json(501, {"error": "GEMINI_API_KEY belum diisi."})
        audio = self._tubuh(MAKS_AUDIO)
        if len(audio) < 1000:
            return self._json(400, {"error": "audio terlalu pendek atau kosong"})

        try:
            hasil = gemini.generate(
                STT_MODEL, gemini.body_audio(base64.b64encode(audio).decode()), konfig.KUNCI
            )
            self._json(200, {"teks": gemini.transkrip_dari(hasil)})
        except gemini.Ditolak as err:
            self._json(503, {"error": err.pesan})


def simpan_memori(
    riwayat: list, mentah: str, fakta_lama: list, mood_lama: dict | None
) -> None:
    """Ditulis SETELAH balasan terkirim: vault mati tidak boleh merusak percakapan
    yang sudah terjawab."""
    if konfig.STUB or not vault.tersedia() or not mentah.strip():
        return  # STUB: percakapan uji tidak boleh menodai riwayat karakter
    try:
        # Model kadang membungkus tag dengan backtick (`[lelah]`) walau dilarang di
        # persona.md. Sisi browser tetap menemukannya (kupasTag mencari di mana pun),
        # tapi mood dan riwayat membaca dari sini -- jadi pembungkusnya ikut dilepas.
        tag_cocok = re.match(r"\s*[`'\"“”]*\s*\[([^\]]{1,20})\]", mentah)
        tag = tag_cocok.group(1).lower() if tag_cocok else None
        isi = re.sub(r"^\s*[`'\"“”]*\s*\[[^\]]{1,20}\][`'\"“”]*\s*", "", mentah).strip()
        tanya = riwayat[-1]["parts"][0]["text"]

        mood = memori.perbarui_mood(mood_lama, tag)
        vault.catat_hari(f"**Master:** {tanya} → **Elaina:** {isi} _({tag or 'tanpa tag'})_")
        vault.simpan_mood(mood)

        # Ekstraksi fakta menambah satu panggilan API, jadi sengaja jarang.
        if mood["pertukaran"] % JEDA_FAKTA == 0:
            percakapan = [
                {"role": m["role"], "content": " ".join(p["text"] for p in m["parts"])}
                for m in riwayat[-12:]
            ]
            baru = memori.ekstrak_fakta(MODEL, percakapan, fakta_lama, konfig.KUNCI)
            if baru:
                vault.simpan_fakta(list(dict.fromkeys([*fakta_lama, *baru]))[-40:])
                print(f"fakta baru tersimpan: {len(baru)}")
    except Exception as err:
        print(f"memori gagal ditulis: {err}", file=sys.stderr)


def baris_banner(nomor: int) -> str:
    """Satu baris "siap" yang dicetak saat server naik -- sengaja fungsi murni, bukan
    print di dalam utama(), supaya bisa diuji dua-dua mode tanpa mengikat port.

    Mode stub wajib bilang stub: riwayat karakter tidak disentuh di sana, dan banner
    yang mengklaim "memori=vault Obsidian" bikin orang mencari fakta uji yang memang
    tidak pernah ada.
    """
    model_chat = "stub (Gemini tidak dipanggil)" if konfig.STUB else MODEL
    memori = "vault Obsidian" if vault.tersedia() else vault.alasan_tidak_tersedia()
    if konfig.STUB:
        memori += " (diam, tidak ditulis)"
    siap = jalur_suara.rantai_aktif()
    tts = "stub (hening 0,2 dtk)" if konfig.STUB else (",".join(siap) or "TIDAK ADA")
    baris = (
        f"sidecar python http://127.0.0.1:{nomor} | key={'siap' if konfig.KUNCI else 'KOSONG'} | "
        f"chat={model_chat} | tts={tts} | stt={STT_MODEL} | memori={memori}"
    )
    # RVC yang dimatikan diam-diam adalah kelas bug yang sama dengan "suara hilang
    # tanpa error" di wav.py. Kalau Master minta RVC tapi asetnya belum ada, itu
    # harus terbaca di baris pertama, bukan tidak muncul sama sekali.
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
    return 0


if __name__ == "__main__":
    sys.exit(utama())
