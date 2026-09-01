import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
out_video_p = asset_dir / "vox_scene5_animated_chart.mp4"

w, h = 1080, 1920
fps = 30.0
duration = 8.2 # 22.00s to 30.18s
total_frames = int(duration * fps)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(str(out_video_p), fourcc, fps, (w, h))

def get_font(size, bold=True):
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf" if bold else "calibri.ttf"]
    for fn in font_names:
        fp = Path(r"C:\Windows\Fonts") / fn
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except:
                pass
    return ImageFont.load_default()

font_title = get_font(46, bold=True)
font_head = get_font(36, bold=True)
font_body = get_font(28, bold=False)
font_val = get_font(32, bold=True)
font_badge = get_font(26, bold=True)

for i in range(total_frames):
    progress = i / (total_frames - 1)
    
    # Base paper canvas
    canvas = Image.new("RGBA", (w, h), (246, 244, 238, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Grid lines
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=(226, 222, 212, 255), width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=(226, 222, 212, 255), width=1)
        
    # Top Header Box
    draw.rounded_rectangle([(80, 80), (1000, 190)], radius=20, fill=(24, 28, 36, 255))
    draw.text((540, 135), "THE DOUBLE WHAMMY EFFECT", font=font_title, fill=(255, 215, 0, 255), anchor="mm")
    
    # Chart Area Card
    chart_x1, chart_y1 = 80, 240
    chart_x2, chart_y2 = 1000, 1100
    draw.rounded_rectangle([(chart_x1, chart_y1), (chart_x2, chart_y2)], radius=24, fill=(255, 255, 255, 255), outline=(200, 190, 175, 255), width=3)
    
    # Sub-grid inside chart
    for cy in range(chart_y1 + 80, chart_y2, 100):
        draw.line([(chart_x1 + 40, cy), (chart_x2 - 40, cy)], fill=(235, 230, 220, 255), width=1)
        
    draw.text((chart_x1 + 60, chart_y1 + 45), "INDIA GOLD PRICE SPIKE (Rs)", font=font_head, fill=(24, 28, 36, 255), anchor="lm")
    
    # Animated Curve Points
    # Baseline: x from chart_x1 + 80 to chart_x2 - 80
    start_x = chart_x1 + 80
    end_x = chart_x2 - 80
    curr_x = start_x + (end_x - start_x) * min(1.0, progress * 1.2)
    
    curve_points = []
    num_pts = 60
    for p_idx in range(num_pts):
        px = start_x + (end_x - start_x) * (p_idx / (num_pts - 1))
        if px > curr_x:
            break
        # Curve shape: starts flat around y=950, slight rise, then steep exponential climb to y=450
        norm_p = (px - start_x) / (end_x - start_x)
        py = 950 - (norm_p ** 2.2) * 500
        curve_points.append((px, py))
        
    if len(curve_points) > 1:
        # Draw shadow
        shadow_pts = [(pt[0], pt[1] + 4) for pt in curve_points]
        draw.line(shadow_pts, fill=(200, 150, 20, 120), width=8)
        # Draw gold curve
        draw.line(curve_points, fill=(230, 160, 20, 255), width=8)
        
        # Draw current tip
        tip_x, tip_y = curve_points[-1]
        draw.ellipse([(tip_x - 12, tip_y - 12), (tip_x + 12, tip_y + 12)], fill=(255, 215, 0, 255), outline=(24, 28, 36, 255), width=3)
        
        if progress > 0.4:
            # Show "Rs 1.5 LAKH" Callout Pill at tip
            draw.rounded_rectangle([(tip_x - 140, tip_y - 80), (tip_x + 140, tip_y - 20)], radius=12, fill=(220, 40, 40, 255))
            draw.text((tip_x, tip_y - 50), "Rs 1,50,000 / 10g", font=font_val, fill=(255, 255, 255, 255), anchor="mm")
            
    # Bottom Explanatory 2 Drivers Cards
    card1_y1, card1_y2 = 1140, 1360
    draw.rounded_rectangle([(80, card1_y1), (520, card1_y2)], radius=20, fill=(255, 255, 255, 255), outline=(210, 160, 40, 255), width=3)
    draw.rounded_rectangle([(80, card1_y1), (520, card1_y1 + 60)], radius=20, fill=(245, 195, 35, 255))
    draw.text((300, card1_y1 + 30), "DRIVER 1", font=font_badge, fill=(24, 28, 36, 255), anchor="mm")
    draw.text((300, card1_y1 + 100), "Global Gold ($) UP", font=font_head, fill=(24, 28, 36, 255), anchor="mm")
    draw.text((300, card1_y1 + 160), "Rising international demand", font=font_body, fill=(100, 110, 120, 255), anchor="mm")

    draw.rounded_rectangle([(560, card1_y1), (1000, card1_y2)], radius=20, fill=(255, 255, 255, 255), outline=(220, 60, 60, 255), width=3)
    draw.rounded_rectangle([(560, card1_y1), (1000, card1_y1 + 60)], radius=20, fill=(220, 60, 60, 255))
    draw.text((780, card1_y1 + 30), "DRIVER 2", font=font_badge, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((780, card1_y1 + 100), "USD / INR (Rs) UP", font=font_head, fill=(220, 40, 40, 255), anchor="mm")
    draw.text((780, card1_y1 + 160), "Rupee loses purchasing power", font=font_body, fill=(100, 110, 120, 255), anchor="mm")

    # Takeaway Banner
    draw.rounded_rectangle([(80, 1400), (1000, 1540)], radius=20, fill=(24, 28, 36, 255), outline=(255, 215, 0, 255), width=2)
    draw.text((540, 1445), "RESULT: DOUBLE MULTIPLIER EFFECT", font=font_head, fill=(255, 215, 0, 255), anchor="mm")
    draw.text((540, 1495), "Both factors compound to create the historic price record", font=font_body, fill=(220, 220, 220, 255), anchor="mm")

    # Write frame
    out_frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGR)
    out.write(out_frame)

out.release()
print("Saved procedural animated Vox chart video: vox_scene5_animated_chart.mp4!")
