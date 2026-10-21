"""Adapter: RVCAdapter.

Implements VoiceConversionPort using Retrieval-based Voice Conversion (RVC).
Safely converts audio in-memory and falls back transparently when RVC is disabled or unavailable.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from silverwolf.config import AppConfig, config
from silverwolf.domain.ports.voice_conversion_port import VoiceConversionPort


class RVCAdapter(VoiceConversionPort):
    """Concrete adapter for RVC voice conversion."""

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.cfg = cfg or config

    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        """Convert timbre of WAV audio into Silver Wolf voice."""
        if not wav_bytes:
            return None

        if not self.cfg.rvc_aktif:
            return wav_bytes

        try:
            import torch  # noqa: F401
            from rvc_python.infer import RVCInference
        except ImportError:
            # Fallback smoothly to original audio if PyTorch / RVC is absent
            return wav_bytes

        model_dir = self.cfg.assets_dir / "rvc" / self.cfg.rvc_model_nama
        model_path = model_dir / f"{self.cfg.rvc_model_nama}.pth"
        index_candidates = list(model_dir.glob("*.index"))
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
        except Exception:
            return wav_bytes
        finally:
            for p in (in_path, out_path):
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass
