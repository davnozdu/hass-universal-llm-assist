"""Conversation agent for Ollama Cloud, DeepSeek, Groq, and Gemini."""

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import llm
from homeassistant.exceptions import HomeAssistantError

from .client import assistant_content, completion_messages, completion_tools, request_completion
from .const import (
    CONF_BASE_URL,
    CONF_CONTROL,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_PROVIDER,
    CONF_TEMPERATURE,
    CONF_THINK,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DOMAIN,
)
from .settings import merged_settings

MAX_TOOL_ITERATIONS = 8


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one Assist agent for this provider entry."""
    async_add_entities([UniversalLLMConversation(entry)])


class UniversalLLMConversation(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """Use a selected model as an Assist conversation agent."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id
        if entry.options.get(CONF_CONTROL, True):
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        settings = merged_settings(self.entry.data, self.entry.options)
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                llm.LLM_API_ASSIST if settings.get(CONF_CONTROL, True) else None,
                settings.get(CONF_PROMPT, DEFAULT_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        for _ in range(MAX_TOOL_ITERATIONS):
            message = await request_completion(
                self.hass,
                settings[CONF_PROVIDER],
                settings[CONF_BASE_URL],
                settings[CONF_API_KEY],
                settings[CONF_MODEL],
                completion_messages(chat_log),
                completion_tools(chat_log),
                thinking=settings.get(CONF_THINK, False),
                temperature=settings.get(
                    CONF_TEMPERATURE,
                    1.0 if settings[CONF_PROVIDER] == "gemini" else 0.7,
                ),
                max_tokens=settings.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            )
            content = assistant_content(self.entity_id, message)
            async for _ in chat_log.async_add_assistant_content(content):
                pass
            if not content.tool_calls:
                return conversation.async_get_result_from_chat_log(user_input, chat_log)

        raise HomeAssistantError("The model called too many tools")
