from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from codex_dictation_app_runtime import describe_model_prepare_state  # noqa: E402
from codex_dictation_diagnostics import first_run_guidance  # noqa: E402
from codex_dictation_settings import Settings  # noqa: E402


class ModelWarmupStatusTests(unittest.TestCase):
    def test_loading_state_mentions_first_download_risk(self):
        brief, log_message = describe_model_prepare_state(
            "large-v3-turbo",
            "loading",
            first_attempt=True,
        )

        self.assertEqual(brief, "모델 다운로드/로드 중 (large-v3-turbo)")
        self.assertIn("다운로드", log_message)

    def test_warmup_and_failure_states_are_distinct(self):
        warmup_brief, _ = describe_model_prepare_state("small", "warming")
        failed_brief, failed_log = describe_model_prepare_state(
            "small",
            "warmup_failed",
            error="cuda unavailable",
        )

        self.assertEqual(warmup_brief, "모델 워밍업 중 (small)")
        self.assertIn("모델 워밍업 실패", failed_brief)
        self.assertIn("cuda unavailable", failed_log)

    def test_first_run_guidance_surfaces_in_progress_model_hints(self):
        settings = Settings(input_device="USB Mic", whisper_model="large-v3-turbo")

        loading_summary, _checklist, _paths, loading_trouble = first_run_guidance(
            settings,
            input_device_count=1,
            model_status="모델 다운로드/로드 중 (large-v3-turbo)",
            hotkey_status="단축키 등록 대기",
        )
        warmup_summary, _checklist, _paths, warmup_trouble = first_run_guidance(
            settings,
            input_device_count=1,
            model_status="모델 워밍업 중 (large-v3-turbo)",
            hotkey_status="단축키 등록됨",
        )

        self.assertIn("모델 다운로드/로드 중", loading_summary)
        self.assertIn("첫 실행이면 모델 다운로드가 길 수 있으니", loading_trouble)
        self.assertIn("모델 워밍업 중", warmup_summary)
        self.assertIn("첫 응답이 잠시 느릴 수 있습니다", warmup_trouble)


if __name__ == "__main__":
    unittest.main()
