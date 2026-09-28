"""UI setup for Universal LLM Assist."""

from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_PROMPT
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
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
    CONF_CONTROL,
    CONF_MODEL,
    CONF_PROVIDER,
    DEFAULT_PROMPT,
    DOMAIN,
    PROVIDERS,
)


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
        default = {CONF_MODEL: PROVIDERS[self._connection[CONF_PROVIDER]][2]}
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
        default = {CONF_MODEL: PROVIDERS[self._connection[CONF_PROVIDER]][2]}
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

    @property
    def _settings(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["refresh_models", "manual_model", "connection"],
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
        )
