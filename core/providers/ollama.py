import json
import urllib.request
import urllib.error
from typing import Optional
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    """Ollama provider using its custom API format."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
    
    @property
    def provider_name(self) -> str:
        return "Ollama"
    
    def get_default_endpoint(self) -> str:
        return f"{self.base_url}/api/generate"
    
    def generate(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        payload = {
            "model": "",
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        url = f"{self.base_url}/api/generate"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=300) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '').strip()
        except (urllib.error.URLError, Exception):
            return None
    
    def list_models(self) -> list[str]:
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method='GET')
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return [m.get('name', '') for m in result.get('models', [])]
        except Exception:
            return []
