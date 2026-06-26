import sqlite3
import os

DB_NAME = "infra_tracking.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email email UNIQUE, password TEXT)''')
    
    # Create Uploads Table to store metadata for PDF generation
    c.execute('''CREATE TABLE IF NOT EXISTS uploads
                 (uid TEXT PRIMARY KEY, filename TEXT, structure_type TEXT, 
                  percent_complete REAL, damages TEXT, image_path TEXT)''')
                  
    conn.commit()
    conn.close()
    
    # Ensure static directory exists for image storage
    os.makedirs("static", exist_ok=True)

if __name__ == "__main__":
    init_db()