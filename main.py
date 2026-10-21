"""HuoHuo // AI Vtuber Desktop Companion — Main Entry Point.

Pemakaian:
    python main.py             # Jalankan antarmuka desktop Live2D companion
    python main.py --cli       # Mode interaktif di terminal (tanpa GUI)
    python main.py --test-voice # Uji coba sintesis suara HuoHuo
    python main.py --voice-in   # Voice-to-Voice: jawab ujaran dari mikrofon
    python main.py --voice-in --voice-loop  # Terus mendengarkan ujaran
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from huohuo.application.dtos.interaction_dto import UserInteractionRequest
from huohuo.config import config
from huohuo.infrastructure.container import Container, create_container
from huohuo.ui.app import start_companion


def run_cli_mode(container: Optional[Container] = None):
    """Mode percakapan langsung di terminal via Clean Architecture."""
    print("=" * 60)
    print(" HuoHuo // Terminal Companion (Mode CLI)")
    print("=" * 60)
    print("Memuat memori dan sistem ikatan...")

    c = container or create_container()
    snap = c.kizuna_repo.load().get_snapshot()
    print(f"Status Ikatan: Level {snap.level} | Tahap: {snap.stage} | Poin: {snap.points:.1f}")
    print("Ketik 'keluar' atau tekan Ctrl+C untuk menutup.\n")

    while True:
        try:
            pesan = input("Master > ").strip()
            if not pesan:
                continue
            if pesan.lower() in ("keluar", "exit", "quit"):
                print("Sampai jumpa lagi, Master!")
                break

            print("HuoHuo sedang berpikir...", end="\r")
            req = UserInteractionRequest(text=pesan, play_audio=True, blocking_audio=True)
            res = c.process_interaction_use_case.execute(req)

            print(f"HuoHuo [{res.emotion}] > {res.cleaned_reply}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nSampai jumpa Master!")
            break


def run_test_voice(container: Optional[Container] = None):
    """Uji coba sintesis suara HuoHuo via SynthesizeVoiceUseCase."""
    print("Menguji sintesis suara Piper TTS + RVC...")
    c = container or create_container()
    sample_text = "H-halo Master... aku HuoHuo. Suaraku sudah tersambung langsung ke Python!"
    print(f"Teks: {sample_text}")
    audio = c.synthesize_voice_use_case.speak(sample_text, blocking=True)
    if audio:
        print(f"Sintesis berhasil ({len(audio)} bytes audio WAV). Memutar ke speaker...")
        print("Selesai diputar!")
    else:
        print("Gagal menghasilkan audio (periksa executable Piper atau model TTS).")


def run_voice_mode(
    container: Optional[Container] = None,
    loop: bool = False,
    iterations: Optional[int] = None,
    play_audio: bool = True,
):
    """Mode Voice-to-Voice: dengar ujaran dari mikrofon, transkripsi, lalu respons."""
    c = container or create_container()
    voice = c.voice_interaction_use_case
    stt = c.stt_port

    print("=" * 60)
    print(" HuoHuo // Voice-to-Voice (mode mikrofon)")
    print("=" * 60)

    if hasattr(stt, "is_available") and not stt.is_available():
        print(
            f"[STT] Backend '{c.cfg.stt_backend}' tidak siap. Pasang 'faster-whisper' "
            "untuk transkripsi offline, atau set VTUBER_STT_BACKEND=mock untuk uji alur."
        )

    n = 0
    try:
        while True:
            print("Mendengarkan ujaran Master... (Ctrl+C untuk keluar)")
            text = voice.execute_once(timeout_seconds=8.0, play_audio=play_audio)
            if text:
                print(f"Master (suara) > {text}")
            else:
                print("(tidak ada ujaran terdeteksi / STT belum tersedia)")
            n += 1
            if not loop and iterations is None:
                break
            if iterations is not None and n >= iterations:
                break
    except (KeyboardInterrupt, EOFError):
        voice.stop()
        print("\nMode suara dihentikan. Sampai jumpa, Master!")


def main():
    parser = argparse.ArgumentParser(description="HuoHuo AI Vtuber Companion")
    parser.add_argument("--cli", action="store_true", help="Jalankan di mode terminal CLI tanpa GUI")
    parser.add_argument("--test-voice", action="store_true", help="Uji sintesis dan pemutaran suara")
    parser.add_argument("--port", type=int, default=8990, help="Port server statis Live2D (default: 8990)")
    parser.add_argument("--voice-in", action="store_true", help="Voice-to-Voice: jawab satu ujaran dari mikrofon")
    parser.add_argument("--voice-loop", action="store_true", help="Terus mendengarkan ujaran dari mikrofon (tanpa henti)")
    parser.add_argument("--voice-iterations", type=int, default=None, help="Batas jumlah ujaran pada mode mikrofon")
    args = parser.parse_args()

    container = create_container()

    if args.test_voice:
        run_test_voice(container)
        return

    if args.cli:
        run_cli_mode(container)
        return

    if args.voice_in or args.voice_loop:
        run_voice_mode(
            container,
            loop=args.voice_loop,
            iterations=args.voice_iterations,
        )
        return

    # Default: Jalankan antarmuka GUI Desktop
    start_companion(port=args.port, container=container)


if __name__ == "__main__":
    main()
