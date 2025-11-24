import sqlite3
import hashlib
import os
import json
from datetime import datetime

DB_NAME = "jobs.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        target_email TEXT,
        subscription_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Add subscription_enabled column if it doesn't exist (migration)
    try:
        c.execute("ALTER TABLE users ADD COLUMN subscription_enabled INTEGER DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create Profiles Table
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        cv_text TEXT,
        structured_profile TEXT,
        search_keywords TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # Create Saved Jobs Table (New Schema with user_id)
    # Check if table exists and has user_id, if not drop and recreate (simplest for dev)
    try:
        c.execute("SELECT user_id FROM saved_jobs LIMIT 1")
    except sqlite3.OperationalError:
        # Table might not exist or old schema
        c.execute("DROP TABLE IF EXISTS saved_jobs")
        
    c.execute('''CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT,
        company TEXT,
        score INTEGER,
        url TEXT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, url)
    )''')
    
    conn.commit()
    conn.close()

# --- User Management ---

def hash_password(password):
    # Simple SHA-256 hashing with a salt would be better, but for this scope:
    # We'll use a fixed salt for simplicity or just hash. 
    # Let's use a basic salt.
    salt = "jobhunter_salt_"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_user(email, password, target_email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        pwd_hash = hash_password(password)
        c.execute("INSERT INTO users (email, password_hash, target_email) VALUES (?, ?, ?)", 
                  (email, pwd_hash, target_email))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None # Email already exists
    finally:
        conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def verify_password(email, password):
    user = get_user_by_email(email)
    if user and user['password_hash'] == hash_password(password):
        return user
    return None

# --- Profile Management ---

def save_profile(user_id, cv_text, profile_json, keywords):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check if profile exists
    c.execute("SELECT id FROM profiles WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    
    profile_str = json.dumps(profile_json)
    keywords_str = json.dumps(keywords)
    
    if exists:
        c.execute('''UPDATE profiles 
                     SET cv_text = ?, structured_profile = ?, search_keywords = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE user_id = ?''', 
                  (cv_text, profile_str, keywords_str, user_id))
    else:
        c.execute('''INSERT INTO profiles (user_id, cv_text, structured_profile, search_keywords) 
                     VALUES (?, ?, ?, ?)''', 
                  (user_id, cv_text, profile_str, keywords_str))
    
    conn.commit()
    conn.close()

def get_profile(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        data = dict(row)
        # Parse JSON fields
        try:
            data['structured_profile'] = json.loads(data['structured_profile'])
        except: data['structured_profile'] = {}
        
        try:
            data['search_keywords'] = json.loads(data['search_keywords'])
        except: data['search_keywords'] = []
        
        return data
    return None

# --- Job Management ---

def save_job(user_id, title, company, score, url):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO saved_jobs (user_id, title, company, score, url) VALUES (?, ?, ?, ?, ?)", 
                  (user_id, title, company, score, url))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_saved_jobs(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM saved_jobs WHERE user_id = ? ORDER BY date_added DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_job(job_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM saved_jobs WHERE id = ? AND user_id = ?", (job_id, user_id))
    conn.commit()
    conn.close()

# --- Admin Functions ---

def get_all_users():
    """Get all users with their profile status."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get users with profile status
    c.execute('''
        SELECT u.*, 
               CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as has_profile,
               p.updated_at as profile_updated
        FROM users u
        LEFT JOIN profiles p ON u.id = p.user_id
        ORDER BY u.created_at DESC
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def toggle_subscription(user_id, enabled):
    """Enable or disable email subscription for a user."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription_enabled = ? WHERE id = ?", (1 if enabled else 0, user_id))
    conn.commit()
    conn.close()

def get_user_stats():
    """Get user statistics."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE subscription_enabled = 1")
    active_subscriptions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM profiles")
    users_with_profiles = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "users_with_profiles": users_with_profiles
    }
