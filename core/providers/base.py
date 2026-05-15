import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

from .exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMBadResponseError,
    LLMEmptyResponseError,
)


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
    def list_models(self, api_key: str = "") -> list[str]:
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

    def retry_generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        model: str,
        api_key: str = "",
        keep_alive: int = 0,
        max_attempts: int = 4,
    ) -> Optional[str]:
        """Generate with exponential backoff retry for transient errors."""
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                    api_key=api_key,
                    keep_alive=keep_alive,
                )
                if result is None:
                    raise LLMEmptyResponseError("Generation returned None")
                return result
            except (LLMConnectionError, LLMTimeoutError, LLMRateLimitError) as e:
                last_error = e
                if attempt < max_attempts:
                    wait = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    logger.warning(
                        "LLM transient error (attempt %d/%d): %s. Retrying in %ds...",
                        attempt, max_attempts, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "LLM transient error (attempt %d/%d): %s. No more retries.",
                        attempt, max_attempts, e,
                    )
                    raise
            except (LLMBadResponseError, LLMEmptyResponseError):
                raise  # Don't retry these
        raise last_error  # Shouldn't reach here, but satisfy type checker
