"""Unit tests for concrete adapters in silverwolf/adapters/."""

import json
from pathlib import Path

from silverwolf.adapters.json_kizuna_repository import JsonKizunaRepository
from silverwolf.adapters.llama_server_adapter import LlamaServerAdapter
from silverwolf.adapters.markdown_vault_repository import MarkdownVaultRepository
from silverwolf.adapters.sounddevice_player_adapter import SounddevicePlayerAdapter
from silverwolf.adapters.webview_ui_adapter import WebviewUIAdapter
from silverwolf.domain.entities.kizuna import KizunaState
from silverwolf.domain.entities.mood import MoodState


def test_json_kizuna_repository(tmp_path: Path):
    target_file = tmp_path / "kizuna.json"
    repo = JsonKizunaRepository(file_path=target_file)

    # 1. Loading non-existent file returns default and creates it
    state = repo.load()
    assert state.level == 1
    assert state.stage == "Asing"

    # 2. Update state and save
    state.record_message("Main game bareng yuk!")
    repo.save(state)

    # 3. Reload and verify persistence
    reloaded = repo.load()
    assert reloaded.total_messages == 1
    assert reloaded.points == state.points
    assert len(reloaded.milestones) == len(state.milestones)


def test_markdown_vault_repository(tmp_path: Path):
    repo = MarkdownVaultRepository(root_dir=tmp_path)

    # 1. Default persona if absent
    persona = repo.load_persona()
    assert "Silver Wolf" in persona

    # 2. Write and load Fakta.md
    fakta_path = tmp_path / "Fakta.md"
    fakta_path.write_text("- Master suka kopi hitam\n- Master gamer PC\n", encoding="utf-8")
    facts = repo.load_facts()
    assert "Master suka kopi hitam" in facts
    assert "Master gamer PC" in facts

    # 3. Save and load mood
    mood = MoodState(valensi=0.8, arousal=0.7, label="Ceria / Antusias")
    repo.save_mood(mood)
    loaded_mood = repo.load_mood()
    assert loaded_mood is not None
    assert loaded_mood.valensi == 0.8
    assert loaded_mood.arousal == 0.7

    # 4. Record history
    repo.record_history("Halo!", "[senyum] Halo juga Master!")
    riwayat_files = list((tmp_path / "Riwayat").glob("*.md"))
    assert len(riwayat_files) == 1
    history_text = riwayat_files[0].read_text(encoding="utf-8")
    assert "Master: Halo!" in history_text
    assert "Silver Wolf: [senyum] Halo juga Master!" in history_text


def test_webview_ui_adapter():
    class MockWindow:
        def __init__(self):
            self.eval_scripts = []

        def evaluate_js(self, script: str):
            self.eval_scripts.append(script)

    mock_win = MockWindow()
    adapter = WebviewUIAdapter(mock_win)

    # Show bubble with special characters requiring sanitization
    adapter.show_bubble("Aku gak mau! 'Katanya' Master bohong \n", "sebal")
    assert len(mock_win.eval_scripts) == 1
    assert "window.showBubble(" in mock_win.eval_scripts[0]
    assert "\\'Katanya\\'" in mock_win.eval_scripts[0]
    assert "sebal" in mock_win.eval_scripts[0]

    # Expression
    adapter.set_expression("kaget")
    assert "window.setExpression('kaget');" in mock_win.eval_scripts[1]

    # Kizuna status
    adapter.set_kizuna_status("⚡ Level 5 • Ceria")
    assert "window.setKizunaStatus('⚡ Level 5 • Ceria');" in mock_win.eval_scripts[2]

    # Mouth open clamped to [0.0, 1.0]
    adapter.set_mouth_open(1.5)
    assert "window.setMouthOpen(1.000);" in mock_win.eval_scripts[3]


def test_llama_server_adapter_fallback():
    # Use invalid endpoint to force in-character fallback
    adapter = LlamaServerAdapter(endpoint="http://127.0.0.1:99999/v1")
    assert adapter.is_healthy() is False

    emotion, reply = adapter.generate([{"role": "user", "content": "Halo pacarku"}])
    assert reply != ""
    assert isinstance(reply, str)
    assert emotion is not None


def test_sounddevice_player_adapter_lifecycle():
    player = SounddevicePlayerAdapter()
    assert player.is_playing is False
    player.stop()
    assert player.is_playing is False
