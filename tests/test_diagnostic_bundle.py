from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from codex_dictation_diagnostics import create_diagnostic_bundle, mask_diagnostic_text  # noqa: E402
from codex_dictation_settings import Settings  # noqa: E402


class DiagnosticBundleTests(unittest.TestCase):
    def test_mask_diagnostic_text_redacts_user_home_and_data_root(self):
        data_root = Path(tempfile.gettempdir()) / "voicepad-diagnostics-mask"
        settings_path = data_root / "codex_dictation.settings.json"
        history_path = data_root / "codex_dictation.history.jsonl"
        log_path = data_root / "codex_dictation.log"
        raw = "\n".join(
            [
                f"home={Path.home().resolve()}",
                f"settings={settings_path}",
                f"log={log_path}",
            ]
        )

        masked = mask_diagnostic_text(
            raw,
            data_root=data_root,
            settings_path=settings_path,
            history_path=history_path,
            log_path=log_path,
        )

        self.assertNotIn(str(Path.home().resolve()), masked)
        self.assertNotIn(str(settings_path), masked)
        self.assertIn("<USER_HOME>", masked)
        self.assertIn("<DATA_ROOT>/codex_dictation.settings.json", masked)

    def test_create_diagnostic_bundle_collects_expected_files_and_masks_prompt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            bundle_root = temp_root / "bundles"
            log_path = temp_root / "codex_dictation.log"
            log_path.write_text(
                f"open {Path.home().resolve()}\\Desktop\\secret.txt\nsecond line",
                encoding="utf-8",
            )
            settings = Settings(initial_prompt="내 이름이 들어간 프롬프트", llm_base_url="http://127.0.0.1:11434")

            bundle_path = create_diagnostic_bundle(
                settings,
                doctor_report=f"Data root: {Path.home().resolve()}\\AppData\\Local\\Voicepad",
                bundle_root=bundle_root,
                log_path=log_path,
                now=datetime(2026, 4, 11, 9, 30, 0),
            )

            self.assertEqual(bundle_path.name, "voicepad-diagnostics-20260411-093000.zip")
            self.assertTrue(bundle_path.exists())

            with zipfile.ZipFile(bundle_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["README.txt", "doctor.txt", "recent-log.txt", "settings.json"],
                )
                doctor_text = archive.read("doctor.txt").decode("utf-8")
                log_text = archive.read("recent-log.txt").decode("utf-8")
                settings_payload = json.loads(archive.read("settings.json").decode("utf-8"))

            self.assertNotIn(str(Path.home().resolve()), doctor_text)
            self.assertNotIn(str(Path.home().resolve()), log_text)
            self.assertEqual(settings_payload["settings"]["initial_prompt"], "<configured>")
            self.assertTrue(settings_payload["masked"])


if __name__ == "__main__":
    unittest.main()
