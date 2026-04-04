import json
import re
import urllib.request
import urllib.error


def generate_variation(
    url: str,
    model: str,
    system_prompt: str,
    target: str,
    sentence: str,
    temp: float,
    keep_alive: int = 0,
) -> str:
    """
    Calls the local LLM API to generate a replacement sentence.
    Supports both Ollama and OpenAI-compatible formats.
    """
    prompt = (
        f"Target Word: {target}\nOriginal Sentence: {sentence}\n\nRephrased Sentence:"
    )

    if "/v1/chat/completions" in url:
        return _generate_openai_compatible(url, model, system_prompt, prompt, temp)
    else:
        return _generate_ollama(url, model, system_prompt, prompt, temp, keep_alive)


def _generate_ollama(
    url: str,
    model: str,
    system_prompt: str,
    prompt: str,
    temperature: float,
    keep_alive: int = 0,
) -> str:
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": 150},
    }

    if keep_alive > 0:
        payload["keep_alive"] = keep_alive * 60

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        with opener.open(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_generated = result.get("response", "").strip()

            generated = re.sub(
                r"<think>.*?", "", raw_generated, flags=re.DOTALL
            ).strip()

            lines = [line.strip() for line in generated.split("\n") if line.strip()]
            return lines[0] if lines else ""

    except (urllib.error.URLError, Exception):
        return None


def _generate_openai_compatible(
    url: str,
    model: str,
    system_prompt: str,
    prompt: str,
    temperature: float,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        # "max_tokens": 150,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        with opener.open(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))

            choices = result.get("choices", [])
            if not choices:
                return ""

            raw_generated = choices[0].get("message", {}).get("content", "").strip()

            generated = re.sub(
                r"<think>.*?", "", raw_generated, flags=re.DOTALL
            ).strip()

            lines = [line.strip() for line in generated.split("\n") if line.strip()]
            result_text = lines[0] if lines else ""
            return result_text

    except urllib.error.HTTPError as e:
        return None
    except urllib.error.URLError as e:
        return None
    except Exception as e:
        return None
