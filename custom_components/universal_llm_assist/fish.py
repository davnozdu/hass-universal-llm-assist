"""Fish Audio voice catalog helpers."""

import asyncio
from typing import Any

import aiohttp

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def fetch_voices(
    hass, api_key: str, language: str, title: str, page: int
) -> list[dict[str, str]]:
    """Find public Fish Audio voices by language code and optional title."""
    params: dict[str, Any] = {
        "language": language.lower().split("-")[0],
        "page_size": 100,
        "page_number": page,
        "sort_by": "score",
    }
    if title:
        params["title"] = title
    try:
        async with asyncio.timeout(30):
            async with async_get_clientsession(hass).get(
                "https://api.fish.audio/model",
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
            ) as response:
                if response.status != 200:
                    raise HomeAssistantError(
                        f"Fish Audio voice list returned HTTP {response.status}"
                    )
                payload = await response.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise HomeAssistantError("Could not load Fish Audio voices") from err
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise HomeAssistantError("Invalid Fish Audio voice list")
    voices = []
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        voice_id, name = item.get("_id"), item.get("title")
        if isinstance(voice_id, str) and voice_id and isinstance(name, str) and name:
            voices.append({"id": voice_id, "name": name})
    return voices
