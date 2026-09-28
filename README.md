# Universal LLM Assist

Custom Home Assistant conversation integration for **Ollama Cloud, DeepSeek, Groq, Gemini**, and other OpenAI-compatible Chat Completions APIs. It receives text from an existing Assist voice pipeline, lets the model call Home Assistant's built-in Assist tools, and sends a short answer back to the pipeline. Optional **Fish Audio** text-to-speech generates the spoken answer; speech recognition remains configured separately in Home Assistant.

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
4. Keep **Allow Home Assistant control** on to allow the model to use the built-in Assist API. Adjust the prompt, thinking switch, temperature, and maximum output tokens as desired. Thinking is off by default. Providers that do not support the switch ignore it.
5. Open **Settings → Voice assistants**, edit your Assist pipeline, and choose the new conversation agent. Your existing speech-to-text engine can stay as it is.
6. In **Settings → Voice assistants → Expose**, expose the entities and scripts this agent should control. Give scripts clear names and descriptions so the model knows when to run them.

Open the integration's settings later to refresh the model catalog, change the model and prompt, or replace the key.

### Fish Audio speech

1. Open this integration's **Configure** menu and choose **Configure Fish Audio speech**.
2. Enter your [Fish Audio API key](https://fish.audio/app/api-keys). The default model is `s2.1-pro-free`. Set the language code, for example `ru`.
3. To choose a voice, reopen **Configure** and select **Find Fish Audio voice by language**. The integration calls Fish Audio's live voice catalog with the language filter; you can narrow by name and change the result page. Select a named voice, enter a test phrase, and use the browser playback link before saving. You can also paste a voice ID manually. With no voice ID, Fish Audio uses its default voice.
4. Set speech speed, expressiveness (`temperature`), intonation variation (`top_p`), speaking style, and latency. The speaking style is sent as an emotion cue in the TTS text; `none` leaves it neutral. **Balanced** is the default latency setting.
5. To hear the saved voice later, choose **Listen to voice in browser** in **Configure**. The integration generates a short MP3 and shows a five-minute playback link that opens in a new browser tab while the Home Assistant settings stay open. You can also choose **Listen to a test phrase** and select a Home Assistant media player for speaker playback.
6. Select **Fish Audio** as the text-to-speech engine in the Assist pipeline. Your LLM conversation agent and speech-to-text engine remain separate selections.

The Fish Audio key is saved only in the Home Assistant config entry. The integration sends the final assistant reply to Fish Audio and returns an MP3 to Home Assistant. Fish Audio's free model is intended for testing and has no latency guarantee; see the [official model overview](https://docs.fish.audio/overview/capabilities).

### Updates

The integration creates a **Universal LLM Assist** update entity. It checks GitHub releases every six hours. Install a new version from Home Assistant's update panel, or enable **Install new releases automatically** in the model settings to download and install updates as they appear. Installation keeps a backup of the previous component directory and restarts Home Assistant. Existing v0.1.0 manual installations need one manual upgrade to v0.2.1 before this update entity becomes available.

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
