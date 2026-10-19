"""Pipeline suara Silver Wolf: Piper TTS (Bahasa Indonesia) + RVC v2.

Menyatukan proses sintesis suara:
1. Normalisasi teks ucapan (TeksUcapan: buang markdown & narasi situasi).
2. Sintesis teks ke audio WAV mono via Piper TTS.
3. Konversi timbre suara ke Silver Wolf via RVC (bila model & dependensi aktif).
4. Hasil audio dikelola 100% in-memory (RAM) tanpa menumpuk berkas di disk.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from silverwolf.config import AppConfig, config
from silverwolf.core.teks_ucapan import bersihkan, buang_narasi
from silverwolf.voice.player import player


class VoicePipeline:
    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    def synthesize_piper(self, text: str) -> bytes:
        """Sintesis teks menjadi audio WAV mono memakai Piper TTS."""
        teks_bersih = bersihkan(buang_narasi(text))
        if not teks_bersih:
            return b""

        piper_exe = Path(self.cfg.piper_exe)
        piper_model = Path(self.cfg.piper_model)

        if not piper_exe.is_file():
            raise FileNotFoundError(f"Piper executable tidak ditemukan: {piper_exe}")
        if not piper_model.is_file():
            raise FileNotFoundError(f"Model Piper TTS tidak ditemukan: {piper_model}")

        # Buat file sementara yang langsung dihapus setelah dibaca
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            cmd = [
                str(piper_exe),
                "-m", str(piper_model),
                "--length-scale", str(self.cfg.piper_length_scale),
                "--noise-scale", str(self.cfg.piper_noise_scale),
                "--noise-w-scale", str(self.cfg.piper_noise_w),
                "-f", str(tmp_path),
            ]
            # Jalankan Piper dengan teks dimasukkan lewat stdin
            res = subprocess.run(
                cmd,
                input=teks_bersih,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if res.returncode != 0:
                print(f"[VoicePipeline] Piper TTS gagal: {res.stderr}")
                return b""

            if tmp_path.is_file() and tmp_path.stat().st_size > 0:
                return tmp_path.read_bytes()
            return b""
        finally:
            if tmp_path.is_file():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def convert_rvc(self, wav_bytes: bytes) -> bytes:
        """Konversi suara ke Silver Wolf memakai RVC.

        Jika RVC dinonaktifkan atau dependensi PyTorch/RVC belum tersedia di lingkungan ini,
        fungsi akan mengembalikan audio Piper secara transparan dan aman.
        """
        if not self.cfg.rvc_aktif or not wav_bytes:
            return wav_bytes

        # Cek apakah modul rvc-python dan torch tersedia
        try:
            import torch  # noqa: F401
            from rvc_python.infer import RVCInference
        except ImportError:
            # Fallback halus: Piper suara jernih tetap terdengar
            return wav_bytes

        model_path = self.cfg.assets_dir / "rvc" / self.cfg.rvc_model_nama / f"{self.cfg.rvc_model_nama}.pth"
        index_candidates = list((self.cfg.assets_dir / "rvc" / self.cfg.rvc_model_nama).glob("*.index"))
        index_path = str(index_candidates[0]) if index_candidates else ""

        if not model_path.is_file():
            return wav_bytes

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_tmp, \
             tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_tmp:
            in_path = Path(in_tmp.name)
            out_path = Path(out_tmp.name)

        try:
            in_path.write_bytes(wav_bytes)

            rvc = RVCInference(
                device="cpu",
                model_path=str(model_path),
                index_path=index_path,
                version=self.cfg.rvc_versi,
            )
            rvc.set_params(
                f0up_key=self.cfg.rvc_transpose,
                index_rate=self.cfg.rvc_index_rate,
                f0method=self.cfg.rvc_f0,
                filter_radius=self.cfg.rvc_filter_radius,
                rms_mix_rate=self.cfg.rvc_rms_mix,
                protect=self.cfg.rvc_protect,
                resample_sr=0,
            )
            rvc.infer_file(str(in_path), str(out_path))

            if out_path.is_file() and out_path.stat().st_size > 0:
                return out_path.read_bytes()
            return wav_bytes
        except Exception as e:
            print(f"[VoicePipeline] Peringatan RVC: {e}")
            return wav_bytes
        finally:
            for p in (in_path, out_path):
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass

    def synthesize(self, text: str) -> bytes:
        """Menghasilkan audio WAV lengkap (Piper -> RVC) dalam memori."""
        piper_wav = self.synthesize_piper(text)
        if not piper_wav:
            return b""
        return self.convert_rvc(piper_wav)

    def speak(
        self,
        text: str,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = False,
    ) -> None:
        """Sintesis teks dan langsung putar ke speaker dengan sinkronisasi bibir."""
        audio_bytes = self.synthesize(text)
        if audio_bytes:
            player.play_wav_bytes(audio_bytes, on_lip_sync=on_lip_sync, blocking=blocking)


# Singleton voice pipeline bawaan
voice = VoicePipeline()
