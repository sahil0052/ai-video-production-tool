import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes" / "rendered_segments"
work_dir.mkdir(parents=True, exist_ok=True)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
flow_dir = base_dir / "renderer" / "public" / "flow_videos"
mmanas_dir = Path(r"C:\Users\HPUSER\Videos\mmanas")
deliverable_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes"

print("Rendering Nisha Homes Broadcast Top Track (1080x960 Edge-to-Edge, Zero Clutter)...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')

try:
    font_bold_lg = ImageFont.truetype("arialbd.ttf", 46)
    font_bold_md = ImageFont.truetype("arialbd.ttf", 36)
    font_bold_sm = ImageFont.truetype("arialbd.ttf", 28)
    font_impact_lg = ImageFont.truetype("impact.ttf", 56)
    font_impact_md = ImageFont.truetype("impact.ttf", 44)
except:
    font_bold_lg = ImageFont.load_default()
    font_bold_md = font_bold_lg
    font_bold_sm = font_bold_lg
    font_impact_lg = font_bold_lg
    font_impact_md = font_bold_lg

def fit_cover(pil_img, target_w=1080, target_h=960, scale_boost=1.0):
    """Resizes and crops any PIL image to fill target_w x target_h edge-to-edge"""
    w, h = pil_img.size
    ratio = max(target_w / w, target_h / h) * scale_boost
    nw, nh = int(w * ratio), int(h * ratio)
    resized = pil_img.resize((nw, nh), Image.Resampling.LANCZOS)
    cx, cy = nw // 2, nh // 2
    return resized.crop((cx - target_w // 2, cy - target_h // 2, cx + target_w // 2, cy + target_h // 2))

def fit_cover_cv2(frame, target_w=1080, target_h=960):
    """Resizes and crops a cv2 frame to fill target_w x target_h edge-to-edge"""
    fh, fw = frame.shape[:2]
    ratio = max(target_w / fw, target_h / fh)
    nw, nh = int(fw * ratio), int(fh * ratio)
    resized = cv2.resize(frame, (nw, nh))
    cx, cy = nw // 2, nh // 2
    return resized[cy - target_h // 2 : cy + target_h // 2, cx - target_w // 2 : cx + target_w // 2]

# =========================================================================
# CLIP 1 [0.00s - 3.58s] (3.58s, 108 frames): Price Trap vs Right Deal
# =========================================================================
seg1_path = work_dir / "seg1_price_trap.mp4"
out = cv2.VideoWriter(str(seg1_path), fourcc, 30.0, (1080, 960))
img1 = Image.open(art_dir / "nisha_price_vs_deal_169_1788174575555.jpg").convert("RGB")

for f in range(108):
    t = f / 30.0
    scale = 1.0 + 0.07 * (t / 3.58)
    cropped = fit_cover(img1, 1080, 960, scale_boost=scale)
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg1:", seg1_path)

# =========================================================================
# CLIP 2 [3.58s - 8.80s] (5.22s, 157 frames): 3 Pillars (Location, Project, Possession)
# =========================================================================
seg2_path = work_dir / "seg2_three_pillars.mp4"
out = cv2.VideoWriter(str(seg2_path), fourcc, 30.0, (1080, 960))
img_loc = Image.open(art_dir / "nisha_location_aerial_169_1788174598183.jpg").convert("RGB")
img_proj = Image.open(art_dir / "nisha_luxury_clubhouse_facade_1788174430404.jpg").convert("RGB")
img_poss = Image.open(art_dir / "nisha_possession_golden_key_1788174453674.jpg").convert("RGB")

# 157 frames total: 0-52 Location (1.73s), 52-104 Project (1.73s), 104-157 Possession (1.76s)
for f in range(157):
    if f < 52:
        img_curr = img_loc
        t = f / 52.0
    elif f < 104:
        img_curr = img_proj
        t = (f - 52) / 52.0
    else:
        img_curr = img_poss
        t = (f - 104) / 53.0
    
    scale = 1.0 + 0.06 * t
    cropped = fit_cover(img_curr, 1080, 960, scale_boost=scale)
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg2:", seg2_path)

# =========================================================================
# CLIP 3 [8.80s - 14.90s] (6.10s, 183 frames): Ready-to-Move & Google Flow Scale
# =========================================================================
seg3_path = work_dir / "seg3_ready_investment.mp4"
out = cv2.VideoWriter(str(seg3_path), fourcc, 30.0, (1080, 960))
img_ready = Image.open(art_dir / "nisha_ready_interior_169_1788174622199.jpg").convert("RGB")
flow_scale_vid = cv2.VideoCapture(str(flow_dir / "flow_liquidity_scale.mp4"))

for f in range(183):
    if f < 90:
        t = f / 90.0
        scale = 1.0 + 0.06 * t
        cropped = fit_cover(img_ready, 1080, 960, scale_boost=scale)
        frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    else:
        ret, fl_frame = flow_scale_vid.read()
        if not ret:
            flow_scale_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, fl_frame = flow_scale_vid.read()
        frame_bgr = fit_cover_cv2(fl_frame, 1080, 960)
        
    out.write(frame_bgr)
flow_scale_vid.release()
out.release()
print("Saved seg3:", seg3_path)

# =========================================================================
# CLIP 4 [14.90s - 21.00s] (6.10s, 183 frames): Real Walkthrough
# =========================================================================
seg4_path = work_dir / "seg4_real_walkthrough.mp4"
out = cv2.VideoWriter(str(seg4_path), fourcc, 30.0, (1080, 960))
mmanas_vid = cv2.VideoCapture(str(mmanas_dir / "video_2026-08-30_17-42-01.mp4"))

for f in range(183):
    ret, m_frame = mmanas_vid.read()
    if not ret:
        mmanas_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, m_frame = mmanas_vid.read()
    frame_bgr = fit_cover_cv2(m_frame, 1080, 960)
    out.write(frame_bgr)
mmanas_vid.release()
out.release()
print("Saved seg4:", seg4_path)

# =========================================================================
# CLIP 5 [21.00s - 28.50s] (7.50s, 225 frames): 4 Cities & 3 Tiers (Aerial + Sleek Text)
# =========================================================================
seg5_path = work_dir / "seg5_four_cities_tiers.mp4"
out = cv2.VideoWriter(str(seg5_path), fourcc, 30.0, (1080, 960))
img_ncr = Image.open(art_dir / "nisha_location_aerial_169_1788174598183.jpg").convert("RGB")

for f in range(225):
    t = f / 225.0
    scale = 1.0 + 0.08 * t
    cropped = fit_cover(img_ncr, 1080, 960, scale_boost=scale).convert("RGBA")
    
    # Broadcast overlay matching exact user requirement
    card = Image.new("RGBA", (1000, 130), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    for y in range(130):
        alpha = int(200 + 40 * (y / 130))
        cd.line([(0, y), (1000, y)], fill=(12, 18, 28, alpha))
    cd.rectangle([0, 0, 999, 129], outline=(255, 215, 0, 240), width=2)
    
    cd.text((500, 38), "GURGAON | NOIDA | GHAZIABAD | SOUTH DELHI", fill=(255, 255, 255, 255), font=font_bold_md, anchor="mm")
    cd.text((500, 90), "AFFORDABLE | ECONOMY | PREMIUM | READY-TO-MOVE", fill=(255, 215, 0, 255), font=font_bold_sm, anchor="mm")
    
    cropped.paste(card, (40, 780), card)
    frame_bgr = cv2.cvtColor(np.array(cropped.convert("RGB")), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved seg5:", seg5_path)

# =========================================================================
# CLIP 6 [28.50s - 33.50s] (5.00s, 150 frames): Selling Property Walkthrough
# =========================================================================
seg6_path = work_dir / "seg6_selling_ready.mp4"
out = cv2.VideoWriter(str(seg6_path), fourcc, 30.0, (1080, 960))
mmanas_vid4 = cv2.VideoCapture(str(mmanas_dir / "video_2026-08-30_17-42-01 (4).mp4"))

for f in range(150):
    ret, m_frame = mmanas_vid4.read()
    if not ret:
        mmanas_vid4.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, m_frame = mmanas_vid4.read()
    frame_bgr = fit_cover_cv2(m_frame, 1080, 960)
    out.write(frame_bgr)
mmanas_vid4.release()
out.release()
print("Saved seg6:", seg6_path)

# =========================================================================
# CLIP 7 [33.50s - 40.133s] (6.63s, 199 frames): Flow Trust Shield + Grand CTA
# =========================================================================
seg7_path = work_dir / "seg7_cta_endcard.mp4"
out = cv2.VideoWriter(str(seg7_path), fourcc, 30.0, (1080, 960))
flow_shield_vid = cv2.VideoCapture(str(flow_dir / "flow_trust_shield.mp4"))

for f in range(199):
    if f < 90:
        # Part A: Google Flow 3D Trust Shield (3.0s)
        ret, s_frame = flow_shield_vid.read()
        if not ret:
            flow_shield_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, s_frame = flow_shield_vid.read()
        frame_bgr = fit_cover_cv2(s_frame, 1080, 960)
    else:
        # Part B: Luxury Grand End Card (3.63s)
        end_card = Image.new("RGB", (1080, 960), (14, 18, 28))
        ed = ImageDraw.Draw(end_card)
        
        # Outer Gold Border
        ed.rectangle([30, 30, 1049, 929], outline=(255, 215, 0), width=3)
        ed.rectangle([38, 38, 1041, 921], outline=(255, 215, 0, 100), width=1)
        
        # Header Brand
        ed.text((540, 200), "NISHA HOMES", fill=(255, 215, 0), font=font_impact_lg, anchor="mm")
        ed.text((540, 290), "Property se aage, sahi deal par focus.", fill=(255, 255, 255), font=font_bold_md, anchor="mm")
        
        # Phone Box
        ed.rectangle([180, 390, 900, 520], fill=(22, 30, 46), outline=(255, 215, 0), width=3)
        ed.text((540, 435), "CALL / WHATSAPP", fill=(0, 220, 255), font=font_bold_sm, anchor="mm")
        ed.text((540, 480), "7303515710", fill=(255, 230, 80), font=font_impact_lg, anchor="mm")
        
        # City Footer
        ed.text((540, 630), "GURGAON  •  NOIDA  •  GHAZIABAD  •  SOUTH DELHI", fill=(0, 220, 255), font=font_bold_md, anchor="mm")
        ed.text((540, 710), "BUYING & SELLING ADVISORY", fill=(200, 210, 220), font=font_bold_sm, anchor="mm")
        
        frame_bgr = cv2.cvtColor(np.array(end_card), cv2.COLOR_RGB2BGR)
    
    out.write(frame_bgr)
flow_shield_vid.release()
out.release()
print("Saved seg7:", seg7_path)

# =========================================================================
# Concatenate all 7 top segments into top_flow_track.mp4
# =========================================================================
concat_txt = work_dir / "concat_list.txt"
with open(concat_txt, "w") as f:
    f.write(f"file '{seg1_path.as_posix()}'\n")
    f.write(f"file '{seg2_path.as_posix()}'\n")
    f.write(f"file '{seg3_path.as_posix()}'\n")
    f.write(f"file '{seg4_path.as_posix()}'\n")
    f.write(f"file '{seg5_path.as_posix()}'\n")
    f.write(f"file '{seg6_path.as_posix()}'\n")
    f.write(f"file '{seg7_path.as_posix()}'\n")

top_track_path = deliverable_dir / "top_flow_track.mp4"
cmd = [
    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(top_track_path)
]
subprocess.run(cmd, check=True)
print("Saved clean edge-to-edge top track:", top_track_path)
