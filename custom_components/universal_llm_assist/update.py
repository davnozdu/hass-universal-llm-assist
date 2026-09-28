"""Install verified GitHub releases from Home Assistant's Updates panel."""

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
import re
from typing import Any

import aiohttp

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_AUTO_UPDATE, DOMAIN, VERSION
from .release_installer import InstallError, install_archive

LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)
RELEASE_API = "https://api.github.com/repos/davnozdu/hass-universal-llm-assist/releases/latest"
DOWNLOAD_PREFIX = "https://github.com/davnozdu/hass-universal-llm-assist/releases/download/"
ASSET_NAME = "universal_llm_assist.zip"
MAX_ZIP_SIZE = 5 * 1024 * 1024
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _version_tuple(version: str) -> tuple[int, int, int]:
    match = TAG_RE.fullmatch("v" + version.lstrip("v"))
    if match is None:
        raise HomeAssistantError("Invalid release version")
    return tuple(map(int, match.groups()))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose one update entity for each configured integration entry."""
    async_add_entities([UniversalLLMAssistUpdate(entry)])


class UniversalLLMAssistUpdate(UpdateEntity):
    """Track and install integration releases."""

    _attr_name = "Universal LLM Assist"
    _attr_title = "Universal LLM Assist"
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_installed_version = VERSION

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_update"
        self._attr_latest_version = VERSION
        self._attr_auto_update = entry.options.get(
            CONF_AUTO_UPDATE, entry.data.get(CONF_AUTO_UPDATE, False)
        )
        self._download_url: str | None = None

    async def async_update(self) -> None:
        """Check the latest GitHub release on a six-hour interval."""
        try:
            release = await self._fetch_release()
        except (HomeAssistantError, aiohttp.ClientError, TimeoutError) as err:
            LOGGER.warning("Unable to check Universal LLM Assist release: %s", err)
            return
        self._attr_latest_version = release["version"]
        self._attr_release_url = release["html_url"]
        self._download_url = release["download_url"]
        if self._attr_auto_update and _version_tuple(release["version"]) > _version_tuple(VERSION):
            try:
                await self.async_install(None, False)
            except HomeAssistantError as err:
                LOGGER.error("Automatic Universal LLM Assist update failed: %s", err)

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install only the newest verified release, then restart Home Assistant."""
        if version is not None and version != self._attr_latest_version:
            raise HomeAssistantError("Only the latest release can be installed")

        state = self.hass.data.setdefault(DOMAIN, {})
        lock = state.setdefault("update_lock", asyncio.Lock())
        async with lock:
            if state.get("update_started"):
                return
            release = await self._fetch_release()
            if _version_tuple(release["version"]) <= _version_tuple(VERSION):
                return
            archive = await self._download_release(release["download_url"])
            try:
                await self.hass.async_add_executor_job(
                    install_archive,
                    archive,
                    release["version"],
                    Path(__file__).resolve().parent,
                )
            except InstallError as err:
                raise HomeAssistantError(str(err)) from err
            state["update_started"] = True
            LOGGER.info("Installed Universal LLM Assist %s; restarting", release["version"])
            await self.hass.services.async_call("homeassistant", "restart", blocking=False)

    async def _fetch_release(self) -> dict[str, str]:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(30):
                async with session.get(
                    RELEASE_API,
                    headers={"Accept": "application/vnd.github+json"},
                ) as response:
                    if response.status != 200:
                        raise HomeAssistantError(
                            f"GitHub release check returned HTTP {response.status}"
                        )
                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise HomeAssistantError("Could not check GitHub releases") from err
        if not isinstance(data, dict):
            raise HomeAssistantError("Invalid GitHub release response")
        tag = data.get("tag_name", "")
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
            raise HomeAssistantError("Invalid GitHub release tag")
        asset = next(
            (
                item
                for item in data.get("assets", [])
                if isinstance(item, dict) and item.get("name") == ASSET_NAME
            ),
            None,
        )
        if asset is None:
            raise HomeAssistantError("Release has no installation ZIP")
        expected = f"{DOWNLOAD_PREFIX}{tag}/{ASSET_NAME}"
        if asset.get("browser_download_url") != expected:
            raise HomeAssistantError("Unexpected release download URL")
        return {
            "version": tag[1:],
            "html_url": f"https://github.com/davnozdu/hass-universal-llm-assist/releases/tag/{tag}",
            "download_url": expected,
        }

    async def _download_release(self, url: str) -> bytes:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(60):
                async with session.get(url) as response:
                    if response.status != 200:
                        raise HomeAssistantError(
                            f"Release download returned HTTP {response.status}"
                        )
                    chunks = []
                    size = 0
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > MAX_ZIP_SIZE:
                            raise HomeAssistantError("Release ZIP is too large")
                        chunks.append(chunk)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError("Could not download the release") from err
        return b"".join(chunks)
