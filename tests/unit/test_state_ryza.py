"""Tes lapisan state 'Ryza-like': parser <state>, perluasan KizunaState, dan
pemakaiannya di use-case chat (energi/aktivitas/quest + strip blok dari teks)."""

from __future__ import annotations

from typing import Optional

from huohuo.application.dtos.interaction_dto import UserInteractionRequest
from huohuo.application.use_cases.process_interaction_use_case import ProcessUserInteractionUseCase
from huohuo.domain.entities.kizuna import KizunaState
from huohuo.domain.entities.mood import MoodState
from huohuo.domain.services.emotion_service import EmotionParserService
from huohuo.domain.services.state_service import StateParserService


def test_emotion_parser_strips_unknown_leading_tag():
    # Tag emosi ngawur dari model kecil (mis. [euforia]) harus dibuang dari teks.
    emo, clean = EmotionParserService.parse("[euforia]\nM-master! A-aku senang!")
    assert emo is None
    assert "euforia" not in clean and "[" not in clean
    assert clean.startswith("M-master")


def test_emotion_parser_keeps_valid_tag():
    emo, clean = EmotionParserService.parse("[senyum] Halo Master")
    assert emo == "senyum"
    assert clean == "Halo Master"


# ── StateParserService ───────────────────────────────────────────────────────

def test_parse_state_block_and_strip():
    raw = "Halo Master! <state>energi=72; aktivitas=belajar bareng; quest=nugas 2/5</state>"
    state, clean = StateParserService.parse(raw)
    assert state["energi"] == 72
    assert state["aktivitas"] == "belajar bareng"
    assert state["quest"] == "nugas 2/5"
    assert clean == "Halo Master!"
    assert "<state>" not in clean and "energi" not in clean


def test_parse_no_block_returns_empty():
    state, clean = StateParserService.parse("Halo biasa aja ya")
    assert state == {}
    assert clean == "Halo biasa aja ya"


def test_parse_english_alias_and_clamp():
    state, _ = StateParserService.parse("x <state>energy=250; activity=meditasi</state>")
    assert state["energi"] == 100  # clamp ke 100
    assert state["aktivitas"] == "meditasi"


def test_parse_multiline_block():
    state, clean = StateParserService.parse("hai\n<state>energi=40\naktivitas=nonton</state>")
    assert state["energi"] == 40
    assert state["aktivitas"] == "nonton"
    assert clean.startswith("hai")


# ── KizunaState perluasan ────────────────────────────────────────────────────

def test_apply_state_updates_fields():
    k = KizunaState.create_default()
    k.apply_state({"energi": 55, "aktivitas": "masak", "quest": "racik ramuan 1/3"})
    assert k.energi == 55
    assert k.aktivitas == "masak"
    assert k.quest == "racik ramuan 1/3"


def test_hud_text_contains_energy_and_activity():
    k = KizunaState.create_default()
    k.energi = 80
    k.aktivitas = "mabar"
    hud = k.hud_text("Ceria")
    assert "80%" in hud and "mabar" in hud and "Kizuna" in hud


# ── Use-case: state diterapkan + teks dibersihkan ────────────────────────────

class _LLM:
    def __init__(self, reply): self.reply = reply
    def generate(self, messages): return "senyum", self.reply
    def stream(self, messages): yield self.reply


class _Repo:
    def __init__(self): self.state = KizunaState.create_default(); self.saves = 0
    def load(self): return self.state
    def save(self, state): self.state = state; self.saves += 1


class _Vault:
    def load_persona(self): return "persona"
    def load_facts(self): return ""
    def load_mood(self): return MoodState.awal()
    def save_mood(self, mood): pass
    def record_history(self, u, r): pass


class _UI:
    def __init__(self): self.bubbles = []; self.statuses = []
    def show_bubble(self, text, emotion="senyum"): self.bubbles.append(text)
    def set_expression(self, emotion): pass
    def set_kizuna_status(self, s): self.statuses.append(s)
    def set_mouth_open(self, level): pass


def test_use_case_applies_state_and_strips_block():
    llm = _LLM("[senyum] A-aku lagi nugas nih Master... <state>energi=61; aktivitas=nugas; quest=nugas 3/5</state>")
    repo = _Repo()
    ui = _UI()
    uc = ProcessUserInteractionUseCase(llm_port=llm, kizuna_repo=repo, memory_vault=_Vault(), ui_port=ui)
    res = uc.execute(UserInteractionRequest(text="lagi apa?", play_audio=False, blocking_audio=False))

    assert res.cleaned_reply == "A-aku lagi nugas nih Master..."
    assert "<state>" not in res.cleaned_reply
    assert repo.state.energi == 61
    assert repo.state.aktivitas == "nugas"
    assert repo.state.quest == "nugas 3/5"
    assert ui.bubbles == ["A-aku lagi nugas nih Master..."]
    assert any("61%" in s for s in ui.statuses)
