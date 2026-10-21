"""Use Case: ProcessUserInteractionUseCase.

Mengorkestrasi alur interaksi pengguna:
1. Membaca fakta, persona, dan suasana hati dari vault.
2. Mencatat pesan di KizunaState dan mendapatkan konteks prompt.
3. Menyusun System Prompt lengkap.
4. Menjalankan inferensi LLM via LLMPort.
5. Mengekstrak emosi dan membersihkan teks untuk konsumsi suara.
6. Memperbarui suasana hati dan menyimpan riwayat percakapan.
7. Memperbarui UI via CompanionUIPort jika tersedia.
8. Mensintesis suara via TTSPort dan memutar audio dengan lip-sync.
"""

from __future__ import annotations
import threading
from typing import Optional

from silverwolf.application.dtos.interaction_dto import InteractionResponse, UserInteractionRequest
from silverwolf.domain.entities.mood import MoodState
from silverwolf.domain.ports.audio_player_port import AudioPlayerPort
from silverwolf.domain.ports.companion_ui_port import CompanionUIPort
from silverwolf.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from silverwolf.domain.ports.llm_port import LLMPort
from silverwolf.domain.ports.memory_vault_port import MemoryVaultPort
from silverwolf.domain.ports.tts_port import TTSPort
from silverwolf.domain.ports.voice_conversion_port import VoiceConversionPort
from silverwolf.domain.services.emotion_service import EmotionParserService
from silverwolf.domain.services.prompt_builder_service import PromptBuilderService
from silverwolf.domain.services.text_speech_service import TextSpeechService


class ProcessUserInteractionUseCase:
    """Use Case interaksi utama Silver Wolf."""

    def __init__(
        self,
        llm_port: LLMPort,
        kizuna_repo: KizunaRepositoryPort,
        memory_vault: MemoryVaultPort,
        tts_port: Optional[TTSPort] = None,
        voice_conversion_port: Optional[VoiceConversionPort] = None,
        audio_player_port: Optional[AudioPlayerPort] = None,
        ui_port: Optional[CompanionUIPort] = None,
    ):
        self.llm = llm_port
        self.kizuna_repo = kizuna_repo
        self.vault = memory_vault
        self.tts = tts_port
        self.voice_conversion = voice_conversion_port
        self.audio_player = audio_player_port
        self.ui = ui_port
        self.history_buffer: list[dict[str, str]] = []

    def execute(self, request: UserInteractionRequest) -> InteractionResponse:
        user_text = request.text.strip()
        if not user_text:
            return InteractionResponse("", "", "netral", 1, "Asing", "Netral", None)

        # 1. Muat data domain
        kizuna = self.kizuna_repo.load()
        kizuna_snap = kizuna.record_message(user_text)
        self.kizuna_repo.save(kizuna)

        persona = self.vault.load_persona()
        fakta = self.vault.load_facts()
        mood = self.vault.load_mood() or MoodState.awal()

        # 2. Susun system prompt & messages
        sys_prompt = PromptBuilderService.build(
            persona=persona,
            fakta=fakta,
            mood=mood,
            kizuna_context=kizuna.get_prompt_context(),
            lokal=True,
        )

        self.history_buffer.append({"role": "user", "content": user_text})
        # Batasi buffer ke 10 pesan terakhir
        recent_history = self.history_buffer[-10:]
        messages = [{"role": "system", "content": sys_prompt}] + recent_history

        # 3. Panggil inferensi LLM
        emotion, raw_reply = self.llm.generate(messages)
        parsed_emotion, cleaned_text = EmotionParserService.parse(raw_reply)
        final_emotion = parsed_emotion or emotion or "senyum"

        self.history_buffer.append({"role": "assistant", "content": f"[{final_emotion}] {cleaned_text}"})

        # 4. Perbarui Mood & Riwayat
        mood_baru = MoodState.perbarui(mood, final_emotion)
        self.vault.save_mood(mood_baru)
        self.vault.record_history(user_text, f"[{final_emotion}] {cleaned_text}")

        # 5. Beri notifikasi ke UI jika port terhubung
        if self.ui:
            self.ui.show_bubble(cleaned_text, final_emotion)
            self.ui.set_expression(final_emotion)
            self.ui.set_kizuna_status(f"⚡ Kizuna: Level {kizuna_snap.level} • {mood_baru.label}")

        # 6. Sintesis suara & putar audio jika diminta
        audio_bytes: Optional[bytes] = None
        if request.play_audio and self.tts:
            teks_ucap = TextSpeechService.bersihkan_untuk_tts(cleaned_text)
            audio_bytes = self.tts.synthesize(teks_ucap)
            if audio_bytes and self.voice_conversion:
                audio_bytes = self.voice_conversion.convert(audio_bytes) or audio_bytes

            if audio_bytes and self.audio_player:
                def on_lip(level: float):
                    if self.ui:
                        self.ui.set_mouth_open(level)

                if request.blocking_audio:
                    self.audio_player.play(audio_bytes, on_lip_sync=on_lip, blocking=True)
                else:
                    threading.Thread(
                        target=lambda: self.audio_player.play(audio_bytes, on_lip_sync=on_lip, blocking=False),
                        daemon=True,
                    ).start()

        return InteractionResponse(
            raw_reply=raw_reply,
            cleaned_reply=cleaned_text,
            emotion=final_emotion,
            kizuna_level=kizuna_snap.level,
            kizuna_stage=kizuna_snap.stage,
            mood_label=mood_baru.label,
            audio_bytes=audio_bytes,
        )
