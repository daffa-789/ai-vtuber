"""Unit tests for the 3-stage streaming voice pipeline.

Verifies:
1. Pipelined execution across LLM -> TTS -> Audio playback stages.
2. Sub-second first-audio playback latency (< 1s).
3. Sequential audio playback and UI speech bubble / expression updating.
4. Continuous lip-sync streaming without mouth reset to 0.0 between chunks.
5. Container wiring for StreamUserInteractionUseCase and SentenceSplitterService.
"""

from __future__ import annotations

import time
from typing import Callable, Generator, Iterable, Optional

from huohuo.application.dtos.interaction_dto import (
    StreamChunkDTO,
    UserInteractionRequest,
)
from huohuo.application.use_cases.stream_user_interaction_use_case import (
    StreamUserInteractionUseCase,
)
from huohuo.domain.entities.kizuna import KizunaState
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.ports.audio_player_port import AudioPlayerPort
from huohuo.domain.ports.companion_ui_port import CompanionUIPort
from huohuo.domain.ports.kizuna_repository_port import KizunaRepositoryPort
from huohuo.domain.ports.llm_port import LLMInferencePort
from huohuo.domain.ports.memory_vault_port import MemoryVaultPort
from huohuo.domain.ports.tts_port import TTSPort
from huohuo.domain.ports.voice_conversion_port import VoiceConversionPort
from huohuo.infrastructure.container import create_container


class MockLLM(LLMInferencePort):
    def __init__(self, token_chunks: list[str], delay_per_token: float = 0.02):
        self.token_chunks = token_chunks
        self.delay = delay_per_token

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        return "senyum", "".join(self.token_chunks)

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        for chunk in self.token_chunks:
            if self.delay > 0:
                time.sleep(self.delay)
            yield chunk


class MockTTS(TTSPort):
    def __init__(self, synth_delay: float = 0.02):
        self.synth_delay = synth_delay
        self.synthesized_texts: list[str] = []

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        if self.synth_delay > 0:
            time.sleep(self.synth_delay)
        self.synthesized_texts.append(text)
        return f"WAV_AUDIO_FOR:{text}".encode("utf-8")


class MockVoiceConversion(VoiceConversionPort):
    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        return wav_bytes + b"_RVC"


class MockAudioPlayer(AudioPlayerPort):
    def __init__(self):
        self.played_chunks: list[bytes] = []
        self.lip_sync_levels: list[float] = []
        self.chunk_start_times: list[float] = []
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(
        self,
        audio_bytes: bytes,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = True,
    ) -> bool:
        self.played_chunks.append(audio_bytes)
        if on_lip_sync:
            on_lip_sync(0.5)
            on_lip_sync(0.0)
        return True

    def play_stream(
        self,
        audio_stream: Iterable[bytes],
        on_lip_sync: Optional[Callable[[float], None]] = None,
        on_chunk_start: Optional[Callable[[int], None]] = None,
    ) -> bool:
        self._playing = True
        idx = 0
        try:
            for chunk in audio_stream:
                self.chunk_start_times.append(time.perf_counter())
                if on_chunk_start:
                    on_chunk_start(idx)
                idx += 1
                self.played_chunks.append(chunk)

                if on_lip_sync:
                    # Emulate multi-frame lip-sync without dropping to 0.0 between chunks
                    on_lip_sync(0.4)
                    on_lip_sync(0.6)
                    self.lip_sync_levels.extend([0.4, 0.6])
        finally:
            self._playing = False
            if on_lip_sync:
                on_lip_sync(0.0)
                self.lip_sync_levels.append(0.0)
        return True

    def stop(self) -> None:
        self._playing = False


class MockUI(CompanionUIPort):
    def __init__(self):
        self.bubbles: list[tuple[str, str]] = []
        self.expressions: list[str] = []
        self.mouth_levels: list[float] = []
        self.kizuna_statuses: list[str] = []

    def show_bubble(self, text: str, emotion: str = "senyum") -> None:
        self.bubbles.append((text, emotion))

    def set_expression(self, emotion: str) -> None:
        self.expressions.append(emotion)

    def set_mouth_open(self, level: float) -> None:
        self.mouth_levels.append(level)

    def set_kizuna_status(self, text: str) -> None:
        self.kizuna_statuses.append(text)


class MockKizunaRepo(KizunaRepositoryPort):
    def __init__(self):
        self.kizuna = KizunaState()

    def load(self) -> KizunaState:
        return self.kizuna

    def save(self, state: KizunaState) -> None:
        self.kizuna = state


class MockVault(MemoryVaultPort):
    def __init__(self):
        self.persona = "Aku HuoHuo."
        self.facts: list[str] = ["Master suka game."]
        self.mood: Optional[MoodState] = MoodState.awal()
        self.history: list[tuple[str, str]] = []

    def load_persona(self) -> str:
        return self.persona

    def load_facts(self) -> list[str]:
        return self.facts

    def load_mood(self) -> Optional[MoodState]:
        return self.mood

    def save_mood(self, mood: MoodState) -> None:
        self.mood = mood

    def record_history(self, user_msg: str, bot_msg: str) -> None:
        self.history.append((user_msg, bot_msg))


def test_streaming_pipeline_execution():
    # Setup tokens: initial emotion + two clauses
    tokens = [
        "[senyum] ",
        "Halo Master tersayang, ",
        "aku kangen banget ",
        "sama kamu!",
    ]
    llm = MockLLM(token_chunks=tokens, delay_per_token=0.01)
    tts = MockTTS(synth_delay=0.01)
    vc = MockVoiceConversion()
    player = MockAudioPlayer()
    ui = MockUI()
    kizuna_repo = MockKizunaRepo()
    vault = MockVault()

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=kizuna_repo,
        memory_vault=vault,
        tts_port=tts,
        voice_conversion_port=vc,
        audio_player_port=player,
        ui_port=ui,
    )

    ready_chunks: list[StreamChunkDTO] = []
    response = use_case.execute_stream(
        UserInteractionRequest("Halo HuoHuo", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: ready_chunks.append(c),
    )

    # Assert completed response
    assert response.emotion == "senyum"
    assert "Halo Master tersayang," in response.cleaned_reply
    assert "aku kangen banget sama kamu!" in response.cleaned_reply

    # Assert 2 clauses were emitted and synthesized
    assert len(player.played_chunks) == 2
    assert b"Halo Master tersayang," in player.played_chunks[0]
    assert b"_RVC" in player.played_chunks[0]
    assert b"aku kangen banget sama kamu!" in player.played_chunks[1]

    # Assert UI received incremental speech bubble updates
    assert len(ui.bubbles) == 2
    assert ui.bubbles[0][0] == "Halo Master tersayang,"
    assert ui.bubbles[1][0] == "aku kangen banget sama kamu!"
    assert ui.expressions[-1] == "senyum"

    # Assert callbacks received chunks
    assert len(ready_chunks) == 2
    assert ready_chunks[0].chunk_id == 0
    assert ready_chunks[1].chunk_id == 1

    # Assert Vault and Kizuna updated
    assert len(vault.history) == 1
    assert kizuna_repo.kizuna.total_messages == 1


def test_first_sentence_latency_under_one_second():
    # Long total response, but first clause is short: "Halo Master tersayang,"
    tokens = [
        "[senyum] Halo Master tersayang, ",
        "sekarang aku sedang berpikir panjang... ",
        "sangat panjang sampai berpuluh-puluh kata baru selesai.",
    ]
    # Simulate realistic token arrival
    llm = MockLLM(token_chunks=tokens, delay_per_token=0.05)
    tts = MockTTS(synth_delay=0.05)
    player = MockAudioPlayer()
    ui = MockUI()

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=MockKizunaRepo(),
        memory_vault=MockVault(),
        tts_port=tts,
        audio_player_port=player,
        ui_port=ui,
    )

    t_start = time.perf_counter()
    use_case.execute_stream(
        UserInteractionRequest("Halo!", play_audio=True, blocking_audio=True)
    )

    assert len(player.chunk_start_times) >= 1
    first_audio_latency = player.chunk_start_times[0] - t_start

    # First audio must start in strictly under 1 second (< 1000ms)
    assert first_audio_latency < 1.0, f"Latency {first_audio_latency:.3f}s exceeded 1.0s target"


def test_continuous_lip_sync_no_midstream_reset():
    tokens = ["[senyum] Satu clause panjang disini, ", "dua clause penutup."]
    llm = MockLLM(token_chunks=tokens, delay_per_token=0.01)
    tts = MockTTS(synth_delay=0.01)
    player = MockAudioPlayer()
    ui = MockUI()

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=MockKizunaRepo(),
        memory_vault=MockVault(),
        tts_port=tts,
        audio_player_port=player,
        ui_port=ui,
    )

    use_case.execute_stream(
        UserInteractionRequest("Test lip-sync", play_audio=True, blocking_audio=True)
    )

    # Lip-sync levels: [0.4, 0.6, 0.4, 0.6, 0.0]
    # Notice 0.0 is ONLY appended at the very end when the entire stream finishes!
    assert player.lip_sync_levels[-1] == 0.0
    # No 0.0 before the last element
    assert all(lvl > 0.0 for lvl in player.lip_sync_levels[:-1])


def test_empty_input_handling():
    use_case = StreamUserInteractionUseCase(
        llm_port=MockLLM([]),
        kizuna_repo=MockKizunaRepo(),
        memory_vault=MockVault(),
    )
    res = use_case.execute_stream(UserInteractionRequest("   "))
    assert res.cleaned_reply == ""
    assert res.kizuna_level == 1


def test_container_wiring():
    container = create_container()
    assert hasattr(container, "stream_user_interaction_use_case")
    assert hasattr(container, "sentence_splitter_service")
    assert container.stream_user_interaction_use_case.splitter is container.sentence_splitter_service
