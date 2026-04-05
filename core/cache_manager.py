import sqlite3
import os
import time

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lapse_tracking (
                card_id INTEGER PRIMARY KEY,
                lapsed_at INTEGER NOT NULL,
                reviews_remaining INTEGER NOT NULL
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


def record_lapse(card_id: int, duration: int) -> None:
    """
    Records that a card has lapsed and sets the number of reviews
    to show the original sentence before resuming shuffling.
    """
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO lapse_tracking (card_id, lapsed_at, reviews_remaining)
            VALUES (?, ?, ?)
        """,
            (card_id, int(time.time()), duration),
        )


def get_lapse_status(card_id: int) -> tuple[bool, int]:
    """
    Checks if a card is currently in lapse recovery mode.
    Returns (is_lapsed, reviews_remaining).
    """
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reviews_remaining FROM lapse_tracking WHERE card_id = ?",
            (card_id,),
        )
        row = cursor.fetchone()
        if row:
            return True, row[0]
        return False, 0


def decrement_lapse_counter(card_id: int) -> None:
    """Decrements the lapse recovery counter for a card."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reviews_remaining FROM lapse_tracking WHERE card_id = ?",
            (card_id,),
        )
        row = cursor.fetchone()
        if row:
            remaining = row[0] - 1
            if remaining <= 0:
                conn.execute(
                    "DELETE FROM lapse_tracking WHERE card_id = ?",
                    (card_id,),
                )
            else:
                conn.execute(
                    "UPDATE lapse_tracking SET reviews_remaining = ? WHERE card_id = ?",
                    (remaining, card_id),
                )


def clear_lapse_data(card_id: int) -> None:
    """Clears lapse tracking data for a specific card."""
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM lapse_tracking WHERE card_id = ?",
            (card_id,),
        )


def clear_all_lapse_data() -> None:
    """Clears all lapse tracking data."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM lapse_tracking")
