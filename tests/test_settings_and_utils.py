from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import codex_dictation_settings as settings_module  # noqa: E402
from codex_dictation_settings import (  # noqa: E402
    DEFAULT_AUDIO_PRESET,
    DEFAULT_LAUNCHER_HOTKEYS,
    DEFAULT_LLM_MODEL,
    ROOT,
    Settings,
    apply_audio_profile,
    audio_preset_label,
    display_path,
    hotkey_conflicts,
    language_label,
    language_model_arg,
    launcher_hotkey_items,
    normalize_audio_profile_name,
    normalize_audio_profiles,
    normalize_hotkey_value,
    llm_profile_label,
    normalize_audio_preset_value,
    normalize_language_value,
    normalize_llm_profile_value,
    normalize_output_mode_value,
    resolve_llm_model,
    snapshot_audio_profile,
)
from codex_dictation_diagnostics import first_run_guidance  # noqa: E402
from codex_dictation_utils import (  # noqa: E402
    filter_history_entries,
    format_history_entry,
    normalize_text,
    read_history_entries,
    short_log_text,
)


class SettingsNormalizationTests(unittest.TestCase):
    def test_display_path_prefers_relative_path_when_under_base(self):
        nested = ROOT / "logs" / "session.log"
        self.assertEqual(display_path(nested, base=ROOT), "logs/session.log")

    def test_display_path_falls_back_to_name_outside_base(self):
        outside = Path.cwd().resolve().parent / "outside.txt"
        self.assertEqual(display_path(outside, base=ROOT), "outside.txt")

    def test_language_normalization_and_labels(self):
        self.assertEqual(normalize_language_value("한국어로"), "ko")
        self.assertEqual(normalize_language_value("english"), "en")
        self.assertEqual(normalize_language_value("???"), "auto")
        self.assertEqual(language_label("en"), "영어")
        self.assertEqual(language_model_arg("자동"), None)
        self.assertEqual(language_model_arg("한국어"), "ko")

    def test_llm_profile_normalization_and_resolution(self):
        self.assertEqual(normalize_llm_profile_value("정확도"), "accurate")
        self.assertEqual(llm_profile_label("custom"), "직접지정")
        balanced = Settings(llm_profile="balanced", llm_model="custom:1")
        custom = Settings(llm_profile="custom", llm_model="custom:1")
        empty_custom = Settings(llm_profile="custom", llm_model="  ")
        self.assertEqual(resolve_llm_model(balanced), "gemma3:4b")
        self.assertEqual(resolve_llm_model(custom), "custom:1")
        self.assertEqual(resolve_llm_model(empty_custom), DEFAULT_LLM_MODEL)

    def test_audio_preset_normalization_and_label(self):
        self.assertEqual(normalize_audio_preset_value("조용한 방"), "quiet")
        self.assertEqual(normalize_audio_preset_value("unknown"), DEFAULT_AUDIO_PRESET)
        self.assertEqual(audio_preset_label("noisy"), "시끄러운 방")

    def test_output_mode_normalization(self):
        self.assertEqual(normalize_output_mode_value("자동"), "auto")
        self.assertEqual(normalize_output_mode_value("clipboard"), "clipboard")
        self.assertEqual(normalize_output_mode_value("직접 입력"), "type")
        self.assertEqual(normalize_output_mode_value("???"), "auto")

    def test_launcher_hotkeys_normalize_aliases_and_fallbacks(self):
        self.assertEqual(normalize_hotkey_value(" Ctrl + Alt + Space "), "ctrl+alt+space")
        self.assertEqual(normalize_hotkey_value("^!Space"), "ctrl+alt+space")
        self.assertEqual(normalize_hotkey_value("  ", fallback="F2"), "f2")

    def test_launcher_hotkey_items_and_conflicts(self):
        settings = Settings(
            launcher_toggle_hotkey="f2",
            launcher_show_hotkey=" F2 ",
            launcher_hide_hotkey="",
            launcher_exit_hotkey="Win + Z",
        )
        items = launcher_hotkey_items(settings)
        self.assertEqual(items[0]["value"], "f2")
        self.assertEqual(items[2]["value"], DEFAULT_LAUNCHER_HOTKEYS["launcher_hide_hotkey"])
        self.assertEqual(items[3]["value"], "win+z")
        self.assertEqual(
            hotkey_conflicts(settings),
            {"f2": ("launcher_toggle_hotkey", "launcher_show_hotkey")},
        )

    def test_audio_profile_name_and_profile_normalization(self):
        self.assertEqual(normalize_audio_profile_name("  회의 용  "), "회의 용")
        normalized = normalize_audio_profiles(
            {
                "  회의 용  ": {
                    "input_gain": 1.4,
                    "always_listen_enabled": True,
                    "unknown": "ignored",
                }
            }
        )
        self.assertEqual(sorted(normalized.keys()), ["회의 용"])
        self.assertEqual(normalized["회의 용"]["input_gain"], 1.4)
        self.assertNotIn("unknown", normalized["회의 용"])

    def test_snapshot_and_apply_audio_profile(self):
        settings = Settings(
            input_device="USB Mic",
            input_gain=1.7,
            noise_gate_threshold=0.01,
            auto_stop_silence_seconds=0.8,
            always_listen_preroll_seconds=0.35,
            voice_trigger_min_rms=0.02,
            voice_trigger_ratio=2.8,
            voice_trigger_consecutive_blocks=3,
            always_listen_enabled=False,
            audio_preset="quiet",
        )
        profile = snapshot_audio_profile(settings)
        reapplied = Settings(audio_preset="noisy")
        apply_audio_profile(reapplied, profile)
        self.assertEqual(reapplied.input_device, "USB Mic")
        self.assertAlmostEqual(reapplied.input_gain, 1.7)
        self.assertFalse(reapplied.always_listen_enabled)
        self.assertEqual(reapplied.audio_preset, DEFAULT_AUDIO_PRESET)

    def test_first_run_guidance_reports_ready_state(self):
        settings = Settings(input_device="USB Mic", whisper_model="large-v3-turbo")
        summary, checklist, paths, trouble = first_run_guidance(
            settings,
            input_device_count=2,
            model_status="모델 준비됨 (large-v3-turbo)",
            hotkey_status="단축키 등록됨",
        )
        self.assertIn("마이크 2개 감지", summary)
        self.assertIn("모델 준비됨", summary)
        self.assertIn("Input Device 확인", checklist)
        self.assertIn("settings.json", paths)
        self.assertIn("Doctor -> 로그 -> 설정", trouble)

    def test_first_run_guidance_surfaces_common_failures(self):
        settings = Settings(input_device="", whisper_model="small")
        summary, _checklist, _paths, trouble = first_run_guidance(
            settings,
            input_device_count=0,
            model_status="모델 준비 건너뜀 (download pending)",
            hotkey_status="단축키 사용 불가 (keyboard missing)",
        )
        self.assertIn("마이크 확인 필요", summary)
        self.assertIn("마이크가 안 보이면", trouble)
        self.assertIn("모델 준비가 느리면", trouble)
        self.assertIn("단축키가 안 먹으면", trouble)

    def test_save_settings_normalizes_launcher_hotkeys_before_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "codex_dictation.settings.json"
            settings = Settings(
                launcher_toggle_hotkey=" ",
                launcher_show_hotkey="Control + Alt + Space",
                launcher_hide_hotkey="Meta + H",
                launcher_exit_hotkey="return",
            )
            with patch.object(settings_module, "ensure_runtime_paths", lambda: None):
                with patch.object(settings_module, "SETTINGS_PATH", settings_path):
                    settings_module.save_settings(settings)

            stored = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["launcher_toggle_hotkey"], "f1")
        self.assertEqual(stored["launcher_show_hotkey"], "ctrl+alt+space")
        self.assertEqual(stored["launcher_hide_hotkey"], "win+h")
        self.assertEqual(stored["launcher_exit_hotkey"], "enter")


class UtilsTests(unittest.TestCase):
    def test_normalize_text_compacts_whitespace(self):
        self.assertEqual(normalize_text("  첫째 줄\r\n둘째   줄  "), "첫째 줄 둘째 줄")

    def test_short_log_text_truncates_with_ellipsis(self):
        truncated = short_log_text("하나 둘 셋 넷 다섯 여섯", limit=9)
        self.assertEqual(truncated, "하나 둘 셋...")
        self.assertEqual(short_log_text("짧은 문장", limit=20), "짧은 문장")

    def test_read_history_entries_returns_latest_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.jsonl"
            history_path.write_text(
                '\n'.join(
                    [
                        '{"timestamp":"2026-04-09T10:00:00","text":"첫 문장"}',
                        '{"timestamp":"2026-04-09T10:01:00","text":"둘째 문장"}',
                    ]
                ),
                encoding="utf-8",
            )
            entries = read_history_entries(history_path)
        self.assertEqual([entry["text"] for entry in entries], ["둘째 문장", "첫 문장"])

    def test_filter_history_entries_matches_normalized_query(self):
        entries = [
            {"timestamp": "2026-04-09T10:00:00", "text": "회의 메모 정리"},
            {"timestamp": "2026-04-09T10:01:00", "text": "장보기 목록"},
        ]
        filtered = filter_history_entries(entries, "회의   메모")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["text"], "회의 메모 정리")

    def test_format_history_entry_includes_timestamp_and_text(self):
        formatted = format_history_entry({"timestamp": "2026-04-09T10:01:02", "text": "최근 기록 테스트"})
        self.assertEqual(formatted, "2026-04-09 10:01:02 | 최근 기록 테스트")


if __name__ == "__main__":
    unittest.main()
