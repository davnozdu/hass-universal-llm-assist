"""Constants for Universal LLM Assist."""

DOMAIN = "universal_llm_assist"
VERSION = "0.2.4"

CONF_PROVIDER = "provider"
CONF_BASE_URL = "base_url"
CONF_MODEL = "model"
CONF_CONTROL = "control_home_assistant"
CONF_THINK = "thinking_mode"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_output_tokens"
CONF_AUTO_UPDATE = "auto_update"
CONF_FISH_API_KEY = "fish_api_key"
CONF_FISH_MODEL = "fish_model"
CONF_FISH_VOICE = "fish_voice"
CONF_FISH_SPEED = "fish_speed"
CONF_FISH_LATENCY = "fish_latency"
CONF_FISH_LANGUAGE = "fish_language"
CONF_FISH_TEMPERATURE = "fish_temperature"
CONF_FISH_TOP_P = "fish_top_p"
CONF_FISH_EMOTION = "fish_emotion"

DEFAULT_MAX_TOKENS = 1024

PROVIDERS = {
    "ollama_cloud": ("Ollama Cloud", "https://ollama.com/v1", "gemma4:31b"),
    "deepseek": ("DeepSeek", "https://api.deepseek.com", "deepseek-flash"),
    "groq": ("Groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "gemini": (
        "Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-3.8-flash",
    ),
    "custom": ("Other OpenAI-compatible API", "", ""),
}

DEFAULT_PROMPT = (
    "You are a fast, capable Home Assistant voice assistant. Understand the user's "
    "intent and respond in the user's language. For a home control request, use the "
    "available Home Assistant tool immediately. Do not claim success until the tool "
    "confirms it. If a request is unclear, ask one short clarifying question. "
    "Your reply will be spoken aloud: use one brief, natural sentence, preferably "
    "under 12 words. Do not repeat the user's request, list device states, add filler, "
    "or explain your reasoning unless asked. For a successful action say only a short "
    "confirmation, such as 'Готово' or 'Свет включён'."
)
