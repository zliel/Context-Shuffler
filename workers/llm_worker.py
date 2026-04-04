from aqt import mw
import threading
from ..core.llm_client import generate_variation


def trigger_generation(
    card_id: int, target: str, sentence: str, config: dict, on_success_callback
) -> None:
    """
    Triggers an asynchronous call to the LLM off the main thread.
    """
    url = config.get("url", "http://localhost:11434/api/generate")
    model = config.get("model", "llama3")
    system_prompt = config.get("system_prompt", "")
    temp = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 150)
    keep_alive = config.get("keep_alive", 0)

    def background_task():
        generated = generate_variation(
            url, model, system_prompt, target, sentence, temp, max_tokens, keep_alive
        )

        if generated:
            mw.taskman.run_on_main(
                lambda: on_success_callback(card_id, sentence, generated)
            )

    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
