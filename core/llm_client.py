import json
import urllib.request
import urllib.error


def generate_variation(
    url: str, model: str, system_prompt: str, target: str, sentence: str, temp: float
) -> str:
    """
    Synchronously calls the local Ollama API to generate a replacement sentence.
    """
    prompt = (
        f"Target Word: {target}\nOriginal Sentence: {sentence}\n\nRephrased Sentence:"
    )

    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": temp, "num_predict": 150},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        import re

        # Bypassing Anki's internal proxies which often intercept or artificially hang localhost
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        with opener.open(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_generated = result.get("response", "").strip()

            # Failsafe regex to forcefully rip out reasoning models' <think> tags
            generated = re.sub(
                r"<think>.*?</think>", "", raw_generated, flags=re.DOTALL
            ).strip()

            # Sanitization: Only take the first non-empty line to cut off AI rambling/notes
            lines = [line.strip() for line in generated.split("\n") if line.strip()]
            generated = lines[0] if lines else ""

            return generated

    except urllib.error.URLError:
        return None
    except Exception:
        return None
