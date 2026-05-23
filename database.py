import sqlite3
from datetime import datetime

# ============================================
# DATABASE SETUP
# ============================================

DB_NAME = "api_keys.db"

def init_db():
    """Create the database and tables if they don't exist"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            plan TEXT DEFAULT 'basic',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create API keys table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key TEXT PRIMARY KEY,
            user_id TEXT,
            plan TEXT DEFAULT 'basic',
            requests_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def add_user(user_id: str, username: str, plan: str = "basic"):
    """Add a new user to the database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (user_id, username, plan) VALUES (?, ?, ?)",
            (user_id, username, plan)
        )
        conn.commit()
        print(f"✅ User {username} added")
    except sqlite3.IntegrityError:
        print(f"⚠️ User {username} already exists")
    finally:
        conn.close()

def save_api_key(api_key: str, user_id: str, plan: str = "basic"):
    """Save an API key to the database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO api_keys (key, user_id, plan) VALUES (?, ?, ?)",
        (api_key, user_id, plan)
    )
    conn.commit()
    conn.close()
    print(f"✅ API key saved for user {user_id}")

def get_api_key_info(api_key: str):
    """Get information about an API key"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, plan, requests_used, is_active FROM api_keys WHERE key = ?",
        (api_key,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "user_id": result[0],
            "plan": result[1],
            "requests_used": result[2],
            "is_active": bool(result[3])
        }
    return None

def increment_requests(api_key: str):
    """Increment the request count for an API key"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE api_keys SET requests_used = requests_used + 1, last_used = ? WHERE key = ?",
        (datetime.now(), api_key)
    )
    conn.commit()
    conn.close()

def list_all_keys():
    """List all API keys (for admin)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT k.key, u.username, k.plan, k.requests_used, k.is_active 
        FROM api_keys k
        JOIN users u ON k.user_id = u.user_id
    """)
    results = cursor.fetchall()
    conn.close()
    return results

def revoke_key(api_key: str):
    """Revoke (deactivate) an API key"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET is_active = 0 WHERE key = ?", (api_key,))
    conn.commit()
    conn.close()
    print(f"✅ API key revoked")

# ============================================
# INITIALIZE DATABASE WITH YOUR API KEY
# ============================================

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    # Add your user account
    add_user("test_user", "test_user", "basic")
    
    # Your API key
    YOUR_API_KEY = "sk-r_2cjYUkxCbCnvwhQDYrnatIUobO6M8xVeyXKuW_Bcc"
    
    # Save your API key to the database
    save_api_key(YOUR_API_KEY, "test_user", "basic")
    
    # Verify it was saved
    key_info = get_api_key_info(YOUR_API_KEY)
    if key_info:
        print(f"\n✅ API Key verified!")
        print(f"   User: {key_info['user_id']}")
        print(f"   Plan: {key_info['plan']}")
        print(f"   Requests used: {key_info['requests_used']}")
        print(f"   Active: {key_info['is_active']}")
    
    # List all keys
    print("\n📋 All API Keys:")
    for key in list_all_keys():
        print(f"   - {key[0][:20]}... | User: {key[1]} | Plan: {key[2]} | Used: {key[3]} | Active: {key[4]}")