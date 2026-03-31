from typing import Optional
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai_compat import LlamaCppProvider, VLLMProvider, LMStudioProvider

PROVIDERS = {
    "ollama": OllamaProvider,
    "llamacpp": LlamaCppProvider,
    "vllm": VLLMProvider,
    "lmstudio": LMStudioProvider,
}

PROVIDER_DEFAULTS = {
    "ollama": "http://localhost:11434",
    "llamacpp": "http://localhost:8080",
    "vllm": "http://localhost:8000",
    "lmstudio": "http://localhost:1234",
}

PROVIDER_NAMES = {
    "ollama": "Ollama",
    "llamacpp": "llama.cpp",
    "vllm": "vLLM",
    "lmstudio": "LM Studio",
}


def get_provider(provider_type: str, base_url: Optional[str] = None) -> LLMProvider:
    """Factory function to create a provider instance."""
    provider_class = PROVIDERS.get(provider_type, OllamaProvider)
    if base_url is None:
        base_url = PROVIDER_DEFAULTS.get(provider_type, "http://localhost:11434")
    return provider_class(base_url)


def get_all_providers() -> list[str]:
    """Return list of all available provider keys."""
    return list(PROVIDERS.keys())
