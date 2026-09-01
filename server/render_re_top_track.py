import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0830_2_realestate" / "rendered_segments"
work_dir.mkdir(parents=True, exist_ok=True)
mmanas_dir = Path(r"C:\Users\HPUSER\Videos\mmanas")
brochure_dir = base_dir / "storage" / "deliverables" / "voxpipe_0830_2_realestate"

print("Rendering 6 custom commercial segments with perfect typography (zero missing glyphs)...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')

try:
    font_large = ImageFont.truetype("arialbd.ttf", 52)
    font_sub = ImageFont.truetype("arialbd.ttf", 36)
    font_tag = ImageFont.truetype("impact.ttf", 46)
    font_title = ImageFont.truetype("impact.ttf", 64)
    font_price = ImageFont.truetype("impact.ttf", 94)
    font_badge = ImageFont.truetype("arialbd.ttf", 44)
    font_rera = ImageFont.truetype("arialbd.ttf", 34)
except:
    font_large = ImageFont.load_default()
    font_sub = font_large
    font_tag = font_large
    font_title = font_large
    font_price = font_large
    font_badge = font_large
    font_rera = font_large

# =========================================================================
# SEGMENT 1 [0.0s - 5.0s] (5.0s, 150 frames): Rent vs Dream Home Key
# =========================================================================
seg1_path = work_dir / "seg1_rent_vs_own.mp4"
out = cv2.VideoWriter(str(seg1_path), fourcc, 30.0, (1080, 960))
aerial_img = Image.open(brochure_dir / "manas_heights_aerial_masterplan.png").convert("RGBA")
aerial_img = aerial_img.resize((1200, int(1200 * aerial_img.height / aerial_img.width)), Image.Resampling.LANCZOS)

for f in range(150):
    t = f / 30.0
    canvas = np.zeros((960, 1080, 3), dtype=np.uint8)
    for y in range(960):
        r = int(15 + (30 - 15) * (y / 960))
        g = int(23 + (45 - 23) * (y / 960))
        b = int(42 + (70 - 42) * (y / 960))
        canvas[y, :] = (b, g, r)

    scale = 1.0 + 0.08 * (t / 5.0)
    cur_w = int(1080 * scale)
    cur_h = int(960 * scale)
    pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
    
    bg_aerial = aerial_img.resize((cur_w, int(cur_w * aerial_img.height / aerial_img.width)), Image.Resampling.BILINEAR)
    off_x = (1080 - bg_aerial.width) // 2
    off_y = (960 - bg_aerial.height) // 2 - int(20 * (t / 5.0))
    pil_canvas.paste(bg_aerial, (off_x, off_y), bg_aerial)

    overlay = Image.new("RGBA", (1080, 960), (15, 23, 42, 140))
    pil_canvas = Image.alpha_composite(pil_canvas, overlay)

    draw = ImageDraw.Draw(pil_canvas)
    badge_alpha = min(1.0, t * 2.0)
    card_y = int(480 - 120 + 15 * np.sin(t * 1.5))
    
    card_bg = Image.new("RGBA", (880, 240), (15, 23, 42, int(220 * badge_alpha)))
    pil_canvas.paste(card_bg, (100, card_y), card_bg)
    
    draw.rectangle([100, card_y, 980, card_y + 240], outline=(255, 215, 0, 255), width=4)
    draw.rectangle([108, card_y + 8, 972, card_y + 232], outline=(255, 215, 0, 100), width=1)

    draw.text((540, card_y + 40), "TIRED OF PAYING MONTHLY RENT?", fill=(255, 100, 100, 255), font=font_large, anchor="mm")
    draw.text((540, card_y + 110), "OWN YOUR OWN HOME TODAY!", fill=(255, 215, 0, 255), font=font_tag, anchor="mm")
    draw.text((540, card_y + 180), "INVEST IN YOUR OWN ASSET @ TITWALA (E)", fill=(240, 240, 240, 255), font=font_sub, anchor="mm")

    frame_bgr = cv2.cvtColor(np.array(pil_canvas.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg1:", seg1_path)

# =========================================================================
# SEGMENT 2 [5.0s - 11.0s] (6.0s, 180 frames): Manas Heights Elevation
# =========================================================================
seg2_path = work_dir / "seg2_elevation.mp4"
out = cv2.VideoWriter(str(seg2_path), fourcc, 30.0, (1080, 960))
elev_img = Image.open(brochure_dir / "manas_heights_building_elevation.png").convert("RGBA")

for f in range(180):
    t = f / 30.0
    canvas = np.zeros((960, 1080, 3), dtype=np.uint8)
    for y in range(960):
        r = int(248 - 25 * (y / 960))
        g = int(244 - 30 * (y / 960))
        b = int(235 - 35 * (y / 960))
        canvas[y, :] = (b, g, r)

    pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
    
    scale = 1.05 + 0.04 * (t / 6.0)
    scaled_w = int(1080 * scale)
    scaled_h = int(scaled_w * elev_img.height / elev_img.width)
    scaled_elev = elev_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    pan_y = int(-180 + 120 * (t / 6.0))
    pil_canvas.paste(scaled_elev, ((1080 - scaled_w) // 2, pan_y), scaled_elev)

    draw = ImageDraw.Draw(pil_canvas)
    draw.rectangle([60, 40, 1020, 140], fill=(15, 23, 42, 230), outline=(255, 215, 0, 255), width=3)
    draw.text((540, 90), "MANAS HEIGHTS - TITWALA (E)", fill=(255, 215, 0, 255), font=font_large, anchor="mm")
    
    draw.rectangle([120, 840, 960, 915], fill=(15, 23, 42, 230), outline=(255, 215, 0, 255), width=2)
    draw.text((540, 877), "A PROJECT BY KVM & MORYA GROUP", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")

    frame_bgr = cv2.cvtColor(np.array(pil_canvas.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg2:", seg2_path)

# =========================================================================
# SEGMENT 3 [11.0s - 18.0s] (7.0s): Real Footage - Living Room & Kitchen
# =========================================================================
seg3_path = work_dir / "seg3_real_living_kitchen.mp4"
cmd = [
    ffmpeg, "-y",
    "-ss", "00:00:01", "-t", "3.5", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (6).mp4"),
    "-ss", "00:00:01", "-t", "3.5", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (7).mp4"),
    "-filter_complex",
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='SPACIOUS 1 BHK LIVING ROOM':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=60[v0];"
    "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='GRANITE PLATFORM & FULL TILED KITCHEN':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=60[v1];"
    "[v0][v1]concat=n=2:v=1:a=0[outv]",
    "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(seg3_path)
]
subprocess.run(cmd, check=True)
print("Saved seg3:", seg3_path)

# =========================================================================
# SEGMENT 4 [18.0s - 25.5s] (7.5s): Real Footage - Bathroom & Amenities Badges
# =========================================================================
seg4_path = work_dir / "seg4_real_bathroom_amenities.mp4"
cmd = [
    ffmpeg, "-y",
    "-ss", "00:00:03", "-t", "3.8", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (4).mp4"),
    "-ss", "00:00:01", "-t", "3.7", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (3).mp4"),
    "-filter_complex",
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='ELEGANT BATHROOM & SANITARY WARE':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=60[v0];"
    "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='HI-SPEED ELEVATORS & CCTV SECURITY':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=60[v1];"
    "[v0][v1]concat=n=2:v=1:a=0[outv]",
    "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(seg4_path)
]
subprocess.run(cmd, check=True)
print("Saved seg4:", seg4_path)

# =========================================================================
# SEGMENT 5 [25.5s - 29.5s] (4.0s, 120 frames): 24 Lakh Price Showcase
# =========================================================================
seg5_path = work_dir / "seg5_pricing_showcase.mp4"
out = cv2.VideoWriter(str(seg5_path), fourcc, 30.0, (1080, 960))

for f in range(120):
    t = f / 30.0
    canvas = np.zeros((960, 1080, 3), dtype=np.uint8)
    for y in range(960):
        r = int(10 + (25 - 10) * (y / 960))
        g = int(16 + (35 - 16) * (y / 960))
        b = int(30 + (60 - 30) * (y / 960))
        canvas[y, :] = (b, g, r)

    pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(pil_canvas)

    pulse = 1.0 + 0.02 * np.sin(t * 4.0)
    card_w = int(960 * pulse)
    card_h = int(720 * pulse)
    cx, cy = 540, 480
    x0, y0 = cx - card_w // 2, cy - card_h // 2
    x1, y1 = cx + card_w // 2, cy + card_h // 2

    draw.rectangle([x0, y0, x1, y1], fill=(15, 23, 42, 240), outline=(255, 215, 0, 255), width=6)
    draw.rectangle([x0 + 10, y0 + 10, x1 - 10, y1 - 10], outline=(255, 215, 0, 140), width=2)

    draw.text((540, y0 + 70), "THOUGHTFULLY PLANNED 1 BHK", fill=(255, 255, 255, 255), font=font_title, anchor="mm")
    
    # Clean green price pill
    draw.rectangle([cx - 420, y0 + 140, cx + 420, y0 + 310], fill=(0, 200, 80, 255), outline=(255, 255, 255, 255), width=3)
    draw.text((540, y0 + 225), "RS. 24 LAKH ONLY", fill=(255, 255, 255, 255), font=font_price, anchor="mm")

    draw.text((540, y0 + 370), "[ ALL INCLUSIVE ] ZERO HIDDEN CHARGES", fill=(255, 215, 0, 255), font=font_badge, anchor="mm")
    draw.text((540, y0 + 440), "TITWALA (E) - READY CONNECTIVITY", fill=(220, 220, 220, 255), font=font_badge, anchor="mm")
    draw.text((540, y0 + 510), "MahaRERA Reg: P51700054620", fill=(255, 215, 0, 255), font=font_rera, anchor="mm")

    frame_bgr = cv2.cvtColor(np.array(pil_canvas.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg5:", seg5_path)

# =========================================================================
# SEGMENT 6 [29.5s - 33.58s] (4.08s, 123 frames): Official Contact & CTA Card
# =========================================================================
seg6_path = work_dir / "seg6_official_cta.mp4"
out = cv2.VideoWriter(str(seg6_path), fourcc, 30.0, (1080, 960))

for f in range(123):
    t = f / 30.0
    canvas = np.zeros((960, 1080, 3), dtype=np.uint8)
    for y in range(960):
        r = int(12 + (28 - 12) * (y / 960))
        g = int(20 + (42 - 20) * (y / 960))
        b = int(38 + (75 - 38) * (y / 960))
        canvas[y, :] = (b, g, r)

    pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(pil_canvas)

    draw.rectangle([40, 40, 1040, 920], fill=(15, 23, 42, 240), outline=(255, 215, 0, 255), width=6)
    draw.rectangle([50, 50, 1030, 910], outline=(255, 215, 0, 120), width=2)

    draw.text((540, 110), "MANAS HEIGHTS", fill=(255, 215, 0, 255), font=font_title, anchor="mm")
    draw.text((540, 175), "BOOK YOUR SITE VISIT TODAY!", fill=(255, 255, 255, 255), font=font_badge, anchor="mm")

    # Green Action Box
    draw.rectangle([100, 230, 980, 410], fill=(0, 180, 70, 255), outline=(255, 255, 255, 255), width=3)
    draw.text((540, 285), "CALL OR WHATSAPP NOW", fill=(255, 255, 255, 255), font=font_tag, anchor="mm")
    draw.text((540, 355), "+91 8591661098 / 8104947371", fill=(255, 255, 255, 255), font=font_large, anchor="mm")

    draw.text((540, 480), "DEVELOPER: KVM & MORYA GROUP", fill=(255, 215, 0, 255), font=font_badge, anchor="mm")
    draw.text((540, 550), "SITE ADDRESS:", fill=(200, 200, 200, 255), font=font_sub, anchor="mm")
    draw.text((540, 600), "S.No. 188 H.No. 2, Narayan Nagar Road,", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
    draw.text((540, 645), "Titwala (East) 421605, Dist: Thane", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")

    draw.text((540, 740), "[ 1 BHK ALL INCLUSIVE: RS. 24 LAKH ]", fill=(255, 215, 0, 255), font=font_badge, anchor="mm")
    draw.text((540, 810), "MahaRERA Registration No: P51700054620", fill=(200, 220, 255, 255), font=font_rera, anchor="mm")

    frame_bgr = cv2.cvtColor(np.array(pil_canvas.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg6:", seg6_path)

# =========================================================================
# Concatenate all 6 top segments into top_flow_track.mp4
# =========================================================================
concat_txt = work_dir / "concat_list.txt"
with open(concat_txt, "w") as f:
    f.write(f"file '{seg1_path.as_posix()}'\n")
    f.write(f"file '{seg2_path.as_posix()}'\n")
    f.write(f"file '{seg3_path.as_posix()}'\n")
    f.write(f"file '{seg4_path.as_posix()}'\n")
    f.write(f"file '{seg5_path.as_posix()}'\n")
    f.write(f"file '{seg6_path.as_posix()}'\n")

top_track_path = brochure_dir / "top_flow_track.mp4"
cmd = [
    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(top_track_path)
]
subprocess.run(cmd, check=True)
print("Saved complete top track:", top_track_path)
