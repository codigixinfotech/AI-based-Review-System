import qrcode
import io
import os
import datetime
import uuid
import math
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
        url = f"{base_url}/?token={token}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H, # Higher correction for cards
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return qr.make_image(fill_color="#0d1b2a", back_color="white").convert("RGB") # Cohesive luxury blue

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
    def generate_card(token: str, base_url: str, company_name: str = "Your Business", industry: str = "Your Industry", phone: str = "0000000000") -> bytes:
        # High resolution settings for print quality
        width, height = 1000, 1500
        
        # Elegant Minimalist Color Palette
        bg_light = (248, 250, 252)      # Ultra-light slate grey background
        navy_primary = (15, 23, 42)     # Deep Navy Slate (Tailwind slate-900)
        gold = (212, 175, 55)           # Metallic Gold
        white = (255, 255, 255)
        grey_text = (100, 116, 139)     # Cool grey (Tailwind slate-500)
        
        # Create canvas
        card = Image.new("RGB", (width, height), bg_light)
        draw = ImageDraw.Draw(card)
        
        # 1. Elegant Border Framing
        # Outer gold border with 24px inner padding
        border_padding = 24
        draw.rectangle(
            [border_padding, border_padding, width - border_padding, height - border_padding], 
            outline=gold, 
            width=3
        )
        
        # Decorative corners (brackets)
        bracket_len = 50
        # Top-Left Bracket
        draw.line([border_padding, border_padding, border_padding + bracket_len, border_padding], fill=navy_primary, width=8)
        draw.line([border_padding, border_padding, border_padding, border_padding + bracket_len], fill=navy_primary, width=8)
        # Top-Right Bracket
        draw.line([width - border_padding, border_padding, width - border_padding - bracket_len, border_padding], fill=navy_primary, width=8)
        draw.line([width - border_padding, border_padding, width - border_padding, border_padding + bracket_len], fill=navy_primary, width=8)
        # Bottom-Left Bracket
        draw.line([border_padding, height - border_padding, border_padding + bracket_len, height - border_padding], fill=navy_primary, width=8)
        draw.line([border_padding, height - border_padding, border_padding, height - border_padding - bracket_len], fill=navy_primary, width=8)
        # Bottom-Right Bracket
        draw.line([width - border_padding, height - border_padding, width - border_padding - bracket_len, height - border_padding], fill=navy_primary, width=8)
        draw.line([width - border_padding, height - border_padding, width - border_padding, height - border_padding - bracket_len], fill=navy_primary, width=8)
        
        # 2. Robust Font Loading with absolute path searches
        import os
        def get_system_font(names):
            search_dirs = []
            if os.name == 'nt':
                windir = os.environ.get('WINDIR', 'C:\\Windows')
                search_dirs.append(os.path.join(windir, 'Fonts'))
            else:
                search_dirs.extend([
                    "/usr/share/fonts/truetype/dejavu",
                    "/usr/share/fonts/truetype",
                    "/usr/share/fonts",
                    "/System/Library/Fonts",
                    "/Library/Fonts"
                ])
            for name in names:
                if os.path.exists(name):
                    return name
                for d in search_dirs:
                    full_path = os.path.join(d, name)
                    if os.path.exists(full_path):
                        return full_path
            return None

        font_path_bold = get_system_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"])
        font_path_reg = get_system_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])

        try:
            if font_path_bold and font_path_reg:
                title_font_size = 64
                title_font = ImageFont.truetype(font_path_bold, title_font_size)
                
                # Dynamically reduce title font if too long
                while True:
                    bbox = draw.textbbox((0, 0), company_name, font=title_font)
                    text_width = bbox[2] - bbox[0]
                    if text_width <= width - 180 or title_font_size <= 24:
                        break
                    title_font_size -= 4
                    title_font = ImageFont.truetype(font_path_bold, title_font_size)

                subtitle_font = ImageFont.truetype(font_path_reg, 32)
                header_font = ImageFont.truetype(font_path_bold, 48)
                footer_text_font = ImageFont.truetype(font_path_reg, 36)
                phone_font = ImageFont.truetype(font_path_bold, 40)
            else:
                # Force fallback to default if font files are somehow missing
                title_font = subtitle_font = header_font = footer_text_font = phone_font = ImageFont.load_default()
        except:
            title_font = subtitle_font = header_font = footer_text_font = phone_font = ImageFont.load_default()

        # 3. Header Section (Centered)
        draw.text((width//2, 160), company_name.upper(), fill=navy_primary, font=title_font, anchor="mm")
        draw.text((width//2, 220), industry.upper(), fill=grey_text, font=subtitle_font, anchor="mm")
        
        # 3.5. Gold Stars
        star_y = 290
        star_size = 25
        star_spacing = 60
        for i in range(-2, 3):
            CardService._draw_star(draw, width//2 + i * star_spacing, star_y, star_size, gold)
        
        # 4. CTA Section
        draw.text((width//2, 380), "LEAVE US A GOOGLE REVIEW", fill=navy_primary, font=header_font, anchor="mm")
        draw.text((width//2, 440), "Scan the QR code below to share your experience", fill=grey_text, font=subtitle_font, anchor="mm")
        
        # 5. QR Code Area (White Rounded Card with drop shadow)
        qr_box_size = 600
        qr_box_x = (width - qr_box_size) // 2
        qr_box_y = 510
        
        # Smooth multi-layered drop shadow
        for i in range(1, 15):
            draw.rounded_rectangle(
                [qr_box_x-i, qr_box_y-i, qr_box_x+qr_box_size+i, qr_box_y+qr_box_size+i], 
                radius=32, 
                outline=(230-i, 234-i, 240-i), 
                width=1
            )

        # White main container with double gold outline
        draw.rounded_rectangle([qr_box_x, qr_box_y, qr_box_x+qr_box_size, qr_box_y+qr_box_size], radius=32, fill="white", outline=gold, width=3)
        
        # QR Code itself (drawn in cohesive navy primary color)
        qr_img = QRService.generate_qr_img(token, base_url)
        qr_size = 520
        resample_filter = getattr(Image, 'LANCZOS', getattr(Image, 'BICUBIC', 3))
        qr_img = qr_img.resize((qr_size, qr_size), resample_filter)
        card.paste(qr_img, (qr_box_x + (qr_box_size - qr_size)//2, qr_box_y + (qr_box_size - qr_size)//2))
        
        # 6. Bottom Message
        draw.text((width//2, 1180), "Thank you for helping us grow", fill=navy_primary, font=footer_text_font, anchor="mm")
        
        # 7. Sleek Contrast Contact Pill (Deep Navy base with Gold accents)
        pill_w, pill_h = 480, 80
        pill_x = (width - pill_w) // 2
        pill_y = 1240
        draw.rounded_rectangle([pill_x, pill_y, pill_x+pill_w, pill_y+pill_h], radius=40, fill=navy_primary, outline=gold, width=3)
        
        # Gold Phone Icon Circle
        icon_cx, icon_cy = pill_x + 50, pill_y + 40
        draw.ellipse([icon_cx-18, icon_cy-18, icon_cx+18, icon_cy+18], fill=gold)
        
        # Inside handset receiver (in navy)
        draw.arc([icon_cx-10, icon_cy-10, icon_cx+10, icon_cy+8], 40, 140, fill=navy_primary, width=3)
        draw.ellipse([icon_cx-10, icon_cy-2, icon_cx-4, icon_cy+4], fill=navy_primary)
        draw.ellipse([icon_cx+4, icon_cy-2, icon_cx+10, icon_cy+4], fill=navy_primary)
        
        # Phone text in shining Gold
        draw.text((width//2 + 25, pill_y + 40), phone, fill=gold, font=phone_font, anchor="mm")

        # 8. Footer decoration
        draw.text((width//2, 1370), "Your feedback is strictly internal & appreciated", fill=grey_text, font=subtitle_font, anchor="mm")

        buf = io.BytesIO()
        card.save(buf, format="PNG")
        return buf.getvalue()

class AIService:
    @staticmethod
    def generate_review_text(business_name: str, service_name: str, rating: str) -> str:
        import random
        # service_name can be multiple services separated by commas
        services_desc = service_name if "," not in service_name else f"various services including {service_name}"
        b_name = business_name if business_name and business_name != "the business" else "the business"
        
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

