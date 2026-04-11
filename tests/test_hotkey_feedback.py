from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from codex_dictation_app_runtime import describe_hotkey_update, hotkey_display_text, summarize_hotkey_group  # noqa: E402
from codex_dictation_settings import Settings, app_hotkey_items, launcher_hotkey_items  # noqa: E402


class HotkeyFeedbackTests(unittest.TestCase):
    def test_hotkey_display_text_formats_common_tokens(self):
        self.assertEqual(hotkey_display_text("ctrl+alt+space"), "Ctrl+Alt+Space")
        self.assertEqual(hotkey_display_text("f10"), "F10")
        self.assertEqual(hotkey_display_text("win+h"), "Win+H")

    def test_summarize_hotkey_group_joins_labels_and_values(self):
        summary = summarize_hotkey_group(
            "현재 앱 단축키",
            app_hotkey_items(Settings(always_listen_hotkey="ctrl+shift+a", record_hotkey="f8")),
        )
        self.assertIn("현재 앱 단축키", summary)
        self.assertIn("항상 듣기 Ctrl+Shift+A", summary)

    def test_describe_hotkey_update_mentions_launcher_reload_and_conflicts(self):
        settings = Settings(
            launcher_show_hotkey="ctrl+alt+space",
            launcher_hide_hotkey="ctrl+alt+space",
        )
        previous = {item["field"]: item["value"] for item in launcher_hotkey_items(Settings())}

        feedback = describe_hotkey_update(previous, settings)

        self.assertIn("런처가 실행 중이면 잠시 뒤 새 설정을 다시 읽습니다.", feedback)
        self.assertIn("충돌 주의:", feedback)
        self.assertIn("Ctrl+Alt+Space", feedback)


if __name__ == "__main__":
    unittest.main()
