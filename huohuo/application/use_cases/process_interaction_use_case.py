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

from huohuo.application.dtos.interaction_dto import InteractionResponse, UserInteractionRequest
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.llm_port import LLMPort
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort
from huohuo.domain.services.emotion_service import EmotionParserService
from huohuo.domain.services.gaya_suara import PetaGayaSuara
from huohuo.domain.services.prompt_builder_service import PromptBuilderService
from huohuo.domain.services.state_service import StateParserService
from huohuo.domain.services.text_speech_service import TextSpeechService


class ProcessUserInteractionUseCase:
    """Use Case interaksi utama HuoHuo."""

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

        # 2. Susun system prompt & messages (sertakan keadaan hidup utk kontinuitas)
        ctx_ikatan = (
            kizuna.get_prompt_context()
            + "\n"
            + StateParserService.format_for_prompt(kizuna.energi, kizuna.aktivitas, kizuna.quest)
        )
        sys_prompt = PromptBuilderService.build(
            persona=persona,
            fakta=fakta,
            mood=mood,
            kizuna_context=ctx_ikatan,
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

        # Ekstrak dulu blok keadaan; perubahan baru disimpan setelah suara siap.
        state_baru, cleaned_text = StateParserService.parse(cleaned_text)
        # Sintesis dan konversi selesai sebelum balon chat boleh ditampilkan.
        audio_bytes: Optional[bytes] = None
        if request.play_audio and self.tts:
            teks_ucap = TextSpeechService.bersihkan_untuk_tts(cleaned_text)
            if teks_ucap:
                try:
                    audio_raw = self.tts.synthesize(
                        teks_ucap,
                        gaya=PetaGayaSuara.gaya_dari_emosi(final_emotion),
                    )
                except TypeError:
                    # Jaga kompatibilitas dengan backend lama tanpa argumen gaya.
                    audio_raw = self.tts.synthesize(teks_ucap)

                if audio_raw:
                    if self.voice_conversion:
                        konversi_emosi = getattr(
                            self.voice_conversion, "convert_with_emotion", None
                        )
                        if callable(konversi_emosi):
                            audio_bytes = konversi_emosi(audio_raw, final_emotion)
                        else:
                            audio_bytes = self.voice_conversion.convert(audio_raw)
                    else:
                        audio_bytes = audio_raw

        # Jika suara diminta tetapi Piper/RVC gagal, tahan jawaban dan jangan
        # memasukkan teks yang tidak terlihat/terdengar ke riwayat percakapan.
        if request.play_audio and not audio_bytes:
            return InteractionResponse(
                raw_reply=raw_reply,
                cleaned_reply=cleaned_text,
                emotion=final_emotion,
                kizuna_level=kizuna_snap.level,
                kizuna_stage=kizuna_snap.stage,
                mood_label=mood.label,
                audio_bytes=None,
            )

        if state_baru:
            kizuna.apply_state(state_baru)
            self.kizuna_repo.save(kizuna)

        self.history_buffer.append(
            {"role": "assistant", "content": f"[{final_emotion}] {cleaned_text}"}
        )

        # Simpan mood dan riwayat jawaban yang benar-benar siap ditampilkan.
        mood_baru = MoodState.perbarui(mood, final_emotion)
        self.vault.save_mood(mood_baru)
        self.vault.record_history(user_text, f"[{final_emotion}] {cleaned_text}")

        # 6. Baru tampilkan teks + ekspresi + status (sinkron dengan suara).
        if self.ui:
            self.ui.show_bubble(cleaned_text, final_emotion)
            self.ui.set_expression(final_emotion)
            self.ui.set_kizuna_status(kizuna.hud_text(mood_baru.label))

        # 7. Putar audio.
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
