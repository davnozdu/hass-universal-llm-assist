"""Set up Universal LLM Assist."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .preview import FishPreviewView


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the conversation agent."""
    state = hass.data.setdefault(DOMAIN, {})
    if not state.get("preview_view_registered"):
        hass.http.register_view(FishPreviewView(hass))
        state["preview_view_registered"] = True
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.CONVERSATION, Platform.TTS, Platform.UPDATE]
    )
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the conversation agent."""
    return await hass.config_entries.async_unload_platforms(
        entry, [Platform.CONVERSATION, Platform.TTS, Platform.UPDATE]
    )


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply updated provider settings."""
    await hass.config_entries.async_reload(entry.entry_id)
