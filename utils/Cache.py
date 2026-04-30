import sqlite3
import hashlib
from datetime import datetime, timezone


# ─────────────────────────────────────────
# STEP 1 — SETUP THE CACHE DATABASE
# ─────────────────────────────────────────


def init_cache(db_path="rag_cache.db"):
    """
    Creates the SQLite cache file and table if they don't exist.
    Run this once at startup — safe to call every time.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS query_cache (
            question_hash     TEXT PRIMARY KEY,
            question          TEXT,
            answer            TEXT,
            retrieval_secs    REAL,
            generation_secs   REAL,
            total_secs        REAL,
            tokens_per_request INTEGER,
            created_at        TEXT
        )
    """
    )

    conn.commit()
    conn.close()
    print("✅ Cache database ready.")


# ─────────────────────────────────────────
# STEP 2 — READ FROM CACHE
# ─────────────────────────────────────────


def get_cached_answer(question: str, db_path="rag_cache.db"):
    """
    Check if we already have an answer for this question.
    Returns the cached row if found, None if not found.
    Think of it like checking your notebook before starting work.
    """

    # Create a unique fingerprint for this question
    # "What is AI?" always becomes the same short code
    # Clean the question first
    clean_question = question.strip().lower()

    # Convert to bytes
    question_bytes = clean_question.encode()

    # Create a short unique fingerprint
    question_hash = hashlib.md5(question_bytes).hexdigest()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT answer, retrieval_secs, generation_secs,
               total_secs, tokens_per_request
        FROM query_cache
        WHERE question_hash = ?
    """,
        (question_hash,),
    )

    row = cursor.fetchone()
    conn.close()

    # Returns None if not found
    # Returns a tuple if found: (answer, retrieval, generation, total, tokens)
    return row


# ─────────────────────────────────────────
# STEP 3 — SAVE TO CACHE
# ─────────────────────────────────────────


def save_to_cache(
    question: str,
    answer: str,
    retrieval_secs: float,
    generation_secs: float,
    total_secs: float,
    tokens_per_request: int,
    db_path="rag_cache.db",
):
    """
    Save a new question + answer into the cache.
    Next time this question is asked → we return instantly.
    """

    question_hash = hashlib.md5(question.strip().lower().encode()).hexdigest()

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # INSERT OR REPLACE means:
    # if question already exists → update it
    # if question is new → insert it
    cursor.execute(
        """
        INSERT OR REPLACE INTO query_cache (
            question_hash, question, answer,
            retrieval_secs, generation_secs, total_secs,
            tokens_per_request, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            question_hash,
            question,
            answer,
            retrieval_secs,
            generation_secs,
            total_secs,
            tokens_per_request,
            created_at,
        ),
    )

    conn.commit()
    conn.close()
