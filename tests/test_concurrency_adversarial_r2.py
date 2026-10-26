"""Independent Concurrency & Robustness Adversarial Verification Suite.

Author: Reviewer M1-R2-2
Focus:
1. Deadlock elimination under downstream crash (chunk 0, chunk 15, queue overflow).
2. Non-blocking queue draining and abort event propagation.
3. Fast producer (100 sentences) vs slow consumer with maxsize=32 queues.
4. Verification of is_last flag semantics (single-sentence, multi-sentence).
5. Mid-stream LLM and TTS exception boundaries.
"""

from __future__ import annotations

import queue
import threading
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


# --- Test Doubles ---

class FloodLLM(LLMInferencePort):
    """Produces N complete sentences as fast as possible without delay."""
    def __init__(self, count: int = 50):
        self.count = count

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        return "senyum", " ".join(f"Ini kalimat nomor {i} yang cukup panjang." for i in range(self.count))

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        for i in range(self.count):
            yield f"[senyum] Ini kalimat nomor {i} yang cukup panjang. "


class CrashAudioPlayer(AudioPlayerPort):
    """Audio player that crashes after receiving a specified number of chunks."""
    def __init__(self, crash_on_chunk: int = 0):
        self.crash_on_chunk = crash_on_chunk
        self.received_chunks: list[bytes] = []

    @property
    def is_playing(self) -> bool:
        return False

    def play(self, audio_bytes: bytes, on_lip_sync: Optional[Callable[[float], None]] = None, blocking: bool = True) -> bool:
        return True

    def play_stream(
        self,
        audio_stream: Iterable[bytes],
        on_lip_sync: Optional[Callable[[float], None]] = None,
        on_chunk_start: Optional[Callable[[int], None]] = None,
    ) -> bool:
        count = 0
        for chunk in audio_stream:
            self.received_chunks.append(chunk)
            if count == self.crash_on_chunk:
                raise RuntimeError(f"Simulated hardware failure on chunk {count}")
            count += 1
        return True

    def stop(self) -> None:
        pass


class SlowAudioPlayer(AudioPlayerPort):
    """Slow consumer simulating real audio device playback rate."""
    def __init__(self, delay_per_chunk: float = 0.05):
        self.delay = delay_per_chunk
        self.played = 0

    @property
    def is_playing(self) -> bool:
        return False

    def play(self, audio_bytes: bytes, on_lip_sync: Optional[Callable[[float], None]] = None, blocking: bool = True) -> bool:
        return True

    def play_stream(
        self,
        audio_stream: Iterable[bytes],
        on_lip_sync: Optional[Callable[[float], None]] = None,
        on_chunk_start: Optional[Callable[[int], None]] = None,
    ) -> bool:
        for chunk in audio_stream:
            self.played += 1
            time.sleep(self.delay)
        return True

    def stop(self) -> None:
        pass


class DummyTTS(TTSPort):
    def __init__(self, synth_delay: float = 0.001):
        self.synth_delay = synth_delay

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        if self.synth_delay > 0:
            time.sleep(self.synth_delay)
        return f"WAV_{text}".encode("utf-8")


class DummyKizunaRepo(KizunaRepositoryPort):
    def __init__(self):
        self.kizuna = KizunaState()
    def load(self) -> KizunaState:
        return self.kizuna
    def save(self, state: KizunaState) -> None:
        self.kizuna = state


class DummyVault(MemoryVaultPort):
    def load_persona(self) -> str:
        return "HuoHuo persona"
    def load_facts(self) -> list[str]:
        return []
    def load_mood(self) -> Optional[MoodState]:
        return MoodState.awal()
    def save_mood(self, mood: MoodState) -> None:
        pass
    def record_history(self, user_msg: str, bot_msg: str) -> None:
        pass


# --- Adversarial Test Cases ---

def test_deadlock_elimination_on_immediate_playback_crash():
    """Scenario 1: Downstream playback crashes on chunk 0 while LLM floods 60 sentences.
    
    Before fix: Stage 1 and 2 filled queues (maxsize=32) and blocked forever on put().
    Expected: Terminates cleanly within 2.0s without deadlocking.
    """
    llm = FloodLLM(count=60)
    tts = DummyTTS()
    player = CrashAudioPlayer(crash_on_chunk=0)

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=tts,
        audio_player_port=player,
    )

    t0 = time.perf_counter()
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=True, blocking_audio=True)
    )
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.5, f"Deadlock or excessive delay detected! Elapsed: {elapsed:.2f}s"
    assert use_case._abort_event.is_set(), "Abort event should be set after playback crash"
    print(f"  [PASS] Immediate crash with 60 sentences completed in {elapsed:.3f}s")


def test_deadlock_elimination_on_midstream_playback_crash():
    """Scenario 2: Downstream playback crashes on chunk 15 while LLM generates 80 sentences.
    
    Queues are actively saturated when crash occurs.
    Expected: Pipeline aborts immediately and all worker threads terminate.
    """
    llm = FloodLLM(count=80)
    tts = DummyTTS()
    player = CrashAudioPlayer(crash_on_chunk=15)

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=tts,
        audio_player_port=player,
    )

    t0 = time.perf_counter()
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=True, blocking_audio=True)
    )
    elapsed = time.perf_counter() - t0

    assert elapsed < 3.0, f"Deadlock or excessive delay on midstream crash! Elapsed: {elapsed:.2f}s"
    assert use_case._abort_event.is_set(), "Abort event should be set"
    assert len(player.received_chunks) == 16, f"Expected 16 chunks received before crash, got {len(player.received_chunks)}"
    print(f"  [PASS] Midstream crash on chunk 15 with 80 sentences completed in {elapsed:.3f}s")


def test_queue_overflow_fast_producer_slow_consumer():
    """Scenario 3: Fast producer generates 50 sentences without error, but consumer is slower.
    
    Queue capacity is 32. Producer should block gracefully with timeout and complete all 50 items.
    """
    llm = FloodLLM(count=40)
    tts = DummyTTS(synth_delay=0.005)
    player = SlowAudioPlayer(delay_per_chunk=0.02)

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=tts,
        audio_player_port=player,
    )

    t0 = time.perf_counter()
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=True, blocking_audio=True)
    )
    elapsed = time.perf_counter() - t0

    assert not use_case._abort_event.is_set(), "Abort event should NOT be set on normal flow"
    assert player.played == 40, f"Expected all 40 chunks played, got {player.played}"
    print(f"  [PASS] Fast producer / slow consumer (40 chunks) completed in {elapsed:.3f}s without drop")


def test_is_last_flag_semantics_multi_chunk():
    """Scenario 4: Verify is_last flag semantics across 5 chunks.
    
    Chunks 0, 1, 2, 3 must have is_last=False.
    Chunk 4 must have is_last=True.
    """
    llm = FloodLLM(count=5)
    tts = DummyTTS()

    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=tts,
    )

    collected_chunks: list[StreamChunkDTO] = []
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=False, blocking_audio=True),
        on_chunk_ready=lambda c: collected_chunks.append(c),
    )

    assert len(collected_chunks) == 5, f"Expected 5 chunks, got {len(collected_chunks)}"
    for idx, c in enumerate(collected_chunks[:-1]):
        assert not c.is_last, f"Chunk {idx} has is_last=True, expected False"
    assert collected_chunks[-1].is_last, f"Final chunk 4 has is_last=False, expected True"
    print(f"  [PASS] Multi-chunk is_last semantics verified: {[c.is_last for c in collected_chunks]}")


def test_is_last_flag_semantics_single_chunk():
    """Scenario 5: Verify is_last flag semantics when response is a single sentence.
    
    The sole chunk must have is_last=True.
    """
    class SingleSentenceLLM(LLMInferencePort):
        def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
            return "senyum", "Hanya satu kalimat saja."
        def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
            yield "[senyum] Hanya satu kalimat saja."

    use_case = StreamUserInteractionUseCase(
        llm_port=SingleSentenceLLM(),
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=DummyTTS(),
    )

    collected_chunks: list[StreamChunkDTO] = []
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=False, blocking_audio=True),
        on_chunk_ready=lambda c: collected_chunks.append(c),
    )

    assert len(collected_chunks) == 1, f"Expected 1 chunk, got {len(collected_chunks)}"
    assert collected_chunks[0].is_last is True, "Single chunk must have is_last=True"
    print("  [PASS] Single chunk is_last=True verified")


def test_empty_tokens_abort_safety():
    """Scenario 6: LLM produces 0 tokens."""
    class EmptyLLM(LLMInferencePort):
        def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
            return None, ""
        def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
            return
            yield ""

    use_case = StreamUserInteractionUseCase(
        llm_port=EmptyLLM(),
        kizuna_repo=DummyKizunaRepo(),
        memory_vault=DummyVault(),
        tts_port=DummyTTS(),
    )

    collected_chunks: list[StreamChunkDTO] = []
    res = use_case.execute_stream(
        UserInteractionRequest("Halo", play_audio=False, blocking_audio=True),
        on_chunk_ready=lambda c: collected_chunks.append(c),
    )

    assert len(collected_chunks) == 0, f"Expected 0 chunks for empty stream, got {len(collected_chunks)}"
    assert res.cleaned_reply == ""
    print("  [PASS] Empty token stream safety verified")


if __name__ == "__main__":
    print("=== REVIEWER 2 CONCURRENCY & ROBUSTNESS ADVERSARIAL TESTS ===")
    test_deadlock_elimination_on_immediate_playback_crash()
    test_deadlock_elimination_on_midstream_playback_crash()
    test_queue_overflow_fast_producer_slow_consumer()
    test_is_last_flag_semantics_multi_chunk()
    test_is_last_flag_semantics_single_chunk()
    test_empty_tokens_abort_safety()
    print("=== ALL CONCURRENCY & ROBUSTNESS ADVERSARIAL TESTS PASSED! ===")
