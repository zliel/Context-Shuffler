from aqt import mw
import threading
from ..core.providers import get_provider
from ..core.providers.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
)


def trigger_generation(
    card_id: int,
    target: str,
    sentence: str,
    config: dict,
    on_success_callback,
    on_error_callback=None,
) -> None:
    """
    Triggers an asynchronous call to the LLM off the main thread.
    Uses retry_generate() for transient failure resilience.
    Calls on_error_callback(error_msg) on failure.
    """
    provider_type = config.get("provider", "ollama")
    base_url = config.get("base_url", "http://localhost:11434")
    model = config.get("model", "llama3")
    system_prompt = config.get("system_prompt", "")
    temp = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 150)
    keep_alive = config.get("keep_alive", 0)
    api_key = config.get("api_key", "")

    def background_task():
        try:
            provider = get_provider(provider_type, base_url)
            prompt = (
                f"Target Word: {target}\n"
                f"Original Sentence: {sentence}\n\n"
                f"Rephrased Sentence:"
            )
            generated = provider.retry_generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temp,
                max_tokens=max_tokens,
                model=model,
                api_key=api_key,
                keep_alive=keep_alive,
            )
            if generated and generated.strip():
                mw.taskman.run_on_main(
                    lambda: on_success_callback(card_id, sentence, generated)
                )
            else:
                if on_error_callback:
                    mw.taskman.run_on_main(
                        lambda: on_error_callback("LLM returned empty response")
                    )
        except LLMConnectionError as e:
            if on_error_callback:
                mw.taskman.run_on_main(
                    lambda: on_error_callback(f"Connection error: {e}")
                )
        except LLMTimeoutError as e:
            if on_error_callback:
                mw.taskman.run_on_main(
                    lambda: on_error_callback(f"Request timed out: {e}")
                )
        except LLMRateLimitError as e:
            if on_error_callback:
                mw.taskman.run_on_main(
                    lambda: on_error_callback(f"Rate limited: {e}")
                )
        except Exception as e:
            if on_error_callback:
                mw.taskman.run_on_main(
                    lambda: on_error_callback(f"Generation failed: {e}")
                )

    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
