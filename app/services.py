import qrcode
import io
import os
import datetime
import uuid
import math
from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

from PIL import Image, ImageDraw, ImageFont

class QRService:
    @staticmethod
    def generate_qr_img(token: str, base_url: str):
        url = f"{base_url}/r/{token}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H, # Higher correction for cards
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return qr.make_image(fill_color="#00358E", back_color="white").convert("RGB") # Matching blue

    @staticmethod
    def generate_qr_bytes(token: str, base_url: str) -> bytes:
        img = QRService.generate_qr_img(token, base_url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

class CardService:
    @staticmethod
    def _draw_star(draw, x, y, size, fill):
        # Helper to draw a star manually
        points = []
        for i in range(10):
            angle = i * 36
            r = size if i % 2 == 0 else size / 2.5
            px = x + r * math.cos(math.radians(angle - 90))
            py = y + r * math.sin(math.radians(angle - 90))
            points.append((px, py))
        draw.polygon(points, fill=fill)

    @staticmethod
    def generate_card(token: str, base_url: str, company_name: str = "Codigix Infotech", industry: str = "Marketing Agency", phone: str = "7066556768") -> bytes:
        # High resolution settings for print quality
        width, height = 1000, 1500
        bg_color = (255, 255, 255)
        blue_primary = (0, 48, 120) 
        blue_light = (245, 248, 255)
        grey_text = (80, 80, 80)
        gold = (255, 193, 7)
        
        # Create canvas
        card = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(card)
        
        # 1. Subtle Background Elements
        # Bottom Blue Gradient/Shape
        draw.rectangle([0, 1200, width, height], fill=blue_primary)
        # Soft curve at the top of the blue section
        draw.ellipse([-200, 1100, width+200, 1350], fill=blue_primary)
        
        # 2. Fonts
        try:
            # Using standard system fonts usually available on Windows
            font_path_bold = "arialbd.ttf"
            font_path_reg = "arial.ttf"
            title_font = ImageFont.truetype(font_path_bold, 72)
            subtitle_font = ImageFont.truetype(font_path_reg, 42)
            header_font = ImageFont.truetype(font_path_bold, 64)
            footer_text_font = ImageFont.truetype(font_path_reg, 42)
            phone_font = ImageFont.truetype(font_path_bold, 58)
        except:
            title_font = subtitle_font = header_font = footer_text_font = phone_font = ImageFont.load_default()

        # 3. Header Section
        draw.text((width//2, 180), company_name, fill=blue_primary, font=title_font, anchor="mm")
        draw.text((width//2, 260), f"- {industry}", fill=grey_text, font=subtitle_font, anchor="mm")
        
        # 4. CTA Section
        draw.text((width//2, 400), "We Value Your Feedback", fill=blue_primary, font=header_font, anchor="mm")
        draw.text((width//2, 480), "Scan the QR code to share your experience", fill=grey_text, font=subtitle_font, anchor="mm")
        
        # 5. QR Code Area (White Rounded Box with Shadow Effect)
        qr_box_size = 650
        qr_box_x = (width - qr_box_size) // 2
        qr_box_y = 580
        
        # Draw soft shadow (simulated with grey rectangles)
        for i in range(1, 15):
            alpha = 15 - i
            draw.rounded_rectangle([qr_box_x-i, qr_box_y-i, qr_box_x+qr_box_size+i, qr_box_y+qr_box_size+i], radius=60, outline=(220+i, 220+i, 220+i), width=2)

        draw.rounded_rectangle([qr_box_x, qr_box_y, qr_box_x+qr_box_size, qr_box_y+qr_box_size], radius=60, fill="white")
        
        # QR Code itself
        qr_img = QRService.generate_qr_img(token, base_url)
        qr_img = qr_img.resize((500, 500))
        card.paste(qr_img, (qr_box_x + (qr_box_size - 500)//2, qr_box_y + (qr_box_size - 500)//2))
        
        # 6. Bottom Message
        draw.text((width//2, 1320), "Your feedback helps us improve", fill="white", font=footer_text_font, anchor="mm")
        
        # 7. Contact Pill
        pill_w, pill_h = 580, 100
        pill_x = (width - pill_w) // 2
        pill_y = 1380
        draw.rounded_rectangle([pill_x, pill_y, pill_x+pill_w, pill_y+pill_h], radius=50, fill=gold)
        
        # Phone Icon (Simple Circle + Dot)
        icon_cx, icon_cy = pill_x + 60, pill_y + 50
        draw.ellipse([icon_cx-25, icon_cy-25, icon_cx+25, icon_cy+25], fill=blue_primary)
        # Handset symbol (simulated with lines)
        draw.arc([icon_cx-12, icon_cy-12, icon_cx+12, icon_cy+12], 0, 180, fill="white", width=4)
        
        draw.text((width//2 + 20, pill_y + 50), phone, fill=blue_primary, font=phone_font, anchor="mm")

        # 8. Border around the whole card (optional but looks clean)
        draw.rectangle([0, 0, width-1, height-1], outline=(240, 240, 240), width=4)

        buf = io.BytesIO()
        card.save(buf, format="PNG")
        return buf.getvalue()

class AIService:
    @staticmethod
    def generate_review_text(service_name: str, rating: str) -> str:
        # service_name can be multiple services separated by commas
        services_desc = service_name if "," not in service_name else f"various services including {service_name}"
        prompt = f"Write a grammatically correct, formal, and professional customer review for {services_desc}. The rating provided is {rating}. Keep it concise and natural, around 2-3 sentences."
        
        # Rule-based fallback
        fallbacks = {
            "Excellent": f"I had an exceptional experience with the {service_name} I received. The team was professional and exceeded my expectations. Highly recommended!",
            "Good": f"I'm very satisfied with the {service_name} services. Everything was handled well and the results are great.",
            "Poor": f"Unfortunately, the {service_name} didn't quite meet my expectations. There's room for improvement in communication and delivery."
        }
        
        if not openai.api_key:
            return fallbacks.get(rating, "Thank you for the service.")
            
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return fallbacks.get(rating, "Thank you for the service.")

class DBService:
    @staticmethod
    def create_review_request(db: Session, client_name: Optional[str] = None, client_industry: Optional[str] = None, google_place_id: Optional[str] = None, allowed_services: Optional[str] = None):
        request = models.ReviewRequest(
            client_name=client_name, 
            client_industry=client_industry,
            google_place_id=google_place_id,
            allowed_services=allowed_services
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def get_request_by_token(db: Session, token: str):
        return db.query(models.ReviewRequest).filter(models.ReviewRequest.token == token).first()

    @staticmethod
    def validate_email_submission(db: Session, email: str) -> bool:
        if not email:
            return True
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        recent_review = db.query(models.Review).filter(
            models.Review.email == email,
            models.Review.created_at >= thirty_days_ago
        ).first()
        return recent_review is None

    @staticmethod
    def submit_review(db: Session, request_id: int, service_id: int, rating: str, email: Optional[str], ai_text: str):
        review = models.Review(
            request_id=request_id,
            service_id=service_id,
            rating=rating,
            email=email,
            ai_generated_text=ai_text
        )
        db.add(review)
        
        # Log analytics
        analytic = models.Analytic(event_type="submission", request_id=request_id)
        db.add(analytic)
        
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def log_scan(db: Session, request_id: int):
        request = db.query(models.ReviewRequest).filter(models.ReviewRequest.id == request_id).first()
        if request and not request.scanned_at:
            request.scanned_at = datetime.datetime.utcnow()
        
        analytic = models.Analytic(event_type="scan", request_id=request_id)
        db.add(analytic)
        db.commit()
