import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes"
work_dir.mkdir(parents=True, exist_ok=True)
raw_assets_dir = base_dir / "storage" / "assets" / "real_estate_raw"
logo_path = base_dir / "storage" / "assets" / "logos" / "nisha_homes_logo.png"
raw_video_path = Path(r"D:\Downloads\0831 (1).mp4")
master_audio_path = work_dir / "master_audio_track.wav"
output_master = work_dir / "edited.mp4"

# Audio loudness
cmd_audio = [
    ffmpeg, "-y",
    "-i", str(raw_video_path),
    "-vn",
    "-af", "acompressor=threshold=-20dB:ratio=3.5:attack=15:release=150,volume=1.0,loudnorm=I=-14.0:TP=-1.5:LRA=7.0",
    "-ar", "48000",
    str(master_audio_path)
]
subprocess.run(cmd_audio, check=True)

# Fonts
try:
    font_bold_xl = ImageFont.truetype("arialbd.ttf", 52)
    font_bold_lg = ImageFont.truetype("arialbd.ttf", 40)
    font_bold_md = ImageFont.truetype("arialbd.ttf", 32)
    font_bold_sm = ImageFont.truetype("arialbd.ttf", 24)
    font_impact_xl = ImageFont.truetype("impact.ttf", 64)
    font_impact_lg = ImageFont.truetype("impact.ttf", 50)
    font_impact_md = ImageFont.truetype("impact.ttf", 38)
except:
    font_bold_xl = ImageFont.load_default()
    font_bold_lg = font_bold_xl
    font_bold_md = font_bold_xl
    font_bold_sm = font_bold_xl
    font_impact_xl = font_bold_xl
    font_impact_lg = font_bold_xl
    font_impact_md = font_bold_xl

# Helper to fit & crop with camera pan/zoom
def fit_cover(pil_img, target_w=1080, target_h=1920, scale_boost=1.0, pan_x=0.0, pan_y=0.0):
    w, h = pil_img.size
    ratio = max(target_w / w, target_h / h) * scale_boost
    nw, nh = int(w * ratio), int(h * ratio)
    resized = pil_img.resize((nw, nh), Image.Resampling.BILINEAR)
    
    cx = int(nw / 2 + pan_x * (nw - target_w) / 2)
    cy = int(nh / 2 + pan_y * (nh - target_h) / 2)
    
    left = max(0, min(cx - target_w // 2, nw - target_w))
    top = max(0, min(cy - target_h // 2, nh - target_h))
    
    return resized.crop((left, top, left + target_w, top + target_h))

# Load REAL photos
img_construction = Image.open(raw_assets_dir / "real_construction_site.jpg").convert("RGB")
img_society = Image.open(raw_assets_dir / "real_luxury_society.jpg").convert("RGB")
img_expressway = Image.open(raw_assets_dir / "real_gurgaon_expressway.jpg").convert("RGB")
img_metro = Image.open(raw_assets_dir / "real_metro_connectivity.jpg").convert("RGB")
img_highrise = Image.open(raw_assets_dir / "real_society_highrise.jpg").convert("RGB")
img_clubhouse = Image.open(raw_assets_dir / "real_society_clubhouse.jpg").convert("RGB")
img_keys = Image.open(raw_assets_dir / "real_house_keys.jpg").convert("RGB")
img_handover = Image.open(raw_assets_dir / "real_handover_keys.jpg").convert("RGB")
img_interior = Image.open(raw_assets_dir / "real_ready_interior.jpg").convert("RGB")
img_advisory = Image.open(raw_assets_dir / "real_advisory_meeting.jpg").convert("RGB")
img_skyline = Image.open(raw_assets_dir / "real_delhi_ncr_skyline.jpg").convert("RGB")
logo_img = Image.open(logo_path).convert("RGBA")

# Build side-by-side price comparison image (1080x960)
comp_img = Image.new("RGB", (1080, 960))
left_half = fit_cover(img_construction, 538, 960, scale_boost=1.05)
right_half = fit_cover(img_society, 538, 960, scale_boost=1.05)
comp_img.paste(left_half, (0, 0))
comp_img.paste(right_half, (542, 0))
d_comp = ImageDraw.Draw(comp_img)
d_comp.line([(540, 0), (540, 960)], fill=(20, 20, 20), width=4)

# Add clear Yellow and White badges
d_comp.rounded_rectangle([30, 40, 320, 100], radius=10, fill=(15, 15, 15, 230), outline=(255, 215, 0), width=2)
d_comp.text((175, 70), "CHEAP PRICE", fill=(255, 215, 0), font=font_bold_md, anchor="mm")

d_comp.rounded_rectangle([760, 40, 1050, 100], radius=10, fill=(15, 15, 15, 230), outline=(255, 255, 255), width=2)
d_comp.text((905, 70), "SAHI DEAL", fill=(255, 255, 255), font=font_bold_md, anchor="mm")

cap = cv2.VideoCapture(str(raw_video_path))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Subtitles ONLY IN YELLOW & WHITE
# Format: (start, end, line1, line2, color1, color2)
# color1 = Yellow (255, 215, 0), color2 = White (255, 255, 255)
subtitles = [
    (0.00, 2.40, "PROPERTY BUYING MISTAKE?", "ONLY LOOKING AT PRICE!", (255, 215, 0), (255, 255, 255)),
    (2.40, 3.80, "BIGGEST ERROR:", "SIRF PRICE DEKHNA!", (255, 255, 255), (255, 215, 0)),
    (3.80, 5.60, "LOCATION & CONNECTIVITY", "EXPRESSWAY • METRO • PRIME ACCESS", (255, 215, 0), (255, 255, 255)),
    (5.60, 7.40, "PROJECT QUALITY", "REPUTED BUILDER & AMENITIES", (255, 255, 255), (255, 215, 0)),
    (7.40, 9.20, "TIMELY POSSESSION", "READY-TO-MOVE • RERA APPROVED", (255, 215, 0), (255, 255, 255)),
    (9.20, 12.20, "READY-TO-MOVE?", "WHO WILL BE THE BUYER?", (255, 255, 255), (255, 215, 0)),
    (12.20, 15.00, "LISTING vs SMART INVESTMENT", "HIGH DEMAND & RESALE LIQUIDITY", (255, 215, 0), (255, 255, 255)),
    (15.00, 21.00, "NISHA HOMES ADVISORY", "RIGHT OPTIONS FOR YOUR EXACT BUDGET", (255, 255, 255), (255, 215, 0)),
    (21.00, 28.50, "GURGAON • NOIDA • GHAZIABAD • S. DELHI", "AFFORDABLE • ECONOMY • PREMIUM", (255, 215, 0), (255, 255, 255)),
    (28.50, 33.50, "SELLING YOUR PROPERTY?", "'FOR SALE' SIGN IS NOT ENOUGH!", (255, 255, 255), (255, 215, 0)),
    (33.50, 40.133, "SAHI PRICING • PRESENTATION • BUYER", "NISHA HOMES: 7303515710", (255, 215, 0), (255, 255, 255)),
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

    # 1. Beat 1 [0.00s - 2.40s]: FULL_CHARACTER (Hook Question)
    if t < 2.40:
        scale = 1.0 + 0.05 * (t / 2.40)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 2. Beat 2 [2.40s - 3.80s]: SPLIT_50_50 (Real Price Trap vs Society Comparison)
    elif t < 3.80:
        p = (t - 2.40) / 1.40
        scale = 1.0 + 0.04 * p
        top_crop = fit_cover(comp_img, 1080, 960, scale_boost=scale)
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 3. Beat 3 [3.80s - 9.20s]: FULL_EXPLAINER (Real 3 Pillars of Indian Real Estate)
    elif t < 9.20:
        if t < 5.60:
            # Pillar 1: Location & Expressway / Metro
            p = (t - 3.80) / 1.80
            scale = 1.02 + 0.06 * p
            canvas = fit_cover(img_expressway, 1080, 1920, scale_boost=scale, pan_y=p * 0.15)
        elif t < 7.40:
            # Pillar 2: Project Quality & Highrise Gated Society
            p = (t - 5.60) / 1.80
            scale = 1.02 + 0.06 * p
            canvas = fit_cover(img_highrise, 1080, 1920, scale_boost=scale, pan_x=p * 0.15)
        else:
            # Pillar 3: Timely Possession & Real Key Handover
            p = (t - 7.40) / 1.80
            scale = 1.02 + 0.06 * p
            canvas = fit_cover(img_handover, 1080, 1920, scale_boost=scale, pan_y=-p * 0.1)

    # 4. Beat 4 [9.20s - 12.20s]: FULL_CHARACTER (Resale Realization)
    elif t < 12.20:
        scale = 1.03 + 0.04 * ((t - 9.20) / 3.00)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 5. Beat 5 [12.20s - 15.00s]: SPLIT_50_50 (Real Finished Apartment Interior)
    elif t < 15.00:
        p = (t - 12.20) / 2.80
        scale = 1.02 + 0.05 * p
        pan = -0.15 + 0.3 * p
        top_crop = fit_cover(img_interior, 1080, 960, scale_boost=scale, pan_x=pan)
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 6. Beat 6 [15.00s - 21.00s]: SPLIT_50_50 (Real Property Advisory Discussion)
    elif t < 21.00:
        p = (t - 15.00) / 6.00
        scale = 1.02 + 0.06 * p
        pan = -0.15 + 0.3 * p
        top_crop = fit_cover(img_advisory, 1080, 960, scale_boost=scale, pan_x=pan)
        
        # Logo watermark in top right
        logo_watermark = logo_img.resize((150, 150), Image.Resampling.LANCZOS)
        top_crop.paste(logo_watermark, (1080 - 170, 20), logo_watermark)
        
        bot_crop = raw_pil.crop((0, 160, 1080, 160 + 960))
        canvas = Image.new("RGB", (1080, 1920))
        canvas.paste(top_crop, (0, 0))
        canvas.paste(bot_crop, (0, 960))
        d = ImageDraw.Draw(canvas)
        d.line([(0, 959), (1080, 959)], fill=(20, 20, 20), width=3)

    # 7. Beat 7 [21.00s - 28.50s]: FULL_EXPLAINER (Real Delhi NCR Skyline)
    elif t < 28.50:
        p = (t - 21.00) / 7.50
        scale = 1.02 + 0.07 * p
        canvas = fit_cover(img_skyline, 1080, 1920, scale_boost=scale, pan_y=p * 0.12).convert("RGBA")
        
        # Broadcast card in Yellow and White
        card = Image.new("RGBA", (1000, 180), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        for y in range(180):
            alpha = int(225 + 20 * (y / 180))
            cd.line([(0, y), (1000, y)], fill=(10, 14, 22, alpha))
        cd.rectangle([0, 0, 999, 179], outline=(255, 215, 0, 240), width=3)
        
        cd.text((500, 50), "GURGAON | NOIDA | GHAZIABAD | SOUTH DELHI", fill=(255, 255, 255, 255), font=font_bold_lg, anchor="mm")
        cd.text((500, 125), "AFFORDABLE • ECONOMY • PREMIUM • READY-TO-MOVE", fill=(255, 215, 0, 255), font=font_bold_md, anchor="mm")
        
        canvas.paste(card, (40, 500), card)
        canvas = canvas.convert("RGB")

    # 8. Beat 8 [28.50s - 33.50s]: FULL_CHARACTER (Addressing Sellers)
    elif t < 33.50:
        scale = 1.02 + 0.04 * ((t - 28.50) / 5.00)
        canvas = fit_cover(raw_pil, 1080, 1920, scale_boost=scale)

    # 9. Beat 9 [33.50s - 40.133s]: FULL_EXPLAINER (Clean Brand End Card in Yellow & White)
    else:
        end_card = Image.new("RGB", (1080, 1920), (12, 16, 26))
        ed = ImageDraw.Draw(end_card)
        
        # Elegant yellow border
        ed.rectangle([30, 40, 1049, 1879], outline=(255, 215, 0), width=3)
        ed.rectangle([42, 52, 1037, 1867], outline=(255, 255, 255, 100), width=1)
        
        # Centered Official Nisha Homes Logo
        logo_display = logo_img.resize((360, 360), Image.Resampling.LANCZOS)
        end_card.paste(logo_display, (360, 220), logo_display)
        
        ed.text((540, 640), "Property se aage, sahi deal par focus.", fill=(255, 255, 255), font=font_bold_lg, anchor="mm")
        
        # Frosted glass card for 3 selling points
        p_box = Image.new("RGBA", (900, 240), (0, 0, 0, 0))
        pbd = ImageDraw.Draw(p_box)
        pbd.rounded_rectangle([0, 0, 899, 239], radius=16, fill=(20, 28, 44, 240), outline=(255, 215, 0, 220), width=2)
        pbd.text((450, 45), "1. SAHI PRICING (Market Valuation)", fill=(255, 215, 0, 255), font=font_bold_md, anchor="mm")
        pbd.text((450, 120), "2. SAHI PRESENTATION (Luxury Media)", fill=(255, 255, 255, 255), font=font_bold_md, anchor="mm")
        pbd.text((450, 195), "3. SAHI BUYER (Verified Network)", fill=(255, 215, 0, 255), font=font_bold_md, anchor="mm")
        end_card.paste(p_box, (90, 710), p_box)
        
        # Call / WhatsApp button in Yellow and White
        phone_box = Image.new("RGBA", (840, 150), (0, 0, 0, 0))
        phd = ImageDraw.Draw(phone_box)
        phd.rounded_rectangle([0, 0, 839, 149], radius=20, fill=(26, 38, 58, 250), outline=(255, 215, 0, 255), width=3)
        phd.text((420, 40), "CALL / WHATSAPP", fill=(255, 255, 255, 255), font=font_bold_md, anchor="mm")
        phd.text((420, 100), "7303515710", fill=(255, 215, 0, 255), font=font_impact_xl, anchor="mm")
        end_card.paste(phone_box, (120, 1000), phone_box)
        
        # Footer in Yellow and White
        ed = ImageDraw.Draw(end_card)
        ed.text((540, 1230), "GURGAON  •  NOIDA  •  GHAZIABAD  •  SOUTH DELHI", fill=(255, 215, 0), font=font_bold_md, anchor="mm")
        ed.text((540, 1290), "READY-TO-MOVE BUYING & SELLING ADVISORY", fill=(255, 255, 255), font=font_bold_sm, anchor="mm")
        
        canvas = end_card

    # Subtitles ONLY IN YELLOW AND WHITE
    line1, line2, c1, c2 = get_current_subtitle(t)
    if line1 and t < 33.50:
        d = ImageDraw.Draw(canvas)
        y_sub = 1680
        def draw_text_outlined(draw, pos, text, font, fill_color, stroke_color=(0, 0, 0), stroke_w=6):
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

# Extract 20 QC Frames
print("Extracting 20 QC Audit Frames...")
audit_dir = work_dir / "audit_frames"
audit_dir.mkdir(parents=True, exist_ok=True)
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
print("REAL RAW PHOTO MASTER RENDER COMPLETED SUCCESSFULLY!")
