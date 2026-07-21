from app.database import SessionLocal
from app.models import Setting

db = SessionLocal()
s = db.query(Setting).filter(Setting.key == "google_place_id").first()
if s:
    s.value = "ChIJreArw1q5wjsRqfAHZXdYqnk"
else:
    db.add(Setting(key="google_place_id", value="ChIJreArw1q5wjsRqfAHZXdYqnk"))
db.commit()
db.close()
print("Place ID updated successfully.")
