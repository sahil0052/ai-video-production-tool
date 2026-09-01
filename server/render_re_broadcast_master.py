import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0830_2_realestate" / "rendered_segments"
work_dir.mkdir(parents=True, exist_ok=True)
mmanas_dir = Path(r"C:\Users\HPUSER\Videos\mmanas")
brochure_dir = base_dir / "storage" / "deliverables" / "voxpipe_0830_2_realestate"
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
real_building_video = Path(r"D:\Downloads\WhatsApp Video 2026-08-30 at 11.10.07 AM.mp4")
logo_path = brochure_dir / "manas_heights_official_logo.png"

print("Rendering Visual Tracks with extra prominent official logo...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')

try:
    font_large = ImageFont.truetype("arialbd.ttf", 52)
    font_sub = ImageFont.truetype("arialbd.ttf", 36)
    font_tag = ImageFont.truetype("impact.ttf", 48)
    font_title = ImageFont.truetype("impact.ttf", 64)
    font_price = ImageFont.truetype("impact.ttf", 94)
    font_badge = ImageFont.truetype("arialbd.ttf", 42)
    font_rera = ImageFont.truetype("arialbd.ttf", 32)
except:
    font_large = ImageFont.load_default()
    font_sub = font_large
    font_tag = font_large
    font_title = font_large
    font_price = font_large
    font_badge = font_large
    font_rera = font_large

logo_img = Image.open(logo_path).convert("RGBA")

def create_glass_bar(width, height, text, subtext="", gold=False):
    bar = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    for y in range(height):
        alpha = int(185 + 40 * (y / height))
        draw.line([(0, y), (width, y)], fill=(12, 18, 32, alpha))
    border_color = (255, 215, 0, 240) if gold else (0, 210, 100, 240)
    draw.rectangle([0, 0, width - 1, height - 1], outline=border_color, width=2)
    draw.line([(0, 0), (width, 0)], fill=(255, 255, 255, 180), width=1)
    
    if subtext:
        draw.text((width // 2, int(height * 0.35)), text, fill=(255, 255, 255, 255), font=font_badge, anchor="mm")
        draw.text((width // 2, int(height * 0.72)), subtext, fill=(255, 215, 0, 255) if gold else (0, 220, 120, 255), font=font_sub, anchor="mm")
    else:
        draw.text((width // 2, height // 2), text, fill=(255, 255, 255, 255), font=font_badge, anchor="mm")
    return bar

# SEGMENT 1 [0.0s - 5.0s]
seg1_path = work_dir / "seg1_rent_vs_own.mp4"
out = cv2.VideoWriter(str(seg1_path), fourcc, 30.0, (1080, 960))
img1_path = art_dir / "re_rent_vs_own_key_1788100864536.jpg"
img1 = Image.open(img1_path).convert("RGB")

for f in range(150):
    t = f / 30.0
    scale = 1.0 + 0.06 * (t / 5.0)
    w = int(img1.width * scale)
    h = int(img1.height * scale)
    scaled = img1.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = w // 2, int(h * 0.52)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960)).convert("RGBA")
    
    scaled_logo = logo_img.resize((190, 190), Image.Resampling.LANCZOS)
    cropped.paste(scaled_logo, (840, 40), scaled_logo)

    glass = create_glass_bar(960, 110, "TIRED OF PAYING MONTHLY RENT?", "INVEST IN YOUR OWN HOME @ TITWALA (E)", gold=True)
    cropped.paste(glass, (60, 800), glass)

    frame_bgr = cv2.cvtColor(np.array(cropped.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()

# SEGMENT 2 [5.0s - 12.8s]
seg2_path = work_dir / "seg2_elevation.mp4"
cmd = [
    ffmpeg, "-y",
    "-ss", "00:00:00.2", "-t", "7.8", "-i", str(real_building_video),
    "-filter_complex",
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='MANAS HEIGHTS - TITWALA (EAST)':fontcolor=gold:fontsize=44:box=1:boxcolor=black@0.75:boxborderw=12:x=(w-text_w)/2:y=790,drawtext=text='10 MINS WALK FROM TITWALA (E) STATION':fontcolor=white:fontsize=34:box=1:boxcolor=black@0.75:boxborderw=8:x=(w-text_w)/2:y=855[outv]",
    "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(seg2_path)
]
subprocess.run(cmd, check=True)

# SEGMENT 3 [12.8s - 20.1s]
seg3_path = work_dir / "seg3_real_living_kitchen.mp4"
cmd = [
    ffmpeg, "-y",
    "-ss", "00:00:01", "-t", "3.65", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (6).mp4"),
    "-ss", "00:00:01", "-t", "3.65", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (7).mp4"),
    "-filter_complex",
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='ACTUAL WALKTHROUGH':fontcolor=gold:fontsize=32:x=60:y=50:box=1:boxcolor=black@0.6:boxborderw=8,drawtext=text='SPACIOUS 1 BHK LIVING ROOM':fontcolor=white:fontsize=44:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=820[v0];"
    "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='ACTUAL WALKTHROUGH':fontcolor=gold:fontsize=32:x=60:y=50:box=1:boxcolor=black@0.6:boxborderw=8,drawtext=text='GRANITE PLATFORM & FULL TILED KITCHEN':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=820[v1];"
    "[v0][v1]concat=n=2:v=1:a=0[outv]",
    "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(seg3_path)
]
subprocess.run(cmd, check=True)

# SEGMENT 4 [20.1s - 27.5s]
seg4_path = work_dir / "seg4_real_bathroom_amenities.mp4"
cmd = [
    ffmpeg, "-y",
    "-ss", "00:00:03", "-t", "3.7", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (4).mp4"),
    "-ss", "00:00:01", "-t", "3.7", "-i", str(mmanas_dir / "video_2026-08-30_17-42-01 (3).mp4"),
    "-filter_complex",
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='ACTUAL WALKTHROUGH':fontcolor=gold:fontsize=32:x=60:y=50:box=1:boxcolor=black@0.6:boxborderw=8,drawtext=text='ELEGANT BATHROOM & SANITARY FITTINGS':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=820[v0];"
    "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,drawtext=text='AMENITIES':fontcolor=gold:fontsize=32:x=60:y=50:box=1:boxcolor=black@0.6:boxborderw=8,drawtext=text='HI-SPEED ELEVATORS & CCTV SECURITY':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.7:boxborderw=10:x=(w-text_w)/2:y=820[v1];"
    "[v0][v1]concat=n=2:v=1:a=0[outv]",
    "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(seg4_path)
]
subprocess.run(cmd, check=True)

# SEGMENT 5 [27.5s - 31.0s]
seg5_path = work_dir / "seg5_pricing_showcase.mp4"
out = cv2.VideoWriter(str(seg5_path), fourcc, 30.0, (1080, 960))
img5_path = art_dir / "re_pricing_24_lakh_1788100931560.jpg"
img5 = Image.open(img5_path).convert("RGB")

for f in range(105):
    t = f / 30.0
    scale = 1.0 + 0.05 * (t / 3.5)
    w = int(img5.width * scale)
    h = int(img5.height * scale)
    scaled = img5.resize((w, h), Image.Resampling.LANCZOS)
    
    cx = w // 2
    cy = int(h * 0.50)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960)).convert("RGBA")
    
    glass = create_glass_bar(980, 110, "TITWALA (E) - READY CONNECTIVITY", "MahaRERA Registration No: P51700054620", gold=True)
    cropped.paste(glass, (50, 800), glass)

    frame_bgr = cv2.cvtColor(np.array(cropped.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()

# SEGMENT 6 [31.0s - 35.433s] (Prominent CTA Card)
seg6_path = work_dir / "seg6_official_cta.mp4"
out = cv2.VideoWriter(str(seg6_path), fourcc, 30.0, (1080, 960))
bg_cta = img5.resize((1700, int(1700 * img5.height / img5.width)), Image.Resampling.LANCZOS)
bg_cta = bg_cta.filter(ImageFilter.GaussianBlur(radius=8))

# Extra prominent CTA logo (260x260)
cta_logo = logo_img.resize((260, 260), Image.Resampling.LANCZOS)

for f in range(133):
    t = f / 30.0
    scale = 1.0 + 0.03 * (t / 4.433)
    w = int(bg_cta.width * scale)
    h = int(bg_cta.height * scale)
    scaled_bg = bg_cta.resize((w, h), Image.Resampling.BILINEAR)
    
    cx = w // 2
    cy = int(h * 0.50)
    cropped_bg = scaled_bg.crop((cx - 540, cy - 480, cx + 540, cy + 480)).convert("RGBA")
    
    vignette = Image.new("RGBA", (1080, 960), (10, 15, 28, 160))
    canvas = Image.alpha_composite(cropped_bg, vignette)
    draw = ImageDraw.Draw(canvas)

    card_w, card_h = 980, 850
    x0, y0 = 50, 55
    x1, y1 = x0 + card_w, y0 + card_h

    card_fill = Image.new("RGBA", (card_w, card_h), (12, 20, 36, 235))
    canvas.paste(card_fill, (x0, y0), card_fill)
    
    draw.rectangle([x0, y0, x1, y1], outline=(255, 215, 0, 255), width=4)
    draw.rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=(255, 215, 0, 100), width=1)

    # Centered High-Res Official Logo
    canvas.paste(cta_logo, (540 - 130, y0 + 10), cta_logo)

    # Green Action Box
    draw.rectangle([x0 + 40, y0 + 280, x1 - 40, y0 + 440], fill=(0, 180, 75, 255), outline=(255, 255, 255, 255), width=3)
    draw.text((540, y0 + 325), "CALL OR WHATSAPP NOW", fill=(255, 255, 255, 255), font=font_tag, anchor="mm")
    draw.text((540, y0 + 390), "+91 8591661098 / 8104947371", fill=(255, 255, 255, 255), font=font_large, anchor="mm")

    # Details
    draw.text((540, y0 + 500), "1 BHK ALL INCLUSIVE: RS. 24 LAKH", fill=(255, 215, 0, 255), font=font_badge, anchor="mm")
    draw.text((540, y0 + 560), "DEVELOPER: KVM & MORYA GROUP", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
    
    draw.text((540, y0 + 620), "SITE ADDRESS:", fill=(200, 200, 200, 255), font=font_sub, anchor="mm")
    draw.text((540, y0 + 665), "S.No. 188 H.No. 2, Narayan Nagar Road,", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
    draw.text((540, y0 + 705), "Titwala (East) 421605, Dist: Thane", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")

    draw.text((540, y0 + 785), "MahaRERA Registration No: P51700054620", fill=(255, 215, 0, 255), font=font_rera, anchor="mm")

    frame_bgr = cv2.cvtColor(np.array(canvas.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()

# Concatenate all 6 top segments into top_flow_track.mp4
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
