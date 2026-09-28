"""Small, redacted provider errors for Home Assistant's UI."""

import json


def provider_error_detail(body: str, api_key: str) -> str:
    """Extract a short API error without exposing a credential or response dump."""
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    message = error.get("message") if isinstance(error, dict) else error
    if not isinstance(message, str):
        return ""
    if api_key:
        message = message.replace(api_key, "[redacted]")
    message = " ".join(message.split())
    return message[:300]
