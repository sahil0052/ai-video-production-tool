import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageFilter
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831" / "rendered_segments"
work_dir.mkdir(parents=True, exist_ok=True)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
deliverable_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831"

print("Rendering 0831 Clean Top Track (Zero Text Clutter, Pure 3D Visuals)...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')

# =========================================================================
# SEGMENT 1 [0.0s - 7.5s] (7.5s, 225 frames): Brain Logic vs Emotion
# =========================================================================
seg1_path = work_dir / "seg1_brain_logic_emotion.mp4"
out = cv2.VideoWriter(str(seg1_path), fourcc, 30.0, (1080, 960))
img1 = Image.open(art_dir / "trade_brain_logic_vs_emotion_1788159331124.jpg").convert("RGB")

for f in range(225):
    t = f / 30.0
    scale = 1.0 + 0.08 * (t / 7.5)
    w = int(img1.width * scale)
    h = int(img1.height * scale)
    scaled = img1.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = w // 2, int(h * 0.50)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg1:", seg1_path)

# =========================================================================
# SEGMENT 2 [7.5s - 14.5s] (7.0s, 210 frames): Overconfidence & Leverage Trap
# =========================================================================
seg2_path = work_dir / "seg2_overconfidence_leverage.mp4"
out = cv2.VideoWriter(str(seg2_path), fourcc, 30.0, (1080, 960))
img2 = Image.open(art_dir / "trade_overconfidence_leverage_1788159356165.jpg").convert("RGB")

for f in range(210):
    t = f / 30.0
    scale = 1.0 + 0.07 * (t / 7.0)
    w = int(img2.width * scale)
    h = int(img2.height * scale)
    scaled = img2.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = int(w * 0.52), int(h * 0.50)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg2:", seg2_path)

# =========================================================================
# SEGMENT 3 [14.5s - 22.0s] (7.5s, 225 frames): Fear & Greed Scale
# =========================================================================
seg3_path = work_dir / "seg3_fear_greed_scale.mp4"
out = cv2.VideoWriter(str(seg3_path), fourcc, 30.0, (1080, 960))
img3 = Image.open(art_dir / "trade_fear_and_greed_scale_1788159445738.jpg").convert("RGB")

for f in range(225):
    t = f / 30.0
    scale = 1.0 + 0.07 * (t / 7.5)
    w = int(img3.width * scale)
    h = int(img3.height * scale)
    scaled = img3.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = w // 2, int(h * 0.48)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg3:", seg3_path)

# =========================================================================
# SEGMENT 4 [22.0s - 29.5s] (7.5s, 225 frames): Revenge Trading Trap
# =========================================================================
seg4_path = work_dir / "seg4_revenge_trap.mp4"
out = cv2.VideoWriter(str(seg4_path), fourcc, 30.0, (1080, 960))
img4 = Image.open(art_dir / "trade_revenge_trading_trap_1788159586337.jpg").convert("RGB")

for f in range(225):
    t = f / 30.0
    scale = 1.0 + 0.08 * (t / 7.5)
    w = int(img4.width * scale)
    h = int(img4.height * scale)
    scaled = img4.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = w // 2, int(h * 0.48)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg4:", seg4_path)

# =========================================================================
# SEGMENT 5 [29.5s - 36.5s] (7.0s, 210 frames): Emotion Overwrites Logic
# =========================================================================
seg5_path = work_dir / "seg5_emotion_overwrites_logic.mp4"
out = cv2.VideoWriter(str(seg5_path), fourcc, 30.0, (1080, 960))
img5 = Image.open(art_dir / "trade_emotion_overwrites_logic_1788159635504.jpg").convert("RGB")

for f in range(210):
    t = f / 30.0
    scale = 1.0 + 0.07 * (t / 7.0)
    w = int(img5.width * scale)
    h = int(img5.height * scale)
    scaled = img5.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = int(w * 0.52), int(h * 0.46)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg5:", seg5_path)

# =========================================================================
# SEGMENT 6 [36.5s - 44.40s] (7.90s, 237 frames): Rules Discipline & Follow CTA
# =========================================================================
seg6_path = work_dir / "seg6_rules_discipline_cta.mp4"
out = cv2.VideoWriter(str(seg6_path), fourcc, 30.0, (1080, 960))
img6 = Image.open(art_dir / "trade_rules_discipline_trophy_1788159662509.jpg").convert("RGB")

for f in range(237):
    t = f / 30.0
    scale = 1.0 + 0.07 * (t / 7.9)
    w = int(img6.width * scale)
    h = int(img6.height * scale)
    scaled = img6.resize((w, h), Image.Resampling.LANCZOS)
    
    cx, cy = w // 2, int(h * 0.50)
    crop_x0 = max(0, cx - 540)
    crop_y0 = max(0, cy - 480)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + 1080, crop_y0 + 960))
    
    frame_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
    out.write(frame_bgr)
out.release()
print("Saved clean seg6:", seg6_path)

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

top_track_path = deliverable_dir / "top_flow_track.mp4"
cmd = [
    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(top_track_path)
]
subprocess.run(cmd, check=True)
print("Saved clean complete top track (Zero Text Overlays):", top_track_path)
