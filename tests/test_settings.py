"""Saved credentials survive optional blank password fields."""

import importlib.util
from pathlib import Path
import unittest


PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/universal_llm_assist/settings.py"
)
SPEC = importlib.util.spec_from_file_location("universal_llm_settings", PATH)
settings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def test_blank_option_does_not_hide_saved_keys(self):
        merged = settings.merged_settings(
            {"api_key": "original", "fish_api_key": "fish-original"},
            {"api_key": "", "fish_api_key": None, "model": "new"},
        )
        self.assertEqual(merged["api_key"], "original")
        self.assertEqual(merged["fish_api_key"], "fish-original")
        self.assertEqual(merged["model"], "new")

    def test_explicit_replacement_is_used(self):
        self.assertEqual(
            settings.merged_settings({"api_key": "old"}, {"api_key": "new"})[
                "api_key"
            ],
            "new",
        )
