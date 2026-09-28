"""Provider diagnostics must be brief and redact the configured key."""

import importlib.util
from pathlib import Path
import unittest


PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/universal_llm_assist/errors.py"
)
SPEC = importlib.util.spec_from_file_location("universal_llm_errors", PATH)
errors = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(errors)


class ProviderErrorTests(unittest.TestCase):
    def test_extracts_and_redacts_message(self):
        detail = errors.provider_error_detail(
            '{"error":{"message":"invalid model and key secret-123"}}',
            "secret-123",
        )
        self.assertEqual(detail, "invalid model and key [redacted]")

    def test_ignores_unknown_response_shapes(self):
        self.assertEqual(errors.provider_error_detail("<html>bad request</html>", "x"), "")
