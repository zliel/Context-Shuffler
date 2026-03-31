from typing import Optional
from .base import LLMProvider
from .ollama import OllamaProvider

PROVIDERS = {
    "ollama": OllamaProvider,
}

PROVIDER_DEFAULTS = {
    "ollama": "http://localhost:11434",
}

PROVIDER_NAMES = {
    "ollama": "Ollama",
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
