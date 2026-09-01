import cv2
import numpy as np
import subprocess, json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ffmpeg = get_ffmpeg_exe()

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
flow_dir = work_dir / "flow_clips"

src_vid = r"D:\Downloads\0901.mp4"
temp_video = work_dir / "temp_composed_video.mp4"
norm_audio = work_dir / "norm_audio.wav"
final_video = work_dir / "edited.mp4"

# 1. EBU R128 Audio Normalization (-14 LUFS)
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
    font_names = ["impact.ttf", "arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf" if bold else "calibri.ttf"]
    for fn in font_names:
        fp = Path(r"C:\Windows\Fonts") / fn
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except:
                pass
    return ImageFont.load_default()

font_sub_l1 = get_font(50, bold=True)
font_sub_l2 = get_font(54, bold=True)

# 3. Load Static Graphics
img_beat2 = Image.open(asset_dir / "beat2_gold_vs_rupee.png").convert("RGBA")
img_beat4 = Image.open(asset_dir / "beat4_formula_breakdown.png").convert("RGBA")
img_beat8 = Image.open(asset_dir / "beat8_outro_card.png").convert("RGBA")

# 4. Load Google Flow Video Clips
cap_flow1 = cv2.VideoCapture(str(flow_dir / "flow_0901_01_dollar_surge.mp4"))
cap_flow2 = cv2.VideoCapture(str(flow_dir / "flow_0901_02_double_whammy.mp4"))
cap_flow3 = cv2.VideoCapture(str(flow_dir / "flow_0901_03_investor_checklist.mp4"))

def get_flow_frame(cap, t_rel, target_size=(1080, 1920)):
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 100
    f_num = int(t_rel * fps) % total
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        if pil_img.size != target_size:
            pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
        return pil_img
    return Image.new("RGBA", target_size, (24, 28, 36, 255))

# 5. Timeline Definition (Duration: 47.51s @ 30 FPS)
TIMELINE = [
    {"start": 0.00,  "end": 2.70,  "layout": "FULL_CHAR", "badge": "MARKET MILESTONE"},
    {"start": 2.70,  "end": 7.14,  "layout": "SPLIT_TOP_STATIC", "asset": img_beat2},
    {"start": 7.14,  "end": 15.02, "layout": "FULL_FLOW_VIDEO", "cap": cap_flow1, "badge": "GLOBAL CURRENCY FLOW"},
    {"start": 15.02, "end": 22.00, "layout": "SPLIT_TOP_STATIC", "asset": img_beat4},
    {"start": 22.00, "end": 30.18, "layout": "FULL_FLOW_VIDEO", "cap": cap_flow2, "badge": "THE DOUBLE WHAMMY"},
    {"start": 30.18, "end": 38.02, "layout": "FULL_CHAR", "badge": "INVESTOR RULE"},
    {"start": 38.02, "end": 44.54, "layout": "SPLIT_TOP_FLOW", "cap": cap_flow3},
    {"start": 44.54, "end": 47.51, "layout": "FULL_STATIC", "asset": img_beat8}
]

# Subtitles with Dual-Tone Yellow & White
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

def draw_text_with_outline(draw, pos, text, font, fill_color, outline_color=(0, 0, 0, 255), outline_w=5):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx*dx + dy*dy <= outline_w*outline_w:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill_color, anchor="mm")

# 6. Video Processing Loop
cap = cv2.VideoCapture(src_vid)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w, h = 1080, 1920

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(temp_video), fourcc, fps, (w, h))

print(f"Rendering Master Video with 3D Google Flow clips: {total_frames} frames @ {fps} fps ({w}x{h})...")

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    t = frame_idx / fps
    seg = next((s for s in TIMELINE if s["start"] <= t < s["end"]), TIMELINE[-1])
    layout = seg["layout"]
    t_rel = t - seg["start"]
    
    canvas = Image.new("RGBA", (w, h), (24, 28, 36, 255))
    
    if layout == "FULL_CHAR":
        char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        canvas.paste(char_pil, (0, 0))
        
        draw_top = ImageDraw.Draw(canvas)
        draw_top.rounded_rectangle([(40, 40), (360, 105)], radius=12, fill=(24, 28, 36, 230), outline=(255, 215, 0, 255), width=2)
        draw_top.text((200, 72), "PROFIT BRICKS", fill=(255, 255, 255, 255), font=get_font(26, bold=True), anchor="mm")
        
        badge_text = seg.get("badge", "MARKET ANALYSIS")
        draw_top.rounded_rectangle([(700, 40), (1040, 105)], radius=12, fill=(255, 215, 0, 240))
        draw_top.text((870, 72), badge_text, fill=(24, 28, 36, 255), font=get_font(24, bold=True), anchor="mm")
        
        if 30.18 <= t < 38.02:
            draw_top.rounded_rectangle([(60, 240), (480, 360)], radius=16, fill=(24, 28, 36, 230), outline=(255, 215, 0, 255), width=3)
            draw_top.text((270, 275), "XAU / USD (GLOBAL GOLD)", fill=(200, 200, 200, 255), font=get_font(22, bold=True), anchor="mm")
            draw_top.text((270, 320), "$2,745.80 / oz", fill=(255, 215, 0, 255), font=get_font(32, bold=True), anchor="mm")
            
            draw_top.rounded_rectangle([(600, 240), (1020, 360)], radius=16, fill=(24, 28, 36, 230), outline=(220, 50, 50, 255), width=3)
            draw_top.text((810, 275), "USD / INR (EXCHANGE)", fill=(200, 200, 200, 255), font=get_font(22, bold=True), anchor="mm")
            draw_top.text((810, 320), "Rs 84.62 (WEAK)", fill=(255, 80, 80, 255), font=get_font(32, bold=True), anchor="mm")
            
    elif layout == "SPLIT_TOP_STATIC":
        asset_img = seg["asset"]
        canvas.paste(asset_img, (0, 0))
        
        char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        char_cropped = char_pil.crop((0, 180, 1080, 1500)).resize((1080, 960), Image.Resampling.LANCZOS)
        canvas.paste(char_cropped, (0, 960))
        
        draw_sep = ImageDraw.Draw(canvas)
        draw_sep.rectangle([(0, 954), (1080, 966)], fill=(24, 28, 36, 255))
        draw_sep.rectangle([(0, 957), (1080, 963)], fill=(255, 215, 0, 255))
        
    elif layout == "SPLIT_TOP_FLOW":
        flow_top = get_flow_frame(seg["cap"], t_rel, (1080, 960))
        canvas.paste(flow_top, (0, 0))
        
        char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        char_cropped = char_pil.crop((0, 180, 1080, 1500)).resize((1080, 960), Image.Resampling.LANCZOS)
        canvas.paste(char_cropped, (0, 960))
        
        draw_sep = ImageDraw.Draw(canvas)
        draw_sep.rectangle([(0, 954), (1080, 966)], fill=(24, 28, 36, 255))
        draw_sep.rectangle([(0, 957), (1080, 963)], fill=(255, 215, 0, 255))
        
    elif layout == "FULL_FLOW_VIDEO":
        flow_full = get_flow_frame(seg["cap"], t_rel, (1080, 1920))
        canvas.paste(flow_full, (0, 0))
        
        draw_badge = ImageDraw.Draw(canvas)
        draw_badge.rounded_rectangle([(40, 40), (360, 105)], radius=12, fill=(24, 28, 36, 230), outline=(255, 215, 0, 255), width=2)
        draw_badge.text((200, 72), "PROFIT BRICKS", fill=(255, 255, 255, 255), font=get_font(26, bold=True), anchor="mm")
        
        badge_text = seg.get("badge", "3D AI FLOW")
        draw_badge.rounded_rectangle([(680, 40), (1040, 105)], radius=12, fill=(255, 215, 0, 240))
        draw_badge.text((860, 72), badge_text, fill=(24, 28, 36, 255), font=get_font(24, bold=True), anchor="mm")
        
    elif layout == "FULL_STATIC":
        asset_img = seg["asset"]
        canvas.paste(asset_img, (0, 0))
        
    # --- Subtitles Overlay ---
    draw = ImageDraw.Draw(canvas)
    sub = next((s for s in SUBTITLES if s["start"] <= t < s["end"]), None)
    if sub:
        l1_text, l1_col = sub["l1"]
        l2_text, l2_col = sub["l2"]
        
        y1, y2 = (1680, 1765) if "SPLIT" in layout or layout == "FULL_STATIC" else (1600, 1685)
        
        draw.rounded_rectangle([(60, y1 - 45), (1020, y2 + 55)], radius=18, fill=(16, 20, 28, 220), outline=(255, 215, 0, 200), width=2)
        draw_text_with_outline(draw, (540, y1), l1_text, font_sub_l1, l1_col, (0, 0, 0, 255), 5)
        draw_text_with_outline(draw, (540, y2), l2_text, font_sub_l2, l2_col, (0, 0, 0, 255), 6)
        
    out_frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGR)
    out.write(out_frame)
    frame_idx += 1
    
    if frame_idx % 200 == 0:
        print(f"Master Compositing: {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)")

cap.release()
cap_flow1.release()
cap_flow2.release()
cap_flow3.release()
out.release()
print("Master visual compositing complete! Muxing high-fidelity audio...")

# 7. Mux High-Fidelity Audio
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
print("ALL DONE: Master Video created successfully at:", str(final_video))
