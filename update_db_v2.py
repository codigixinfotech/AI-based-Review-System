from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE review_requests ADD COLUMN allowed_services VARCHAR"))
        conn.commit()
        print("Column allowed_services added successfully.")
    except Exception as e:
        print(f"Error or column already exists: {e}")
