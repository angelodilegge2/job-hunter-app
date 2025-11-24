import sqlite3
from datetime import datetime

DB_NAME = "jobs.db"

def init_db():
    """Initialize the database and create the saved_jobs table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            score INTEGER,
            url TEXT,
            date_added TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_job(title, company, score, url):
    """Save a job to the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if already exists to avoid duplicates (optional but good UX)
    c.execute("SELECT id FROM saved_jobs WHERE url = ?", (url,))
    if c.fetchone():
        conn.close()
        return False # Already saved

    c.execute('''
        INSERT INTO saved_jobs (title, company, score, url, date_added)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, company, score, url, date_added))
    conn.commit()
    conn.close()
    return True

def get_saved_jobs():
    """Retrieve all saved jobs."""
    conn = sqlite3.connect(DB_NAME)
    # Return dictionary objects for easier pandas conversion
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM saved_jobs ORDER BY date_added DESC")
    rows = c.fetchall()
    conn.close()
    
    jobs = []
    for row in rows:
        jobs.append(dict(row))
    return jobs

def delete_job(job_id):
    """Delete a job by ID."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM saved_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
