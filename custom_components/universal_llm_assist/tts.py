"""Fish Audio text-to-speech for Assist pipelines."""

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.components.tts import TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_FISH_API_KEY,
    CONF_FISH_EMOTION,
    CONF_FISH_LATENCY,
    CONF_FISH_LANGUAGE,
    CONF_FISH_MODEL,
    CONF_FISH_SPEED,
    CONF_FISH_TEMPERATURE,
    CONF_FISH_TOP_P,
    CONF_FISH_VOICE,
)

LOGGER = logging.getLogger(__name__)
FISH_TTS_URL = "https://api.fish.audio/v1/tts"
MAX_AUDIO_BYTES = 10 * 1024 * 1024


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add Fish Audio only after its key has been configured."""
    settings = {**entry.data, **entry.options}
    if settings.get(CONF_FISH_API_KEY):
        async_add_entities([FishAudioTTS(entry, settings)])


class FishAudioTTS(TextToSpeechEntity):
    """Generate spoken answers through Fish Audio."""

    _attr_name = "Fish Audio"
    _attr_default_language = "ru"
    _attr_supported_languages = [
        "ru", "en", "de", "fr", "es", "it", "pt", "pl", "ja", "ko", "zh", "ar", "nl"
    ]

    def __init__(self, entry: ConfigEntry, settings: dict[str, Any]) -> None:
        self._attr_unique_id = f"{entry.entry_id}_fish_audio"
        self._attr_default_language = settings.get(CONF_FISH_LANGUAGE, "ru")
        self._settings = settings

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> tuple[str | None, bytes | None]:
        """Request MP3 audio from the Fish Audio API."""
        audio = await synthesize_fish_audio(self.hass, self._settings, message)
        return "mp3", audio


async def synthesize_fish_audio(
    hass: HomeAssistant,
    settings: dict[str, Any],
    message: str,
    voice_override: str | None = None,
) -> bytes:
    """Generate audio for the TTS entity or a browser preview."""
    model = settings.get(CONF_FISH_MODEL, "s2.1-pro-free")
    emotion = settings.get(CONF_FISH_EMOTION, "none")
    spoken_text = message
    if emotion != "none":
        marker = f"({emotion})" if model == "s1" else f"[{emotion}]"
        spoken_text = f"{marker} {message}"
    body: dict[str, Any] = {
        "text": spoken_text,
        "format": "mp3",
        "latency": settings.get(CONF_FISH_LATENCY, "balanced"),
        "prosody": {"speed": settings.get(CONF_FISH_SPEED, 1.0)},
        "temperature": settings.get(CONF_FISH_TEMPERATURE, 0.7),
        "top_p": settings.get(CONF_FISH_TOP_P, 0.7),
    }
    if voice := (voice_override or settings.get(CONF_FISH_VOICE, "")).strip():
        body["reference_id"] = voice
    headers = {
        "Authorization": f"Bearer {settings[CONF_FISH_API_KEY]}",
        "model": model,
    }
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(90):
            async with session.post(FISH_TTS_URL, json=body, headers=headers) as response:
                if response.status != 200:
                    LOGGER.warning("Fish Audio TTS failed with HTTP %s", response.status)
                    raise HomeAssistantError(
                        f"Fish Audio speech generation failed (HTTP {response.status})"
                    )
                chunks = []
                size = 0
                async for chunk in response.content.iter_chunked(65536):
                    size += len(chunk)
                    if size > MAX_AUDIO_BYTES:
                        raise HomeAssistantError("Fish Audio returned oversized audio")
                    chunks.append(chunk)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise HomeAssistantError("Fish Audio speech generation failed") from err
    if not chunks:
        raise HomeAssistantError("Fish Audio returned empty audio")
    return b"".join(chunks)
