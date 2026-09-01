import cv2
import numpy as np
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ffmpeg = get_ffmpeg_exe()

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
clip_dir = work_dir / "flow_clips"
asset_dir = work_dir / "assets"

src_vid = r"D:\Downloads\0901.mp4"
temp_video = work_dir / "temp_composed_video.mp4"
norm_audio = work_dir / "norm_audio.wav"
final_video = work_dir / "edited.mp4"

# 1. Audio Normalization
print("Normalizing audio to -14 LUFS...")
cmd_audio = [
    ffmpeg, "-y", "-i", src_vid,
    "-af", "loudnorm=I=-14:LRA=7:TP=-1.5",
    "-ar", "44100", "-ac", "2",
    str(norm_audio)
]
subprocess.run(cmd_audio, check=True)

# 2. Font Setup
def get_font(size, bold=True):
    names = ["impact.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    for fn in names:
        fp = Path(r"C:\Windows\Fonts") / fn
        if fp.exists():
            try: return ImageFont.truetype(str(fp), size)
            except: pass
    return ImageFont.load_default()

font_sub_l1 = get_font(48, True)
font_sub_l2 = get_font(52, True)
font_outro_title = get_font(38, True)
font_outro_sub = get_font(26, False)

# 3. Load ALL Google Flow Clips
flow_clips = {}
clip_files = {
    "dollar_surge":     clip_dir / "flow_0901_01_dollar_surge.mp4",
    "double_whammy":    clip_dir / "flow_0901_02_double_whammy.mp4",
    "investor_check":   clip_dir / "flow_0901_03_investor_checklist.mp4",
    "gold_paradox":     clip_dir / "flow_0901_04_gold_paradox.mp4",
    "formula_engine":   clip_dir / "flow_0901_05_formula_engine.mp4",
    "smart_analysis":   clip_dir / "flow_0901_06_smart_analysis.mp4",
}
for name, fp in clip_files.items():
    cap = cv2.VideoCapture(str(fp))
    if not cap.isOpened():
        print(f"❌ MANDATORY HALT: Cannot open Flow clip {fp.name}!")
        sys.exit(1)
    flow_clips[name] = cap
    fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_c = cap.get(cv2.CAP_PROP_FPS) or 24
    print(f"  Loaded {fp.name}: {fc} frames @ {fps_c:.0f} fps ({fc/fps_c:.1f}s)")

# Load new logo for outro
logo_path = asset_dir / "profit_bricks_new_logo.png"
logo_img = Image.open(logo_path).convert("RGBA") if logo_path.exists() else None

if logo_img:
    lw, lh = logo_img.size
    new_lw = 400
    new_lh = int(lh * (new_lw / lw))
    logo_img_resized = logo_img.resize((new_lw, new_lh), Image.Resampling.LANCZOS)
else:
    logo_img_resized = None

def get_flow_frame(clip_cap, t_rel, target_w=1080, target_h=1920):
    fps_c = clip_cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(clip_cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    f_num = int(t_rel * fps_c) % max(total, 1)
    clip_cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = clip_cap.read()
    if not ret:
        clip_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = clip_cap.read()
    if ret:
        pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        if pil.size != (target_w, target_h):
            pil = pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
        return pil
    return Image.new("RGBA", (target_w, target_h), (20, 20, 20, 255))

# 4. Timeline: ALL Flow Clips, ZERO self-made animations
TIMELINE = [
    {"start": 0.00,  "end": 2.70,  "layout": "FULL_CHAR"},
    {"start": 2.70,  "end": 7.14,  "layout": "SPLIT_FLOW", "clip": "gold_paradox"},
    {"start": 7.14,  "end": 15.02, "layout": "FULL_FLOW",  "clip": "dollar_surge"},
    {"start": 15.02, "end": 22.00, "layout": "SPLIT_FLOW", "clip": "formula_engine"},
    {"start": 22.00, "end": 30.18, "layout": "FULL_FLOW",  "clip": "double_whammy"},
    {"start": 30.18, "end": 38.02, "layout": "FULL_CHAR"},
    {"start": 38.02, "end": 44.54, "layout": "SPLIT_FLOW", "clip": "smart_analysis"},
    {"start": 44.54, "end": 47.51, "layout": "OUTRO_FLOW", "clip": "investor_check"},
]

# 5. Subtitles (Yellow + White only)
SUBTITLES = [
    {"start": 0.00,  "end": 2.70,  "l1": ("GOLD AT RS 1.5 LAKH?", (255, 215, 0)), "l2": ("ALL-TIME HIGH RECORD!", (255, 255, 255))},
    {"start": 2.70,  "end": 5.10,  "l1": ("LEKIN KYA GOLD", (255, 255, 255)), "l2": ("ACTUALLY ITNA STRONG HUA?", (255, 215, 0))},
    {"start": 5.10,  "end": 7.14,  "l1": ("YA PROBLEM GOLD MEIN NAHI...", (255, 255, 255)), "l2": ("RUPEE MEIN HAI?", (255, 215, 0))},
    {"start": 7.14,  "end": 10.00, "l1": ("MAAN LO GLOBAL GOLD PRICE", (255, 255, 255)), "l2": ("BILKUL SAME HAI ($)", (255, 215, 0))},
    {"start": 10.00, "end": 15.02, "l1": ("LEKIN AGAR DOLLAR MEHENGA HO JAAYE", (255, 255, 255)), "l2": ("INDIA KO ZYADA RUPEES DENE PADENGE!", (255, 215, 0))},
    {"start": 15.02, "end": 19.30, "l1": ("ACTUALLY DONO CHEEZEIN MATTER KARTI HAIN", (255, 255, 255)), "l2": ("GLOBAL GOLD + USD/INR FOREX", (255, 215, 0))},
    {"start": 19.30, "end": 23.50, "l1": ("RUPEE WEAK HONE PAR BHI", (255, 255, 255)), "l2": ("GOLD MEHENGA HO JAATA HAI!", (255, 215, 0))},
    {"start": 23.50, "end": 27.20, "l1": ("KABHI SIRF RUPEE WEAK HOTA HAI...", (255, 215, 0)), "l2": ("AUR GOLD PRICE SAME HOTA HAI", (255, 255, 255))},
    {"start": 27.20, "end": 30.18, "l1": ("AUR JAB DONO SAATH MEIN MOVE KAREIN", (255, 255, 255)), "l2": ("INDIA MEIN SUPER SPIKE AATA HAI!", (255, 215, 0))},
    {"start": 30.18, "end": 34.00, "l1": ("ISLIYE GOLD RATE DEKHTE WAQT", (255, 255, 255)), "l2": ("SIRF GOLD KO MAT DEKHO!", (255, 215, 0))},
    {"start": 34.00, "end": 38.02, "l1": ("GLOBAL GOLD ($) KE SAATH", (255, 255, 255)), "l2": ("USD/INR RATE BHI CHECK KARO!", (255, 215, 0))},
    {"start": 38.02, "end": 41.90, "l1": ("NEXT TIME GOLD RATE JUMP KARE", (255, 255, 255)), "l2": ("CHECK: GOLD MOVED YA RUPEE WEAK?", (255, 215, 0))},
    {"start": 41.90, "end": 44.54, "l1": ("YA DONO HI HUA HAI?", (255, 215, 0)), "l2": ("SMART INVESTOR ANALYSIS!", (255, 255, 255))},
    {"start": 44.54, "end": 47.51, "l1": ("MARKET CONCEPTS IN SIMPLE HINDI", (255, 255, 255)), "l2": ("FOLLOW PROFIT BRICKS!", (255, 215, 0))}
]

def draw_text_outline(draw, pos, text, font, fill, outline=(0,0,0,255), w=5):
    x, y = pos
    for dx in range(-w, w+1):
        for dy in range(-w, w+1):
            if dx*dx + dy*dy <= w*w:
                draw.text((x+dx, y+dy), text, font=font, fill=outline, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")

# 6. Main Render Loop
cap = cv2.VideoCapture(src_vid)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w, h = 1080, 1920

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(temp_video), fourcc, fps, (w, h))

print(f"Rendering Flow-Only Master: {total_frames} frames @ {fps} fps...")

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break

    t = frame_idx / fps
    seg = next((s for s in TIMELINE if s["start"] <= t < s["end"]), TIMELINE[-1])
    layout = seg["layout"]
    t_rel = t - seg["start"]

    canvas = Image.new("RGBA", (w, h), (20, 20, 20, 255))
    char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")

    if layout == "FULL_CHAR":
        canvas.paste(char_pil, (0, 0))

    elif layout == "FULL_FLOW":
        clip_name = seg["clip"]
        flow_frame = get_flow_frame(flow_clips[clip_name], t_rel)
        canvas.paste(flow_frame, (0, 0))

    elif layout == "SPLIT_FLOW":
        clip_name = seg["clip"]
        flow_frame = get_flow_frame(flow_clips[clip_name], t_rel, 1080, 960)
        canvas.paste(flow_frame, (0, 0))

        char_cropped = char_pil.crop((0, 150, 1080, 1450)).resize((1080, 960), Image.Resampling.LANCZOS)
        canvas.paste(char_cropped, (0, 960))

        draw_sep = ImageDraw.Draw(canvas)
        draw_sep.rectangle([(0, 955), (1080, 965)], fill=(24, 28, 36, 255))
        draw_sep.rectangle([(0, 958), (1080, 962)], fill=(255, 215, 0, 255))

    elif layout == "OUTRO_FLOW":
        clip_name = seg["clip"]
        flow_frame = get_flow_frame(flow_clips[clip_name], t_rel)
        canvas.paste(flow_frame, (0, 0))

        # Overlay Glass Card with New Official Profit Bricks Logo
        draw_outro = ImageDraw.Draw(canvas)
        draw_outro.rounded_rectangle([(100, 180), (980, 880)], radius=24,
                                     fill=(16, 20, 28, 235), outline=(255, 215, 0, 255), width=3)
        
        if logo_img_resized:
            lx = (1080 - logo_img_resized.width) // 2
            ly = 220
            canvas.paste(logo_img_resized, (lx, ly), logo_img_resized)
            
        draw_outro.text((540, 740), "FOREX AUTOMATION & TRADING", font=font_outro_title, fill=(255, 215, 0, 255), anchor="mm")
        draw_outro.text((540, 805), "Master Market Economics in Simple Hindi", font=font_outro_sub, fill=(220, 220, 220, 255), anchor="mm")

    # Subtitles
    draw = ImageDraw.Draw(canvas)
    sub = next((s for s in SUBTITLES if s["start"] <= t < s["end"]), None)
    if sub:
        l1_text, l1_col = sub["l1"]
        l2_text, l2_col = sub["l2"]
        y1, y2 = 1750, 1825

        draw.rounded_rectangle([(60, y1-38), (1020, y2+48)], radius=18,
                               fill=(16, 20, 28, 225), outline=(255, 215, 0, 200), width=2)
        draw_text_outline(draw, (540, y1), l1_text, font_sub_l1, l1_col)
        draw_text_outline(draw, (540, y2), l2_text, font_sub_l2, l2_col)

    out_frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGR)
    out.write(out_frame)
    frame_idx += 1

    if frame_idx % 200 == 0:
        print(f"  Rendering: {frame_idx}/{total_frames} ({frame_idx/total_frames*100:.1f}%)")

cap.release()
for c in flow_clips.values():
    c.release()
out.release()
print("Visual compositing done! Muxing audio...")

# 7. Mux Audio
cmd_mux = [
    ffmpeg, "-y",
    "-i", str(temp_video),
    "-i", str(norm_audio),
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    "-shortest",
    str(final_video)
]
subprocess.run(cmd_mux, check=True)

sz = final_video.stat().st_size / (1024*1024)
print(f"\nMASTER VIDEO COMPLETE: {final_video} ({sz:.1f} MB)")
