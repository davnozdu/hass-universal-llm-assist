"""OpenAI-compatible chat completions transport and message conversion."""

import asyncio
import json
from typing import Any
from uuid import uuid4

import aiohttp
from probatio import to_openapi

from homeassistant.components import conversation
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def fetch_models(hass, provider: str, base_url: str, api_key: str) -> list[str]:
    """Fetch model IDs from a provider's current catalog."""
    url = (
        f"{base_url.rstrip('/').removesuffix('/v1')}/api/tags"
        if provider == "ollama_cloud"
        else f"{base_url.rstrip('/')}/models"
    )
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(30):
            async with session.get(
                url, headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                if response.status in (401, 403):
                    raise HomeAssistantError("Invalid API key")
                if response.status >= 400:
                    raise HomeAssistantError(f"Model list returned HTTP {response.status}")
                payload = await response.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise HomeAssistantError("Could not load model list") from err
    except (ValueError, TypeError) as err:
        raise HomeAssistantError("Invalid model list response") from err
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise HomeAssistantError("Provider did not return a model list")
    names = {
        model.get("name" if provider == "ollama_cloud" else "id")
        for model in models
        if isinstance(model, dict)
    }
    return sorted(name for name in names if isinstance(name, str) and name)


def completion_messages(chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    """Convert Home Assistant's chat history to Chat Completions messages."""
    messages: list[dict[str, Any]] = []
    for item in chat_log.content:
        if item.role in ("system", "user"):
            messages.append({"role": item.role, "content": item.content})
        elif item.role == "assistant":
            message: dict[str, Any] = {"role": "assistant", "content": item.content}
            if isinstance(item.native, dict):
                for key in ("reasoning_content", "extra_content"):
                    if key in item.native:
                        message[key] = item.native[key]
            if item.tool_calls:
                native_calls = (
                    item.native.get("tool_calls")
                    if isinstance(item.native, dict)
                    else None
                )
                message["tool_calls"] = native_calls or [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.tool_name,
                            "arguments": json.dumps(call.tool_args, ensure_ascii=False),
                        },
                    }
                    for call in item.tool_calls
                ]
            messages.append(message)
        elif item.role == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.tool_call_id,
                    "content": json.dumps(item.tool_result, ensure_ascii=False),
                }
            )
    return messages


def completion_tools(chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    """Expose only tools supplied by the selected Home Assistant LLM API."""
    api = chat_log.llm_api
    if api is None:
        return []
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": to_openapi(
                    tool.parameters, custom_serializer=api.custom_serializer
                ),
            },
        }
        for tool in api.tools
    ]


async def request_completion(
    hass,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Request one nonstreaming completion from the configured provider."""
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    headers = {"Authorization": f"Bearer {api_key}"}
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(120):
            async with session.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status >= 400:
                    # The server's error may contain user input. Keep it out of logs.
                    raise HomeAssistantError(
                        f"LLM provider returned HTTP {response.status}. "
                        "Check the API key, model name, and provider URL."
                    )
                result = await response.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise HomeAssistantError("Could not reach the LLM provider") from err
    except (ValueError, TypeError) as err:
        raise HomeAssistantError("Invalid JSON response from LLM provider") from err
    try:
        message = result["choices"][0]["message"]
        if not isinstance(message, dict):
            raise TypeError
        return message
    except (KeyError, IndexError, TypeError) as err:
        raise HomeAssistantError("LLM provider returned no assistant message") from err


def assistant_content(entity_id: str, message: dict[str, Any]) -> conversation.AssistantContent:
    """Convert model output to Home Assistant content and validated tool inputs."""
    calls = []
    normalized_calls = []
    for raw in message.get("tool_calls") or []:
        try:
            function = raw["function"]
            args = function["arguments"]
            parsed = json.loads(args) if isinstance(args, str) else args
            if not isinstance(parsed, dict):
                raise ValueError
            call_id = raw.get("id") or uuid4().hex
            calls.append(
                llm.ToolInput(
                    id=call_id,
                    tool_name=function["name"],
                    tool_args=parsed,
                )
            )
            normalized_calls.append({**raw, "id": call_id})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as err:
            raise HomeAssistantError("LLM provider returned an invalid tool call") from err
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise HomeAssistantError("LLM provider returned unsupported message content")
    if normalized_calls:
        message = {**message, "tool_calls": normalized_calls}
    return conversation.AssistantContent(
        agent_id=entity_id,
        content=content,
        tool_calls=calls or None,
        native=message,
    )
