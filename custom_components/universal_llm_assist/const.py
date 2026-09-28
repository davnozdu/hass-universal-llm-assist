"""Constants for Universal LLM Assist."""

DOMAIN = "universal_llm_assist"

CONF_PROVIDER = "provider"
CONF_BASE_URL = "base_url"
CONF_MODEL = "model"
CONF_CONTROL = "control_home_assistant"

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
