# TEST_READY — Automated Opaque-Box E2E Testing Suite for Phase 2

> **Project**: HuoHuo AI Vtuber — Phase 2: Realtime Streaming Voice-to-Voice, Proactive Companion & Production CI/CD  
> **Status**: **READY** (Test Suite Implemented & Verified)  
> **Date**: 2026-10-21  
> **Author**: E2E Test Writer (`teamwork_preview_test_writer`)  
> **Execution Engine**: Playwright with System Microsoft Edge (`channel="msedge"`), Headless  
> **Constraints Adhered**: Zero Chromium downloads, 100% opaque-box requirement-driven testing, 4-tier design methodology, progressive testability.

---

## 1. Quick Start & Test Runner Commands

### Run Full E2E Test Suite
```bash
uv run pytest tests/e2e/ -v
```

### Run by Specific Feature
- **Feature F1 (Voice Streaming & Lip-Sync)**:
  ```bash
  uv run pytest tests/e2e/test_phase2_f1_voice_streaming.py -v
  ```
- **Feature F2 (Voice-to-Voice Microphone Interaction)**:
  ```bash
  uv run pytest tests/e2e/test_phase2_f2_v2v_mic.py -v
  ```
- **Feature F3 (Window Drag Region & Live2D Expressions/Motions)**:
  ```bash
  uv run pytest tests/e2e/test_phase2_f3_companion_polish.py -v
  ```
- **Feature F4 (CLI Execution Compatibility)**:
  ```bash
  uv run pytest tests/e2e/test_phase2_f4_cli_compatibility.py -v
  ```
- **Tiers 3 & 4 (Cross-Feature Combinations & Real-World Sessions)**:
  ```bash
  uv run pytest tests/e2e/test_phase2_cross_feature_e2e.py -v
  ```

### Run Entire Repository Test Suite (Unit + E2E)
```bash
uv run pytest
```

---

## 2. 4-Tier Test Suite Architecture

The Phase 2 E2E testing suite is structured around a 4-Tier Opaque-Box Methodology:

```
+-------------------------------------------------------------------------+
| Tier 4: Real-World Application Scenarios (Comprehensive End-to-End)     |
|   - Full conversation session (chat -> streaming bubble -> lip-sync)    |
|   - Complete voice-to-voice interaction session                         |
|   - Companion idle state with user interruption                         |
|   - Full CLI conversation subprocess session                            |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
| Tier 3: Cross-Feature Combinations (Pairwise Feature Interactions)      |
|   - Mic toggle during chat typing                                       |
|   - Streaming bubble with concurrent continuous mouth RMS sync          |
|   - Expression and motion triggering during active speech stream        |
|   - Mic listening state coexisting with incoming speech bubble          |
|   - Quick action interruption during streaming response                 |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
| Tier 2: Boundary & Corner Cases (Stress & Defect Immunity)              |
|   - Mouth open clamping: negative values (-99.0) and excessive (>1.0)   |
|   - NaN/null/non-numeric argument safety in JS APIs                     |
|   - Empty, whitespace, and extreme monologue length (>500 chars)        |
|   - Rapid mic toggling and pywebview bridge fallback                    |
|   - Unknown Live2D expression names & invalid motion group protection   |
|   - HTML/XSS sanitization in status badge                               |
|   - CLI invalid arguments, empty stdin lines, and immediate EOF         |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
| Tier 1: Feature Coverage (Happy-Path Tests in Isolation)                |
|   - F1: Streaming bubble single/multi-clause & continuous lip-sync      |
|   - F2: Microphone toggle button (#mic-btn), active/inactive styling    |
|   - F3: Window drag region (.header-bar), all 9 expressions & motions   |
|   - F4: CLI flags (--help, --cli, --test-voice, --voice-in)             |
+-------------------------------------------------------------------------+
```

---

## 3. Test Inventory & Requirement Traceability Matrix

| Feature | Tier | Test Function | Description | Spec Source |
|---|---|---|---|---|
| **F1** | Tier 1 | `test_t1_f1_streaming_bubble_single_clause` | Single clause streaming display & emotion tag | F1.1, F1.3 |
| **F1** | Tier 1 | `test_t1_f1_streaming_bubble_sequential_clauses` | Multi-sentence sequential streaming without tearing | F1.1, F1.3 |
| **F1** | Tier 1 | `test_t1_f1_lipsync_standard_mouth_values` | Mouth open values at 0.0, 0.5, 1.0 boundaries | F1.4 |
| **F1** | Tier 1 | `test_t1_f1_lipsync_continuous_rms_stream` | Continuous RMS streaming frames without jitter | F1.4 |
| **F1** | Tier 1 | `test_t1_f1_bubble_visibility_toggle` | Speech bubble visibility toggle on message | F1.3 |
| **F1** | Tier 2 | `test_t2_f1_mouth_open_clamping_negative` | Negative numbers clamped to 0.0 | F1.4 |
| **F1** | Tier 2 | `test_t2_f1_mouth_open_clamping_excessive` | Values > 1.0 clamped to 1.0 | F1.4 |
| **F1** | Tier 2 | `test_t2_f1_mouth_open_nan_and_invalid_types` | NaN/null/string non-numeric safety | F1.4 |
| **F1** | Tier 2 | `test_t2_f1_streaming_bubble_empty_text` | Empty and whitespace text handling | F1.1 |
| **F1** | Tier 2 | `test_t2_f1_streaming_bubble_long_monologue` | Long text containment without viewport break | F1.3 |
| **F2** | Tier 1 | `test_t1_f2_mic_button_dom_presence` | `#mic-btn` DOM presence and visibility | F2.5 |
| **F2** | Tier 1 | `test_t1_f2_mic_button_click_bridge_emission` | Clicking `#mic-btn` emits `toggle_voice_input` | F2.5 |
| **F2** | Tier 1 | `test_t1_f2_mic_active_styling_state` | `setVoiceListening(true)` activates glowing styles | F2.5 |
| **F2** | Tier 1 | `test_t1_f2_mic_inactive_styling_state` | `setVoiceListening(false)` clears glowing styles | F2.5 |
| **F2** | Tier 1 | `test_t1_f2_mic_status_badge_update` | `setVoiceStatus` updates badge text | F2.5 |
| **F2** | Tier 2 | `test_t2_f2_mic_rapid_toggle_clicks` | Rapid clicks do not desynchronize state | F2.5 |
| **F2** | Tier 2 | `test_t2_f2_mic_bridge_missing_fallback` | Safe fallback when pywebview bridge is absent | F2.5 |
| **F2** | Tier 2 | `test_t2_f2_mic_speech_recognized_callback` | `window.onSpeechRecognized` integration | F2.5 |
| **F2** | Tier 2 | `test_t2_f2_mic_error_status_display` | Displaying audio error strings in status badge | F2.5 |
| **F2** | Tier 2 | `test_t2_f2_mic_status_xss_sanitization` | Script tags in status badge escape safely | F2.5 |
| **F3** | Tier 1 | `test_t1_f3_header_drag_region` | `.header-bar` has `pywebview-drag-region` | F3.2 |
| **F3** | Tier 1 | `test_t1_f3_header_controls_clickable` | Window close `.btn-ctrl-close` emits `close_window` | F3.2 |
| **F3** | Tier 1 | `test_t1_f3_minimize_control_clickable` | Window minimize `.btn-ctrl-minimize` emits `minimize_window` | F3.2 |
| **F3** | Tier 1 | `test_t1_f3_window_controls_outside_drag_region` | `.window-controls` sits outside `.pywebview-drag-region` so clicks do not drag | F3.2 |
| **F3** | Tier 1 | `test_t1_f3_live2d_all_nine_expressions` | All 9 Live2D expressions activate cleanly | F3.3 |
| **F3** | Tier 1 | `test_t1_f3_live2d_motion_api` | `window.setMotion` plays `isyarat:0` to `isyarat:3` | F3.3 |
| **F3** | Tier 1 | `test_t1_f3_kizuna_status_badge_multistage` | Multi-stage Kizuna milestone badges | F3.3 |
| **F3** | Tier 2 | `test_t2_f3_set_expression_unknown_safeguard` | Unregistered expression does not crash PIXI | F3.3 |
| **F3** | Tier 2 | `test_t2_f3_set_motion_invalid_group_safeguard` | Invalid group or index handled gracefully | F3.3 |
| **F3** | Tier 2 | `test_t2_f3_drag_region_does_not_block_mouse_tracking` | Focus tracking works across window regions | F3.2 |
| **F3** | Tier 2 | `test_t2_f3_status_badge_extreme_content` | Unicode & emoji status badge containment | F3.3 |
| **F3** | Tier 2 | `test_t2_f3_quick_action_buttons_no_drag_property` | Quick action buttons clickable and responsive | F3.2 |
| **F4** | Tier 1 | `test_t1_f4_cli_help_flag_zero_exit` | `python main.py --help` returns code 0 | F4.1, R3 |
| **F4** | Tier 1 | `test_t1_f4_cli_help_describes_core_options` | Help message lists `--cli`, `--test-voice`, `--port` | F4.1, R3 |
| **F4** | Tier 1 | `test_t1_f4_cli_interactive_clean_exit` | `--cli` terminates on `'keluar\n'` with code 0 | F4.1, R3 |
| **F4** | Tier 1 | `test_t1_f4_cli_interactive_exit_synonyms` | `--cli` terminates on `'exit\n'` and `'quit\n'` | F4.1, R3 |
| **F4** | Tier 1 | `test_t1_f4_cli_test_voice_execution` | `--test-voice` runs synthesis without error | F4.1, R3 |
| **F4** | Tier 2 | `test_t2_f4_cli_unknown_flag_rejection` | Unsupported flag returns argparse code 2 | F4.1, R3 |
| **F4** | Tier 2 | `test_t2_f4_cli_empty_lines_resilience` | Empty stdin lines do not crash CLI loop | F4.1, R3 |
| **F4** | Tier 2 | `test_t2_f4_cli_immediate_eof_resilience` | Immediate EOF exits without stacktrace | F4.1, R3 |
| **F4** | Tier 2 | `test_t2_f4_cli_invalid_port_type` | Non-integer port returns code 2 | F4.1, R3 |
| **F4** | Tier 2 | `test_t2_f4_cli_voice_in_flag_supported` | `--voice-in` flag listed in `--help` | F2.6 |
| **Cross** | Tier 3 | `test_t3_mic_toggle_during_chat_typing` | Mic toggle + chat input submission | F2 + F1 |
| **Cross** | Tier 3 | `test_t3_streaming_bubble_with_continuous_mouth_sync` | Streaming speech + continuous lip sync | F1.3 + F1.4 |
| **Cross** | Tier 3 | `test_t3_expression_and_motion_during_speech_stream` | Expression/motion changes + speech stream | F3.3 + F1.3 |
| **Cross** | Tier 3 | `test_t3_mic_listening_state_with_incoming_bubble` | Mic active + incoming speech bubble | F2.5 + F1.3 |
| **Cross** | Tier 3 | `test_t3_quick_action_interruption_during_streaming` | Quick action interruption during speech | F3.1 + F1.3 |
| **Session** | Tier 4 | `test_t4_full_conversation_session` | End-to-end multi-turn conversation flow | Full E2E |
| **Session** | Tier 4 | `test_t4_voice_interaction_session` | End-to-end Voice-to-Voice session | Full E2E |
| **Session** | Tier 4 | `test_t4_proactive_idle_and_interruption_session` | Proactive idle companion & interruption | Full E2E |
| **Session** | Tier 4 | `test_t4_full_cli_conversation_session` | Full interactive terminal companion session | Full E2E |

---

## 4. Progressive Testability & Milestone Transition

All tests are equipped with progressive testability guards:
- During milestone development (M1, M2, M3, M4), tests requiring features not yet merged will cleanly report `SKIPPED` rather than failing or timing out.
- As each milestone lands (`worker_m1`, `worker_m2`, `worker_m3`), the corresponding test cases automatically activate and assert the requirements.
- At Milestone M5, 100% of the 53 test cases run to completion.

### Current Test Run Baseline (26 Okt 2026)
```
tests/e2e/test_companion_e2e.py ......................  5 lulus
tests/e2e/test_phase2_f1_voice_streaming.py .......... 10 lulus
tests/e2e/test_phase2_f2_v2v_mic.py .................. 10 lulus
tests/e2e/test_phase2_f3_companion_polish.py ......... 11 lulus
tests/e2e/test_phase2_f4_cli_compatibility.py ........ 10 lulus
tests/e2e/test_phase2_cross_feature_e2e.py ..........  9 lulus
================================================> 55 lulus dalam 55.35 dtk
tests/unit/ .......................................... 75 lulus
================================================> TOTAL 130 lulus, 0 skip
```
- **Nol kegagalan, nol skip.** Baseline lama (21 Okt) masih mencentang 15 skip
  "pending M2/M3" untuk F2 dan F3 — keduanya sudah rilis, jadi tidak ada lagi
  yang menunggu milestone.
- **Nol unduhan Playwright Chromium**
- **100% jalan di Microsoft Edge bawaan sistem (`channel="msedge"`)**
