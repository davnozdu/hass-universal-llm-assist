"""Fish Audio numeric input accepts both common decimal separators."""

import importlib.util
from pathlib import Path
import unittest


PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/universal_llm_assist/numbers.py"
)
SPEC = importlib.util.spec_from_file_location("universal_llm_numbers", PATH)
numbers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(numbers)


class FishSpeedTests(unittest.TestCase):
    def test_decimal_comma_and_point_are_equivalent(self):
        self.assertEqual(numbers.parse_fish_speed("1,2"), 1.2)
        self.assertEqual(numbers.parse_fish_speed("1.2"), 1.2)
        self.assertEqual(numbers.parse_fish_speed(" 0,5 "), 0.5)

    def test_invalid_and_out_of_range_values(self):
        for value in ("", "fast", "1,2,3", "0,4", "2.1", "nan", "inf"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                numbers.parse_fish_speed(value)
