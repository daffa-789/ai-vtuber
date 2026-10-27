"""Use Case: StreamUserInteractionUseCase.

Implements a 3-stage asynchronous pipelined streaming architecture:
Stage 1: LLM token stream -> SentenceSplitterService (produces complete clauses/sentences)
Stage 2: Sentence queue -> PiperTTS / RVC synthesis worker (produces audio chunks)
Stage 3: Audio queue -> Sounddevice continuous player & UI bubble / lip-sync streaming

Achieves sub-second first-audio playback (< 1s) and continuous lip-sync without mouth reset.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional

from huohuo.application.dtos.interaction_dto import (
    InteractionResponse,
    StreamChunkDTO,
    UserInteractionRequest,
)
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.llm_port import LLMInferencePort, LLMPort
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort
from huohuo.domain.services.prompt_builder_service import PromptBuilderService
from huohuo.domain.services.gaya_suara import PetaGayaSuara
from huohuo.domain.services.sentence_splitter_service import SentenceSplitterService
from huohuo.domain.services.text_speech_service import TextSpeechService


class StreamUserInteractionUseCase:
    """3-stage streaming interaction use case for low-latency voice-to-voice companion."""

    def __init__(
        self,
        llm_port: LLMInferencePort,
        kizuna_repo: KizunaRepositoryPort,
        memory_vault: MemoryVaultPort,
        tts_port: Optional[TTSPort] = None,
        voice_conversion_port: Optional[VoiceConversionPort] = None,
        audio_player_port: Optional[AudioPlayerPort] = None,
        ui_port: Optional[CompanionUIPort] = None,
        splitter_service: Optional[SentenceSplitterService] = None,
    ):
        self.llm = llm_port
        self.kizuna_repo = kizuna_repo
        self.vault = memory_vault
        self.tts = tts_port
        self.voice_conversion = voice_conversion_port
        self.audio_player = audio_player_port
        self.ui = ui_port
        self.splitter = splitter_service or SentenceSplitterService()
        self.history_buffer: list[dict[str, str]] = []
        self._abort_event = threading.Event()

    def execute_stream(
        self,
        request: UserInteractionRequest,
        on_chunk_ready: Optional[Callable[[StreamChunkDTO], None]] = None,
    ) -> InteractionResponse:
        """Executes 3-stage asynchronous pipeline.

        Returns completed InteractionResponse after generation and (if requested) playback.
        """
        self._abort_event.clear()
        user_text = request.text.strip()
        if not user_text:
            return InteractionResponse("", "", "netral", 1, "Asing", "Netral", None)

        # 1. Load domain state
        kizuna = self.kizuna_repo.load()
        kizuna_snap = kizuna.record_message(user_text)
        self.kizuna_repo.save(kizuna)

        persona = self.vault.load_persona()
        fakta = self.vault.load_facts()
        mood = self.vault.load_mood() or MoodState.awal()

        # 2. Build system prompt & messages
        sys_prompt = PromptBuilderService.build(
            persona=persona,
            fakta=fakta,
            mood=mood,
            kizuna_context=kizuna.get_prompt_context(),
            lokal=True,
        )

        self.history_buffer.append({"role": "user", "content": user_text})
        recent_history = self.history_buffer[-10:]
        messages = [{"role": "system", "content": sys_prompt}] + recent_history

        # 3. Setup communication queues
        sentence_queue: queue.Queue[Optional[tuple[Optional[str], str]]] = queue.Queue(maxsize=32)
        audio_queue: queue.Queue[Optional[StreamChunkDTO]] = queue.Queue(maxsize=32)

        collected_sentences: list[str] = []
        collected_emotions: list[str] = []
        stage1_error: list[Exception] = []
        first_audio_bytes: list[bytes] = []

        # Stage 1: LLM stream -> SentenceSplitter
        def _stage1_producer() -> None:
            try:
                token_stream = self.llm.stream(messages)
                for emotion, clause_text in self.splitter.split_stream(token_stream):
                    if self._abort_event.is_set():
                        break
                    if clause_text:
                        collected_sentences.append(clause_text)
                        if emotion:
                            collected_emotions.append(emotion)
                        while not self._abort_event.is_set():
                            try:
                                sentence_queue.put((emotion, clause_text), timeout=1.0)
                                break
                            except queue.Full:
                                continue
            except Exception as exc:
                stage1_error.append(exc)
            finally:
                try:
                    sentence_queue.put(None, timeout=1.0)
                except Exception:
                    pass

        # Stage 2: Sentence queue -> PiperTTS & RVC synthesis
        def _stage2_synthesis_worker() -> None:
            chunk_id = 0
            pending_chunk: Optional[StreamChunkDTO] = None
            try:
                while not self._abort_event.is_set():
                    try:
                        item = sentence_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if item is None:
                        # Reached EOF: flush pending chunk with is_last=True
                        if pending_chunk is not None:
                            pending_chunk.is_last = True
                            while not self._abort_event.is_set():
                                try:
                                    audio_queue.put(pending_chunk, timeout=1.0)
                                    break
                                except queue.Full:
                                    continue
                            pending_chunk = None
                        break

                    emotion, clause_text = item
                    clean_for_speech = TextSpeechService.bersihkan_untuk_tts(clause_text)

                    wav_bytes: Optional[bytes] = None
                    if request.play_audio and self.tts and clean_for_speech.strip():
                        try:
                            try:
                                wav_bytes = self.tts.synthesize(
                                    clean_for_speech,
                                    gaya=PetaGayaSuara.gaya_dari_emosi(emotion),
                                )
                            except TypeError:
                                wav_bytes = self.tts.synthesize(clean_for_speech)
                            if wav_bytes and self.voice_conversion:
                                konversi_emosi = getattr(
                                    self.voice_conversion, "convert_with_emotion", None
                                )
                                if callable(konversi_emosi):
                                    wav_bytes = konversi_emosi(wav_bytes, emotion)
                                else:
                                    wav_bytes = self.voice_conversion.convert(wav_bytes)
                        except Exception:
                            wav_bytes = None

                    # Jangan tampilkan potongan jawaban jika proses suara gagal.
                    if request.play_audio and not wav_bytes:
                        continue

                    if wav_bytes and not first_audio_bytes:
                        first_audio_bytes.append(wav_bytes)

                    # If we had a prior pending chunk, it was NOT the last
                    if pending_chunk is not None:
                        pending_chunk.is_last = False
                        while not self._abort_event.is_set():
                            try:
                                audio_queue.put(pending_chunk, timeout=1.0)
                                break
                            except queue.Full:
                                continue

                    pending_chunk = StreamChunkDTO(
                        chunk_id=chunk_id,
                        text=clause_text,
                        emotion=emotion or "senyum",
                        audio_bytes=wav_bytes,
                        is_last=False,
                    )
                    chunk_id += 1
            finally:
                if pending_chunk is not None and not self._abort_event.is_set():
                    pending_chunk.is_last = True
                    try:
                        audio_queue.put(pending_chunk, timeout=1.0)
                    except Exception:
                        pass
                try:
                    audio_queue.put(None, timeout=1.0)
                except Exception:
                    pass
                if self._abort_event.is_set():
                    while True:
                        try:
                            sentence_queue.get_nowait()
                        except queue.Empty:
                            break

        # Stage 3: Audio queue -> Sounddevice continuous player & UI updates
        def _stage3_playback_worker() -> None:
            def _audio_generator():
                while not self._abort_event.is_set():
                    try:
                        chunk = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if chunk is None:
                        break

                    # Dispatch chunk ready callback
                    if on_chunk_ready:
                        try:
                            on_chunk_ready(chunk)
                        except Exception:
                            pass

                    # Update UI speech bubble and avatar expression
                    if self.ui:
                        try:
                            self.ui.show_bubble(chunk.text, chunk.emotion)
                            self.ui.set_expression(chunk.emotion)
                        except Exception:
                            pass

                    if chunk.audio_bytes:
                        yield chunk.audio_bytes

            def _on_lip(level: float) -> None:
                if self.ui:
                    try:
                        self.ui.set_mouth_open(level)
                    except Exception:
                        pass

            try:
                if self.audio_player and request.play_audio:
                    if hasattr(self.audio_player, "play_stream"):
                        self.audio_player.play_stream(
                            _audio_generator(),
                            on_lip_sync=_on_lip,
                        )
                    else:
                        # Fallback if audio player only implements single play()
                        for audio_chunk in _audio_generator():
                            self.audio_player.play(audio_chunk, on_lip_sync=_on_lip, blocking=True)
                else:
                    # No audio playback requested: drain queue and update UI
                    for _ in _audio_generator():
                        pass
            except Exception:
                self._abort_event.set()
            finally:
                if self._abort_event.is_set():
                    while True:
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            break

        t1 = threading.Thread(target=_stage1_producer, daemon=True, name="Stage1-LLMProducer")
        t2 = threading.Thread(target=_stage2_synthesis_worker, daemon=True, name="Stage2-TTSSynthesizer")
        t3 = threading.Thread(target=_stage3_playback_worker, daemon=True, name="Stage3-AudioPlayer")

        t1.start()
        t2.start()
        t3.start()

        # Always wait for Stage 1 to finish so complete reply and state updates are finalized
        t1.join(timeout=10.0)

        # If blocking audio is requested, wait for Stage 2 & 3 to completely finish playback
        if request.blocking_audio or not request.play_audio:
            t2.join(timeout=10.0)
            t3.join(timeout=10.0)

        # Finalize domain state
        final_emotion = collected_emotions[0] if collected_emotions else "senyum"
        full_cleaned_text = " ".join(collected_sentences).strip()

        self.history_buffer.append(
            {"role": "assistant", "content": f"[{final_emotion}] {full_cleaned_text}"}
        )

        mood_baru = MoodState.perbarui(mood, final_emotion)
        self.vault.save_mood(mood_baru)
        self.vault.record_history(user_text, f"[{final_emotion}] {full_cleaned_text}")

        if self.ui:
            try:
                self.ui.set_kizuna_status(f"⚡ Kizuna: Level {kizuna_snap.level} • {mood_baru.label}")
            except Exception:
                pass

        return InteractionResponse(
            raw_reply=full_cleaned_text,
            cleaned_reply=full_cleaned_text,
            emotion=final_emotion,
            kizuna_level=kizuna_snap.level,
            kizuna_stage=kizuna_snap.stage,
            mood_label=mood_baru.label,
            audio_bytes=first_audio_bytes[0] if first_audio_bytes else None,
        )
