import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

PLATES_DIR = Path(r"renderer/public/assets/bank_vox_plates")
PLATES_DIR.mkdir(parents=True, exist_ok=True)

FONT_BLACK = r"C:\Windows\Fonts\ariblk.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"

def get_font(size, black=True):
    try:
        p = FONT_BLACK if black and os.path.exists(FONT_BLACK) else FONT_BOLD
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.load_default()

def create_parchment_base(width=1080, height=960, grid=True):
    img = Image.new("RGB", (width, height), (246, 240, 228))
    np_arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-10, 10, (height, width, 3))
    np_arr = np.clip(np_arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(np_arr)
    draw = ImageDraw.Draw(img)
    
    if grid:
        for y in range(40, height, 40):
            draw.line([(0, y), (width, y)], fill=(220, 212, 198), width=1)
        draw.line([(70, 0), (70, height)], fill=(235, 175, 175), width=2)
        draw.line([(75, 0), (75, height)], fill=(235, 175, 175), width=1)
        draw.line([(width - 120, 0), (width - 120, height)], fill=(185, 205, 225), width=2)
    return img

def add_torn_card(base, x, y, w, h, bg_color=(252, 250, 245), border_color=(210, 200, 185)):
    shadow = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([15, 15, w + 25, h + 25], fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    base.paste(shadow, (x - 20, y - 20), shadow)
    
    card = Image.new("RGBA", (w, h), bg_color + (255,))
    c_draw = ImageDraw.Draw(card)
    c_draw.rectangle([0, 0, w - 1, h - 1], outline=border_color, width=3)
    base.paste(card, (x, y), card)
    return x, y, w, h

def draw_centered_text(draw, text, y, font, fill, width=1080):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return x, y, tw, bbox[3] - bbox[1]

print("Generating Centered, Pixel-Perfect Vox Typography Plates...")

f_h1 = get_font(54, True)
f_h2 = get_font(42, True)
f_h3 = get_font(32, True)
f_hero = get_font(72, True)
f_huge = get_font(96, True)

# 1. bank01_passbook_10lakh.jpg (1080x960)
img1 = create_parchment_base(1080, 960)
add_torn_card(img1, 70, 90, 940, 780, bg_color=(250, 248, 240))
d1 = ImageDraw.Draw(img1)
d1.rectangle([70, 90, 1010, 190], fill=(225, 215, 195))
draw_centered_text(d1, "SAVINGS PASSBOOK STATEMENT", 120, f_h2, (40, 35, 30))
d1.line([(120, 300), (960, 300)], fill=(200, 190, 170), width=3)
draw_centered_text(d1, "TOTAL AVAILABLE BALANCE", 240, f_h3, (110, 105, 100))
draw_centered_text(d1, "Rs. 10,00,000", 330, f_huge, (25, 130, 45))
draw_centered_text(d1, "CAN YOU WITHDRAW THIS TOMORROW?", 470, f_h2, (190, 35, 35))
# Red question mark badge
d1.ellipse([780, 290, 930, 440], outline=(225, 40, 40), width=7)
d1.text((835, 315), "?", fill=(225, 40, 40), font=f_hero)
# Red marker underlines
for offset in range(-15, 25, 10):
    d1.line([(120, 740 + offset), (960, 710 + offset)], fill=(225, 45, 45), width=4)
img1.save(PLATES_DIR / "bank01_passbook_10lakh.jpg", quality=95)

# 2. bank02_vault_open.jpg (Full Explainer 1080x1920)
img2 = create_parchment_base(1080, 1920)
add_torn_card(img2, 70, 120, 940, 1680, bg_color=(246, 242, 230))
d2 = ImageDraw.Draw(img2)
draw_centered_text(d2, "THE VAULT REALITY", 200, f_hero, (30, 30, 30))
d2.line([(140, 300), (940, 300)], fill=(180, 170, 150), width=4)
cx, cy, r_out = 540, 860, 350
d2.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(215, 208, 195), outline=(50, 45, 40), width=16)
d2.ellipse([cx - 240, cy - 240, cx + 240, cy + 240], fill=(235, 230, 218), outline=(80, 75, 70), width=8)
for deg in range(0, 360, 45):
    rad = math.radians(deg)
    d2.line([(cx + int(90 * math.cos(rad)), cy + int(90 * math.sin(rad))),
             (cx + int(330 * math.cos(rad)), cy + int(330 * math.sin(rad)))], fill=(45, 40, 35), width=12)
d2.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(40, 35, 30))
d2.rectangle([110, 1340, 970, 1480], fill=(225, 35, 35))
draw_centered_text(d2, "WHERE IS YOUR MONEY?", 1375, f_h1, (255, 255, 255))
draw_centered_text(d2, "NOT SITTING IN A LOCKER!", 1540, f_h1, (40, 40, 40))
img2.save(PLATES_DIR / "bank02_vault_open.jpg", quality=95)

# 3. bank03_fractional_circulation.jpg (1080x960)
img3 = create_parchment_base(1080, 960)
add_torn_card(img3, 60, 80, 960, 800, bg_color=(248, 245, 236))
d3 = ImageDraw.Draw(img3)
draw_centered_text(d3, "FRACTIONAL RESERVE BANKING", 120, f_h1, (30, 30, 30))
d3.ellipse([90, 290, 340, 540], fill=(225, 238, 250), outline=(40, 90, 170), width=6)
d3.text((125, 385), "DEPOSITOR\n  (YOU)", fill=(25, 60, 130), font=f_h3)
d3.ellipse([415, 290, 665, 540], fill=(250, 238, 220), outline=(180, 110, 30), width=6)
d3.text((460, 385), "  BANK\nSYSTEM", fill=(130, 75, 15), font=f_h3)
d3.ellipse([740, 290, 990, 540], fill=(230, 248, 230), outline=(35, 140, 55), width=6)
d3.text((765, 385), "BORROWERS\n& BUSINESS", fill=(20, 100, 40), font=f_h3)
d3.line([(340, 415), (415, 415)], fill=(225, 40, 40), width=10)
d3.line([(665, 415), (740, 415)], fill=(35, 150, 45), width=10)
draw_centered_text(d3, "YOUR MONEY CIRCULATES IN THE ECONOMY", 660, f_h2, (190, 35, 35))
img3.save(PLATES_DIR / "bank03_fractional_circulation.jpg", quality=95)

# 4. bank04_liquidity_scale.jpg (Full Explainer 1080x1920)
img4 = create_parchment_base(1080, 1920)
add_torn_card(img4, 70, 120, 940, 1680, bg_color=(245, 242, 232))
d4 = ImageDraw.Draw(img4)
draw_centered_text(d4, "LIQUIDITY MISMATCH", 200, f_hero, (30, 30, 30))
d4.polygon([(540, 780), (460, 980), (620, 980)], fill=(70, 65, 60))
d4.line([(180, 640), (900, 940)], fill=(40, 35, 30), width=16)
d4.line([(180, 640), (100, 800)], fill=(80, 75, 70), width=5)
d4.line([(180, 640), (260, 800)], fill=(80, 75, 70), width=5)
d4.rectangle([70, 800, 290, 960], fill=(220, 245, 220), outline=(35, 130, 50), width=5)
d4.text((95, 830), "CASH ON\n  HAND\n (10-15%)", fill=(25, 100, 40), font=f_h3)
d4.line([(900, 940), (800, 1140)], fill=(80, 75, 70), width=5)
d4.line([(900, 940), (1000, 1140)], fill=(80, 75, 70), width=5)
d4.rectangle([760, 1140, 1020, 1360], fill=(250, 220, 220), outline=(190, 40, 40), width=6)
d4.text((785, 1180), "LOANS & EMIs\n  LOCKED UP\n   (85-90%)", fill=(170, 30, 30), font=f_h3)
d4.rectangle([90, 1480, 990, 1620], fill=(225, 35, 35))
draw_centered_text(d4, "IF EVERYONE ASKS CASH -> CRISIS!", 1520, f_h2, (255, 255, 255))
img4.save(PLATES_DIR / "bank04_liquidity_scale.jpg", quality=95)

# 5. bank05_ledger_1crore.jpg (1080x960)
img5 = create_parchment_base(1080, 960)
add_torn_card(img5, 60, 80, 960, 800, bg_color=(250, 248, 240))
d5 = ImageDraw.Draw(img5)
draw_centered_text(d5, "CENTRAL BANK LEDGER", 110, f_h1, (40, 40, 40))
d5.line([(120, 190), (960, 190)], fill=(190, 180, 160), width=3)
draw_centered_text(d5, "100 DEPOSITORS  x  Rs. 1,00,000", 230, f_h2, (70, 65, 60))
draw_centered_text(d5, "TOTAL LIABILITIES: Rs. 1 CRORE", 320, f_hero, (190, 35, 35))
d5.rectangle([100, 470, 980, 590], fill=(230, 245, 230), outline=(40, 130, 50), width=3)
draw_centered_text(d5, "PHYSICAL CASH IN VAULT: Rs. 10 LAKHS", 510, f_h2, (25, 110, 40))
draw_centered_text(d5, "DEFICIT: Rs. 90,00,000 IF ALL WITHDRAW", 670, f_h2, (180, 30, 30))
img5.save(PLATES_DIR / "bank05_ledger_1crore.jpg", quality=95)

# 6. bank06_crowd_queue.jpg (Full Explainer 1080x1920)
img6 = create_parchment_base(1080, 1920)
add_torn_card(img6, 70, 120, 940, 1680, bg_color=(246, 240, 228))
d6 = ImageDraw.Draw(img6)
draw_centered_text(d6, "THE PANIC QUEUE", 190, f_hero, (190, 30, 30))
for px in [140, 300, 740, 900]:
    d6.rectangle([px, 360, px + 80, 1050], fill=(210, 200, 185), outline=(50, 45, 40), width=4)
d6.polygon([(100, 360), (540, 180), (980, 360)], fill=(190, 180, 160), outline=(50, 45, 40), width=6)
draw_centered_text(d6, "NATIONAL BANK", 280, f_h2, (30, 30, 30))
for i in range(14):
    qx = 150 + i * 57
    qy = 1150 + (i % 3) * 20
    d6.ellipse([qx, qy - 60, qx + 50, qy - 10], fill=(30, 30, 30))
    d6.rectangle([qx - 5, qy - 10, qx + 55, qy + 140], fill=(45, 45, 45))
d6.rectangle([90, 1460, 990, 1620], fill=(225, 35, 35))
draw_centered_text(d6, "ALL 100 DEPOSITORS OUTSIDE!", 1510, f_h1, (255, 255, 255))
img6.save(PLATES_DIR / "bank06_crowd_queue.jpg", quality=95)

# 7. bank07_bankrun_headline.jpg (1080x960)
img7 = create_parchment_base(1080, 960)
add_torn_card(img7, 60, 80, 960, 800, bg_color=(248, 242, 230))
d7 = ImageDraw.Draw(img7)
draw_centered_text(d7, "THE FINANCIAL CHRONICLE", 115, f_h2, (20, 20, 20))
d7.line([(100, 185), (980, 185)], fill=(20, 20, 20), width=4)
d7.rectangle([100, 250, 980, 470], fill=(225, 30, 30))
draw_centered_text(d7, "B A N K   R U N", 305, f_huge, (255, 255, 255))
draw_centered_text(d7, "WHEN EVERYONE WITHDRAWS, NO ONE GETS CASH", 530, f_h3, (30, 30, 30))
draw_centered_text(d7, "LIQUIDITY EXHAUSTION IN PROGRESS", 670, f_h1, (190, 30, 30))
img7.save(PLATES_DIR / "bank07_bankrun_headline.jpg", quality=95)

# 8. bank08_panic_dominoes.jpg (Full Explainer 1080x1920)
img8 = create_parchment_base(1080, 1920)
add_torn_card(img8, 70, 120, 940, 1680, bg_color=(245, 240, 228))
d8 = ImageDraw.Draw(img8)
draw_centered_text(d8, "PANIC CONTAGION", 190, f_hero, (190, 30, 30))
for idx in range(5):
    dx = 170 + idx * 135
    dy = 500 + idx * 135
    d8.polygon([(dx, dy), (dx + 100, dy + 25), (dx + 40, dy + 320), (dx - 60, dy + 290)], fill=(35, 35, 35), outline=(225, 40, 40), width=5)
    d8.text((dx - 10, dy + 100), f"BANK {idx+1}", fill=(255, 255, 255), font=f_h3)
d8.rectangle([90, 1460, 990, 1620], fill=(225, 35, 35))
draw_centered_text(d8, "FEAR CRASHES THE SYSTEM", 1510, f_h1, (255, 255, 255))
img8.save(PLATES_DIR / "bank08_panic_dominoes.jpg", quality=95)

# 9. bank09_trust_shield.jpg (1080x960)
img9 = create_parchment_base(1080, 960)
add_torn_card(img9, 60, 80, 960, 800, bg_color=(248, 245, 235))
d9 = ImageDraw.Draw(img9)
draw_centered_text(d9, "THE TRUE FOUNDATION OF MONEY", 120, f_h2, (30, 30, 30))
d9.polygon([(540, 250), (760, 340), (720, 590), (540, 710), (360, 590), (320, 340)], fill=(235, 200, 110), outline=(160, 110, 25), width=8)
d9.text((435, 410), "TRUST\n  AND\nLIQUIDITY", fill=(50, 35, 10), font=f_h2)
draw_centered_text(d9, "NOT CASH, BUT CONFIDENCE IN THE SYSTEM", 770, f_h3, (180, 30, 30))
img9.save(PLATES_DIR / "bank09_trust_shield.jpg", quality=95)

# 10. bank10_follow_cta.jpg (1080x960)
img10 = create_parchment_base(1080, 960)
add_torn_card(img10, 60, 80, 960, 800, bg_color=(248, 245, 235))
d10 = ImageDraw.Draw(img10)
draw_centered_text(d10, "MASTER MONEY & TRADING CONCEPTS", 140, f_h2, (40, 35, 30))
d10.rectangle([180, 320, 900, 500], fill=(225, 30, 30), outline=(160, 20, 20), width=6)
draw_centered_text(d10, "FOLLOW FOR MORE", 370, f_hero, (255, 255, 255))
draw_centered_text(d10, "SIMPLE EXPLANATIONS EVERY DAY", 660, f_h2, (100, 90, 80))
img10.save(PLATES_DIR / "bank10_follow_cta.jpg", quality=95)

print("All 10 Centered, Pixel-Perfect Vox Typography Plates saved!")
