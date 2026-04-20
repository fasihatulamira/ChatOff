
# ===== AUTHENTICATION + CHAT HISTORY + KNOWLEDGE BASE MODULE =====
# Handles user auth, chat history, and the knowledge base (option table) in MySQL (chatdb).

import os
import hashlib
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ─────────────────────────────────────────────
#  Database connection settings
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": os.getenv("DB_PASSWORD"),
    "database": "chatdb",
}


def _get_connection():
    """Open and return a connection to the MySQL database."""
    return mysql.connector.connect(**DB_CONFIG)


# ─────────────────────────────────────────────
#  Database initialisation
# ─────────────────────────────────────────────
def init_db():
    """
    Create the 'chatdb' database (if absent), and all three tables:
      - users         : registered accounts
      - option        : knowledge base entries
      - chat_history  : per-user conversation log
    Called once at app startup.
    """
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
        )
        cursor = conn.cursor()

        # Create database if it doesn't already exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")

        # users table is handled manually by the user


        # ── option (knowledge base) table ────────────────────────────────
        # Stores custom knowledge / instructions for the chatbot.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `option` (
                id         INT          PRIMARY KEY AUTO_INCREMENT,
                title      VARCHAR(120) NOT NULL,
                content    TEXT         NOT NULL,
                created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── chat_history table ───────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id         INT          PRIMARY KEY AUTO_INCREMENT,
                user_id    INT          NOT NULL,
                sender     VARCHAR(20)  NOT NULL,
                message    TEXT         NOT NULL,
                model      VARCHAR(60)  NOT NULL DEFAULT 'llama3',
                created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    except Error as e:
        raise RuntimeError(f"Could not initialise the database: {e}")


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """Return a SHA-256 hex digest of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()


def _get_user_id(username: str) -> int | None:
    """Return the integer id for a given username, or None if not found."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username.strip().lower(),))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


# ─────────────────────────────────────────────
#  Authentication API
# ─────────────────────────────────────────────
def register_user(full_name: str, username: str, email: str, password: str) -> tuple[bool, str]:
    """
    Attempt to register a new user.
    Returns (True, "success") on success, or (False, reason) on failure.
    """
    if not full_name.strip() or not username.strip() or not email.strip() or not password.strip():
        return False, "All fields are required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (fullname, username, email, password) VALUES (%s, %s, %s, %s)",
            (full_name.strip(), username.strip().lower(), email.strip().lower(), _hash_password(password))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "success"

    except mysql.connector.IntegrityError as e:
        err = str(e)
        if "username" in err:
            return False, "Username already taken. Please choose another."
        elif "email" in err:
            return False, "Email is already registered. Please log in."
        return False, "Registration failed. Please try again."

    except Error as e:
        return False, f"Database error: {e}"


def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    Validate login credentials.
    Returns (True, full_name) on success, or (False, error_message) on failure.
    """
    if not username.strip() or not password.strip():
        return False, "Username and password are required."

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fullname, password FROM users WHERE username = %s",
            (username.strip().lower(),)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

    except Error as e:
        return False, f"Database error: {e}"

    if row is None:
        return False, "No account found with that username."

    full_name, stored_hash = row
    if stored_hash != _hash_password(password):
        return False, "Incorrect password. Please try again."

    return True, full_name


# ─────────────────────────────────────────────
#  Knowledge Base API  (option table)
# ─────────────────────────────────────────────
def add_knowledge(title: str, content: str) -> tuple[bool, str]:
    """
    Add a new knowledge base entry.
    Returns (True, "success") or (False, error_message).
    """
    if not title.strip() or not content.strip():
        return False, "Title and content are required."

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO `option` (title, content) VALUES (%s, %s)",
            (title.strip(), content.strip())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "success"

    except Error as e:
        return False, f"Database error: {e}"


def get_all_knowledge() -> list[dict]:
    """
    Return all knowledge base entries as a list of dicts:
    { id, title, content, created_at }
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, title, content, created_at FROM `option` ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    except Error:
        return []


def delete_knowledge(entry_id: int) -> None:
    """Delete a knowledge base entry by its id."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM `option` WHERE id = %s", (entry_id,))
        conn.commit()
        cursor.close()
        conn.close()

    except Error:
        pass


def clear_knowledge() -> None:
    """Delete all entries from the knowledge base."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM `option`")
        conn.commit()
        cursor.close()
        conn.close()

    except Error:
        pass


def build_system_prompt() -> str:
    """
    Build a system prompt string from all knowledge base entries.
    Returns empty string if no entries exist.
    """
    entries = get_all_knowledge()
    if not entries:
        return ""

    parts = ["You are a helpful AI assistant. Use the following knowledge base to answer accurately:\n"]
    for entry in reversed(entries):   # oldest first = higher priority
        parts.append(f"### {entry['title']}\n{entry['content']}\n")

    return "\n".join(parts)


# ─────────────────────────────────────────────
#  Chat History API
# ─────────────────────────────────────────────
def save_message(username: str, sender: str, message: str, model: str = "llama3") -> None:
    """
    Persist a single chat message for the given user.
    sender – 'user' or 'bot'
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return

        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, sender, message, model) VALUES (%s, %s, %s, %s)",
            (user_id, sender, message, model)
        )
        conn.commit()
        cursor.close()
        conn.close()

    except Error:
        pass


def load_history(username: str, limit: int = 100) -> list[dict]:
    """
    Return the last `limit` messages for this user, oldest-first.
    Each entry is a dict: { sender, message, model, created_at }
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return []

        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT sender, message, model, created_at
            FROM   chat_history
            WHERE  user_id = %s
            ORDER  BY created_at DESC
            LIMIT  %s
            """,
            (user_id, limit)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return list(reversed(rows))

    except Error:
        return []


def clear_history(username: str) -> None:
    """Delete all chat history for the given user."""
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return

        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

    except Error:
        pass
