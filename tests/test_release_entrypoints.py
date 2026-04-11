import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseEntrypointTests(unittest.TestCase):
    def test_integrated_launcher_starts_hotkeys_before_app(self):
        content = (REPO_ROOT / "run_voicepad.bat").read_text(encoding="utf-8")
        hotkey_idx = content.index("run_codex_hotkeys.bat")
        app_idx = content.index("run_codex_dictation.bat")
        self.assertLess(hotkey_idx, app_idx)

    def test_release_package_includes_integrated_launcher(self):
        content = (REPO_ROOT / "package_codex_dictation_release.ps1").read_text(encoding="utf-8")
        self.assertIn('"run_voicepad.bat"', content)


if __name__ == "__main__":
    unittest.main()
