import sqlite3
import os

DB_FILE = "bot_memory.db"

def reset_db():
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print(f"Items before reset: {cursor.execute('SELECT count(*) FROM seen_items').fetchone()[0]}")
        cursor.execute('DELETE FROM seen_items')
        conn.commit()
        print("✅ Database cleared. The bot will now re-process and re-send all recent items.")
        conn.close()
    else:
        print("Database not found. Nothing to reset.")

if __name__ == "__main__":
    reset_db()
