"""Use Case: TouchHeadpatUseCase.

Mengorkestrasi interaksi sentuhan kepala / headpat:
1. Mencatat sentuhan di KizunaState.
2. Memperbarui ekspresi avatar menjadi 'kaget'.
3. Menghasilkan respons ucapan tulus HuoHuo.
4. Mensintesis dan memutar suara dengan lip-sync.
"""

from __future__ import annotations
import threading
from typing import Optional

from huohuo.application.dtos.interaction_dto import HeadpatResponse
from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort
from huohuo.domain.services.text_speech_service import TextSpeechService

BALASAN_HEADPAT = (
    "Eh... Master tiba-tiba elus kepalaku?! Rambutku jadi berantakan tahu... "
    "Tapi... rasanya hangat sih..."
)


class TouchHeadpatUseCase:
    """Use Case interaksi headpat."""

    def __init__(
        self,
        kizuna_repo: KizunaRepositoryPort,
        tts_port: Optional[TTSPort] = None,
        voice_conversion_port: Optional[VoiceConversionPort] = None,
        audio_player_port: Optional[AudioPlayerPort] = None,
        ui_port: Optional[CompanionUIPort] = None,
    ):
        self.kizuna_repo = kizuna_repo
        self.tts = tts_port
        self.voice_conversion = voice_conversion_port
        self.audio_player = audio_player_port
        self.ui = ui_port

    def execute(self, play_audio: bool = True, blocking_audio: bool = False) -> HeadpatResponse:
        kizuna = self.kizuna_repo.load()
        snap = kizuna.record_touch()
        # Elus kepala bikin HuoHuo senang -> energi naik, lagi "dielus".
        kizuna.energi = min(100, kizuna.energi + 6)
        kizuna.aktivitas = "dielus kepalanya"
        self.kizuna_repo.save(kizuna)

        emotion = "kaget"
        balasan = BALASAN_HEADPAT

        # Siapkan suara dulu (sintesis + konversi RVC) supaya teks & suara muncul bareng.
        audio_bytes: Optional[bytes] = None
        if play_audio and self.tts:
            teks_ucap = TextSpeechService.bersihkan_untuk_tts(balasan)
            audio_bytes = self.tts.synthesize(teks_ucap)
            if audio_bytes and self.voice_conversion:
                audio_bytes = self.voice_conversion.convert(audio_bytes) or audio_bytes

        # Baru tampilkan teks + ekspresi + status (sinkron dengan suara).
        if self.ui:
            self.ui.show_bubble(balasan, emotion)
            self.ui.set_expression(emotion)
            self.ui.set_kizuna_status(kizuna.hud_text("Tersipu"))

        # Putar audio.
        if audio_bytes and self.audio_player:
            def on_lip(level: float):
                if self.ui:
                    self.ui.set_mouth_open(level)

            if blocking_audio:
                self.audio_player.play(audio_bytes, on_lip_sync=on_lip, blocking=True)
            else:
                threading.Thread(
                    target=lambda: self.audio_player.play(audio_bytes, on_lip_sync=on_lip, blocking=False),
                    daemon=True,
                ).start()

        return HeadpatResponse(
            reply_text=balasan,
            emotion=emotion,
            kizuna_level=snap.level,
            audio_bytes=audio_bytes,
        )
