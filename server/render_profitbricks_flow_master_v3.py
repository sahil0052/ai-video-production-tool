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

font_sub_l1 = get_font(48, bold=True)
font_sub_l2 = get_font(52, bold=True)
font_ticker = get_font(24, bold=True)
font_ticker_val = get_font(30, bold=True)

# 3. Load Static Graphics
img_beat2 = Image.open(asset_dir / "vox_beat2_paradox.png").convert("RGBA")
img_beat4 = Image.open(asset_dir / "vox_beat4_formula.png").convert("RGBA")
img_beat7 = Image.open(asset_dir / "vox_beat7_checklist.png").convert("RGBA")
img_beat8 = Image.open(asset_dir / "vox_beat8_outro.png").convert("RGBA")

# 4. Load Animated Video Elements
cap_scene3 = cv2.VideoCapture(str(asset_dir / "vox_scene3_currency_flow.mp4"))
cap_scene5 = cv2.VideoCapture(str(asset_dir / "vox_scene5_animated_chart.mp4"))

def get_anim_frame(cap, t_rel, target_size=(1080, 1920)):
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 100
    f_num = int(t_rel * fps) % total
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        if pil_img.size != target_size:
            pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
        return pil_img
    return Image.new("RGBA", target_size, (246, 244, 238, 255))

# 5. Timeline Definition (Duration: 47.51s @ 30 FPS)
TIMELINE = [
    {"start": 0.00,  "end": 2.70,  "layout": "FULL_CHAR"},
    {"start": 2.70,  "end": 7.14,  "layout": "SPLIT_50_50", "asset": img_beat2},
    {"start": 7.14,  "end": 15.02, "layout": "FULL_ANIM_VIDEO", "cap": cap_scene3},
    {"start": 15.02, "end": 22.00, "layout": "SPLIT_50_50", "asset": img_beat4},
    {"start": 22.00, "end": 30.18, "layout": "FULL_ANIM_VIDEO", "cap": cap_scene5},
    {"start": 30.18, "end": 38.02, "layout": "FULL_CHAR_HUD"},
    {"start": 38.02, "end": 44.54, "layout": "SPLIT_50_50", "asset": img_beat7},
    {"start": 44.54, "end": 47.51, "layout": "FULL_STATIC", "asset": img_beat8}
]

# Subtitles with Clean Dual-Tone Yellow & White
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

print(f"Rendering Clean Vox Explainer Master: {total_frames} frames @ {fps} fps ({w}x{h})...")

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    t = frame_idx / fps
    seg = next((s for s in TIMELINE if s["start"] <= t < s["end"]), TIMELINE[-1])
    layout = seg["layout"]
    t_rel = t - seg["start"]
    
    canvas = Image.new("RGBA", (w, h), (246, 244, 238, 255))
    
    if layout in ["FULL_CHAR", "FULL_CHAR_HUD"]:
        char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        canvas.paste(char_pil, (0, 0))
        
        # Subtle HUD Tickers in Beat 6
        if layout == "FULL_CHAR_HUD":
            draw_hud = ImageDraw.Draw(canvas)
            # Tickers placed unobtrusively in top corners away from center face
            draw_hud.rounded_rectangle([(60, 160), (460, 270)], radius=16, fill=(24, 28, 36, 230), outline=(255, 215, 0, 255), width=2)
            draw_hud.text((260, 195), "XAU / USD (GOLD)", fill=(200, 200, 200, 255), font=font_ticker, anchor="mm")
            draw_hud.text((260, 235), "$2,745.80 / oz", fill=(255, 215, 0, 255), font=font_ticker_val, anchor="mm")
            
            draw_hud.rounded_rectangle([(620, 160), (1020, 270)], radius=16, fill=(24, 28, 36, 230), outline=(220, 50, 50, 255), width=2)
            draw_hud.text((820, 195), "USD / INR (FOREX)", fill=(200, 200, 200, 255), font=font_ticker, anchor="mm")
            draw_hud.text((820, 235), "Rs 84.62 (WEAK)", fill=(255, 80, 80, 255), font=font_ticker_val, anchor="mm")
            
    elif layout == "SPLIT_50_50":
        # Top 50%: Clean Vox Asset (1080x960)
        asset_img = seg["asset"]
        canvas.paste(asset_img, (0, 0))
        
        # Bottom 50%: Presenter with natural headroom (crop from 150 to 1450)
        char_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        char_cropped = char_pil.crop((0, 150, 1080, 1450)).resize((1080, 960), Image.Resampling.LANCZOS)
        canvas.paste(char_cropped, (0, 960))
        
        # Split separator bar
        draw_sep = ImageDraw.Draw(canvas)
        draw_sep.rectangle([(0, 954), (1080, 966)], fill=(24, 28, 36, 255))
        draw_sep.rectangle([(0, 957), (1080, 963)], fill=(255, 215, 0, 255))
        
    elif layout == "FULL_ANIM_VIDEO":
        # Full 1080x1920 Explanatory Procedural Animation (Beat 3 & Beat 5)
        anim_frame = get_anim_frame(seg["cap"], t_rel, (1080, 1920))
        canvas.paste(anim_frame, (0, 0))
        
    elif layout == "FULL_STATIC":
        # Full Outro Card (Beat 8)
        asset_img = seg["asset"]
        canvas.paste(asset_img, (0, 0))
        
    # --- Subtitles Overlay (Lower Third: Safe from Face/Neck) ---
    draw = ImageDraw.Draw(canvas)
    sub = next((s for s in SUBTITLES if s["start"] <= t < s["end"]), None)
    if sub:
        l1_text, l1_col = sub["l1"]
        l2_text, l2_col = sub["l2"]
        
        # Subtitle positioning: y1=1750, y2=1825 (Safely at bottom)
        y1, y2 = 1750, 1825
        
        # Sleek dark backing pill with gold hairline border
        draw.rounded_rectangle([(60, y1 - 38), (1020, y2 + 48)], radius=18, fill=(16, 20, 28, 225), outline=(255, 215, 0, 200), width=2)
        draw_text_with_outline(draw, (540, y1), l1_text, font_sub_l1, l1_col, (0, 0, 0, 255), 5)
        draw_text_with_outline(draw, (540, y2), l2_text, font_sub_l2, l2_col, (0, 0, 0, 255), 6)
        
    out_frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGR)
    out.write(out_frame)
    frame_idx += 1
    
    if frame_idx % 200 == 0:
        print(f"Master Rendering: {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)")

cap.release()
cap_scene3.release()
cap_scene5.release()
out.release()
print("Master visual compositing finished! Muxing high-fidelity audio...")

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
print("MASTER VIDEO RENDER COMPLETE:", str(final_video))
