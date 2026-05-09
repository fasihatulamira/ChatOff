
# ===== AUTHENTICATION + CHAT HISTORY + KNOWLEDGE BASE MODULE =====
# Handles user auth, chat history, and the knowledge base (option table) in MySQL (chatdb).

import os
import hashlib
import uuid
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
#  Topics Builder API
# ─────────────────────────────────────────────
def save_topic(parent_id: int | None, topic_name: str, reply_message: str = "") -> int:
    """
    Save a new topic (or sub-topic) to chat_topics.
    Returns the newly generated ID.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_topics (parent_id, topic_name, reply_message) VALUES (%s, %s, %s)",
            (parent_id, topic_name.strip(), reply_message.strip())
        )
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id
    except Error as e:
        print(f"Error saving topic: {e}")
        return -1

def get_main_topics() -> list[dict]:
    """Return all main topics (parent_id IS NULL)."""
    try:
        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chat_topics WHERE parent_id IS NULL ORDER BY created_at ASC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error:
        return []

def get_sub_topics(parent_id: int) -> list[dict]:
    """Return sub-topics for a specific parent topic."""
    try:
        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chat_topics WHERE parent_id = %s ORDER BY created_at ASC", (parent_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error:
        return []

def get_all_topics() -> list[dict]:
    """Return all topics for management."""
    try:
        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch all topics, left join to get parent name if it exists
        cursor.execute("""
            SELECT t1.*, t2.topic_name as parent_name 
            FROM chat_topics t1 
            LEFT JOIN chat_topics t2 ON t1.parent_id = t2.id 
            ORDER BY t1.parent_id ASC, t1.created_at ASC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error:
        return []

def delete_topic(topic_id: int) -> bool:
    """Delete a topic (and cascade its subtopics)."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_topics WHERE id = %s", (topic_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error:
        return False

def update_topic(topic_id: int, topic_name: str, reply_message: str) -> bool:
    """Update a topic's name and reply message."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_topics SET topic_name = %s, reply_message = %s WHERE id = %s",
            (topic_name.strip(), reply_message.strip(), topic_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error:
        return False


# ─────────────────────────────────────────────
#  Chat History API
# ─────────────────────────────────────────────
def save_message(username: str, session_id: str, prompt_text: str, response_text: str) -> None:
    """
    Persist a single chat interaction for the given user and session.
    Automatically generates a session title if it's the first message.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return

        conn = _get_connection()
        cursor = conn.cursor()

        # Check if this session already has a title
        cursor.execute("SELECT session_title FROM chat_history WHERE session_id = %s LIMIT 1", (session_id,))
        row = cursor.fetchone()
        
        if row:
            session_title = row[0]
        else:
            # Generate title from the first 50 chars of the first message
            session_title = prompt_text[:50] + ("..." if len(prompt_text) > 50 else "")

        cursor.execute(
            "INSERT INTO chat_history (user_id, session_id, session_title, prompt_text, response_text) VALUES (%s, %s, %s, %s, %s)",
            (user_id, session_id, session_title, prompt_text, response_text)
        )
        conn.commit()
        cursor.close()
        conn.close()

    except Error:
        pass


def get_user_sessions(username: str) -> list[dict]:
    """
    Return unique sessions for this user with their title and latest message date.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return []

        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT session_id, session_title, MAX(created_at) as last_active
            FROM   chat_history
            WHERE  user_id = %s
            GROUP  BY session_id, session_title
            ORDER  BY last_active DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error:
        return []


def load_session_messages(username: str, session_id: str) -> list[dict]:
    """
    Load all messages for a specific session.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return []

        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT prompt_text, response_text, created_at
            FROM   chat_history
            WHERE  user_id = %s AND session_id = %s
            ORDER  BY created_at ASC
            """,
            (user_id, session_id)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error:
        return []


def update_session_title(session_id: str, new_title: str) -> bool:
    """
    Update the title for a specific session.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_history SET session_title = %s WHERE session_id = %s",
            (new_title.strip(), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error:
        return False


def load_history(username: str, limit: int = 100) -> list[dict]:
    """
    Deprecated: Use load_session_messages. 
    Remaining for backward compatibility if needed.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return []

        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT prompt_text, response_text, created_at
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


def _setup_default_admin():
    """Create a default admin account if it does not already exist."""
    admin_user = "admin"
    admin_pass = "admin123"
    
    # Check if admin already exists
    if _get_user_id(admin_user) is None:
        try:
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (fullname, username, email, password) VALUES (%s, %s, %s, %s)",
                ("Administrator", admin_user, "admin@chatoff.local", _hash_password(admin_pass))
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Error:
            pass

# Run this once when the module is imported
_setup_default_admin()
