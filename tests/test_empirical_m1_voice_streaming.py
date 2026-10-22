"""Empirical Stress & Adversarial Verification: Milestone M1 Voice Streaming Pipeline.

Adversarial Challenger Suite:
1. Slow token generation (50ms per token) -> Measure TTFA (< 1.0s).
2. Bursty token generation (10 tokens at once, 500ms pause, 10 tokens) -> Assert pipelining decoupling.
3. Instant token generation (0ms delay) -> Measure baseline pipeline latency.
4. Lip-sync continuity in SounddevicePlayerAdapter -> Verify 0.0 is never emitted between chunks.
5. Single-character token fragmentation -> Verify state machine robustness.
6. Mid-stream LLM exception resilience -> Verify zero deadlock / hanging threads.
7. Empty/whitespace stream handling.

Can be run via:
    uv run python tests/test_empirical_m1_voice_streaming.py
or
    uv run pytest tests/test_empirical_m1_voice_streaming.py
"""

from __future__ import annotations

import io
import math
import struct
import sys
import time
from typing import Callable, Generator, Iterable, Optional
import wave

import pytest

from huohuo.adapters.sounddevice_player_adapter import SounddevicePlayerAdapter
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
from huohuo.domain.services.sentence_splitter_service import SentenceSplitterService


# =============================================================================
# Synthetic Audio Generator (Standard Library wave + struct)
# =============================================================================

def generate_synthetic_wav(duration_s: float = 0.20, frequency: float = 440.0, volume: float = 0.5) -> bytes:
    """Generate in-memory PCM 16-bit 16000Hz mono WAV bytes with non-zero audio energy."""
    framerate = 16000
    n_samples = int(framerate * duration_s)
    samples = [
        int(32767 * volume * math.sin(2 * math.pi * frequency * i / framerate))
        for i in range(n_samples)
    ]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


# =============================================================================
# Test Doubles & Adversarial LLM Generators
# =============================================================================

class SlowTokenLLM(LLMInferencePort):
    """Simulates slow token streaming (e.g. 50ms per token)."""

    def __init__(self, tokens: list[str], delay_per_token: float = 0.050):
        self.tokens = tokens
        self.delay = delay_per_token

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        return "senyum", "".join(self.tokens)

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        for token in self.tokens:
            if self.delay > 0:
                time.sleep(self.delay)
            yield token


class BurstyTokenLLM(LLMInferencePort):
    """Simulates bursty token streaming: burst of tokens, long pause, then remaining tokens."""

    def __init__(
        self,
        burst1: list[str],
        pause_s: float,
        burst2: list[str],
    ):
        self.burst1 = burst1
        self.pause_s = pause_s
        self.burst2 = burst2

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        return "goda", "".join(self.burst1 + self.burst2)

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        # Burst 1: rapid yield
        for token in self.burst1:
            yield token

        # Pause: LLM reasoning stall / network jitter
        time.sleep(self.pause_s)

        # Burst 2: second burst
        for token in self.burst2:
            yield token


class ExceptionTokenLLM(LLMInferencePort):
    """Simulates mid-stream network drop / SSE disconnection."""

    def __init__(self, initial_tokens: list[str], error_after: int = 3):
        self.initial_tokens = initial_tokens
        self.error_after = error_after

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        raise RuntimeError("LLM inference aborted")

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        for i, token in enumerate(self.initial_tokens):
            if i >= self.error_after:
                raise ConnectionResetError("SSE stream abruptly terminated by remote host")
            time.sleep(0.01)
            yield token


class BenchmarkTTS(TTSPort):
    """TTS with simulated synthesis compute latency."""

    def __init__(self, latency_per_chunk: float = 0.030):
        self.latency = latency_per_chunk
        self.synthesized_clauses: list[str] = []

    def synthesize(self, text: str) -> Optional[bytes]:
        if self.latency > 0:
            time.sleep(self.latency)
        self.synthesized_clauses.append(text)
        return generate_synthetic_wav(duration_s=0.15)


class InstrumentedAudioPlayer(AudioPlayerPort):
    """Instrumented audio player recording microsecond timestamps and lip-sync calls."""

    def __init__(self, frame_delay: float = 0.020):
        self.frame_delay = frame_delay
        self.played_chunks: list[bytes] = []
        self.chunk_receipt_times: list[float] = []
        self.lip_sync_log: list[tuple[float, float]] = []  # (perf_counter, level)
        self.is_playing_state = False

    @property
    def is_playing(self) -> bool:
        return self.is_playing_state

    def play(
        self,
        audio_bytes: bytes,
        on_lip_sync: Optional[Callable[[float], None]] = None,
        blocking: bool = True,
    ) -> bool:
        self.played_chunks.append(audio_bytes)
        self.chunk_receipt_times.append(time.perf_counter())
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
        self.is_playing_state = True
        idx = 0
        try:
            for chunk in audio_stream:
                now = time.perf_counter()
                self.chunk_receipt_times.append(now)
                self.played_chunks.append(chunk)

                if on_chunk_start:
                    on_chunk_start(idx)
                idx += 1

                # Simulate continuous audio chunk frames with non-zero lip sync
                if on_lip_sync:
                    for simulated_lvl in [0.45, 0.65]:
                        t_frame = time.perf_counter()
                        self.lip_sync_log.append((t_frame, simulated_lvl))
                        on_lip_sync(simulated_lvl)
                        if self.frame_delay > 0:
                            time.sleep(self.frame_delay)
        finally:
            self.is_playing_state = False
            if on_lip_sync:
                t_frame = time.perf_counter()
                self.lip_sync_log.append((t_frame, 0.0))
                on_lip_sync(0.0)
        return True

    def stop(self) -> None:
        self.is_playing_state = False


class InMemoryKizunaRepo(KizunaRepositoryPort):
    def __init__(self):
        self.kizuna = KizunaState()

    def load(self) -> KizunaState:
        return self.kizuna

    def save(self, state: KizunaState) -> None:
        self.kizuna = state


class InMemoryVault(MemoryVaultPort):
    def __init__(self):
        self.persona = "HuoHuo persona"
        self.facts = ["Master likes games"]
        self.mood = MoodState.awal()
        self.history = []

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


class InstrumentedUI(CompanionUIPort):
    def __init__(self):
        self.bubbles: list[tuple[float, str, str]] = []
        self.mouth_updates: list[tuple[float, float]] = []

    def show_bubble(self, text: str, emotion: str = "senyum") -> None:
        self.bubbles.append((time.perf_counter(), text, emotion))

    def set_expression(self, emotion: str) -> None:
        pass

    def set_mouth_open(self, level: float) -> None:
        self.mouth_updates.append((time.perf_counter(), level))

    def set_kizuna_status(self, text: str) -> None:
        pass


# =============================================================================
# Test Scenarios
# =============================================================================

BENCHMARK_RESULTS: dict[str, dict] = {}


def test_slow_token_generation_ttfa() -> None:
    """Test 1: Slow token generation (50ms/token). Asserts TTFA < 1.0s."""
    tokens = [
        "[senyum] ",
        "Halo ",
        "Master ",
        "tersayang, ",  # Clause 1 boundary here (4 tokens)
        "aku ",
        "kangen ",
        "banget ",
        "nih ",
        "sama ",
        "kamu!",
    ]
    llm = SlowTokenLLM(tokens, delay_per_token=0.050)
    tts = BenchmarkTTS(latency_per_chunk=0.030)
    player = InstrumentedAudioPlayer(frame_delay=0.010)
    ui = InstrumentedUI()
    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=tts,
        audio_player_port=player,
        ui_port=ui,
    )

    ready_chunks: list[StreamChunkDTO] = []
    t_0 = time.perf_counter()
    response = use_case.execute_stream(
        UserInteractionRequest("Halo HuoHuo", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: ready_chunks.append(c),
    )
    t_end = time.perf_counter()

    assert len(player.chunk_receipt_times) >= 1, "AudioPlayer received no chunks!"
    t_audio = player.chunk_receipt_times[0]
    ttfa = t_audio - t_0
    total_duration = t_end - t_0

    # Strict assertion: TTFA must be < 1.0s
    assert ttfa < 1.0, f"Slow token TTFA violated: {ttfa:.4f}s >= 1.0s"
    assert response.emotion == "senyum"
    assert "Halo Master tersayang," in response.cleaned_reply

    # Verify StreamChunkDTO is_last propagation
    assert len(ready_chunks) >= 2, f"Expected >= 2 chunks, got {len(ready_chunks)}"
    assert ready_chunks[-1].is_last is True, f"Final chunk is_last must be True, got {ready_chunks[-1].is_last}"
    assert all(c.is_last is False for c in ready_chunks[:-1]), f"Intermediate chunks must be False: {[c.is_last for c in ready_chunks]}"

    # Verify Lip-Sync Continuity: no 0.0 before final frame
    levels = [lvl for _, lvl in player.lip_sync_log]
    assert len(levels) >= 3, "Expected at least 3 lip-sync events"
    assert levels[-1] == 0.0, "Last lip-sync level must reset to 0.0"
    assert all(lvl > 0.0 for lvl in levels[:-1]), f"Lip-sync dropped to 0.0 prematurely: {levels}"

    BENCHMARK_RESULTS["test_slow_token_generation_ttfa"] = {
        "scenario": "slow_50ms",
        "t0": t_0,
        "t_audio": t_audio,
        "ttfa_seconds": ttfa,
        "total_duration_seconds": total_duration,
        "chunks_count": len(player.played_chunks),
        "is_last_flags": [c.is_last for c in ready_chunks],
    }


def test_bursty_token_generation_pipelining() -> None:
    """Test 2: Bursty token generation (10 tokens at once, then 500ms pause).

    Asserts TTFA < 1.0s AND verifies that audio plays BEFORE the 500ms pause finishes.
    """
    burst1 = [
        "[goda] ",
        "Halo ",
        "Master ",
        "tersayang, ",  # Clause 1 boundary in burst 1
        "lagi ",
        "sibuk ",
        "apa ",
        "nih ",
        "sekarang? ",
    ]
    burst2 = [
        "Ayo ",
        "kita ",
        "mabar ",
        "game ",
        "sekarang!",
    ]
    llm = BurstyTokenLLM(burst1=burst1, pause_s=0.500, burst2=burst2)
    tts = BenchmarkTTS(latency_per_chunk=0.030)
    player = InstrumentedAudioPlayer(frame_delay=0.010)
    ui = InstrumentedUI()
    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=tts,
        audio_player_port=player,
        ui_port=ui,
    )

    ready_chunks: list[StreamChunkDTO] = []
    t_0 = time.perf_counter()
    response = use_case.execute_stream(
        UserInteractionRequest("Mabar yuk", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: ready_chunks.append(c),
    )
    t_end = time.perf_counter()

    assert len(player.chunk_receipt_times) >= 2, "Expected at least 2 audio chunks"
    t_audio = player.chunk_receipt_times[0]
    ttfa = t_audio - t_0
    total_duration = t_end - t_0

    # 1. Assert TTFA < 1.0s
    assert ttfa < 1.0, f"Bursty token TTFA violated: {ttfa:.4f}s >= 1.0s"

    # 2. Assert asynchronous pipelining:
    # Audio for clause 1 starts playing well BEFORE the 500ms pause completes!
    assert ttfa < 0.25, f"Expected pipelined TTFA < 0.25s, got {ttfa:.4f}s"
    assert total_duration >= 0.50, f"Total stream time {total_duration:.4f}s should exceed pause duration 0.50s"

    # 3. Assert StreamChunkDTO is_last propagation
    assert len(ready_chunks) >= 2, f"Expected >= 2 chunks, got {len(ready_chunks)}"
    assert ready_chunks[-1].is_last is True, f"Final chunk is_last must be True, got {ready_chunks[-1].is_last}"
    assert all(c.is_last is False for c in ready_chunks[:-1]), f"Intermediate chunks must be False: {[c.is_last for c in ready_chunks]}"

    # 4. Assert lip-sync continuity
    levels = [lvl for _, lvl in player.lip_sync_log]
    assert levels[-1] == 0.0
    assert all(lvl > 0.0 for lvl in levels[:-1]), f"Lip-sync dropped to 0.0 mid-stream: {levels}"

    BENCHMARK_RESULTS["test_bursty_token_generation_pipelining"] = {
        "scenario": "bursty_500ms_pause",
        "t0": t_0,
        "t_audio": t_audio,
        "ttfa_seconds": ttfa,
        "total_duration_seconds": total_duration,
        "chunks_count": len(player.played_chunks),
        "is_last_flags": [c.is_last for c in ready_chunks],
    }


def test_instant_token_generator() -> None:
    """Test 3: Instant token generator (0ms delay).

    Measures baseline pipeline overhead and confirms sub-second latency.
    """
    tokens = [
        "[semangat] ",
        "Pagi ",
        "Master! ",
        "Siap ",
        "untuk ",
        "misi ",
        "hari ",
        "ini? ",
    ]
    llm = SlowTokenLLM(tokens, delay_per_token=0.0)
    tts = BenchmarkTTS(latency_per_chunk=0.020)
    player = InstrumentedAudioPlayer(frame_delay=0.010)
    ui = InstrumentedUI()
    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=tts,
        audio_player_port=player,
        ui_port=ui,
    )

    ready_chunks: list[StreamChunkDTO] = []
    t_0 = time.perf_counter()
    response = use_case.execute_stream(
        UserInteractionRequest("Selamat pagi", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: ready_chunks.append(c),
    )
    t_end = time.perf_counter()

    assert len(player.chunk_receipt_times) >= 1
    t_audio = player.chunk_receipt_times[0]
    ttfa = t_audio - t_0
    total_duration = t_end - t_0

    assert ttfa < 1.0, f"Instant TTFA exceeded 1.0s: {ttfa:.4f}s"
    assert ttfa < 0.50, f"Instant TTFA expected < 500ms, got {ttfa:.4f}s"

    # Assert StreamChunkDTO is_last propagation
    assert len(ready_chunks) >= 2, f"Expected >= 2 chunks, got {len(ready_chunks)}"
    assert ready_chunks[-1].is_last is True, f"Final chunk is_last must be True, got {ready_chunks[-1].is_last}"
    assert all(c.is_last is False for c in ready_chunks[:-1]), f"Intermediate chunks must be False: {[c.is_last for c in ready_chunks]}"

    levels = [lvl for _, lvl in player.lip_sync_log]
    assert levels[-1] == 0.0
    assert all(lvl > 0.0 for lvl in levels[:-1])

    BENCHMARK_RESULTS["test_instant_token_generator"] = {
        "scenario": "instant",
        "t0": t_0,
        "t_audio": t_audio,
        "ttfa_seconds": ttfa,
        "total_duration_seconds": total_duration,
        "chunks_count": len(player.played_chunks),
        "is_last_flags": [c.is_last for c in ready_chunks],
    }


def _has_audio_output_device() -> bool:
    """True bila ada perangkat keluar audio (diperlukan uji lip-sync nyata)."""
    try:
        import sounddevice as sd

        return any(d.get("maxoutputchannels", 0) > 0 for d in sd.query_devices())
    except Exception:
        return False


@pytest.mark.skipif(
    not _has_audio_output_device(),
    reason="Tidak ada perangkat keluar audio (headless CI) untuk uji lip-sync nyata",
)
def test_sounddevice_adapter_real_lipsync_continuity() -> None:
    """Test 4: Verify SounddevicePlayerAdapter.play_stream() directly with real WAV chunks.

    Confirms that in real adapter execution, on_lip_sync does not drop to 0.0 between consecutive chunks.
    """
    chunk1 = generate_synthetic_wav(duration_s=0.10, frequency=440.0, volume=0.6)
    chunk2 = generate_synthetic_wav(duration_s=0.10, frequency=880.0, volume=0.6)

    player = SounddevicePlayerAdapter()
    captured_lip_sync: list[float] = []

    def _lip_callback(lvl: float) -> None:
        captured_lip_sync.append(round(lvl, 3))

    t_start = time.perf_counter()
    ok = player.play_stream([chunk1, chunk2], on_lip_sync=_lip_callback)
    t_elapsed = time.perf_counter() - t_start

    assert ok is True
    assert len(captured_lip_sync) >= 4, f"Expected >= 4 lip frames, got {len(captured_lip_sync)}"

    # Lip-sync continuity check:
    # 1. Last value must be 0.0
    assert captured_lip_sync[-1] == 0.0, f"Expected final value 0.0, got {captured_lip_sync[-1]}"
    # 2. Every single preceding value must be > 0.0
    preceding = captured_lip_sync[:-1]
    assert all(v > 0.0 for v in preceding), f"Intermediate zero detected in lip-sync stream: {captured_lip_sync}"

    BENCHMARK_RESULTS["test_sounddevice_adapter_real_lipsync_continuity"] = {
        "test": "sounddevice_lipsync_continuity",
        "frames_count": len(captured_lip_sync),
        "levels": captured_lip_sync,
        "duration_seconds": t_elapsed,
    }


def test_adversarial_single_character_slow_stream() -> None:
    """Test 5: Adversarial single-character streaming (1 char per token, 10ms delay)."""
    full_sentence = "[senyum] Halo Master, ayo main!"
    tokens = list(full_sentence)  # 31 tokens of 1 character each
    llm = SlowTokenLLM(tokens, delay_per_token=0.010)
    tts = BenchmarkTTS(latency_per_chunk=0.020)
    player = InstrumentedAudioPlayer(frame_delay=0.010)
    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=tts,
        audio_player_port=player,
    )

    t_0 = time.perf_counter()
    response = use_case.execute_stream(
        UserInteractionRequest("Ayo main", play_audio=True, blocking_audio=True)
    )
    t_end = time.perf_counter()

    t_audio = player.chunk_receipt_times[0]
    ttfa = t_audio - t_0

    assert ttfa < 1.0, f"Single-character TTFA exceeded 1.0s: {ttfa:.4f}s"
    assert response.cleaned_reply == "Halo Master, ayo main!"
    BENCHMARK_RESULTS["test_adversarial_single_character_slow_stream"] = {
        "scenario": "adversarial_char_stream",
        "ttfa_seconds": ttfa,
        "total_duration_seconds": t_end - t_0,
    }


def test_adversarial_midstream_exception_handling():
    """Test 6: Adversarial mid-stream exception handling.

    Verifies pipeline does not deadlock or hang if LLM stream aborts abruptly.
    """
    initial_tokens = ["[senyum] ", "Halo Master tersayang, ", "dan tiba-tiba mati!"]
    llm = ExceptionTokenLLM(initial_tokens=initial_tokens, error_after=2)
    tts = BenchmarkTTS(latency_per_chunk=0.020)
    player = InstrumentedAudioPlayer(frame_delay=0.010)
    use_case = StreamUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=tts,
        audio_player_port=player,
    )

    t_0 = time.perf_counter()
    response = use_case.execute_stream(
        UserInteractionRequest("Crash test", play_audio=True, blocking_audio=True)
    )
    duration = time.perf_counter() - t_0

    # Pipeline must terminate cleanly and promptly (< 1.0s)
    assert duration < 1.0, f"Pipeline hung on exception: duration {duration:.4f}s"
    # Even with mid-stream abort, first clause was salvaged and played
    assert len(player.played_chunks) >= 1
    assert "Halo Master tersayang," in response.cleaned_reply


def test_stream_chunk_dto_is_last_propagation() -> None:
    """Test 7: Exhaustive verification of is_last=True propagation.

    Verifies:
    1. Single-clause stream emits exactly 1 chunk with is_last=True.
    2. Multi-clause stream (5 clauses) emits exactly 5 chunks with is_last=[False, False, False, False, True].
    3. Stream without audio (play_audio=False) still dispatches chunks to on_chunk_ready with is_last=True on the final chunk.
    4. Empty interaction text returns immediately without emitting chunks.
    """
    # Sub-case 1: Single clause stream
    chunks_single: list[StreamChunkDTO] = []
    uc_single = StreamUserInteractionUseCase(
        llm_port=SlowTokenLLM(["[senyum] Hanya satu kalimat saja!"], delay_per_token=0.0),
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=BenchmarkTTS(0.0),
        audio_player_port=InstrumentedAudioPlayer(0.0),
        ui_port=InstrumentedUI(),
    )
    uc_single.execute_stream(
        UserInteractionRequest("Hi", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: chunks_single.append(c),
    )
    assert len(chunks_single) == 1, f"Expected 1 chunk, got {len(chunks_single)}"
    assert chunks_single[0].is_last is True, f"Single chunk must have is_last=True, got {chunks_single[0].is_last}"
    assert chunks_single[0].chunk_id == 0

    # Sub-case 2: Multi-clause stream (5 distinct clauses >= 15 chars)
    tokens_multi = [
        "[senyum] Ini adalah klausa panjang ke-0, ",
        "ini adalah klausa panjang ke-1, ",
        "ini adalah klausa panjang ke-2, ",
        "ini adalah klausa panjang ke-3, ",
        "dan ini adalah klausa penutup!",
    ]
    chunks_multi: list[StreamChunkDTO] = []
    uc_multi = StreamUserInteractionUseCase(
        llm_port=SlowTokenLLM(tokens_multi, delay_per_token=0.0),
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=BenchmarkTTS(0.0),
        audio_player_port=InstrumentedAudioPlayer(0.0),
        ui_port=InstrumentedUI(),
    )
    uc_multi.execute_stream(
        UserInteractionRequest("Hi multi", play_audio=True, blocking_audio=True),
        on_chunk_ready=lambda c: chunks_multi.append(c),
    )
    assert len(chunks_multi) == 5, f"Expected 5 chunks, got {len(chunks_multi)}"
    flags = [c.is_last for c in chunks_multi]
    assert flags == [False, False, False, False, True], f"Unexpected is_last flags: {flags}"
    assert [c.chunk_id for c in chunks_multi] == [0, 1, 2, 3, 4]

    # Sub-case 3: Play audio disabled (play_audio=False)
    chunks_no_audio: list[StreamChunkDTO] = []
    uc_no_audio = StreamUserInteractionUseCase(
        llm_port=SlowTokenLLM(["[senyum] Kalimat pertama tanpa audio, ", "kalimat kedua tanpa audio!"], delay_per_token=0.0),
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
        tts_port=BenchmarkTTS(0.0),
        audio_player_port=InstrumentedAudioPlayer(0.0),
        ui_port=InstrumentedUI(),
    )
    uc_no_audio.execute_stream(
        UserInteractionRequest("No audio", play_audio=False, blocking_audio=True),
        on_chunk_ready=lambda c: chunks_no_audio.append(c),
    )
    assert len(chunks_no_audio) == 2, f"Expected 2 chunks, got {len(chunks_no_audio)}"
    assert chunks_no_audio[0].is_last is False
    assert chunks_no_audio[1].is_last is True
    assert chunks_no_audio[0].audio_bytes is None
    assert chunks_no_audio[1].audio_bytes is None

    # Sub-case 4: Empty input string
    chunks_empty: list[StreamChunkDTO] = []
    uc_empty = StreamUserInteractionUseCase(
        llm_port=SlowTokenLLM([], delay_per_token=0.0),
        kizuna_repo=InMemoryKizunaRepo(),
        memory_vault=InMemoryVault(),
    )
    res_empty = uc_empty.execute_stream(
        UserInteractionRequest("   "),
        on_chunk_ready=lambda c: chunks_empty.append(c),
    )
    assert len(chunks_empty) == 0
    assert res_empty.cleaned_reply == ""

    BENCHMARK_RESULTS["test_stream_chunk_dto_is_last_propagation"] = {
        "single_clause_is_last": [c.is_last for c in chunks_single],
        "multi_clause_is_last": flags,
        "no_audio_is_last": [c.is_last for c in chunks_no_audio],
    }


# =============================================================================
# CLI Main Runner
# =============================================================================

def run_all_empirical_tests() -> int:
    print("=" * 80)
    print("EMPIRICAL CHALLENGER VERIFICATION: MILESTONE M1 VOICE STREAMING")
    print("=" * 80)

    results = []
    tests = [
        ("1. Slow Token Generation (50ms/token)", test_slow_token_generation_ttfa),
        ("2. Bursty Token Generation (10 tokens, 500ms pause)", test_bursty_token_generation_pipelining),
        ("3. Instant Token Generation (0ms delay)", test_instant_token_generator),
        ("4. SounddevicePlayerAdapter Lip-Sync Continuity", test_sounddevice_adapter_real_lipsync_continuity),
        ("5. Single-Character Fragmentation (10ms/char)", test_adversarial_single_character_slow_stream),
        ("6. Mid-Stream LLM Exception Resilience", test_adversarial_midstream_exception_handling),
        ("7. StreamChunkDTO is_last Propagation", test_stream_chunk_dto_is_last_propagation),
    ]

    all_passed = True
    for name, test_fn in tests:
        print(f"\n[RUNNING] {name}...")
        try:
            test_fn()
            print(f"  -> PASS")
            res = BENCHMARK_RESULTS.get(test_fn.__name__, {})
            if isinstance(res, dict) and res:
                for k, v in res.items():
                    if isinstance(v, float):
                        print(f"     {k}: {v:.4f}")
                    else:
                        print(f"     {k}: {v}")
            results.append((name, "PASS", res))
        except AssertionError as exc:
            print(f"  -> FAIL: {exc}")
            results.append((name, "FAIL", str(exc)))
            all_passed = False
        except Exception as exc:
            print(f"  -> ERROR: {exc}")
            results.append((name, "ERROR", str(exc)))
            all_passed = False

    print("\n" + "=" * 80)
    print("EMPIRICAL VERIFICATION SUMMARY")
    print("=" * 80)
    for name, status, details in results:
        status_str = f"[{status}]".ljust(8)
        print(f"{status_str} {name}")

    if all_passed:
        print("\nOVERALL EMPIRICAL VERDICT: APPROVE (100% Passed, TTFA < 1.0s, Lip-Sync Continuous)")
        return 0
    else:
        print("\nOVERALL EMPIRICAL VERDICT: REQUEST_CHANGES")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_empirical_tests())
