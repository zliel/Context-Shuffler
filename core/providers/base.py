from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
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
