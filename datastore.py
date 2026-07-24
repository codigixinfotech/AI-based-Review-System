import json
import os
import datetime
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

class DataStore:
    def __init__(self):
        self.init_db()

    def get_connection(self):
        try:
            db_port = int(os.getenv("DB_PORT", "3306"))
        except ValueError:
            db_port = 3306
        return pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=db_port,
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root"),
            database=os.getenv("DB_NAME", "review_qr_db"),
            autocommit=True
        )

    def init_db(self):
        # 1. Connect to MySQL server without database to create the DB if missing
        try:
            db_port = int(os.getenv("DB_PORT", "3306"))
        except ValueError:
            db_port = 3306
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=db_port,
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", "root")
            )
            cursor = conn.cursor()
            db_name = os.getenv("DB_NAME", "review_qr_db")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            cursor.close()
            conn.close()
        except pymysql.Error as err:
            print(f"Failed to connect to MySQL or create DB: {err}")
            raise err

        # 2. Reconnect directly to the database and create tables
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key_name VARCHAR(255) PRIMARY KEY,
                value_text TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_requests (
                token VARCHAR(36) PRIMARY KEY,
                client_name VARCHAR(255) NOT NULL,
                client_industry VARCHAR(255),
                google_place_id VARCHAR(255),
                allowed_services TEXT,
                phone VARCHAR(20) DEFAULT '0000000000',
                created_at DATETIME,
                scanned_at DATETIME,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                token VARCHAR(36),
                service_id INT,
                rating VARCHAR(20),
                email VARCHAR(255),
                ai_generated_text TEXT,
                created_at DATETIME,
                FOREIGN KEY (token) REFERENCES review_requests(token) ON DELETE SET NULL,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(50),
                token VARCHAR(36),
                timestamp DATETIME
            )
        """)
        
        # Populate default services if database is completely empty
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            default_services = [
                "SEO Optimization", "Social Media Marketing", "Pay-Per-Click (PPC)",
                "Content Marketing", "Email Marketing", "Web Development",
                "Graphic Designing", "Video Editing"
            ]
            for s in default_services:
                cursor.execute("INSERT INTO services (name) VALUES (%s)", (s,))
        
        cursor.close()
        conn.close()

        # 3. Handle data migration from data.json if it exists
        if os.path.exists("data.json"):
            try:
                with open("data.json", "r") as f:
                    old_data = json.load(f)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Migrate settings
                for k, v in old_data.get("settings", {}).items():
                    cursor.execute("INSERT IGNORE INTO settings (key_name, value_text) VALUES (%s, %s)", (k, str(v)))
                
                # Migrate services
                for s in old_data.get("services", []):
                    cursor.execute("INSERT IGNORE INTO services (id, name) VALUES (%s, %s)", (s["id"], s["name"]))
                
                # Migrate review requests
                for t, r in old_data.get("review_requests", {}).items():
                    created_at = datetime.datetime.fromisoformat(r["created_at"]) if r.get("created_at") else None
                    scanned_at = datetime.datetime.fromisoformat(r["scanned_at"]) if r.get("scanned_at") else None
                    cursor.execute("""
                        INSERT IGNORE INTO review_requests 
                        (token, client_name, client_industry, google_place_id, allowed_services, phone, created_at, scanned_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        r["token"], r["client_name"], r.get("client_industry", ""), r.get("google_place_id", ""),
                        r.get("allowed_services", ""), r.get("phone", "0000000000"), created_at, scanned_at, r.get("is_active", True)
                    ))
                
                # Migrate reviews
                for r in old_data.get("reviews", []):
                    created_at = datetime.datetime.fromisoformat(r["created_at"]) if r.get("created_at") else None
                    cursor.execute("""
                        INSERT IGNORE INTO reviews (id, token, service_id, rating, email, ai_generated_text, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        r["id"], r["token"], r["service_id"], r["rating"], r.get("email", ""), r.get("ai_generated_text", ""), created_at
                    ))
                
                # Migrate analytics
                for a in old_data.get("analytics", []):
                    timestamp = datetime.datetime.fromisoformat(a["timestamp"]) if a.get("timestamp") else None
                    cursor.execute("""
                        INSERT IGNORE INTO analytics (event_type, token, timestamp)
                        VALUES (%s, %s, %s)
                    """, (a["event_type"], a.get("token", ""), timestamp))
                
                cursor.close()
                conn.close()
                
                # Rename the file so we don't migrate it again
                os.rename("data.json", "data.json.bak")
                print("Successfully migrated data.json to MySQL Database.")
            except Exception as ex:
                print(f"Data migration warning: {ex}")

    # Services
    def get_services(self):
        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT id, name FROM services")
        services = cursor.fetchall()
        cursor.close()
        conn.close()
        return services

    def add_service(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO services (name) VALUES (%s)", (name,))
            new_id = cursor.lastrowid
            service = {"id": new_id, "name": name}
        except pymysql.Error as err:
            print(f"Error adding service: {err}")
            service = None
        finally:
            cursor.close()
            conn.close()
        return service

    def remove_service(self, service_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
        cursor.close()
        conn.close()

    # Settings
    def get_setting(self, key, default=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value_text FROM settings WHERE key_name = %s", (key,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key_name, value_text) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value_text = %s
        """, (key, str(value), str(value)))
        cursor.close()
        conn.close()

    # Review Requests
    def create_review_request(self, client_name, client_industry, google_place_id, allowed_services_ids, phone="0000000000"):
        import uuid
        token = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO review_requests (token, client_name, client_industry, google_place_id, allowed_services, phone, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (token, client_name, client_industry, google_place_id, allowed_services_ids, phone, created_at))
        cursor.close()
        conn.close()
        
        return {
            "token": token,
            "client_name": client_name,
            "client_industry": client_industry,
            "google_place_id": google_place_id,
            "allowed_services": allowed_services_ids,
            "phone": phone,
            "created_at": created_at,
            "scanned_at": None,
            "is_active": True
        }

    def get_request(self, token):
        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT token, client_name, client_industry, google_place_id, allowed_services, phone, created_at, scanned_at, is_active FROM review_requests WHERE token = %s", (token,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            # Format datetime columns to string ISO format
            if isinstance(row["created_at"], datetime.datetime):
                row["created_at"] = row["created_at"].isoformat()
            if isinstance(row["scanned_at"], datetime.datetime):
                row["scanned_at"] = row["scanned_at"].isoformat()
        return row

    # Analytics
    def log_scan(self, token):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Update request scan timestamp if not scanned before
        cursor.execute("SELECT scanned_at FROM review_requests WHERE token = %s", (token,))
        row = cursor.fetchone()
        if row and row[0] is None:
            cursor.execute("UPDATE review_requests SET scanned_at = %s WHERE token = %s", (now, token))
        
        # 2. Append scan event to analytics
        cursor.execute("INSERT INTO analytics (event_type, token, timestamp) VALUES (%s, %s, %s)", ("scan", token, now))
        cursor.close()
        conn.close()

    def submit_review(self, token, service_id, rating, email, ai_text):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Insert review
        cursor.execute("""
            INSERT INTO reviews (token, service_id, rating, email, ai_generated_text, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (token, service_id, rating, email, ai_text, now))
        
        # 2. Insert analytics event
        cursor.execute("INSERT INTO analytics (event_type, token, timestamp) VALUES (%s, %s, %s)", ("submission", token, now))
        
        cursor.close()
        conn.close()

    def validate_email_submission(self, email):
        if not email:
            return True
            
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if the email submitted in the last 30 days
        thirty_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE email = %s AND created_at >= %s", (email, thirty_days_ago))
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return count == 0

    # Dashboard Stats
    def get_dashboard_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM review_requests")
        total_requests = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analytics WHERE event_type = 'scan'")
        total_scans = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analytics WHERE event_type = 'submission'")
        total_submissions = cursor.fetchone()[0]
        
        conversion_rate = (total_submissions / total_scans * 100) if total_scans > 0 else 0
        cursor.close()
        
        # Fetch 10 most recent reviews
        cursor_dict = conn.cursor(pymysql.cursors.DictCursor)
        cursor_dict.execute("""
            SELECT r.id, r.token, r.service_id, r.rating, r.email, r.ai_generated_text, r.created_at, s.name as service_name
            FROM reviews r
            LEFT JOIN services s ON r.service_id = s.id
            ORDER BY r.created_at DESC LIMIT 10
        """)
        recent_reviews = cursor_dict.fetchall()
        cursor_dict.close()
        conn.close()
        
        # Format dates to string
        for r in recent_reviews:
            if isinstance(r["created_at"], datetime.datetime):
                r["created_at"] = r["created_at"].isoformat()
        
        return {
            "total_requests": total_requests,
            "total_scans": total_scans,
            "total_submissions": total_submissions,
            "conversion_rate": conversion_rate,
            "recent_reviews": recent_reviews
        }

# Global instance
db = DataStore()
