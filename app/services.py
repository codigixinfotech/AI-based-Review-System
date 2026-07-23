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
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL") # Set this to your provider's URL, e.g. https://openrouter.ai/api/v1

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
            
            title_font_size = 72
            title_font = ImageFont.truetype(font_path_bold, title_font_size)
            
            # Dynamically reduce title font size if it exceeds the card width
            while True:
                bbox = draw.textbbox((0, 0), company_name, font=title_font)
                text_width = bbox[2] - bbox[0]
                if text_width <= width - 80 or title_font_size <= 24:
                    break
                title_font_size -= 4
                title_font = ImageFont.truetype(font_path_bold, title_font_size)

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
        qr_box_y = 570
        
        # Draw soft shadow (simulated with grey rectangles)
        for i in range(1, 15):
            draw.rounded_rectangle([qr_box_x-i, qr_box_y-i, qr_box_x+qr_box_size+i, qr_box_y+qr_box_size+i], radius=60, outline=(220+i, 220+i, 220+i), width=2)

        draw.rounded_rectangle([qr_box_x, qr_box_y, qr_box_x+qr_box_size, qr_box_y+qr_box_size], radius=60, fill="white")
        
        # QR Code itself
        qr_img = QRService.generate_qr_img(token, base_url)
        # Use a larger size for the QR so it feels better aligned and balanced
        qr_size = 560
        # Use Image.LANCZOS for high quality down/upsampling if available, fallback to BICUBIC
        resample_filter = getattr(Image, 'LANCZOS', getattr(Image, 'BICUBIC', 3))
        qr_img = qr_img.resize((qr_size, qr_size), resample_filter)
        card.paste(qr_img, (qr_box_x + (qr_box_size - qr_size)//2, qr_box_y + (qr_box_size - qr_size)//2))
        
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
    def generate_review_text(business_name: str, service_name: str, rating: str) -> str:
        import random
        # service_name can be multiple services separated by commas
        services_desc = service_name if "," not in service_name else f"various services including {service_name}"
        b_name = business_name if business_name and business_name != "the business" else "Codigix Infotech"
        
        if rating in ["Excellent", "Good"]:
            prompt = (
                f"You are a delighted customer writing a {rating} Google review for {b_name}. "
                "Write a completely unique, highly engaging, and natural-sounding review (3-4 sentences). "
                f"CRITICAL: You MUST explicitly mention the business name '{b_name}' in your review. "
                f"CRITICAL: You MUST highlight and praise the specific services received: '{services_desc}'. "
                "Naturally weave in high-volume, catchy SEO keywords related to the specific services to boost local search rankings (e.g., 'best quality', 'highly professional', 'top-rated', and industry-specific terms). "
                "Ensure the review is completely different every time by varying the sentence structure, opening phrases, and specific compliments. "
                "Sound like a genuine, enthusiastic human client who had an amazing experience."
            )
        else:
            prompt = (
                f"Write a realistic, constructive customer review for {b_name} regarding their {services_desc}. The rating provided is {rating}. "
                f"CRITICAL: Explicitly mention the business name '{b_name}'. "
                "Make it sound natural, distinct, and point out areas for improvement without being overly aggressive (2-3 sentences)."
            )
        
        # Dynamic fallbacks in case the OpenAI API key is missing or invalid
        fallbacks_excellent = [
            f"I had an exceptional experience with {b_name} for their {service_name}. The team was highly professional, delivered top-quality results, and exceeded my expectations. If you're looking for the best service, I highly recommend {b_name}!",
            f"Absolutely fantastic {service_name} services from {b_name}! They really took the time to understand my needs and delivered outstanding quality. Five stars all the way.",
            f"If you need {service_name}, look no further than {b_name}. Their expertise and attention to detail are unmatched. I'll definitely be returning for future projects."
        ]
        
        fallbacks_good = [
            f"I'm very satisfied with the {service_name} I received from {b_name}. The process was smooth, and the results are great. Solid service overall.",
            f"Good experience with {b_name} for their {service_name}. The team was polite and got the job done efficiently. Would recommend.",
            f"They did a great job on the {service_name}. A few minor hiccups, but overall a very positive experience and good quality work from {b_name}."
        ]
        
        fallbacks_poor = [
            f"Unfortunately, the {service_name} from {b_name} didn't quite meet my expectations. There's room for improvement in communication and delivery.",
            f"Not the best experience with the {service_name} at {b_name}. I felt that the quality could have been much better given the price.",
            f"I was somewhat disappointed with the {service_name} provided by {b_name}. Hoping they can improve their processes in the future."
        ]
        
        fallback_dict = {
            "Excellent": fallbacks_excellent,
            "Good": fallbacks_good,
            "Poor": fallbacks_poor
        }
        
        selected_fallback = random.choice(fallback_dict.get(rating, [f"Thank you for the {service_name} from {b_name}."]))

        if not api_key or api_key == "your_openai_api_key_here":
            return selected_fallback
            
        try:
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            model_name = os.getenv("AI_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.8 # Higher temperature for more variety
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return selected_fallback

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
