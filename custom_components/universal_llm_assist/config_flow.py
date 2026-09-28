"""UI setup for Universal LLM Assist."""

from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_PROMPT
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import fetch_models
from .const import (
    CONF_BASE_URL,
    CONF_AUTO_UPDATE,
    CONF_CONTROL,
    CONF_FISH_API_KEY,
    CONF_FISH_EMOTION,
    CONF_FISH_LATENCY,
    CONF_FISH_LANGUAGE,
    CONF_FISH_MODEL,
    CONF_FISH_SPEED,
    CONF_FISH_TEMPERATURE,
    CONF_FISH_TOP_P,
    CONF_FISH_VOICE,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_PROVIDER,
    CONF_TEMPERATURE,
    CONF_THINK,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DOMAIN,
    PROVIDERS,
)
from .fish import fetch_voices
from .preview import store_preview
from .tts import synthesize_fish_audio


def _valid_url(value: str) -> bool:
    """Allow only HTTP(S) endpoints with a hostname and no credentials."""
    parsed = urlsplit(value)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not (
        parsed.username or parsed.password or parsed.query or parsed.fragment
    )


def _settings_schema(model_selector, current: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MODEL, default=current.get(CONF_MODEL, "")): model_selector,
            vol.Required(
                CONF_CONTROL, default=current.get(CONF_CONTROL, True)
            ): BooleanSelector(),
            vol.Required(
                CONF_PROMPT, default=current.get(CONF_PROMPT, DEFAULT_PROMPT)
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_THINK, default=current.get(CONF_THINK, False)
            ): BooleanSelector(),
            vol.Required(
                CONF_TEMPERATURE,
                default=current.get(
                    CONF_TEMPERATURE,
                    1.0 if current.get(CONF_PROVIDER) == "gemini" else 0.7,
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=2, step=0.1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_MAX_TOKENS,
                default=current.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=64, max=8192, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_AUTO_UPDATE, default=current.get(CONF_AUTO_UPDATE, False)
            ): BooleanSelector(),
        }
    )


def _manual_schema(current: dict[str, Any]) -> vol.Schema:
    return _settings_schema(
        TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)), current
    )


def _catalog_schema(models: list[str], current: dict[str, Any]) -> vol.Schema:
    options = [SelectOptionDict(label=model, value=model) for model in models]
    selected = current.get(CONF_MODEL) or models[0]
    if selected and selected not in models:
        options.insert(0, SelectOptionDict(label=f"{selected} (saved)", value=selected))
    return _settings_schema(
        SelectSelector(SelectSelectorConfig(options=options)),
        {**current, CONF_MODEL: selected},
    )


class UniversalLLMAssistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a provider and a model."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}
        self._models: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = user_input[CONF_PROVIDER]
            url = (user_input.get(CONF_BASE_URL) or PROVIDERS[provider][1]).strip()
            if not _valid_url(url):
                errors[CONF_BASE_URL] = "invalid_url"
            elif not user_input[CONF_API_KEY].strip():
                errors[CONF_API_KEY] = "required"
            else:
                self._connection = {
                    CONF_PROVIDER: provider,
                    CONF_NAME: user_input[CONF_NAME].strip(),
                    CONF_BASE_URL: url.rstrip("/"),
                    CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                }
                return await self.async_step_model_menu()
        schema = vol.Schema(
            {
                vol.Required(CONF_PROVIDER, default="ollama_cloud"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(label=details[0], value=provider)
                            for provider, details in PROVIDERS.items()
                        ]
                    )
                ),
                vol.Required(CONF_NAME, default="Universal LLM Assist"): str,
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_BASE_URL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_model_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="model_menu", menu_options=["refresh_models", "manual_model"]
        )

    async def async_step_refresh_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        try:
            self._models = await fetch_models(
                self.hass,
                self._connection[CONF_PROVIDER],
                self._connection[CONF_BASE_URL],
                self._connection[CONF_API_KEY],
            )
            if not self._models:
                raise HomeAssistantError("Empty model list")
        except HomeAssistantError:
            return self.async_show_form(
                step_id="refresh_models",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_load_models"},
            )
        return await self.async_step_models()

    async def async_step_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._finish(user_input)
        default = {
            CONF_MODEL: PROVIDERS[self._connection[CONF_PROVIDER]][2],
            CONF_PROVIDER: self._connection[CONF_PROVIDER],
        }
        return self.async_show_form(
            step_id="models", data_schema=_catalog_schema(self._models, default)
        )

    async def async_step_manual_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_MODEL].strip():
                return self._finish(user_input)
            return self.async_show_form(
                step_id="manual_model",
                data_schema=_manual_schema(user_input),
                errors={CONF_MODEL: "required"},
            )
        default = {
            CONF_MODEL: PROVIDERS[self._connection[CONF_PROVIDER]][2],
            CONF_PROVIDER: self._connection[CONF_PROVIDER],
        }
        return self.async_show_form(
            step_id="manual_model", data_schema=_manual_schema(default)
        )

    def _finish(self, settings: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(
            title=self._connection[CONF_NAME],
            data={**self._connection, **settings},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return UniversalLLMAssistOptionsFlow(config_entry)


class UniversalLLMAssistOptionsFlow(OptionsFlow):
    """Change settings and refresh the model list later."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._models: list[str] = []
        self._voices: list[dict[str, str]] = []
        self._voice_language = "ru"
        self._pending_voice: str | None = None
        self._pending_fish_settings: dict[str, Any] = {}
        self._browser_preview_url: str | None = None

    @property
    def _settings(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self._settings
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "refresh_models", "manual_model", "connection", "fish_audio",
                "fish_voice_search",
                "fish_voice_preview",
                "fish_browser_preview",
            ],
            description_placeholders={
                "provider_name": PROVIDERS.get(
                    current.get(CONF_PROVIDER), ("LLM", "", "")
                )[0],
                "llm_key_status": "✓" if current.get(CONF_API_KEY) else "—",
                "fish_key_status": "✓" if current.get(CONF_FISH_API_KEY) else "—",
            },
        )

    async def async_step_refresh_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self._settings
        try:
            self._models = await fetch_models(
                self.hass,
                current[CONF_PROVIDER],
                current[CONF_BASE_URL],
                current[CONF_API_KEY],
            )
            if not self._models:
                raise HomeAssistantError("Empty model list")
        except HomeAssistantError:
            return self.async_show_form(
                step_id="refresh_models",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_load_models"},
            )
        return await self.async_step_models()

    async def async_step_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._entry.options, **user_input}
            )
        return self.async_show_form(
            step_id="models",
            data_schema=_catalog_schema(self._models, self._settings),
        )

    async def async_step_manual_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_MODEL].strip():
                return self.async_create_entry(
                    title="", data={**self._entry.options, **user_input}
                )
            return self.async_show_form(
                step_id="manual_model",
                data_schema=_manual_schema(user_input),
                errors={CONF_MODEL: "required"},
            )
        return self.async_show_form(
            step_id="manual_model", data_schema=_manual_schema(self._settings)
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_BASE_URL].strip().rstrip("/")
            if not _valid_url(url):
                errors[CONF_BASE_URL] = "invalid_url"
            else:
                changes = {CONF_BASE_URL: url}
                if key := user_input.get(CONF_API_KEY, "").strip():
                    changes[CONF_API_KEY] = key
                return self.async_create_entry(
                    title="", data={**self._entry.options, **changes}
                )
        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_URL, default=self._settings[CONF_BASE_URL]
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    vol.Optional(CONF_API_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "provider_name": PROVIDERS.get(
                    self._settings.get(CONF_PROVIDER), ("LLM", "", "")
                )[0],
                "key_status": "✓" if self._settings.get(CONF_API_KEY) else "—"
            },
        )

    async def async_step_fish_audio(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure optional Fish Audio TTS without displaying a saved key."""
        errors: dict[str, str] = {}
        current = self._settings
        if user_input is not None:
            changes = {
                CONF_FISH_MODEL: user_input[CONF_FISH_MODEL].strip(),
                CONF_FISH_VOICE: user_input.get(CONF_FISH_VOICE, "").strip(),
                CONF_FISH_SPEED: user_input[CONF_FISH_SPEED],
                CONF_FISH_LATENCY: user_input[CONF_FISH_LATENCY],
                CONF_FISH_LANGUAGE: user_input[CONF_FISH_LANGUAGE].strip().lower().split("-")[0],
                CONF_FISH_TEMPERATURE: user_input[CONF_FISH_TEMPERATURE],
                CONF_FISH_TOP_P: user_input[CONF_FISH_TOP_P],
                CONF_FISH_EMOTION: user_input[CONF_FISH_EMOTION],
            }
            if key := user_input.get(CONF_FISH_API_KEY, "").strip():
                changes[CONF_FISH_API_KEY] = key
            if user_input.get("fish_load_voices"):
                lookup = {**current, **changes}
                if not lookup.get(CONF_FISH_API_KEY):
                    errors["base"] = "fish_key_required"
                else:
                    try:
                        self._voices = await fetch_voices(
                            self.hass,
                            lookup[CONF_FISH_API_KEY],
                            changes[CONF_FISH_LANGUAGE],
                            "",
                            1,
                        )
                    except HomeAssistantError:
                        errors["base"] = "cannot_load_voices"
                    else:
                        if not self._voices:
                            errors["base"] = "no_voices"
                        else:
                            self._pending_fish_settings = changes
                            self._voice_language = changes[CONF_FISH_LANGUAGE]
                            return await self.async_step_fish_voice_results()
            else:
                return self.async_create_entry(
                    title="", data={**self._entry.options, **changes}
                )
            current = {**current, **changes}
        return self.async_show_form(
            step_id="fish_audio",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_FISH_API_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Required(
                        CONF_FISH_MODEL,
                        default=current.get(CONF_FISH_MODEL, "s2.1-pro-free"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=name, value=name)
                                for name in (
                                    "s2.1-pro-free",
                                    "s2.1-pro",
                                    "s2-pro",
                                    "s1",
                                )
                            ]
                        )
                    ),
                    vol.Optional(
                        CONF_FISH_VOICE,
                        default=current.get(CONF_FISH_VOICE, ""),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Required(
                        CONF_FISH_LANGUAGE,
                        default=current.get(CONF_FISH_LANGUAGE, "ru"),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Required(
                        "fish_load_voices",
                        default=(user_input or {}).get("fish_load_voices", False),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_FISH_SPEED,
                        default=current.get(CONF_FISH_SPEED, 1.0),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0.5, max=2.0, step=0.1, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_FISH_TEMPERATURE,
                        default=current.get(CONF_FISH_TEMPERATURE, 0.7),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=1, step=0.05, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_FISH_TOP_P,
                        default=current.get(CONF_FISH_TOP_P, 0.7),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=1, step=0.05, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_FISH_EMOTION,
                        default=current.get(CONF_FISH_EMOTION, "none"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=value, value=value)
                                for value in (
                                    "none", "calm", "confident", "happy",
                                    "soft tone", "in a hurry tone",
                                )
                            ]
                        )
                    ),
                    vol.Required(
                        CONF_FISH_LATENCY,
                        default=current.get(CONF_FISH_LATENCY, "balanced"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(label=value, value=value)
                                for value in ("low", "balanced", "normal")
                            ]
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "key_status": "✓" if self._settings.get(CONF_FISH_API_KEY) else "—"
            },
        )

    async def async_step_fish_voice_search(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Search the Fish Audio voice catalog with a language code."""
        current = self._settings
        errors: dict[str, str] = {}
        if user_input is not None:
            key = current.get(CONF_FISH_API_KEY)
            if not key:
                errors["base"] = "fish_key_required"
            else:
                try:
                    self._voices = await fetch_voices(
                        self.hass,
                        key,
                        user_input[CONF_FISH_LANGUAGE].strip(),
                        user_input.get("fish_voice_title", "").strip(),
                        int(user_input["fish_voice_page"]),
                    )
                except HomeAssistantError:
                    errors["base"] = "cannot_load_voices"
                else:
                    if not self._voices:
                        errors["base"] = "no_voices"
                    else:
                        self._voice_language = (
                            user_input[CONF_FISH_LANGUAGE].strip().lower().split("-")[0]
                        )
                        return await self.async_step_fish_voice_results()
        return self.async_show_form(
            step_id="fish_voice_search",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FISH_LANGUAGE,
                        default=(user_input or current).get(CONF_FISH_LANGUAGE, "ru"),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Optional(
                        "fish_voice_title",
                        default=(user_input or {}).get("fish_voice_title", ""),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Required(
                        "fish_voice_page",
                        default=(user_input or {}).get("fish_voice_page", 1),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=100, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_fish_voice_results(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save the selected Fish Audio voice ID."""
        if user_input is not None:
            selected = user_input[CONF_FISH_VOICE]
            if selected not in {voice["id"] for voice in self._voices}:
                return self.async_abort(reason="invalid_voice")
            self._pending_voice = selected
            return await self.async_step_fish_browser_preview()
        return self.async_show_form(
            step_id="fish_voice_results",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FISH_VOICE): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    label=f"{voice['name']} ({voice['id'][:8]})",
                                    value=voice["id"],
                                )
                                for voice in self._voices
                            ]
                        )
                    )
                }
            ),
        )

    async def async_step_fish_browser_preview(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Generate an MP3 for browser playback before saving a voice."""
        errors: dict[str, str] = {}
        if user_input is not None:
            settings = {**self._settings, **self._pending_fish_settings}
            if not settings.get(CONF_FISH_API_KEY):
                errors["base"] = "fish_key_required"
            else:
                try:
                    audio = await synthesize_fish_audio(
                        self.hass,
                        settings,
                        user_input["test_text"],
                        voice_override=self._pending_voice,
                    )
                except HomeAssistantError:
                    errors["base"] = "preview_failed"
                else:
                    self._browser_preview_url = store_preview(self.hass, audio)
                    return await self.async_step_fish_browser_ready()
        return self.async_show_form(
            step_id="fish_browser_preview",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "test_text", default="Привет! Я готов помочь."
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
                }
            ),
            errors=errors,
        )

    async def async_step_fish_browser_ready(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show a browser playback link, then save the selected voice."""
        if user_input is not None:
            changes = {}
            if self._pending_voice:
                changes = {
                    CONF_FISH_VOICE: self._pending_voice,
                    CONF_FISH_LANGUAGE: self._voice_language,
                }
            return self.async_create_entry(
                title="",
                data={**self._entry.options, **self._pending_fish_settings, **changes},
            )
        return self.async_show_form(
            step_id="fish_browser_ready",
            data_schema=vol.Schema({}),
            description_placeholders={"preview_url": self._browser_preview_url or ""},
        )

    async def async_step_fish_voice_preview(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Speak a test phrase on a chosen Home Assistant media player."""
        errors: dict[str, str] = {}
        tts_id = er.async_get(self.hass).async_get_entity_id(
            "tts", DOMAIN, f"{self._entry.entry_id}_fish_audio"
        )
        if not tts_id:
            errors["base"] = "fish_tts_required"
        elif user_input is not None:
            try:
                await self.hass.services.async_call(
                    "tts",
                    "speak",
                    {
                        "entity_id": tts_id,
                        "media_player_entity_id": user_input["media_player"],
                        "message": user_input["test_text"],
                        "cache": False,
                    },
                    blocking=True,
                )
            except HomeAssistantError:
                errors["base"] = "preview_failed"
            else:
                return self.async_create_entry(title="", data=self._entry.options)
        return self.async_show_form(
            step_id="fish_voice_preview",
            data_schema=vol.Schema(
                {
                    vol.Required("media_player"): EntitySelector(
                        EntitySelectorConfig(domain="media_player")
                    ),
                    vol.Required(
                        "test_text", default="Привет! Я готов помочь."
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                }
            ),
            errors=errors,
        )
