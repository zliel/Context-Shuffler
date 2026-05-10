import re
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        model: str,
        api_key: str = "",
        keep_alive: int = 0,
    ) -> Optional[str]:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models. Returns empty list if not supported."""
        pass

    @abstractmethod
    def get_default_endpoint(self) -> str:
        """Return the default endpoint URL for this provider."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider."""
        pass

    @staticmethod
    def clean_response(raw: str) -> str:
        if not raw:
            return ""
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        return lines[0] if lines else ""

    def warm_up(self, model: str, keep_alive: int = 0) -> bool:
        """Warm up the model. Override in subclass if supported."""
        return True
