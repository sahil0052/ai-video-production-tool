import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes"
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
logo_path = base_dir / "storage" / "assets" / "logos" / "nisha_homes_logo.png"
raw_video_path = Path(r"D:\Downloads\0831 (1).mp4")
master_audio_path = work_dir / "master_audio_track.wav"
output_master = work_dir / "edited.mp4"

# Fonts
try:
    font_bold_xl = ImageFont.truetype("arialbd.ttf", 52)
    font_bold_lg = ImageFont.truetype("arialbd.ttf", 42)
    font_bold_md = ImageFont.truetype("arialbd.ttf", 34)
    font_bold_sm = ImageFont.truetype("arialbd.ttf", 26)
    font_impact_xl = ImageFont.truetype("impact.ttf", 64)
    font_impact_lg = ImageFont.truetype("impact.ttf", 52)
    font_impact_md = ImageFont.truetype("impact.ttf", 40)
except:
    font_bold_xl = ImageFont.load_default()
    font_bold_lg = font_bold_xl
    font_bold_md = font_bold_xl
    font_bold_sm = font_bold_xl
    font_impact_xl = font_bold_xl
    font_impact_lg = font_bold_xl
    font_impact_md = font_bold_xl

def fit_cover(pil_img, target_w=1080, target_h=1920, scale_boost=1.0):
    w, h = pil_img.size
    ratio = max(target_w / w, target_h / h) * scale_boost
    nw, nh = int(w * ratio), int(h * ratio)
    resized = pil_img.resize((nw, nh), Image.Resampling.BILINEAR)
    cx, cy = nw // 2, nh // 2
    return resized.crop((cx - target_w // 2, cy - target_h // 2, cx + target_w // 2, cy + target_h // 2))

img_price_vs_deal = Image.open(art_dir / "nisha_price_vs_deal_169_1788174575555.jpg").convert("RGB")
img_location_916 = Image.open(art_dir / "nisha_prime_location_aerial_1788174404868.jpg").convert("RGB")
img_clubhouse_916 = Image.open(art_dir / "nisha_luxury_clubhouse_facade_1788174430404.jpg").convert("RGB")
img_key_916 = Image.open(art_dir / "nisha_possession_golden_key_1788174453674.jpg").convert("RGB")
img_ready_interior_169 = Image.open(art_dir / "nisha_ready_interior_169_1788174622199.jpg").convert("RGB")
img_location_169 = Image.open(art_dir / "nisha_location_aerial_169_1788174598183.jpg").convert("RGB")
logo_img = Image.open(logo_path).convert("RGBA")

cap = cv2.VideoCapture(str(raw_video_path))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

subtitles = [
    (0.00, 2.40, "PROPERTY BUYING MISTAKE?", "ONLY LOOKING AT PRICE!", (255, 215, 0), (255, 60, 60)),
    (2.40, 3.80, "BIGGEST ERROR:", "SIRF PRICE DEKHNA!", (255, 255, 255), (255, 60, 60)),
    (3.80, 5.60, "LOCATION & CONNECTIVITY", "EXPRESSWAY • METRO • PRIME ACCESS", (0, 220, 255), (255, 215, 0)),
    (5.60, 7.40, "PROJECT QUALITY", "RESORT CLUBHOUSE & AMENITIES", (255, 215, 0), (255, 255, 255)),
    (7.40, 9.20, "TIMELY POSSESSION", "READY-TO-MOVE • RERA APPROVED", (0, 230, 100), (255, 215, 0)),
    (9.20, 12.20, "READY-TO-MOVE?", "WHO WILL BE THE BUYER?", (255, 215, 0), (255, 255, 255)),
    (12.20, 15.00, "LISTING vs SMART INVESTMENT", "HIGH DEMAND & RESALE LIQUIDITY", (0, 220, 255), (0, 230, 100)),
    (15.00, 21.00, "NISHA HOMES ADVISORY", "RIGHT OPTIONS FOR YOUR EXACT BUDGET", (255, 215, 0), (255, 255, 255)),
    (21.00, 28.50, "GURGAON • NOIDA • GHAZIABAD • S. DELHI", "AFFORDABLE • ECONOMY • PREMIUM", (0, 220, 255), (255, 215, 0)),
    (28.50, 33.50, "SELLING YOUR PROPERTY?", "'FOR SALE' SIGN IS NOT ENOUGH!", (255, 215, 0), (255, 60, 60)),
    (33.50, 40.133, "SAHI PRICING • PRESENTATION • BUYER", "NISHA HOMES: 7303515710", (255, 215, 0), (0, 230, 100)),
]

def get_current_subtitle(t):
    for s_start, s_end, line1, line2, c1, c2 in subtitles:
        if s_start <= t < s_end:
            return line1, line2, c1, c2
    return None, None, None, None

ffmpeg_cmd = [
    ffmpeg, "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", "1080x1920",
    "-pix_fmt", "bgr24",
    "-r", "30",
    "-i", "-",
    "-i", str(master_audio_path),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-preset", "veryfast",
    "-crf", "18",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    str(output_master)
]

proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

for frame_idx in range(total_frames):
    t = frame_idx / 30.0
    ret, raw_frame = cap.read()
    if not ret:
        break

    raw_rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
    raw_pil = Image.fromarray(raw_rgb)

    # 1. Beat 1 [0.00s - 2.40s]: FULL_CHARACTER
    if t < 2.40:
        scale = 1.0 + 0.05 * (t / 2.40)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 2. Beat 2 [2.40s - 3.80s]: SPLIT_50_50
    elif t < 3.80:
        scale = 1.0 + 0.06 * ((t - 2.40) / 1.40)
        top_crop = fit_cover(img_price_vs_deal, 1080, 960, scale_boost=scale)
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 3. Beat 3 [3.80s - 9.20s]: FULL_EXPLAINER
    elif t < 9.20:
        if t < 5.60:
            scale = 1.0 + 0.05 * ((t - 3.80) / 1.80)
            canvas = fit_cover(img_location_916, 1080, 1920, scale_boost=scale)
        elif t < 7.40:
            scale = 1.0 + 0.05 * ((t - 5.60) / 1.80)
            canvas = fit_cover(img_clubhouse_916, 1080, 1920, scale_boost=scale)
        else:
            scale = 1.0 + 0.05 * ((t - 7.40) / 1.80)
            canvas = fit_cover(img_key_916, 1080, 1920, scale_boost=scale)

    # 4. Beat 4 [9.20s - 12.20s]: FULL_CHARACTER
    elif t < 12.20:
        scale = 1.03 + 0.04 * ((t - 9.20) / 3.00)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 5. Beat 5 [12.20s - 15.00s]: SPLIT_50_50
    elif t < 15.00:
        scale = 1.0 + 0.06 * ((t - 12.20) / 2.80)
        top_crop = fit_cover(img_ready_interior_169, 1080, 960, scale_boost=scale)
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 6. Beat 6 [15.00s - 21.00s]: SPLIT_50_50
    elif t < 21.00:
        scale = 1.0 + 0.06 * ((t - 15.00) / 6.00)
        top_crop = fit_cover(img_location_169, 1080, 960, scale_boost=scale)
        logo_watermark = logo_img.resize((150, 150), Image.Resampling.LANCZOS)
        top_crop.paste(logo_watermark, (1080 - 170, 20), logo_watermark)
        
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 7. Beat 7 [21.00s - 28.50s]: FULL_EXPLAINER
    elif t < 28.50:
        scale = 1.0 + 0.06 * ((t - 21.00) / 7.50)
        canvas = fit_cover(img_location_916, 1080, 1920, scale_boost=scale).convert("RGBA")
        
        card = Image.new("RGBA", (1000, 180), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        for y in range(180):
            alpha = int(210 + 35 * (y / 180))
            cd.line([(0, y), (1000, y)], fill=(12, 16, 24, alpha))
        cd.rectangle([0, 0, 999, 179], outline=(255, 215, 0, 240), width=3)
        
        cd.text((500, 50), "GURGAON | NOIDA | GHAZIABAD | SOUTH DELHI", fill=(255, 255, 255, 255), font=font_bold_lg, anchor="mm")
        cd.text((500, 125), "AFFORDABLE • ECONOMY • PREMIUM • READY-TO-MOVE", fill=(255, 215, 0, 255), font=font_bold_md, anchor="mm")
        
        canvas.paste(card, (40, 500), card)
        canvas = canvas.convert("RGB")

    # 8. Beat 8 [28.50s - 33.50s]: FULL_CHARACTER
    elif t < 33.50:
        scale = 1.02 + 0.04 * ((t - 28.50) / 5.00)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 9. Beat 9 [33.50s - 40.133s]: FULL_EXPLAINER (Grand End Card)
    else:
        end_card = Image.new("RGB", (1080, 1920), (14, 18, 28))
        ed = ImageDraw.Draw(end_card)
        
        ed.rectangle([30, 40, 1049, 1879], outline=(255, 215, 0), width=4)
        ed.rectangle([40, 50, 1039, 1869], outline=(255, 215, 0, 120), width=2)
        
        logo_display = logo_img.resize((360, 360), Image.Resampling.LANCZOS)
        end_card.paste(logo_display, (360, 240), logo_display)
        
        ed.text((540, 660), "Property se aage, sahi deal par focus.", fill=(255, 255, 255), font=font_bold_lg, anchor="mm")
        
        ed.rectangle([100, 750, 980, 980], fill=(22, 28, 42), outline=(255, 215, 0), width=2)
        ed.text((540, 805), "1. SAHI PRICING (Market Valuation)", fill=(255, 215, 0), font=font_bold_md, anchor="mm")
        ed.text((540, 865), "2. SAHI PRESENTATION (Luxury Media)", fill=(255, 255, 255), font=font_bold_md, anchor="mm")
        ed.text((540, 925), "3. SAHI BUYER (Verified Network)", fill=(0, 220, 255), font=font_bold_md, anchor="mm")
        
        phone_box = Image.new("RGBA", (840, 160), (0, 0, 0, 0))
        pbd = ImageDraw.Draw(phone_box)
        pbd.rounded_rectangle([0, 0, 839, 159], radius=20, fill=(28, 38, 58, 250), outline=(255, 215, 0, 255), width=3)
        pbd.text((420, 45), "CALL / WHATSAPP", fill=(0, 220, 255, 255), font=font_bold_md, anchor="mm")
        pbd.text((420, 105), "7303515710", fill=(255, 230, 80, 255), font=font_impact_xl, anchor="mm")
        end_card.paste(phone_box, (120, 1060), phone_box)
        
        ed.text((540, 1300), "GURGAON  •  NOIDA  •  GHAZIABAD  •  SOUTH DELHI", fill=(0, 220, 255), font=font_bold_md, anchor="mm")
        ed.text((540, 1370), "READY-TO-MOVE BUYING & SELLING ADVISORY", fill=(200, 210, 220), font=font_bold_sm, anchor="mm")
        
        canvas = end_card

    # Subtitles
    line1, line2, c1, c2 = get_current_subtitle(t)
    if line1 and t < 33.50:
        d = ImageDraw.Draw(canvas)
        y_sub = 1680
        def draw_text_outlined(draw, pos, text, font, fill_color, stroke_color=(10, 10, 10), stroke_w=5):
            x, y = pos
            draw.text((x, y), text, font=font, fill=fill_color, anchor="mm", stroke_width=stroke_w, stroke_fill=stroke_color)

        if line2:
            draw_text_outlined(d, (540, y_sub - 35), line1, font_impact_md, c1)
            draw_text_outlined(d, (540, y_sub + 35), line2, font_impact_md, c2)
        else:
            draw_text_outlined(d, (540, y_sub), line1, font_impact_lg, c1)

    frame_bgr = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
    proc.stdin.write(frame_bgr.tobytes())

cap.release()
proc.stdin.close()
proc.wait()

audit_dir = work_dir / "audit_frames"
audit_vid = cv2.VideoCapture(str(output_master))
audit_total = int(audit_vid.get(cv2.CAP_PROP_FRAME_COUNT))
step = audit_total // 20
for idx in range(20):
    f_num = min(idx * step, audit_total - 1)
    audit_vid.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = audit_vid.read()
    if ret:
        cv2.imwrite(str(audit_dir / f"frame_{idx+1:03d}.jpg"), frame)
audit_vid.release()
print("RE-RENDER COMPLETED WITH CLEAN TYPOGRAPHY!")
