# Universal LLM Assist

Custom Home Assistant conversation integration for **Ollama Cloud, DeepSeek, Groq, Gemini**, and other OpenAI-compatible Chat Completions APIs. It receives text from an existing Assist voice pipeline, lets the model call Home Assistant's built-in Assist tools, and sends a short answer back to the pipeline. Speech recognition and speech synthesis remain configured in Home Assistant.

## Requirements

- Home Assistant Core **2026.9** or newer.
- An API key for your chosen provider and a model with **function/tool calling** support.
- The devices and scripts you want to control must be exposed to Assist. Only those exposed items are available to the model.

## Install

### HACS

Add this GitHub repository as a custom repository of type **Integration** in HACS, install *Universal LLM Assist*, and restart Home Assistant.

### Manual

Download `universal_llm_assist.zip` from a release and extract it into your Home Assistant `config` directory. The result must be `config/custom_components/universal_llm_assist/manifest.json`. Restart Home Assistant.

## Configure

1. Open **Settings → Devices & services → Add integration → Universal LLM Assist**.
2. Select Ollama Cloud, DeepSeek, Groq, or Gemini and paste the corresponding API key. The official API URL is filled in automatically; you can override it.
3. Press **Считать актуальные модели / Load current models** to fetch the live catalog and select a model. The manual entry path is available if a provider does not expose a model catalog.
4. Keep **Allow Home Assistant control** on to allow the model to use the built-in Assist API. Adjust the prompt if desired.
5. Open **Settings → Voice assistants**, edit your Assist pipeline, and choose the new conversation agent. Your existing speech-to-text engine can stay as it is.
6. In **Settings → Voice assistants → Expose**, expose the entities and scripts this agent should control. Give scripts clear names and descriptions so the model knows when to run them.

Open the integration's settings later to refresh the model catalog, change the model and prompt, or replace the key.

**Ollama Cloud:** Use an [Ollama API key](https://ollama.com/settings/keys), not a local Ollama sign-in. The integration connects directly to `https://ollama.com/v1`. For this API, model names are those returned by the cloud API, for example `gemma4:31b`; CLI names ending in `:cloud` are different.

The default prompt is tuned for spoken responses: short, in the user's language, and based on confirmed tool results. Model latency depends on the provider and selected model. The integration currently uses nonstreaming responses and can call tools for up to eight rounds per request.

## Provider endpoints

| Provider | Default base URL | Model list |
| --- | --- | --- |
| Ollama Cloud | `https://ollama.com/v1` | Ollama `/api/tags` |
| DeepSeek | `https://api.deepseek.com` | `/models` |
| Groq | `https://api.groq.com/openai/v1` | `/models` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `/models` |

The model list is loaded only when requested in the setup or options menu. No key is stored in this repository; Home Assistant stores keys in its config entry data.

## Development

The release workflow packages `custom_components/universal_llm_assist` as `universal_llm_assist.zip` when a `v*` tag is pushed. It does not embed API keys.
