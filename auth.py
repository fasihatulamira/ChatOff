
# AUTHENTICATION + CHAT HISTORY + KNOWLEDGE BASE
# Handles user auth, chat history, and the knowledge base (option table) in MySQL (chatdb).

import os
import uuid
import mysql.connector
from mysql.connector import Error
from paths import load_env
from password_utils import hash_password, verify_password, is_bcrypt_hash

load_env()


# ─────────────────────────────────────────────
#  Database connection settings
# ─────────────────────────────────────────────
def _get_connection():
    """Open and return a connection to the MySQL database."""
    config = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "user":     os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_DATABASE", "chatdb"),
    }
    return mysql.connector.connect(**config)


def test_db_connection(host, user, password, database) -> tuple[bool, str]:
    """Test a database connection with the provided credentials."""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connection_timeout=5
        )
        conn.close()
        return True, "Connection successful!"
    except Error as e:
        return False, str(e)


_REQUIRED_TABLES = ("users", "chat_history", "chat_topics", "option")


def check_database() -> tuple[bool, str]:
    """
    Verify MySQL is reachable and all required tables exist.
    Returns (True, "OK") or (False, error_message).
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = {row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        missing = [t for t in _REQUIRED_TABLES if t not in tables]
        if missing:
            return (
                False,
                "Missing database tables: "
                + ", ".join(missing)
                + ". Import schema.sql into your MySQL chatdb database.",
            )
        return True, "OK"
    except Error as e:
        return False, f"Cannot connect to MySQL: {e}"




# ─────────────────────────────────────────────
#  Schema migration (Phase 4)
# ─────────────────────────────────────────────
def ensure_schema() -> None:
    """Apply idempotent schema upgrades for existing databases."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM users LIKE 'must_change_password'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users MODIFY password VARCHAR(255) NOT NULL")
            cursor.execute(
                "ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0"
            )
            cursor.execute(
                "UPDATE users SET must_change_password = 1 WHERE username = 'admin'"
            )
            conn.commit()

        cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'prompt_text'")
        prompt_col = cursor.fetchone()
        if prompt_col:
            col_type = str(prompt_col[1]).upper()
            if "MEDIUMTEXT" not in col_type and "LONGTEXT" not in col_type:
                cursor.execute(
                    "ALTER TABLE chat_history "
                    "MODIFY prompt_text MEDIUMTEXT NOT NULL, "
                    "MODIFY response_text MEDIUMTEXT NOT NULL"
                )
                conn.commit()

        cursor.close()
        conn.close()
    except Error as e:
        print(f"Schema migration note: {e}")


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────
def _upgrade_password_hash(username: str, password: str) -> None:
    """Migrate a legacy SHA-256 hash to bcrypt after successful login."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = %s WHERE username = %s",
            (hash_password(password), username.strip().lower()),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Error:
        pass


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
            "INSERT INTO users (fullname, username, email, password, must_change_password) VALUES (%s, %s, %s, %s, 0)",
            (full_name.strip(), username.strip().lower(), email.strip().lower(), hash_password(password)),
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


def is_admin_user(username: str) -> bool:
    return username.strip().lower() == "admin"


def login_user(username: str, password: str) -> tuple[bool, str | dict]:
    """
    Validate login credentials.
    On success returns (True, {"full_name": ..., "must_change_password": bool}).
    On failure returns (False, error_message).
    """
    if not username.strip() or not password.strip():
        return False, "Username and password are required."

    uname = username.strip().lower()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fullname, password, must_change_password FROM users WHERE username = %s",
            (uname,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

    except Error as e:
        return False, f"Database error: {e}"

    if row is None:
        return False, "No account found with that username."

    full_name, stored_hash, must_change_flag = row
    if not verify_password(password, stored_hash):
        return False, "Incorrect password. Please try again."

    if not is_bcrypt_hash(stored_hash):
        _upgrade_password_hash(uname, password)

    must_change = bool(must_change_flag)
    if uname == "admin" and password == "admin123":
        must_change = True

    return True, {"full_name": full_name, "must_change_password": must_change}


def change_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
    """Update password after verifying the current one."""
    if not current_password.strip() or not new_password.strip():
        return False, "All fields are required."
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."
    if new_password == "admin123":
        return False, "Please choose a password other than the default."

    uname = username.strip().lower()

    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (uname,))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            conn.close()
            return False, "User not found."

        stored_hash = row[0]
        if not verify_password(current_password, stored_hash):
            cursor.close()
            conn.close()
            return False, "Current password is incorrect."

        cursor.execute(
            "UPDATE users SET password = %s, must_change_password = 0 WHERE username = %s",
            (hash_password(new_password), uname),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "success"

    except Error as e:
        return False, f"Database error: {e}"


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
def save_topic(parent_id: int | None, topic_name: str, reply_message: str = "", pdf_source: str | None = None) -> int:
    """
    Save a new topic (or sub-topic) to chat_topics.
    Returns the newly generated ID.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_topics (parent_id, topic_name, reply_message, pdf_source) VALUES (%s, %s, %s, %s)",
            (parent_id, topic_name.strip(), reply_message.strip(), pdf_source.strip() if pdf_source else None)
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

def get_topic_by_id(topic_id: int) -> dict:
    """Return a single topic by its ID."""
    try:
        conn = _get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chat_topics WHERE id = %s", (topic_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row
    except Error:
        return None

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
    """Delete a topic and all of its sub-topics."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_topics WHERE parent_id = %s", (topic_id,))
        cursor.execute("DELETE FROM chat_topics WHERE id = %s", (topic_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error:
        return False

def update_topic(topic_id: int, topic_name: str, reply_message: str, pdf_source: str | None = None) -> bool:
    """Update a topic's name, reply message, and pdf_source."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_topics SET topic_name = %s, reply_message = %s, pdf_source = %s WHERE id = %s",
            (topic_name.strip(), reply_message.strip(), pdf_source.strip() if pdf_source else None, topic_id)
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
def save_message(username: str, session_id: str, prompt_text: str, response_text: str) -> tuple[bool, str | None]:
    """
    Persist a single chat interaction for the given user and session.
    Returns (True, None) on success or (False, error_message) on failure.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return False, f"User '{username}' was not found in the database."

        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT session_title FROM chat_history WHERE session_id = %s LIMIT 1", (session_id,))
        row = cursor.fetchone()

        if row:
            session_title = row[0]
        else:
            # Title is VARCHAR(255); use only the visible user question, not RAG context.
            preview = (prompt_text or "").strip()
            session_title = preview[:50] + ("..." if len(preview) > 50 else "")

        session_title = (session_title or "Chat")[:255]

        cursor.execute(
            "INSERT INTO chat_history (user_id, session_id, session_title, prompt_text, response_text) VALUES (%s, %s, %s, %s, %s)",
            (user_id, session_id, session_title, prompt_text, response_text)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, None

    except Error as e:
        return False, str(e)


def get_user_sessions(username: str) -> tuple[list[dict], str | None]:
    """
    Return unique sessions for this user with their title and latest message date.
    Returns (sessions, None) or ([], error_message) on failure.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return [], f"User '{username}' was not found in the database."

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
        return rows, None
    except Error as e:
        return [], str(e)


def load_session_messages(username: str, session_id: str) -> tuple[list[dict], str | None]:
    """
    Load all messages for a specific session.
    Returns (messages, None) or ([], error_message) on failure.
    """
    try:
        user_id = _get_user_id(username)
        if user_id is None:
            return [], f"User '{username}' was not found in the database."

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
        return rows, None
    except Error as e:
        return [], str(e)


def update_session_title(session_id: str, new_title: str) -> bool:
    """
    Update the title for a specific session.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_history SET session_title = %s WHERE session_id = %s",
            (new_title.strip()[:255], session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error:
        return False



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

    try:
        if _get_user_id(admin_user) is not None:
            return
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (fullname, username, email, password, must_change_password) VALUES (%s, %s, %s, %s, 1)",
            ("Administrator", admin_user, "admin@chatoff.local", hash_password(admin_pass)),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Error:
        pass

ensure_schema()
_setup_default_admin()
