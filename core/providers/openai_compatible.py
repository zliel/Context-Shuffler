import json
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMProvider


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
        keep_alive: int = 0,
    ) -> Optional[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        url = f"{self.base_url}/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return ""
        except (urllib.error.URLError, Exception):
            return None

    def list_models(self) -> list[str]:
        try:
            url = f"{self.base_url}/v1/models"
            req = urllib.request.Request(url, method="GET")
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
