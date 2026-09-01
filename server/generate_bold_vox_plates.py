import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

PLATES_DIR = Path(r"renderer/public/assets/bank_vox_plates")
PLATES_DIR.mkdir(parents=True, exist_ok=True)

# System Fonts
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_BLACK = r"C:\Windows\Fonts\ariblk.ttf"

def get_font(size, bold=True):
    try:
        p = FONT_BLACK if bold and os.path.exists(FONT_BLACK) else FONT_BOLD
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.load_default()

def create_parchment_base(width=1080, height=960, grid=True):
    img = Image.new("RGB", (width, height), (245, 238, 224))
    np_arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-10, 10, (height, width, 3))
    np_arr = np.clip(np_arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(np_arr)
    draw = ImageDraw.Draw(img)
    
    if grid:
        # Accounting ledger lines
        for y in range(40, height, 40):
            draw.line([(0, y), (width, y)], fill=(220, 210, 195), width=1)
        # Margin rules
        draw.line([(80, 0), (80, height)], fill=(235, 175, 175), width=2)
        draw.line([(85, 0), (85, height)], fill=(235, 175, 175), width=1)
        draw.line([(width - 160, 0), (width - 160, height)], fill=(185, 205, 225), width=2)
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

print("Generating 10 BOLD Vox Typography Plates...")

f_title = get_font(52, True)
f_sub = get_font(34, True)
f_hero = get_font(76, True)
f_huge = get_font(110, True)

# 1. bank01_passbook_10lakh.jpg (1080x960)
img1 = create_parchment_base(1080, 960)
add_torn_card(img1, 80, 100, 920, 760, bg_color=(250, 248, 240))
d1 = ImageDraw.Draw(img1)
d1.rectangle([80, 100, 1000, 200], fill=(225, 215, 195))
d1.text((120, 125), "SAVINGS PASSBOOK STATEMENT", fill=(40, 35, 30), font=f_title)
d1.line([(120, 310), (960, 310)], fill=(200, 190, 170), width=3)
d1.text((120, 245), "TOTAL ACCOUNT BALANCE", fill=(110, 105, 100), font=f_sub)
d1.text((120, 340), "Rs. 10,00,000", fill=(25, 130, 45), font=f_huge)
d1.text((120, 490), "CAN YOU WITHDRAW THIS TOMORROW?", fill=(190, 35, 35), font=f_title)
# Red question mark
d1.ellipse([760, 280, 950, 470], outline=(225, 40, 40), width=8)
d1.text((825, 305), "?", fill=(225, 40, 40), font=f_huge)
# Red marker underlines
for offset in range(-15, 25, 10):
    d1.line([(100, 720 + offset), (980, 690 + offset)], fill=(225, 45, 45), width=4)
img1.save(PLATES_DIR / "bank01_passbook_10lakh.jpg", quality=95)

# 2. bank02_vault_open.jpg (Full Explainer 1080x1920)
img2 = create_parchment_base(1080, 1920)
add_torn_card(img2, 80, 140, 920, 1640, bg_color=(246, 242, 230))
d2 = ImageDraw.Draw(img2)
d2.text((180, 220), "THE VAULT REALITY", fill=(30, 30, 30), font=f_hero)
d2.line([(140, 320), (940, 320)], fill=(180, 170, 150), width=4)
# Huge Vault Circle
cx, cy, r_out = 540, 880, 380
d2.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(215, 208, 195), outline=(50, 45, 40), width=16)
d2.ellipse([cx - 260, cy - 260, cx + 260, cy + 260], fill=(235, 230, 218), outline=(80, 75, 70), width=8)
# Spokes
for deg in range(0, 360, 45):
    rad = math.radians(deg)
    d2.line([(cx + int(100 * math.cos(rad)), cy + int(100 * math.sin(rad))),
             (cx + int(360 * math.cos(rad)), cy + int(360 * math.sin(rad)))], fill=(45, 40, 35), width=12)
d2.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(40, 35, 30))
# Big Bold Explainer Text
d2.rectangle([120, 1340, 960, 1500], fill=(225, 35, 35))
d2.text((150, 1380), "WHERE IS YOUR MONEY?", fill=(255, 255, 255), font=f_hero)
d2.text((140, 1560), "NOT SITTING IN A LOCKER!", fill=(40, 40, 40), font=f_title)
img2.save(PLATES_DIR / "bank02_vault_open.jpg", quality=95)

# 3. bank03_fractional_circulation.jpg (1080x960)
img3 = create_parchment_base(1080, 960)
add_torn_card(img3, 60, 80, 960, 800, bg_color=(248, 245, 236))
d3 = ImageDraw.Draw(img3)
d3.text((120, 120), "FRACTIONAL RESERVE BANKING", fill=(30, 30, 30), font=f_title)
# 3 Big Hubs
d3.ellipse([100, 300, 340, 540], fill=(225, 238, 250), outline=(40, 90, 170), width=6)
d3.text((135, 390), "DEPOSITOR\n  (YOU)", fill=(25, 60, 130), font=f_sub)
d3.ellipse([420, 300, 660, 540], fill=(250, 238, 220), outline=(180, 110, 30), width=6)
d3.text((465, 390), "  BANK\nSYSTEM", fill=(130, 75, 15), font=f_sub)
d3.ellipse([740, 300, 980, 540], fill=(230, 248, 230), outline=(35, 140, 55), width=6)
d3.text((765, 390), "BORROWERS\n& BUSINESS", fill=(20, 100, 40), font=f_sub)
# Large arrows
d3.line([(340, 420), (420, 420)], fill=(225, 40, 40), width=10)
d3.line([(660, 420), (740, 420)], fill=(35, 150, 45), width=10)
d3.text((160, 660), "YOUR MONEY CIRCULATES IN THE ECONOMY", fill=(190, 35, 35), font=f_title)
img3.save(PLATES_DIR / "bank03_fractional_circulation.jpg", quality=95)

# 4. bank04_liquidity_scale.jpg (Full Explainer 1080x1920)
img4 = create_parchment_base(1080, 1920)
add_torn_card(img4, 80, 140, 920, 1640, bg_color=(245, 242, 232))
d4 = ImageDraw.Draw(img4)
d4.text((180, 220), "LIQUIDITY MISMATCH", fill=(30, 30, 30), font=f_hero)
# Scale Fulcrum
d4.polygon([(540, 780), (460, 1000), (620, 1000)], fill=(70, 65, 60))
# Tilted beam
d4.line([(180, 640), (900, 940)], fill=(40, 35, 30), width=16)
# Left Pan (Cash)
d4.line([(180, 640), (100, 800)], fill=(80, 75, 70), width=5)
d4.line([(180, 640), (260, 800)], fill=(80, 75, 70), width=5)
d4.rectangle([70, 800, 290, 960], fill=(220, 245, 220), outline=(35, 130, 50), width=5)
d4.text((100, 830), "CASH ON\n  HAND\n (10-15%)", fill=(25, 100, 40), font=f_sub)
# Right Pan (Loans)
d4.line([(900, 940), (800, 1140)], fill=(80, 75, 70), width=5)
d4.line([(900, 940), (1000, 1140)], fill=(80, 75, 70), width=5)
d4.rectangle([760, 1140, 1020, 1360], fill=(250, 220, 220), outline=(190, 40, 40), width=6)
d4.text((785, 1180), "LOANS & EMIs\n  LOCKED UP\n   (85-90%)", fill=(170, 30, 30), font=f_sub)
d4.rectangle([100, 1480, 980, 1640], fill=(225, 35, 35))
d4.text((140, 1520), "IF EVERYONE ASKS CASH → CRISIS!", fill=(255, 255, 255), font=f_title)
img4.save(PLATES_DIR / "bank04_liquidity_scale.jpg", quality=95)

# 5. bank05_ledger_1crore.jpg (1080x960)
img5 = create_parchment_base(1080, 960)
add_torn_card(img5, 60, 80, 960, 800, bg_color=(250, 248, 240))
d5 = ImageDraw.Draw(img5)
d5.text((120, 120), "CENTRAL BANK LEDGER", fill=(40, 40, 40), font=f_title)
d5.line([(120, 200), (960, 200)], fill=(190, 180, 160), width=3)
d5.text((120, 240), "100 DEPOSITORS  x  Rs. 1,00,000", fill=(70, 65, 60), font=f_title)
d5.text((120, 340), "TOTAL LIABILITIES: Rs. 1 CRORE", fill=(190, 35, 35), font=f_hero)
d5.rectangle([100, 480, 980, 600], fill=(230, 245, 230), outline=(40, 130, 50), width=3)
d5.text((140, 515), "PHYSICAL CASH IN VAULT: Rs. 10 LAKHS", fill=(25, 110, 40), font=f_title)
d5.text((120, 680), "DEFICIT: Rs. 90,00,000 IF ALL WITHDRAW", fill=(180, 30, 30), font=f_title)
img5.save(PLATES_DIR / "bank05_ledger_1crore.jpg", quality=95)

# 6. bank06_crowd_queue.jpg (Full Explainer 1080x1920)
img6 = create_parchment_base(1080, 1920)
add_torn_card(img6, 80, 140, 920, 1640, bg_color=(246, 240, 228))
d6 = ImageDraw.Draw(img6)
d6.text((160, 200), "THE PANIC QUEUE", fill=(190, 30, 30), font=f_hero)
# Bank Pillars
for px in [140, 300, 740, 900]:
    d6.rectangle([px, 380, px + 80, 1050], fill=(210, 200, 185), outline=(50, 45, 40), width=4)
d6.polygon([(100, 380), (540, 200), (980, 380)], fill=(190, 180, 160), outline=(50, 45, 40), width=6)
d6.text((360, 300), "NATIONAL BANK", fill=(30, 30, 30), font=f_title)
# Crowd queue
for i in range(14):
    qx = 160 + i * 55
    qy = 1150 + (i % 3) * 20
    d6.ellipse([qx, qy - 60, qx + 50, qy - 10], fill=(30, 30, 30))
    d6.rectangle([qx - 5, qy - 10, qx + 55, qy + 140], fill=(45, 45, 45))
d6.rectangle([100, 1460, 980, 1640], fill=(225, 35, 35))
d6.text((130, 1505), "ALL 100 DEPOSITORS OUTSIDE!", fill=(255, 255, 255), font=f_hero)
img6.save(PLATES_DIR / "bank06_crowd_queue.jpg", quality=95)

# 7. bank07_bankrun_headline.jpg (1080x960)
img7 = create_parchment_base(1080, 960)
add_torn_card(img7, 60, 80, 960, 800, bg_color=(248, 242, 230))
d7 = ImageDraw.Draw(img7)
d7.text((140, 120), "THE FINANCIAL CHRONICLE", fill=(20, 20, 20), font=f_title)
d7.line([(100, 190), (980, 190)], fill=(20, 20, 20), width=4)
# Huge Red Stamp Banner
d7.rectangle([100, 260, 980, 480], fill=(225, 30, 30))
d7.text((160, 310), "B A N K   R U N", fill=(255, 255, 255), font=f_huge)
d7.text((120, 540), "WHEN EVERYONE WITHDRAWS, NO ONE GETS CASH", fill=(30, 30, 30), font=f_title)
d7.text((120, 680), "LIQUIDITY EXHAUSTION IN PROGRESS", fill=(190, 30, 30), font=f_hero)
img7.save(PLATES_DIR / "bank07_bankrun_headline.jpg", quality=95)

# 8. bank08_panic_dominoes.jpg (Full Explainer 1080x1920)
img8 = create_parchment_base(1080, 1920)
add_torn_card(img8, 80, 140, 920, 1640, bg_color=(245, 240, 228))
d8 = ImageDraw.Draw(img8)
d8.text((180, 200), "PANIC CONTAGION", fill=(190, 30, 30), font=f_hero)
for idx in range(5):
    dx = 180 + idx * 130
    dy = 520 + idx * 130
    d8.polygon([(dx, dy), (dx + 100, dy + 25), (dx + 40, dy + 320), (dx - 60, dy + 290)], fill=(35, 35, 35), outline=(225, 40, 40), width=5)
    d8.text((dx - 10, dy + 100), f"BANK {idx+1}", fill=(255, 255, 255), font=f_sub)
d8.rectangle([100, 1440, 980, 1620], fill=(225, 35, 35))
d8.text((140, 1485), "FEAR CRASHES THE SYSTEM", fill=(255, 255, 255), font=f_hero)
img8.save(PLATES_DIR / "bank08_panic_dominoes.jpg", quality=95)

# 9. bank09_trust_shield.jpg (1080x960)
img9 = create_parchment_base(1080, 960)
add_torn_card(img9, 60, 80, 960, 800, bg_color=(248, 245, 235))
d9 = ImageDraw.Draw(img9)
d9.text((140, 120), "THE TRUE FOUNDATION OF MONEY", fill=(30, 30, 30), font=f_title)
# Shield
d9.polygon([(540, 260), (760, 350), (720, 600), (540, 720), (360, 600), (320, 350)], fill=(235, 200, 110), outline=(160, 110, 25), width=8)
d9.text((435, 430), "TRUST\n  AND\nLIQUIDITY", fill=(50, 35, 10), font=f_title)
d9.text((120, 780), "NOT CASH, BUT CONFIDENCE IN THE SYSTEM", fill=(180, 30, 30), font=f_title)
img9.save(PLATES_DIR / "bank09_trust_shield.jpg", quality=95)

# 10. bank10_follow_cta.jpg (1080x960)
img10 = create_parchment_base(1080, 960)
add_torn_card(img10, 60, 80, 960, 800, bg_color=(248, 245, 235))
d10 = ImageDraw.Draw(img10)
d10.text((120, 140), "MASTER MONEY & TRADING CONCEPTS", fill=(40, 35, 30), font=f_title)
d10.rectangle([200, 340, 880, 520], fill=(225, 30, 30), outline=(160, 20, 20), width=6)
d10.text((290, 390), "FOLLOW FOR MORE", fill=(255, 255, 255), font=f_hero)
d10.text((160, 660), "SIMPLE EXPLANATIONS EVERY DAY", fill=(100, 90, 80), font=f_title)
img10.save(PLATES_DIR / "bank10_follow_cta.jpg", quality=95)

print("All 10 BOLD Vox Typography Plates generated successfully!")
