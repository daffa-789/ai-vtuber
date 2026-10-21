"""Unit tests for pure domain entities and value objects."""

from huohuo.domain.entities.character import Character, CharacterFacts, MemoryEntry, Persona
from huohuo.domain.entities.chat_message import ChatMessage, ChatRole
from huohuo.domain.entities.kizuna import KizunaMilestone, KizunaSnapshot, KizunaState
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.value_objects.emotion import EmotionTag


def test_emotion_tag_value_object():
    assert EmotionTag.SENYUM == "senyum"
    assert EmotionTag.from_str("[goda]") == EmotionTag.GODA
    assert EmotionTag.from_str("sebal") == EmotionTag.SEBAL
    assert EmotionTag.from_str("unknown_tag") == EmotionTag.NETRAL
    assert EmotionTag.from_str(None) == EmotionTag.NETRAL
    assert "senyum" in EmotionTag.valid_tags()


def test_mood_state_transitions():
    mood = MoodState.awal()
    assert mood.valensi == 0.6
    assert mood.arousal == 0.5
    assert "Santai" in mood.label

    # Positive emotion updates
    cheerful = MoodState.perbarui(mood, "senyum")
    assert cheerful.valensi > mood.valensi
    assert cheerful.arousal >= mood.arousal

    # Negative emotion updates
    annoyed = MoodState.perbarui(mood, "sebal")
    assert annoyed.valensi < mood.valensi

    # Invalid emotion leaves mood unchanged
    unchanged = MoodState.perbarui(mood, None)
    assert unchanged.valensi == mood.valensi


def test_kizuna_state_logic():
    kizuna = KizunaState.create_default()
    assert kizuna.level == 1
    assert kizuna.points == 0.0

    # Record message
    snap = kizuna.record_message("Ayo mabar game bareng!")
    assert kizuna.total_messages == 1
    assert snap.points > 0.0

    # Record touch
    snap_touch = kizuna.record_touch()
    assert kizuna.total_touches == 1
    assert snap_touch.total_touches == 1

    prompt_ctx = kizuna.get_prompt_context()
    assert "STATUS IKATAN KIZUNA" in prompt_ctx
    assert f"Level {snap_touch.level}" in prompt_ctx


def test_chat_message_entity():
    msg = ChatMessage(role=ChatRole.USER, content="Halo HuoHuo!")
    assert msg.role == ChatRole.USER
    assert msg.content == "Halo HuoHuo!"
    assert msg.created_at != ""
    assert msg.to_dict() == {"role": "user", "content": "Halo HuoHuo!"}


def test_character_entity():
    char = Character()
    assert char.name == "HuoHuo"
    persona = Persona(content="Gamer hacker")
    assert persona.version == "1.0"
