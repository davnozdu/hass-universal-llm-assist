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
