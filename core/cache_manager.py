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
        conn.execute("PRAGMA journal_mode=WAL")


def clear_all_variations():
    try:
        with _get_connection() as conn:
            conn.execute("DELETE FROM variations")
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def get_variation(card_id: int) -> str:
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT variation_text FROM variations WHERE card_id = ?", (card_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return None  # Fail silently — return cache miss


def save_variation(card_id: int, original: str, generated: str) -> None:
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO variations (card_id, variation_text)
                VALUES (?, ?)
            """,
                (card_id, generated),
            )
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass  # Silent failure — next review will retry


def record_lapse(card_id: int, duration: int) -> None:
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO lapse_tracking (card_id, lapsed_at, reviews_remaining)
                VALUES (?, ?, ?)
            """,
                (card_id, int(time.time()), duration),
            )
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def get_lapse_status(card_id: int) -> tuple[bool, int]:
    try:
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
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return False, 0


def decrement_lapse_counter(card_id: int) -> None:
    try:
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
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def clear_lapse_data(card_id: int) -> None:
    try:
        with _get_connection() as conn:
            conn.execute(
                "DELETE FROM lapse_tracking WHERE card_id = ?",
                (card_id,),
            )
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def clear_all_lapse_data() -> None:
    try:
        with _get_connection() as conn:
            conn.execute("DELETE FROM lapse_tracking")
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def get_all_variations() -> list[tuple[int, str]]:
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT card_id, variation_text FROM variations ORDER BY card_id"
            )
            return cursor.fetchall()
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return []


def delete_variation(card_id: int) -> None:
    try:
        with _get_connection() as conn:
            conn.execute("DELETE FROM variations WHERE card_id = ?", (card_id,))
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass


def repair_db() -> bool:
    """Attempts to repair a corrupted database by recreating it.
    Returns True if successful, False otherwise.
    Warning: This will DELETE all existing data.
    """
    try:
        db_path = DB_PATH
        backup_path = db_path + ".corrupted"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(db_path, backup_path)
        init_db()
        return True
    except Exception:
        return False
