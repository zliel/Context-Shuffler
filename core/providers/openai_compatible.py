import json
import socket
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMProvider
from .exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMBadResponseError,
    LLMEmptyResponseError,
)


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider (vLLM, LM Studio, llama.cpp, etc.)."""

    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "OpenAI-Compatible"

    def get_default_endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        url = f"{self.base_url}/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")

        try:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if not choices:
                    raise LLMBadResponseError("OpenAI response missing choices")
                raw = choices[0].get("message", {}).get("content", "").strip()
                if not raw:
                    raise LLMEmptyResponseError("Empty response from OpenAI-compatible provider")
                return self.clean_response(raw) if raw else ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                raise LLMRateLimitError(f"Server rate-limited (HTTP {e.code})")
            raise LLMConnectionError(f"HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Connection failed: {e.reason}")
        except socket.timeout:
            raise LLMTimeoutError("Request timed out")
        except json.JSONDecodeError as e:
            raise LLMBadResponseError(f"Invalid JSON response: {e}")
        except KeyError as e:
            raise LLMBadResponseError(f"Response missing key: {e}")
        except LLMEmptyResponseError:
            raise
        except Exception as e:
            raise LLMConnectionError(f"Provider error: {e}")

    def list_models(self, api_key: str = "") -> list[str]:
        try:
            url = f"{self.base_url}/v1/models"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Content-Type", "application/json")
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return [m.get("id", "") for m in result.get("data", [])]
        except Exception:
            return []

    def warm_up(self, model: str, keep_alive: int = 0) -> bool:
        """OpenAI-compatible servers don't support warm-up in the same way."""
        return True
