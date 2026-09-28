"""Read config entry values while retaining previously saved API keys."""

from typing import Any, Mapping


SECRET_FIELDS = ("api_key", "fish_api_key")


def merged_settings(
    data: Mapping[str, Any], options: Mapping[str, Any]
) -> dict[str, Any]:
    """An empty optional password field must not erase a saved key."""
    result = {**data, **options}
    for field in SECRET_FIELDS:
        if not options.get(field) and data.get(field):
            result[field] = data[field]
    return result
