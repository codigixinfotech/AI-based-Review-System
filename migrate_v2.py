import sqlite3
import os

db_path = "review_qr.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE review_requests ADD COLUMN client_industry TEXT;")
        print("Column client_industry added successfully.")
    except sqlite3.OperationalError:
        print("Column client_industry already exists.")
    conn.commit()
    conn.close()
else:
    print("Database not found. It will be created with new schema on next run.")
