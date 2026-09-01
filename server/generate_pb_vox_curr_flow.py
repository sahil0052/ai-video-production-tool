import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
out_video_p = asset_dir / "vox_scene3_currency_flow.mp4"

w, h = 1080, 1920
fps = 30.0
duration = 7.88
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

font_title = get_font(44, bold=True)
font_head = get_font(34, bold=True)
font_body = get_font(28, bold=False)
font_bold_body = get_font(30, bold=True)
font_val = get_font(28, bold=True)

for i in range(total_frames):
    progress = i / (total_frames - 1)
    
    canvas = Image.new("RGBA", (w, h), (246, 244, 238, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Grid lines
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=(226, 222, 212, 255), width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=(226, 222, 212, 255), width=1)
        
    # Top Header Box
    draw.rounded_rectangle([(80, 80), (1000, 190)], radius=20, fill=(24, 28, 36, 255))
    draw.text((540, 135), "WHY DOLLAR MAKES GOLD MEHENGA", font=font_title, fill=(255, 215, 0, 255), anchor="mm")
    
    # Case 1 Card (Normal Exchange Rate)
    draw.rounded_rectangle([(80, 230), (1000, 660)], radius=24, fill=(255, 255, 255, 255), outline=(40, 120, 220, 255), width=3)
    draw.rounded_rectangle([(80, 230), (1000, 310)], radius=24, fill=(40, 120, 220, 255))
    draw.text((540, 270), "CASE 1: BASELINE EXCHANGE RATE ($1 = Rs 80)", font=font_head, fill=(255, 255, 255, 255), anchor="mm")
    
    draw.text((140, 370), "• Global Gold Price:", font=font_body, fill=(60, 70, 80, 255), anchor="lm")
    draw.text((800, 370), "$2,500 / oz", font=font_bold_body, fill=(24, 28, 36, 255), anchor="rm")
    
    draw.text((140, 440), "• USD / INR Exchange:", font=font_body, fill=(60, 70, 80, 255), anchor="lm")
    draw.text((800, 440), "Rs 80 / $1", font=font_bold_body, fill=(24, 28, 36, 255), anchor="rm")
    
    draw.rounded_rectangle([(140, 510), (940, 610)], radius=16, fill=(240, 246, 255, 255), outline=(40, 120, 220, 255), width=2)
    draw.text((540, 560), "INDIA LANDED COST = Rs 2,00,000", font=font_val, fill=(30, 90, 180, 255), anchor="mm")
    
    # Case 2 Card (Dollar Surges / Rupee Weakens)
    if progress > 0.15:
        draw.rounded_rectangle([(80, 700), (1000, 1150)], radius=24, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=3)
        draw.rounded_rectangle([(80, 700), (1000, 780)], radius=24, fill=(220, 50, 50, 255))
        draw.text((540, 740), "CASE 2: DOLLAR MEHENGA ($1 = Rs 90)", font=font_head, fill=(255, 255, 255, 255), anchor="mm")
        
        draw.text((140, 840), "• Global Gold Price:", font=font_body, fill=(60, 70, 80, 255), anchor="lm")
        draw.text((800, 840), "$2,500 / oz (NO CHANGE!)", font=font_bold_body, fill=(24, 28, 36, 255), anchor="rm")
        
        draw.text((140, 910), "• USD / INR Exchange:", font=font_body, fill=(60, 70, 80, 255), anchor="lm")
        draw.text((800, 910), "Rs 90 / $1 (+12.5% SURGE)", font=font_bold_body, fill=(220, 40, 40, 255), anchor="rm")
        
        draw.rounded_rectangle([(140, 980), (940, 1090)], radius=16, fill=(255, 240, 240, 255), outline=(220, 50, 50, 255), width=2)
        draw.text((540, 1035), "INDIA LANDED COST = Rs 2,25,000 (+Rs 25,000 EXTRA!)", font=font_val, fill=(200, 30, 30, 255), anchor="mm")
        
    # Takeaway Box
    if progress > 0.4:
        draw.rounded_rectangle([(80, 1200), (1000, 1540)], radius=24, fill=(24, 28, 36, 255), outline=(255, 215, 0, 255), width=2)
        draw.text((540, 1260), "CRITICAL MARKET TAKEAWAY", font=font_head, fill=(255, 215, 0, 255), anchor="mm")
        draw.text((540, 1330), "Global gold price did not increase at all...", font=font_body, fill=(200, 200, 200, 255), anchor="mm")
        draw.text((540, 1390), "India paid more simply because:", font=font_body, fill=(200, 200, 200, 255), anchor="mm")
        draw.text((540, 1460), "THE INDIAN RUPEE LOST VALUE!", font=font_head, fill=(255, 80, 80, 255), anchor="mm")

    out_frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGBA2BGR)
    out.write(out_frame)

out.release()
print("Saved refreshed vox_scene3_currency_flow.mp4!")
