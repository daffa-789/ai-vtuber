"""Unit tests for Application Use Cases using isolated mock ports."""

from typing import Callable, Generator, Iterable, Optional

from huohuo.application.dtos.interaction_dto import UserInteractionRequest
from huohuo.application.use_cases.process_interaction_use_case import (
    ProcessUserInteractionUseCase,
)
from huohuo.application.use_cases.synthesize_voice_use_case import (
    SynthesizeVoiceUseCase,
)
from huohuo.application.use_cases.touch_headpat_use_case import (
    TouchHeadpatUseCase,
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


class MockLLM(LLMInferencePort):
    def __init__(self, reply: str = "[goda] Hehe tentu saja Master!"):
        self.reply = reply
        self.called_messages = []

    def generate(self, messages: list[dict[str, str]]) -> tuple[Optional[str], str]:
        self.called_messages.append(messages)
        return "goda", self.reply

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        self.called_messages.append(messages)
        yield self.reply


class MockKizunaRepo(KizunaRepositoryPort):
    def __init__(self):
        self.state = KizunaState.create_default()
        self.saved_states = []

    def load(self) -> KizunaState:
        return self.state

    def save(self, state: KizunaState) -> None:
        self.state = state
        self.saved_states.append(state)


class MockMemoryVault(MemoryVaultPort):
    def __init__(self):
        self.mood = MoodState.awal()
        self.history = []

    def load_persona(self) -> str:
        return "HuoHuo persona"

    def load_facts(self) -> str:
        return "- Master suka main game RPG"

    def load_mood(self) -> Optional[MoodState]:
        return self.mood

    def save_mood(self, mood: MoodState) -> None:
        self.mood = mood

    def record_history(self, user_text: str, reply_text: str) -> None:
        self.history.append((user_text, reply_text))


class MockTTS(TTSPort):
    def __init__(self):
        self.synthesized_texts = []

    def synthesize(self, text: str, gaya: Optional[str] = None) -> Optional[bytes]:
        self.synthesized_texts.append(text)
        return b"RIFFmockwavdata"


class MockVoiceConversion(VoiceConversionPort):
    def __init__(self):
        self.converted_inputs = []

    def convert(self, wav_bytes: bytes) -> Optional[bytes]:
        self.converted_inputs.append(wav_bytes)
        return b"RIFFrvcconvertedwav"


class MockAudioPlayer(AudioPlayerPort):
    def __init__(self):
        self.played_audio = []
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
        self.played_audio.append(audio_bytes)
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
        for chunk in audio_stream:
            self.played_audio.append(chunk)
            if on_lip_sync:
                on_lip_sync(0.5)
        if on_lip_sync:
            on_lip_sync(0.0)
        return True

    def stop(self) -> None:
        self._playing = False


class MockUI(CompanionUIPort):
    def __init__(self):
        self.bubbles = []
        self.expressions = []
        self.statuses = []
        self.mouth_levels = []

    def show_bubble(self, text: str, emotion: str = "senyum") -> None:
        self.bubbles.append((text, emotion))

    def set_expression(self, emotion: str) -> None:
        self.expressions.append(emotion)

    def set_kizuna_status(self, status_text: str) -> None:
        self.statuses.append(status_text)

    def set_mouth_open(self, level: float) -> None:
        self.mouth_levels.append(level)


def test_process_user_interaction_use_case():
    llm = MockLLM(reply="[senyum] Halo Master tersayang!")
    kizuna_repo = MockKizunaRepo()
    vault = MockMemoryVault()
    tts = MockTTS()
    vc = MockVoiceConversion()
    player = MockAudioPlayer()
    ui = MockUI()

    use_case = ProcessUserInteractionUseCase(
        llm_port=llm,
        kizuna_repo=kizuna_repo,
        memory_vault=vault,
        tts_port=tts,
        voice_conversion_port=vc,
        audio_player_port=player,
        ui_port=ui,
    )

    req = UserInteractionRequest(text="Halo pacar gamerku!", play_audio=True, blocking_audio=True)
    res = use_case.execute(req)

    # Assert response DTO
    assert res.emotion == "senyum"
    assert "Halo Master tersayang!" in res.cleaned_reply
    assert res.kizuna_level >= 1
    assert res.audio_bytes == b"RIFFrvcconvertedwav"

    # Assert mock calls
    assert len(llm.called_messages) == 1
    assert kizuna_repo.state.total_messages == 1
    assert len(vault.history) == 1
    assert len(tts.synthesized_texts) == 1
    assert len(vc.converted_inputs) == 1
    assert len(player.played_audio) == 1
    assert len(ui.bubbles) == 1
    assert ui.bubbles[0][1] == "senyum"
    assert "senyum" in ui.expressions
    assert len(ui.mouth_levels) > 0


def test_touch_headpat_use_case():
    kizuna_repo = MockKizunaRepo()
    tts = MockTTS()
    vc = MockVoiceConversion()
    player = MockAudioPlayer()
    ui = MockUI()

    use_case = TouchHeadpatUseCase(
        kizuna_repo=kizuna_repo,
        tts_port=tts,
        voice_conversion_port=vc,
        audio_player_port=player,
        ui_port=ui,
    )

    res = use_case.execute(play_audio=True, blocking_audio=True)

    assert res.emotion == "kaget"
    assert "elus kepalaku" in res.reply_text.lower()
    assert kizuna_repo.state.total_touches == 1
    assert len(ui.bubbles) == 1
    assert ui.bubbles[0][1] == "kaget"
    assert "kaget" in ui.expressions


def test_synthesize_voice_use_case():
    tts = MockTTS()
    vc = MockVoiceConversion()
    player = MockAudioPlayer()

    use_case = SynthesizeVoiceUseCase(
        tts_port=tts,
        voice_conversion_port=vc,
        audio_player_port=player,
    )

    # Synthesize with conversion
    audio = use_case.synthesize("Halo Master [senyum] *tertawa manis*")
    assert audio == b"RIFFrvcconvertedwav"
    assert tts.synthesized_texts[0] == "Halo Master tertawa manis"

    # Speak with playback
    spoken = use_case.speak("Testing suara", blocking=True)
    assert spoken == b"RIFFrvcconvertedwav"
    assert len(player.played_audio) == 1
