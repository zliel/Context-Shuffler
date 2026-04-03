import sqlite3
import os

# Store the cache database physically next to the scripts in the addon dir
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cache.db")


def _get_connection():
    """Returns a SQLite connection object with context manager safety."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Ensures the caching table exists when Anki starts up."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS variations (
                card_id INTEGER PRIMARY KEY,
                variation_text TEXT NOT NULL
            )
        """)


def clear_all_variations():
    """Wipes the entire cache database, useful for prompt resets."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM variations")


def get_variation(card_id: int) -> str:
    """
    Fetches the singular next sentence stored for the specific card.
    Returns None if the card hasn't been reviewed before.
    """
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT variation_text FROM variations WHERE card_id = ?", (card_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None


def save_variation(card_id: int, original: str, generated: str) -> None:
    """
    Used as the callback upon `llm_worker.trigger_generation` success.
    Overwrites the old generation with the latest one seamlessly.
    Note: original is passed from the success callback signature, but we only store the new text.
    """
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO variations (card_id, variation_text)
            VALUES (?, ?)
        """,
            (card_id, generated),
        )
