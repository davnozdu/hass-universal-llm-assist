"""Locale-friendly numeric input helpers."""

from __future__ import annotations

import math


def parse_fish_speed(value: str | float | int) -> float:
    """Accept a decimal comma or point and enforce Fish Audio's speed range."""
    try:
        speed = float(str(value).strip().replace(",", "."))
    except ValueError as err:
        raise ValueError("Invalid speech speed") from err
    if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
        raise ValueError("Speech speed must be between 0.5 and 2.0")
    return speed


def integer_token_limit(value: str | float | int) -> int:
    """Return a JSON integer even when a UI number selector supplied 1024.0."""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("Invalid output token limit") from err
    if (
        not math.isfinite(numeric)
        or not 64 <= numeric <= 8192
        or not numeric.is_integer()
    ):
        raise ValueError("Output token limit must be an integer from 64 to 8192")
    return int(numeric)
