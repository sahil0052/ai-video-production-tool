import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
asset_dir.mkdir(parents=True, exist_ok=True)

# 1. Process New Logo
new_logo_src = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42\.user_uploaded\media_1788263333234.jpg")
img_logo = Image.open(new_logo_src).convert("RGBA")
# Make background transparent if white
datas = img_logo.getdata()
newData = []
for item in datas:
    # If pixel is near white (>240 in all channels), make it transparent
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        newData.append((255, 255, 255, 0))
    else:
        newData.append(item)
img_logo.putdata(newData)
img_logo.save(asset_dir / "profit_bricks_new_logo.png")
print("Saved transparent new Profit Bricks logo!")

# 2. Font Helpers
def get_font(size, bold=True):
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf" if bold else "calibri.ttf", "segoeuib.ttf"]
    for fn in font_names:
        fp = Path(r"C:\Windows\Fonts") / fn
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except:
                pass
    return ImageFont.load_default()

font_title = get_font(44, bold=True)
font_card_head = get_font(34, bold=True)
font_body = get_font(28, bold=False)
font_bold_body = get_font(30, bold=True)
font_tag = get_font(24, bold=True)
font_hero = get_font(60, bold=True)

def create_paper_canvas(w, h):
    # Cream vintage paper background with subtle grid
    canvas = Image.new("RGBA", (w, h), (246, 244, 238, 255))
    draw = ImageDraw.Draw(canvas)
    grid_col = (226, 222, 212, 255)
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=grid_col, width=1)
    return canvas

# -------------------------------------------------------------
# Asset 1: Beat 2 - The Gold vs Rupee Paradox (Split Top: 1080x960)
# Visual: Balance scale / 2 Physical Cards (Gold Ingot Constant vs Rupee Falling)
# -------------------------------------------------------------
img_b2 = create_paper_canvas(1080, 960)
d2 = ImageDraw.Draw(img_b2)

# Title Card
d2.rounded_rectangle([(80, 60), (1000, 150)], radius=18, fill=(24, 28, 36, 255))
d2.text((540, 105), "THE GOLD PARADOX", font=font_title, fill=(255, 215, 0, 255), anchor="mm")

# Left Column: Global Gold (Constant)
d2.rounded_rectangle([(80, 200), (510, 880)], radius=24, fill=(255, 255, 255, 255), outline=(210, 160, 40, 255), width=3)
d2.rounded_rectangle([(80, 200), (510, 290)], radius=24, fill=(245, 195, 35, 255))
d2.text((295, 245), "GLOBAL GOLD ($)", font=font_card_head, fill=(24, 28, 36, 255), anchor="mm")

# Gold Icon & Price
d2.rounded_rectangle([(160, 360), (430, 480)], radius=16, fill=(255, 248, 220, 255), outline=(210, 160, 40, 255), width=2)
d2.text((295, 420), "GOLD INGOT", font=font_hero, fill=(180, 120, 0, 255), anchor="mm")
d2.text((295, 540), "$2,700 / oz", font=font_hero, fill=(24, 28, 36, 255), anchor="mm")

d2.rounded_rectangle([(140, 640), (450, 720)], radius=14, fill=(240, 244, 248, 255), outline=(100, 140, 180, 255), width=2)
d2.text((295, 680), "PRICE UNCHANGED", font=font_bold_body, fill=(30, 80, 140, 255), anchor="mm")
d2.text((295, 780), "Flat Global Market", font=font_body, fill=(100, 110, 120, 255), anchor="mm")

# Right Column: Indian Rupee (Depreciating)
d2.rounded_rectangle([(570, 200), (1000, 880)], radius=24, fill=(255, 255, 255, 255), outline=(220, 60, 60, 255), width=3)
d2.rounded_rectangle([(570, 200), (1000, 290)], radius=24, fill=(225, 60, 60, 255))
d2.text((785, 245), "INDIAN RUPEE (INR)", font=font_card_head, fill=(255, 255, 255, 255), anchor="mm")

# Rupee Icon & Price
d2.rounded_rectangle([(650, 360), (920, 480)], radius=16, fill=(255, 235, 235, 255), outline=(220, 60, 60, 255), width=2)
d2.text((785, 420), "DEVALUING", font=font_hero, fill=(200, 30, 30, 255), anchor="mm")
d2.text((785, 540), "Rs 84.50 / $", font=font_hero, fill=(200, 30, 30, 255), anchor="mm")

d2.rounded_rectangle([(630, 640), (940, 720)], radius=14, fill=(255, 235, 235, 255), outline=(220, 60, 60, 255), width=2)
d2.text((785, 680), "RUPEE WEAKENS", font=font_bold_body, fill=(200, 30, 30, 255), anchor="mm")
d2.text((785, 780), "India Import Cost Surges", font=font_body, fill=(100, 110, 120, 255), anchor="mm")

img_b2.save(asset_dir / "vox_beat2_paradox.png")
print("Saved vox_beat2_paradox.png")

# -------------------------------------------------------------
# Asset 2: Beat 4 - The 2-Engine Formula (Split Top: 1080x960)
# Visual: Clear math formula cards + visual engine pills
# -------------------------------------------------------------
img_b4 = create_paper_canvas(1080, 960)
d4 = ImageDraw.Draw(img_b4)

# Formula Hero Card
d4.rounded_rectangle([(80, 60), (1000, 320)], radius=24, fill=(24, 28, 36, 255), outline=(255, 215, 0, 255), width=3)
d4.text((540, 120), "THE GOLD PRICING FORMULA", font=font_tag, fill=(200, 200, 200, 255), anchor="mm")
d4.text((540, 190), "INDIAN GOLD PRICE (Rs)", font=font_hero, fill=(255, 215, 0, 255), anchor="mm")
d4.text((540, 265), "= Global Gold ($)  x  USD / INR Forex (Rs)", font=font_card_head, fill=(255, 255, 255, 255), anchor="mm")

# 2 Engine Columns below
d4.rounded_rectangle([(80, 380), (510, 880)], radius=20, fill=(255, 255, 255, 255), outline=(40, 120, 220, 255), width=3)
d4.rounded_rectangle([(80, 380), (510, 470)], radius=20, fill=(40, 120, 220, 255))
d4.text((295, 425), "ENGINE 1", font=font_card_head, fill=(255, 255, 255, 255), anchor="mm")
d4.text((295, 540), "GLOBAL GOLD ($)", font=font_title, fill=(24, 28, 36, 255), anchor="mm")
d4.text((295, 630), "• Wars & Geopolitics", font=font_body, fill=(60, 70, 80, 255), anchor="mm")
d4.text((295, 710), "• Central Bank Reserves", font=font_body, fill=(60, 70, 80, 255), anchor="mm")
d4.text((295, 790), "• US Fed Interest Rates", font=font_body, fill=(60, 70, 80, 255), anchor="mm")

d4.rounded_rectangle([(570, 380), (1000, 880)], radius=20, fill=(255, 255, 255, 255), outline=(220, 60, 60, 255), width=3)
d4.rounded_rectangle([(570, 380), (1000, 470)], radius=20, fill=(220, 60, 60, 255))
d4.text((785, 425), "ENGINE 2", font=font_card_head, fill=(255, 255, 255, 255), anchor="mm")
d4.text((785, 540), "USD / INR FOREX", font=font_title, fill=(24, 28, 36, 255), anchor="mm")
d4.text((785, 630), "• Rupee Depreciation", font=font_body, fill=(60, 70, 80, 255), anchor="mm")
d4.text((785, 710), "• India Import Deficit", font=font_body, fill=(60, 70, 80, 255), anchor="mm")
d4.text((785, 790), "• Global Capital Flows", font=font_body, fill=(60, 70, 80, 255), anchor="mm")

img_b4.save(asset_dir / "vox_beat4_formula.png")
print("Saved vox_beat4_formula.png")

# -------------------------------------------------------------
# Asset 3: Beat 7 - Investor Action Checklist (Split Top: 1080x960)
# Visual: Clean 2-item checklist cards
# -------------------------------------------------------------
img_b7 = create_paper_canvas(1080, 960)
d7 = ImageDraw.Draw(img_b7)

d7.rounded_rectangle([(80, 60), (1000, 160)], radius=18, fill=(24, 28, 36, 255))
d7.text((540, 110), "SMART INVESTOR CHECKLIST", font=font_title, fill=(255, 215, 0, 255), anchor="mm")

# Check 1
d7.rounded_rectangle([(80, 220), (1000, 500)], radius=20, fill=(255, 255, 255, 255), outline=(40, 160, 80, 255), width=3)
d7.ellipse([(130, 310), (230, 410)], fill=(40, 160, 80, 255))
d7.text((180, 360), "1", font=font_hero, fill=(255, 255, 255, 255), anchor="mm")
d7.text((580, 310), "CHECK GLOBAL GOLD (XAU / USD)", font=font_card_head, fill=(24, 28, 36, 255), anchor="mm")
d7.text((580, 380), "Did global gold actually rally in US Dollars?", font=font_body, fill=(100, 110, 120, 255), anchor="mm")
d7.text((580, 440), "STATUS: Constant vs Surging", font=font_bold_body, fill=(40, 120, 220, 255), anchor="mm")

# Check 2
d7.rounded_rectangle([(80, 560), (1000, 840)], radius=20, fill=(255, 255, 255, 255), outline=(220, 60, 60, 255), width=3)
d7.ellipse([(130, 650), (230, 750)], fill=(220, 60, 60, 255))
d7.text((180, 700), "2", font=font_hero, fill=(255, 255, 255, 255), anchor="mm")
d7.text((580, 650), "CHECK USD / INR EXCHANGE RATE", font=font_card_head, fill=(24, 28, 36, 255), anchor="mm")
d7.text((580, 720), "Did the Indian Rupee weaken against the US Dollar?", font=font_body, fill=(100, 110, 120, 255), anchor="mm")
d7.text((580, 780), "STATUS: Currency Impact Multiplier", font=font_bold_body, fill=(220, 60, 60, 255), anchor="mm")

img_b7.save(asset_dir / "vox_beat7_checklist.png")
print("Saved vox_beat7_checklist.png")

# -------------------------------------------------------------
# Asset 4: Beat 8 - Brand Outro Card with New Official Logo (1080x1920)
# -------------------------------------------------------------
img_b8 = create_paper_canvas(1080, 1920)
d8 = ImageDraw.Draw(img_b8)

# Outro Box
d8.rounded_rectangle([(80, 240), (1000, 1680)], radius=32, fill=(255, 255, 255, 255), outline=(210, 160, 40, 255), width=4)

# Place New Logo
logo_file = asset_dir / "profit_bricks_new_logo.png"
if logo_file.exists():
    logo_p = Image.open(logo_file).convert("RGBA")
    logo_w, logo_h = 700, 700
    logo_resized = logo_p.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    img_b8.paste(logo_resized, (190, 360), logo_resized)

d8.rounded_rectangle([(140, 1140), (940, 1300)], radius=20, fill=(24, 28, 36, 255))
d8.text((540, 1190), "FOREX AUTOMATION & TRADING", font=font_card_head, fill=(255, 215, 0, 255), anchor="mm")
d8.text((540, 1250), "Master Market Economics in Simple Hindi", font=font_body, fill=(220, 220, 220, 255), anchor="mm")

d8.rounded_rectangle([(240, 1380), (840, 1520)], radius=24, fill=(18, 98, 62, 255), outline=(210, 160, 40, 255), width=3)
d8.text((540, 1450), "FOLLOW PROFIT BRICKS", font=font_title, fill=(255, 255, 255, 255), anchor="mm")

img_b8.save(asset_dir / "vox_beat8_outro.png")
print("Saved vox_beat8_outro.png with new official logo!")
