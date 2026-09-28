"""Short-lived browser playback for Fish Audio voice previews."""

import secrets
import time

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PREVIEW_TTL_SECONDS = 300


def store_preview(hass: HomeAssistant, audio: bytes) -> str:
    """Keep a generated preview in memory for five minutes."""
    previews = hass.data.setdefault(DOMAIN, {}).setdefault("previews", {})
    now = time.monotonic()
    for token, (expires, _) in list(previews.items()):
        if expires < now:
            previews.pop(token, None)
    while len(previews) >= 10:
        previews.pop(next(iter(previews)))
    token = secrets.token_urlsafe(24)
    previews[token] = (now + PREVIEW_TTL_SECONDS, audio)
    return f"/api/universal_llm_assist/preview/{token}"


class FishPreviewView(HomeAssistantView):
    """Serve an unguessable, expiring MP3 to the local browser."""

    url = "/api/universal_llm_assist/preview/{token}"
    name = "api:universal_llm_assist:preview"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, token: str) -> web.Response:
        item = self.hass.data.get(DOMAIN, {}).get("previews", {}).get(token)
        if not item or item[0] < time.monotonic():
            raise web.HTTPNotFound
        return web.Response(
            body=item[1],
            content_type="audio/mpeg",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
