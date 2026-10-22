"""Unit tests: Feature F3 — Proactive Companion (idle service + window position memory).

ProactiveIdleService murni (tanpa I/O/waktu sistem) sehingga dapat diuji
deterministik. Helper posisi jendela diuji dengan filesystem sementara.
"""

from __future__ import annotations

from huohuo.domain.services.proactive_idle_service import ProactiveIdleService
from huohuo.ui.app import _load_window_position, _save_window_position

VALID_EMOTIONS = {
    "senyum", "goda", "sebal", "kaget", "bingung", "lelah",
    "semangat", "sedih", "netral",
}


def test_below_min_idle_returns_none():
    assert ProactiveIdleService.pick_proactive(10, 5, 8) is None


def test_morning_returns_proactive_all_levels():
    picked = ProactiveIdleService.pick_proactive(600, 1, 8, rng=lambda: 0.0)
    assert picked is not None
    emotion, text = picked
    assert emotion in VALID_EMOTIONS
    assert isinstance(text, str) and text.strip()


def test_deep_night_blocked_for_low_kizuna():
    # Jam 23 (malam) tapi ikatan rendah -> belum nyaman menginisiasi.
    assert ProactiveIdleService.pick_proactive(600, 1, 23) is None
    assert ProactiveIdleService.pick_proactive(600, 4, 23) is None


def test_deep_night_allowed_for_high_kizuna():
    picked = ProactiveIdleService.pick_proactive(600, 8, 23, rng=lambda: 0.0)
    assert picked is not None
    assert picked[0] in VALID_EMOTIONS


def test_wrap_subuh_window():
    # Jam 2 (subuh) dengan ikatan tinggi tetap menghasilkan sapaan.
    picked = ProactiveIdleService.pick_proactive(300, 10, 2, rng=lambda: 0.0)
    assert picked is not None


def test_deterministic_with_seeded_rng():
    a = ProactiveIdleService.pick_proactive(500, 6, 13, rng=lambda: 0.42)
    b = ProactiveIdleService.pick_proactive(500, 6, 13, rng=lambda: 0.42)
    assert a == b


# ── Window position persistence ──────────────────────────────────────────────
def test_save_and_load_position_roundtrip(tmp_path):
    f = tmp_path / "window_position.json"
    _save_window_position(f, 120, 340)
    assert _load_window_position(f) == (120, 340)


def test_load_missing_file_returns_none(tmp_path):
    assert _load_window_position(tmp_path / "absen.json") == (None, None)


def test_load_negative_coords_treated_as_unset(tmp_path):
    f = tmp_path / "p.json"
    f.write_text('{"x": -1, "y": 10}', encoding="utf-8")
    assert _load_window_position(f) == (None, None)
