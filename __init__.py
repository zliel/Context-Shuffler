"""
Context Shuffler
Intercepts card rendering and replaces example sentences with LLM-generated variations.
"""

import threading
from aqt import mw, gui_hooks
from aqt.qt import QAction, qconnect
from aqt.utils import tooltip
from .core import cache_manager
from .core.providers import get_provider
from .workers import llm_worker

# Initialize the cache database once upon startup
cache_manager.init_db()

# Session State Tracking
# Used to ensure front and back of the card match and that we only trigger 1 API call per review.
last_card_id = None
current_session_variation = None
last_kind = None


def on_card_will_show(text: str, card: "anki.cards.Card", kind: str) -> str:
    """
    Hook to modify the card's HTML before it is rendered.
    """
    global last_card_id, current_session_variation, last_kind

    if not text:
        return text

    # Only process cards in the reviewer
    if kind not in ("reviewQuestion", "reviewAnswer"):
        return text

    config = mw.addonManager.getConfig(__name__) or {}

    # Master Enable/Disable Toggle
    if not config.get("enabled", True):
        return text

    # Deck Filtering mechanism
    deck_name = mw.col.decks.name(card.did)
    enabled_decks = config.get("enabled_decks", [])

    if enabled_decks and deck_name not in enabled_decks:
        return text

    try:
        note = card.note()
    except Exception:
        return text

    context_field = config.get("context_field", "ExampleSentence")
    target_field = config.get("target_field", "TargetWord")

    if context_field not in note or target_field not in note:
        return text

    original_context = note[context_field]
    target_word = note[target_field]

    # --- Session Management Logic ---

    is_new_review = False

    if kind == "reviewQuestion":
        if card.id != last_card_id or last_kind == "reviewAnswer":
            is_new_review = True

    if is_new_review:
        last_card_id = card.id

        # Fetch the variation from the cache
        cached_val = cache_manager.get_variation(card.id)
        current_session_variation = cached_val if cached_val else None

        # Trigger the background generation
        def on_success(card_id: int, original: str, generated: str) -> None:
            cache_manager.save_variation(card_id, original, generated)
            tooltip("CS: Context Updated", period=1000)

        llm_worker.trigger_generation(
            card_id=card.id,
            target=target_word,
            sentence=original_context,
            config=config,
            on_success_callback=on_success,
        )

    # --- State Snapshot ---
    last_kind = kind

    # --- Replacement Logic ---

    if current_session_variation and card.id == last_card_id:
        text = text.replace(original_context, current_session_variation)

    return text


def on_settings_clicked() -> None:
    from .gui.settings_dialog import show_settings_dialog

    show_settings_dialog(__name__)


def on_reviewer_init(reviewer) -> None:
    config = mw.addonManager.getConfig(__name__) or {}
    if not config.get("enabled", True):
        return

    provider_type = config.get("provider", "ollama")
    model = config.get("model", "qwen3-vl:8b-instruct")
    keep_alive = config.get("keep_alive", 0)
    base_url = config.get("base_url", "http://localhost:11434")

    def warm_up_task():
        try:
            provider = get_provider(provider_type, base_url)
            if hasattr(provider, "warm_up"):
                provider.warm_up(model, keep_alive)
            mw.taskman.run_on_main(lambda: tooltip("CS: Warm-up sent", period=1500))
        except Exception:
            pass

    thread = threading.Thread(target=warm_up_task, daemon=True)
    thread.start()


def setup_menu() -> None:
    action = QAction("Context Shuffler Settings...", mw)
    qconnect(action.triggered, on_settings_clicked)
    mw.form.menuTools.addAction(action)


gui_hooks.card_will_show.append(on_card_will_show)
gui_hooks.reviewer_did_init.append(on_reviewer_init)
setup_menu()
