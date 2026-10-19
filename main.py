"""Silver Wolf // AI Vtuber Desktop Companion — Main Entry Point.

Pemakaian:
    python main.py             # Jalankan antarmuka desktop Live2D companion
    python main.py --cli       # Mode interaktif di terminal (tanpa GUI)
    python main.py --test-voice # Uji coba sintesis suara Silver Wolf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from silverwolf.config import config
from silverwolf.core.kizuna import KizunaEngine
from silverwolf.core.memory import CharacterVault, ChatHistory
from silverwolf.core.mood import Mood
from silverwolf.core.persona_composer import gabung_system
from silverwolf.inference.llama_client import LlamaClient
from silverwolf.voice.pipeline import VoicePipeline


def run_cli_mode():
    """Mode percakapan langsung di terminal."""
    print("=" * 60)
    print(" Silver Wolf // Terminal Companion (Mode CLI)")
    print("=" * 60)
    print("Memuat memori dan sistem ikatan...")

    vault = CharacterVault(config.memory_dir)
    kizuna = KizunaEngine(config.memory_dir / "kizuna" / "silverwolf_kizuna_v1.json")
    llama = LlamaClient()
    voice = VoicePipeline()
    history = ChatHistory()

    snap = kizuna.get_snapshot()
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

            # Catat pesan
            snap = kizuna.record_message(pesan)
            persona = vault.baca_persona()
            fakta = vault.baca_fakta()
            mood = vault.baca_mood() or Mood.awal()
            kizuna_ctx = kizuna.get_prompt_context()

            sys_prompt = gabung_system(
                persona=persona,
                fakta=fakta,
                mood=mood,
                lokal=True,
                kizuna_context=kizuna_ctx,
            )

            history.tambah("user", pesan)
            messages = [{"role": "system", "content": sys_prompt}] + history.ke_format_llm()

            print("Silver Wolf sedang berpikir...", end="\r")
            emotion, balasan = llama.generate(messages)
            history.tambah("assistant", f"[{emotion or 'senyum'}] {balasan}")

            # Perbarui status
            mood_baru = Mood.perbarui(mood, emotion)
            vault.simpan_mood(mood_baru)
            vault.catat_riwayat(pesan, f"[{emotion or 'senyum'}] {balasan}")

            print(f"Silver Wolf [{emotion or 'senyum'}] > {balasan}\n")

            # Ucapkan balasan
            try:
                voice.speak(balasan, blocking=True)
            except Exception as err:
                print(f"[Suara] Catatan: {err}")

        except (KeyboardInterrupt, EOFError):
            print("\nSampai jumpa Master!")
            break


def run_test_voice():
    """Uji coba sintesis suara Silver Wolf."""
    print("Menguji sintesis suara Piper TTS...")
    vp = VoicePipeline()
    sample_text = "Halo Master! Aku Silver Wolf, pacar gamer kamu. Suaraku sudah tersambung langsung ke Python!"
    print(f"Teks: {sample_text}")
    audio = vp.synthesize(sample_text)
    if audio:
        print(f"Sintesis berhasil ({len(audio)} bytes audio WAV). Memutar ke speaker...")
        vp.speak(sample_text, blocking=True)
        print("Selesai diputar!")
    else:
        print("Gagal menghasilkan audio.")


def main():
    parser = argparse.ArgumentParser(description="Silver Wolf AI Vtuber Companion")
    parser.add_argument("--cli", action="store_true", help="Jalankan di mode terminal CLI tanpa GUI")
    parser.add_argument("--test-voice", action="store_true", help="Uji sintesis dan pemutaran suara")
    parser.add_argument("--port", type=int, default=8990, help="Port server statis Live2D (default: 8990)")
    args = parser.parse_args()

    if args.test_voice:
        run_test_voice()
        return

    if args.cli:
        run_cli_mode()
        return

    # Default: Jalankan antarmuka GUI Desktop
    from silverwolf.ui.app import start_companion
    start_companion(port=args.port)


if __name__ == "__main__":
    main()
