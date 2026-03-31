import json
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    """Base class for OpenAI-compatible providers (llama.cpp, vLLM, LM Studio)."""
    
    def __init__(self, base_url: str, provider_name: str):
        self.base_url = base_url.rstrip('/')
        self._provider_name = provider_name
    
    @property
    def provider_name(self) -> str:
        return self._provider_name
    
    def get_default_endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions"
    
    def generate(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        url = f"{self.base_url}/v1/chat/completions"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=300) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        except (urllib.error.URLError, Exception):
            return None
    
    def list_models(self) -> list[str]:
        try:
            url = f"{self.base_url}/v1/models"
            req = urllib.request.Request(url, method='GET')
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return [m.get('id', '') for m in result.get('data', [])]
        except Exception:
            return []


class LlamaCppProvider(OpenAICompatibleProvider):
    """llama.cpp server provider."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__(base_url, "llama.cpp")


class VLLMProvider(OpenAICompatibleProvider):
    """vLLM provider."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url, "vLLM")


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio provider."""
    
    def __init__(self, base_url: str = "http://localhost:1234"):
        super().__init__(base_url, "LM Studio")
