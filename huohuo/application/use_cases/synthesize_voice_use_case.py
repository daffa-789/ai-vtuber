"""Use Case: SynthesizeVoiceUseCase.

Manages in-memory voice synthesis pipeline:
1. Normalizes text for speech (stripping markdown, stage directions, emotion brackets).
2. Synthesizes base WAV audio via TTSPort (Piper TTS).
3. Optionally converts voice timbre via VoiceConversionPort (RVC).
4. Optionally outputs audio via AudioPlayerPort with lip-sync callbacks.
All audio processing is strictly in-memory without persistent disk pollution.
"""

from __future__ import annotations
from typing import Callable, Optional

from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort
from huohuo.domain.services.emotion_service import EmotionParserService
from huohuo.domain.services.gaya_suara import PetaGayaSuara
from huohuo.domain.services.text_speech_service import TextSpeechService


class SynthesizeVoiceUseCase:
    """Use case for in-memory speech synthesis and voice conversion."""

    def __init__(
        self,
        tts_port: TTSPort,
        voice_conversion_port: Optional[VoiceConversionPort] = None,
        audio_player_port: Optional[AudioPlayerPort] = None,
    ):
        self.tts = tts_port
        self.voice_conversion = voice_conversion_port
        self.audio_player = audio_player_port

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        """Synthesize text into in-memory WAV bytes.

        Kalau `gaya` tidak diberikan, gaya diambil dari tag emosi di awal teks
        ([senyum], [goda], [sebal], ...). Emosi itu sudah dihitung LLM untuk
        menggerakkan wajah Live2D, jadi sayang kalau suaranya tetap datar padahal
        wajahnya sedang menggoda.
        """
        emosi, _ = EmotionParserService.parse(text)
        if gaya is None:
            gaya = PetaGayaSuara.gaya_dari_emosi(emosi)

        cleaned_text = TextSpeechService.bersihkan_untuk_tts(text)
        if not cleaned_text:
            return None

        wav_bytes = self.tts.synthesize(cleaned_text, gaya=gaya)
        if not wav_bytes:
            return None

        if self.voice_conversion:
            konversi_emosi = getattr(
                self.voice_conversion, "convert_with_emotion", None
            )
            if callable(konversi_emosi):
                return konversi_emosi(wav_bytes, emosi or "netral")
            return self.voice_conversion.convert(wav_bytes)

        return wav_bytes

    def speak(
        self,
        text: str,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = True,
        gaya: Optional[str] = None,
    ) -> Optional[bytes]:
        """Synthesize text and play to speaker in-memory with optional lip-sync."""
        wav_bytes = self.synthesize(text, gaya=gaya)
        if wav_bytes and self.audio_player:
            self.audio_player.play(wav_bytes, on_lip_sync=on_lip_sync, blocking=blocking)
        return wav_bytes
