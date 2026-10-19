"""Unit test untuk kizuna dan memory."""

import tempfile
from pathlib import Path
from silverwolf.core.kizuna import KizunaEngine
from silverwolf.core.memory import CharacterVault, ChatHistory
from silverwolf.core.mood import Mood


def test_kizuna_engine_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_file = Path(tmpdir) / "kizuna.json"
        engine = KizunaEngine(storage_path=storage_file)

        # Snapshot awal
        snap1 = engine.get_snapshot()
        assert snap1.level == 1
        assert snap1.points == 0.0

        # Catat pesan
        snap2 = engine.record_message("Halo Silver Wolf", points=10.0)
        assert snap2.points == 10.0
        assert snap2.total_interactions == 1

        # Uji persistensi: muat ulang engine dari berkas yang sama
        engine_reloaded = KizunaEngine(storage_path=storage_file)
        snap3 = engine_reloaded.get_snapshot()
        assert snap3.points == 10.0
        assert snap3.total_interactions == 1

        # Cek prompt context
        ctx = engine.get_prompt_context()
        assert "Konteks Hubungan Ikatan (Kizuna)" in ctx
        assert "Level 1" in ctx


def test_character_vault_fakta_dan_mood():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = CharacterVault(tmpdir)

        # Simpan & baca fakta
        vault.simpan_fakta(["Master suka game RPG", "Master suka ngoding"])
        fakta = vault.baca_fakta()
        assert "Master suka game RPG" in fakta
        assert "Master suka ngoding" in fakta

        # Simpan & baca mood
        mood = Mood(valensi=0.8, energi=0.9, afinitas=0.95, pertukaran=5, alasan="senang")
        vault.simpan_mood(mood)
        mood_dibaca = vault.baca_mood()
        assert mood_dibaca is not None
        assert abs(mood_dibaca.valensi - 0.8) < 0.05
        assert abs(mood_dibaca.energi - 0.9) < 0.05


def test_chat_history():
    history = ChatHistory(batas_pesan=5)
    history.tambah("user", "Halo")
    history.tambah("assistant", "[senyum] Halo Master!")

    msgs = history.ke_format_llm()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "[senyum] Halo Master!"
