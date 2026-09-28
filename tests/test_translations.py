"""Guard browser preview copy against unsupported HTML translation tags."""

import json
from pathlib import Path
from string import Formatter
import unittest


ROOT = Path(__file__).resolve().parents[1] / "custom_components/universal_llm_assist"


class PreviewTranslationTests(unittest.TestCase):
    def test_preview_link_uses_markdown_in_all_languages(self):
        for path in (ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))):
            with self.subTest(path=path):
                description = json.loads(path.read_text())["options"]["step"][
                    "fish_browser_ready"
                ]["description"]
                self.assertIn("]({preview_url})", description)
                self.assertNotIn("<a", description)

    def test_key_status_placeholders_match_flow(self):
        expected = {
            "init": {"provider_name", "llm_key_status", "fish_key_status"},
            "connection": {"provider_name", "key_status"},
            "fish_audio": {"key_status"},
        }
        for path in (ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))):
            options = json.loads(path.read_text())["options"]["step"]
            for step, placeholders in expected.items():
                with self.subTest(path=path, step=step):
                    found = {
                        field
                        for _, field, _, _ in Formatter().parse(options[step]["description"])
                        if field
                    }
                    self.assertEqual(found, placeholders)
