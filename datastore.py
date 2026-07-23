import json
import os
import uuid
import datetime

DATA_FILE = "data.json"

class DataStore:
    def __init__(self):
        self.data = {
            "services": [
                {"id": 1, "name": "SEO Optimization"},
                {"id": 2, "name": "Social Media Marketing"},
                {"id": 3, "name": "Pay-Per-Click (PPC)"},
                {"id": 4, "name": "Content Marketing"},
                {"id": 5, "name": "Email Marketing"},
                {"id": 6, "name": "Web Development"},
                {"id": 7, "name": "Graphic Designing"},
                {"id": 8, "name": "Video Editing"}
            ],
            "review_requests": {},
            "reviews": [],
            "analytics": [],
            "settings": {}
        }
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    file_data = json.load(f)
                    # Merge while keeping defaults if keys are missing
                    for k in self.data.keys():
                        if k in file_data:
                            self.data[k] = file_data[k]
            except Exception as e:
                print(f"Error loading {DATA_FILE}: {e}")

    def save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving {DATA_FILE}: {e}")

    # Services
    def get_services(self):
        return self.data["services"]

    def add_service(self, name):
        new_id = max([s["id"] for s in self.data["services"]], default=0) + 1
        service = {"id": new_id, "name": name}
        self.data["services"].append(service)
        self.save()
        return service

    def remove_service(self, service_id):
        self.data["services"] = [s for s in self.data["services"] if s["id"] != service_id]
        self.save()

    # Settings
    def get_setting(self, key, default=""):
        return self.data["settings"].get(key, default)

    def set_setting(self, key, value):
        self.data["settings"][key] = value
        self.save()

    # Review Requests
    def create_review_request(self, client_name, client_industry, google_place_id, allowed_services_ids, phone="0000000000"):
        token = str(uuid.uuid4())
        req = {
            "token": token,
            "client_name": client_name,
            "client_industry": client_industry,
            "google_place_id": google_place_id,
            "allowed_services": allowed_services_ids,
            "phone": phone,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "scanned_at": None,
            "is_active": True
        }
        self.data["review_requests"][token] = req
        self.save()
        return req

    def get_request(self, token):
        return self.data["review_requests"].get(token)

    # Analytics
    def log_scan(self, token):
        req = self.get_request(token)
        if req and not req["scanned_at"]:
            req["scanned_at"] = datetime.datetime.utcnow().isoformat()
        
        self.data["analytics"].append({
            "event_type": "scan",
            "token": token,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        self.save()

    def submit_review(self, token, service_id, rating, email, ai_text):
        new_id = len(self.data["reviews"]) + 1
        review = {
            "id": new_id,
            "token": token,
            "service_id": service_id,
            "rating": rating,
            "email": email,
            "ai_generated_text": ai_text,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        self.data["reviews"].append(review)
        
        self.data["analytics"].append({
            "event_type": "submission",
            "token": token,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        self.save()
        return review

    def validate_email_submission(self, email):
        if not email:
            return True
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        
        for r in self.data["reviews"]:
            if r.get("email") == email:
                created_at = datetime.datetime.fromisoformat(r["created_at"])
                if created_at >= thirty_days_ago:
                    return False
        return True

    # Dashboard Stats
    def get_dashboard_stats(self):
        total_requests = len(self.data["review_requests"])
        total_scans = sum(1 for a in self.data["analytics"] if a["event_type"] == "scan")
        total_submissions = sum(1 for a in self.data["analytics"] if a["event_type"] == "submission")
        conversion_rate = (total_submissions / total_scans * 100) if total_scans > 0 else 0
        
        recent_reviews = self.data["reviews"][-10:]
        recent_reviews.reverse() # newest first
        
        # Hydrate service names
        hydrated_reviews = []
        for r in recent_reviews:
            s_name = next((s["name"] for s in self.data["services"] if s["id"] == r["service_id"]), "Unknown Service")
            r_copy = r.copy()
            r_copy["service_name"] = s_name
            hydrated_reviews.append(r_copy)

        return {
            "total_requests": total_requests,
            "total_scans": total_scans,
            "total_submissions": total_submissions,
            "conversion_rate": conversion_rate,
            "recent_reviews": hydrated_reviews
        }

# Global instance
db = DataStore()
