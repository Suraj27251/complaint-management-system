import sqlite3
import os

# Create the folder if it doesn't exist
os.makedirs("database", exist_ok=True)

# Connect and create DB
conn = sqlite3.connect('database/complaints.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT,
    name TEXT,
    phone TEXT,
    issue TEXT,
    status TEXT,
    timestamp TEXT
)
''')

conn.commit()
conn.close()
print("✅ Database created at database/complaints.db")
