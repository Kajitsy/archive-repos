import sqlite3
import time
import traceback
from modules.config import DB_FILE
from modules.utils import one_encode_user_id, two_encode_user_id, get_current_time

# --- Database Initialization ---
def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT NOT NULL,
                last_name TEXT, encoded_id TEXT NOT NULL UNIQUE,
                two_encoded_id TEXT NOT NULL UNIQUE, last_seen TEXT NOT NULL,
                messages_sent INTEGER, messages_received INTEGER,
                register_at TEXT NOT NULL
            )
        ''')
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "messages_sent" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN messages_sent INTEGER")
        if "messages_received" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN messages_received INTEGER")
        if "register_at" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN register_at TEXT")
            
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_encoded_id ON users(encoded_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_two_encoded_id ON users(two_encoded_id)')
        # User Targets Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_targets (
                sender_id TEXT PRIMARY KEY, target_id TEXT
            )
        ''')
        # Blacklists Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklists (
                blocker_id TEXT NOT NULL, blocked_id TEXT NOT NULL, blocked_at TEXT,
                last_message_at TEXT, PRIMARY KEY (blocker_id, blocked_id)
            )
        ''')
        # Reply Links Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reply_links (
                recipient_id TEXT NOT NULL, message_id INTEGER NOT NULL,
                original_sender_id TEXT NOT NULL, PRIMARY KEY (recipient_id, message_id)
            )
        ''')
        # User Settings Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY, blacklist_enabled INTEGER DEFAULT 1,
                reset_recipient INTEGER DEFAULT 1, answers INTEGER DEFAULT 1
            )
        ''')        
        conn.commit()
    print("Database initialized successfully.")

# --- Generic DB Executor ---
def _execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Executes a given SQL query with parameters and optional fetching/committing."""
    try:
        # Using check_same_thread=False IS NOT RECOMMENDED for complex apps.
        # Consider using a thread-safe queue or connection pooling for production.
        with sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = None
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            if commit:
                conn.commit()
            return result
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"DATABASE LOCKED. Query: {query}. Retrying...")
            time.sleep(0.2) # Simple backoff
            return _execute_query(query, params, fetchone, fetchall, commit) # Be cautious with recursion depth
        else:
            print(f"Database Operational Error: {e}\nQuery: {query}\nParams: {params}")
            traceback.print_exc()
            return None
    except Exception as e:
        print(f"General Database Error: {e}\nQuery: {query}\nParams: {params}")
        traceback.print_exc()
        return None

# --- User Data Management ---
def update_user_data(user):
    """Saves or updates user info, returns encoded IDs."""
    if not user: return None, None
    user_id = user.id
    encoded_id = one_encode_user_id(user_id)
    two_encoded_id = two_encode_user_id(user_id)
    now = get_current_time()

    if not encoded_id or not two_encoded_id:
        print(f"Error encoding IDs for user {user_id}")
        return None, None
    row = _execute_query(
        f"SELECT messages_sent FROM users WHERE encoded_id = ?",
        (encoded_id,),
        fetchone=True
    )
    if row is None:
        _execute_query(
            """INSERT OR REPLACE INTO users
               (user_id, username, first_name, last_name, encoded_id, two_encoded_id, last_seen, messages_sent, messages_received, register_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, user.username, user.first_name, user.last_name, encoded_id, two_encoded_id, now, 0, 0, now),
            commit=True
        )
    else:
        row2 = _execute_query(
            f"SELECT messages_received FROM users WHERE encoded_id = ?",
            (encoded_id,),
            fetchone=True
        )
        row3 = _execute_query(
            f"SELECT register_at FROM users WHERE encoded_id = ?",
            (encoded_id,),
            fetchone=True
        )

        _execute_query(
            """INSERT OR REPLACE INTO users
               (user_id, username, first_name, last_name, encoded_id, two_encoded_id, last_seen, messages_sent, messages_received, register_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, user.username, user.first_name, user.last_name, encoded_id, two_encoded_id, now, row[0] or 0, row2[0] or 0, row3[0] or now),
            commit=True
        )
    return encoded_id, two_encoded_id

# --- Settings Management ---
def get_user_settings(user_id_encoded):
    """Retrieves user settings or creates default ones if none exist."""
    default_settings = {"blacklist_enabled": True, "reset_recipient": True, "answers": True}
    settings_row = _execute_query("SELECT blacklist_enabled, reset_recipient, answers FROM user_settings WHERE user_id = ?", (user_id_encoded,), fetchone=True)
    if settings_row:
        return {
            "blacklist_enabled": bool(settings_row["blacklist_enabled"]),
            "reset_recipient": bool(settings_row["reset_recipient"]),
            "answers": bool(settings_row["answers"])
        }
    else:
        # Ensure the user exists in the settings table before returning defaults
        _execute_query("INSERT OR IGNORE INTO user_settings (user_id, blacklist_enabled, reset_recipient, answers) VALUES (?, ?, ?, ?)",
                       (user_id_encoded, 1, 1, 1), commit=True)
        return default_settings

def set_user_setting(user_id_encoded, setting_name, value):
    """Updates a specific user setting."""
    db_value = 1 if value else 0
    # Ensure the user row exists first (optional, depends on whether get_user_settings always ran first)
    _execute_query("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id_encoded,), commit=True)
    _execute_query(f"UPDATE user_settings SET {setting_name} = ? WHERE user_id = ?", (db_value, user_id_encoded), commit=True)

# --- Target Management ---
def get_user_target(sender_id_encoded):
    """Gets the current target ID for a sender."""
    result = _execute_query("SELECT target_id FROM user_targets WHERE sender_id = ?", (sender_id_encoded,), fetchone=True)
    return result['target_id'] if result else None

def set_user_target(sender_id_encoded, target_id_encoded):
    """Sets or clears the target ID for a sender."""
    if target_id_encoded:
        _execute_query("INSERT OR REPLACE INTO user_targets (sender_id, target_id) VALUES (?, ?)",
                       (sender_id_encoded, target_id_encoded), commit=True)
    else:
         _execute_query("DELETE FROM user_targets WHERE sender_id = ?", (sender_id_encoded,), commit=True)


# --- Blacklist Management ---
def add_to_blacklist(blocker_id_encoded, blocked_id_two_encoded):
    """Adds a user to the blocker's blacklist."""
    now = get_current_time()
    _execute_query("INSERT OR REPLACE INTO blacklists (blocker_id, blocked_id, blocked_at) VALUES (?, ?, ?)",
                   (blocker_id_encoded, blocked_id_two_encoded, now), commit=True)

def remove_from_blacklist(blocker_id_encoded, blocked_id_two_encoded):
    """Removes a user from the blocker's blacklist."""
    _execute_query("DELETE FROM blacklists WHERE blocker_id = ? AND blocked_id = ?",
                   (blocker_id_encoded, blocked_id_two_encoded), commit=True)

def get_blacklist(blocker_id_encoded):
    """Retrieves the entire blacklist for a user."""
    return _execute_query("SELECT blocked_id, blocked_at, last_message_at FROM blacklists WHERE blocker_id = ? ORDER BY blocked_at DESC",
                          (blocker_id_encoded,), fetchall=True) or []

def is_user_blocked(blocker_id_encoded, blocked_id_two_encoded):
    """Checks if a user is blocked by another user."""
    return _execute_query("SELECT 1 FROM blacklists WHERE blocker_id = ? AND blocked_id = ?",
                          (blocker_id_encoded, blocked_id_two_encoded), fetchone=True) is not None

def update_blacklist_last_message(blocker_id_encoded, blocked_id_two_encoded):
    """Updates the timestamp of the last blocked message attempt."""
    now = get_current_time()
    _execute_query("UPDATE blacklists SET last_message_at = ? WHERE blocker_id = ? AND blocked_id = ?",
                   (now, blocker_id_encoded, blocked_id_two_encoded), commit=True)

# --- Reply Link Management ---
def add_reply_link(recipient_id_encoded, message_id, original_sender_id_encoded):
    """Stores a link between a received message and its original anonymous sender."""
    _execute_query("INSERT OR IGNORE INTO reply_links (recipient_id, message_id, original_sender_id) VALUES (?, ?, ?)",
                   (recipient_id_encoded, message_id, original_sender_id_encoded), commit=True)

def get_reply_sender(recipient_id_encoded, message_id):
    """Retrieves the original sender ID for a replied-to message."""
    result = _execute_query("SELECT original_sender_id FROM reply_links WHERE recipient_id = ? AND message_id = ?",
                            (recipient_id_encoded, message_id), fetchone=True)
    return result['original_sender_id'] if result else None

# --- Message Count Tracking ---
def increment_message_count(user_id_encoded, sent=True):
    """Increments the sent or received message count for a user."""
    column = "messages_sent" if sent else "messages_received"
    row = _execute_query(
        f"SELECT {column} FROM users WHERE encoded_id = ?",
        (user_id_encoded,),
        fetchone=True
    )

    if row is None:
        messages_sent = 1 if sent else 0
        messages_received = 1 if not sent else 0

        _execute_query(
            "INSERT INTO users (encoded_id, messages_sent, messages_received) VALUES (?, ?, ?)",
            (user_id_encoded, messages_sent, messages_received),
            commit=True
        )
    else:
        current_value = row[0] or 0
        new_value = current_value + 1

        _execute_query(
            f"UPDATE users SET {column} = ? WHERE encoded_id = ?",
            (new_value, user_id_encoded),
            commit=True
        )
        
def get_message_count(user_id_encoded, sent=True):
    """Increments the sent or received message count for a user."""
    column = "messages_sent" if sent else "messages_received"
    row = _execute_query(
        f"SELECT {column} FROM users WHERE encoded_id = ?",
        (user_id_encoded,),
        fetchone=True
    )

    return row[0] if row else 0

def get_user_registration_date(user_id_encoded):
    """Retrieves the registration date for a user."""
    row = _execute_query(
        "SELECT register_at FROM users WHERE encoded_id = ?",
        (user_id_encoded,),
        fetchone=True
    )
    return row[0] if row else None