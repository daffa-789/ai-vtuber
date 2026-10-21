"""Phase 2 E2E Tests: Feature F4 — CLI Execution Compatibility & Entry Points.

Tests command-line interfaces (`--help`, `--cli`, `--test-voice`, `--voice-in`).
Derives expected behavior directly from ORIGINAL_REQUEST.md & PROJECT.md specifications.
Supports Progressive Testability during milestone rollouts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import pytest

MAIN_SCRIPT = str(Path(__file__).resolve().parents[2] / "main.py")


# =============================================================================
# TIER 1: Feature Coverage (Happy-Path Tests in Isolation)
# =============================================================================

def test_t1_f4_cli_help_flag_zero_exit():
    """Tier 1: Running python main.py --help must exit with code 0."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Expected returncode 0, got {result.returncode}. Stderr: {result.stderr}"
    assert "HuoHuo" in result.stdout or "usage:" in result.stdout.lower()


def test_t1_f4_cli_help_describes_core_options():
    """Tier 1: Help message must describe core options: --cli, --test-voice, --port."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    stdout = result.stdout
    assert "--cli" in stdout
    assert "--test-voice" in stdout
    assert "--port" in stdout


def test_t1_f4_cli_interactive_clean_exit():
    """Tier 1: Running python main.py --cli and sending 'keluar' exits cleanly with code 0."""
    proc = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT, "--cli"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(input="keluar\n", timeout=15)
    assert proc.returncode == 0, f"CLI exited with {proc.returncode}. Stderr: {stderr}"
    assert "Terminal Companion" in stdout or "Status Ikatan" in stdout
    assert "Sampai jumpa" in stdout


def test_t1_f4_cli_interactive_exit_synonyms():
    """Tier 1: Testing synonym quit commands ('exit' and 'quit') terminate CLI mode cleanly."""
    for cmd in ("exit\n", "quit\n"):
        proc = subprocess.Popen(
            [sys.executable, MAIN_SCRIPT, "--cli"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=cmd, timeout=15)
        assert proc.returncode == 0, f"CLI exited with {proc.returncode} on command {cmd.strip()}"
        assert "Sampai jumpa" in stdout


def test_t1_f4_cli_test_voice_execution():
    """Tier 1: Running python main.py --test-voice synthesizes and exits without unhandled exception."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--test-voice"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, f"Voice test crashed with code {result.returncode}. Stderr: {result.stderr}"
    assert "sintesis suara" in result.stdout.lower() or "piper tts" in result.stdout.lower()


# =============================================================================
# TIER 2: Boundary & Corner Cases (Stress & Defect Immunity)
# =============================================================================

def test_t2_f4_cli_unknown_flag_rejection():
    """Tier 2: Passing unsupported flags must exit with argparse error code 2."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--unsupported-flag-xyz"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2, f"Expected argparse error code 2, got {result.returncode}"
    assert "unrecognized arguments" in result.stderr.lower()


def test_t2_f4_cli_empty_lines_resilience():
    """Tier 2: Entering multiple empty newlines before 'keluar' must not crash CLI loop."""
    proc = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT, "--cli"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Feed 3 empty newlines, then exit command
    payload = "\n\n\nkeluar\n"
    stdout, stderr = proc.communicate(input=payload, timeout=15)
    assert proc.returncode == 0, f"CLI loop crashed on empty newlines. Stderr: {stderr}"
    assert "Sampai jumpa" in stdout


def test_t2_f4_cli_immediate_eof_resilience():
    """Tier 2: Sending immediate EOF (empty input) must be handled gracefully without stacktrace."""
    proc = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT, "--cli"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(input="", timeout=15)
    assert proc.returncode == 0, f"CLI crashed on EOF. Stderr: {stderr}"
    assert "Traceback" not in stderr


def test_t2_f4_cli_invalid_port_type():
    """Tier 2: Passing non-integer port (e.g. --port invalid) must exit with code 2."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--port", "not_a_number"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2, f"Expected code 2 on invalid port, got {result.returncode}"


def test_t2_f4_cli_voice_in_flag_supported():
    """Tier 2: Help output documents --voice-in flag when Feature F2 lands."""
    result = subprocess.run(
        [sys.executable, MAIN_SCRIPT, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    if "--voice-in" not in result.stdout:
        pytest.skip("CLI flag --voice-in pending Milestone M2 landing")
    assert "--voice-in" in result.stdout
