import os
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

PLATES_DIR = Path(r"renderer/public/assets/bank_vox_plates")
PLATES_DIR.mkdir(parents=True, exist_ok=True)

# Helper function to create vintage parchment/ledger texture
def create_parchment_base(width=1080, height=960, grid=True):
    # Cream / aged paper background
    img = Image.new("RGB", (width, height), (242, 236, 222))
    draw = ImageDraw.Draw(img)
    
    # Add subtle aged noise
    np_arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-12, 12, (height, width, 3))
    np_arr = np.clip(np_arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(np_arr)
    draw = ImageDraw.Draw(img)
    
    if grid:
        # Accounting ledger lines
        for y in range(40, height, 40):
            draw.line([(0, y), (width, y)], fill=(215, 205, 190), width=1)
        # Vertical accounting margin rules
        draw.line([(90, 0), (90, height)], fill=(230, 180, 180), width=2)
        draw.line([(95, 0), (95, height)], fill=(230, 180, 180), width=1)
        draw.line([(width - 240, 0), (width - 240, height)], fill=(190, 205, 225), width=2)
        draw.line([(width - 120, 0), (width - 120, height)], fill=(190, 205, 225), width=1)
        
    return img

def add_torn_paper_card(base, x, y, w, h, bg_color=(252, 250, 245), border_color=(220, 215, 200)):
    # Draw a torn paper card with shadow and subtle jagged edges
    shadow = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([15, 15, w + 25, h + 25], fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    base.paste(shadow, (x - 20, y - 20), shadow)
    
    card = Image.new("RGBA", (w, h), bg_color + (255,))
    c_draw = ImageDraw.Draw(card)
    c_draw.rectangle([0, 0, w - 1, h - 1], outline=border_color, width=2)
    
    base.paste(card, (x, y), card)
    return x, y, w, h

print("Generating 10 High-Fidelity Vox Paper Collage Plates...")

# 1. bank01_passbook_10lakh.jpg
img1 = create_parchment_base(1080, 960)
d1 = ImageDraw.Draw(img1)
add_torn_paper_card(img1, 140, 160, 800, 640, bg_color=(248, 246, 238))
d1 = ImageDraw.Draw(img1)
# Header
d1.rectangle([140, 160, 940, 240], fill=(228, 220, 205))
d1.text((180, 185), "SAVINGS PASSBOOK // ACCOUNT STATEMENT", fill=(50, 45, 40), font=None)
d1.line([(180, 320), (900, 320)], fill=(200, 190, 175), width=2)
d1.text((180, 280), "AVAILABLE BALANCE", fill=(120, 115, 110))
d1.text((180, 340), "Rs. 10,00,000.00", fill=(30, 120, 50))
d1.text((180, 430), "STATUS: ACTIVE DEPOSIT", fill=(100, 100, 100))
# Big red question mark circle
d1.ellipse([700, 280, 880, 460], outline=(220, 40, 40), width=6)
d1.text((765, 310), "?", fill=(220, 40, 40))
# Hand-drawn red speed lines
for offset in range(-20, 30, 10):
    d1.line([(100, 750 + offset), (980, 720 + offset)], fill=(220, 50, 50), width=3)
img1.save(PLATES_DIR / "bank01_passbook_10lakh.jpg", quality=95)

# 2. bank02_vault_open.jpg (Full Explainer 1080x1920)
img2 = create_parchment_base(1080, 1920)
d2 = ImageDraw.Draw(img2)
add_torn_paper_card(img2, 100, 200, 880, 1520, bg_color=(245, 242, 232))
d2 = ImageDraw.Draw(img2)
# Vault Door Circle
d2.ellipse([240, 500, 840, 1100], fill=(210, 205, 195), outline=(60, 55, 50), width=12)
d2.ellipse([340, 600, 740, 1000], fill=(235, 230, 220), outline=(100, 95, 90), width=6)
# Spokes / Gears
for deg in range(0, 360, 45):
    rad = math.radians(deg)
    x1, y1 = 540 + int(120 * math.cos(rad)), 800 + int(120 * math.sin(rad))
    x2, y2 = 540 + int(280 * math.cos(rad)), 800 + int(280 * math.sin(rad))
    d2.line([(x1, y1), (x2, y2)], fill=(50, 45, 40), width=8)
d2.ellipse([490, 750, 590, 850], fill=(50, 45, 40))
d2.text((260, 300), "THE VAULT REALITY", fill=(40, 35, 30))
d2.text((200, 1260), "CASH IN VAULT vs TOTAL DEPOSITS", fill=(180, 40, 40))
d2.text((200, 1340), "WHERE IS YOUR MONEY ACTUALLY KEPT?", fill=(60, 60, 60))
img2.save(PLATES_DIR / "bank02_vault_open.jpg", quality=95)

# 3. bank03_fractional_circulation.jpg
img3 = create_parchment_base(1080, 960)
d3 = ImageDraw.Draw(img3)
add_torn_paper_card(img3, 100, 100, 880, 760, bg_color=(248, 245, 236))
d3 = ImageDraw.Draw(img3)
d3.text((160, 150), "FRACTIONAL RESERVE SYSTEM", fill=(40, 40, 40))
# Draw 3 circular hubs: Depositors -> Bank -> Borrowers
d3.ellipse([160, 320, 360, 520], fill=(225, 235, 245), outline=(50, 100, 180), width=4)
d3.text((200, 400), "DEPOSITOR\n  (YOU)", fill=(30, 60, 120))
d3.ellipse([440, 320, 640, 520], fill=(245, 235, 220), outline=(180, 120, 40), width=4)
d3.text((490, 400), " BANK\nSYSTEM", fill=(120, 80, 20))
d3.ellipse([720, 320, 920, 520], fill=(230, 245, 230), outline=(40, 140, 60), width=4)
d3.text((750, 400), "BUSINESS\nLOANS & EMI", fill=(20, 90, 40))
# Connecting circulation arrows
d3.line([(360, 420), (440, 420)], fill=(220, 40, 40), width=6)
d3.line([(640, 420), (720, 420)], fill=(40, 160, 40), width=6)
d3.arc([260, 500, 820, 720], 0, 180, fill=(100, 100, 100), width=4)
d3.text((380, 680), "INTEREST & CIRCULATION", fill=(100, 100, 100))
img3.save(PLATES_DIR / "bank03_fractional_circulation.jpg", quality=95)

# 4. bank04_liquidity_scale.jpg (Full Explainer 1080x1920)
img4 = create_parchment_base(1080, 1920)
d4 = ImageDraw.Draw(img4)
add_torn_paper_card(img4, 100, 200, 880, 1520, bg_color=(246, 243, 233))
d4 = ImageDraw.Draw(img4)
d4.text((280, 300), "LIQUIDITY IMBALANCE", fill=(40, 35, 30))
# Fulcrum / Balance scale tilted
d4.polygon([(540, 800), (480, 980), (600, 980)], fill=(80, 75, 70))
# Beam tilted: left up, right down
d4.line([(220, 680), (860, 920)], fill=(40, 35, 30), width=10)
# Left pan: Small physical cash (Rs. 10 Lakhs)
d4.line([(220, 680), (160, 820)], fill=(100, 95, 90), width=3)
d4.line([(220, 680), (280, 820)], fill=(100, 95, 90), width=3)
d4.rectangle([140, 820, 300, 880], fill=(220, 240, 220), outline=(40, 120, 50), width=3)
d4.text((160, 840), "PHYSICAL CASH\n(10-15%)", fill=(30, 90, 40))
# Right pan: Huge debt contracts (90%)
d4.line([(860, 920), (800, 1100)], fill=(100, 95, 90), width=3)
d4.line([(860, 920), (920, 1100)], fill=(100, 95, 90), width=3)
d4.rectangle([760, 1100, 960, 1260], fill=(245, 220, 220), outline=(180, 40, 40), width=4)
d4.text((780, 1150), "LOANS, EMIs\n& ASSETS (85-90%)", fill=(160, 30, 30))
img4.save(PLATES_DIR / "bank04_liquidity_scale.jpg", quality=95)

# 5. bank05_ledger_1crore.jpg
img5 = create_parchment_base(1080, 960)
d5 = ImageDraw.Draw(img5)
add_torn_paper_card(img5, 100, 120, 880, 720, bg_color=(250, 248, 240))
d5 = ImageDraw.Draw(img5)
d5.text((160, 160), "CENTRAL LEDGER // 100 DEPOSITORS", fill=(40, 40, 40))
d5.line([(160, 230), (920, 230)], fill=(180, 170, 155), width=2)
d5.text((160, 260), "100 DEPOSITORS  x  Rs. 1,00,000 EACH", fill=(80, 75, 70))
d5.text((160, 360), "TOTAL LIABILITIES: Rs. 1,00,00,000 (1 CRORE)", fill=(180, 40, 40))
d5.text((160, 460), "ACTUAL CASH ON HAND: Rs. 10,00,000", fill=(30, 110, 50))
d5.rectangle([150, 560, 930, 680], fill=(235, 230, 215), outline=(150, 140, 125), width=2)
d5.text((180, 600), "DEFICIT IF ALL 100 DEMAND CASH SIMULTANEOUSLY", fill=(200, 30, 30))
img5.save(PLATES_DIR / "bank05_ledger_1crore.jpg", quality=95)

# 6. bank06_crowd_queue.jpg (Full Explainer 1080x1920)
img6 = create_parchment_base(1080, 1920)
d6 = ImageDraw.Draw(img6)
add_torn_paper_card(img6, 80, 160, 920, 1600, bg_color=(245, 240, 230))
d6 = ImageDraw.Draw(img6)
d6.text((220, 260), "THE PANIC QUEUE OUTSIDE", fill=(180, 30, 30))
# Bank Facade Pillars
d6.rectangle([140, 420, 220, 1100], fill=(210, 200, 185), outline=(60, 55, 50), width=3)
d6.rectangle([280, 420, 360, 1100], fill=(210, 200, 185), outline=(60, 55, 50), width=3)
d6.rectangle([720, 420, 800, 1100], fill=(210, 200, 185), outline=(60, 55, 50), width=3)
d6.rectangle([860, 420, 940, 1100], fill=(210, 200, 185), outline=(60, 55, 50), width=3)
d6.polygon([(100, 420), (540, 240), (980, 420)], fill=(190, 180, 165), outline=(60, 55, 50), width=4)
d6.text((440, 340), "FIRST NATIONAL BANK", fill=(30, 30, 30))
# Queue silhouettes
for i in range(12):
    qx = 220 + i * 55
    qy = 1200 + (i % 3) * 15
    d6.ellipse([qx, qy - 50, qx + 40, qy - 10], fill=(40, 40, 40))
    d6.rectangle([qx - 5, qy - 10, qx + 45, qy + 120], fill=(50, 50, 50))
d6.text((180, 1480), "ALL 100 DEPOSITORS DEMANDING CASH AT ONCE", fill=(180, 30, 30))
img6.save(PLATES_DIR / "bank06_crowd_queue.jpg", quality=95)

# 7. bank07_bankrun_headline.jpg
img7 = create_parchment_base(1080, 960)
d7 = ImageDraw.Draw(img7)
add_torn_paper_card(img7, 100, 100, 880, 760, bg_color=(246, 242, 230))
d7 = ImageDraw.Draw(img7)
# Newspaper header
d7.text((180, 160), "THE FINANCIAL CHRONICLE", fill=(20, 20, 20))
d7.line([(180, 220), (900, 220)], fill=(30, 30, 30), width=3)
d7.line([(180, 228), (900, 228)], fill=(30, 30, 30), width=1)
# Bold Stamp
d7.rectangle([160, 300, 920, 480], fill=(225, 35, 35))
d7.text((220, 350), "B A N K   R U N", fill=(255, 255, 255))
d7.text((180, 540), "WHEN EVERYONE WITHDRAWS, NO ONE GETS CASH", fill=(40, 40, 40))
d7.text((180, 620), "LIQUIDITY EXHAUSTION IN PROGRESS", fill=(160, 30, 30))
img7.save(PLATES_DIR / "bank07_bankrun_headline.jpg", quality=95)

# 8. bank08_panic_dominoes.jpg (Full Explainer 1080x1920)
img8 = create_parchment_base(1080, 1920)
d8 = ImageDraw.Draw(img8)
add_torn_paper_card(img8, 80, 160, 920, 1600, bg_color=(245, 240, 230))
d8 = ImageDraw.Draw(img8)
d8.text((260, 260), "PANIC CONTAGION SPREAD", fill=(180, 30, 30))
# Domino chain falling
for idx in range(6):
    dx = 200 + idx * 110
    dy = 600 + idx * 100
    angle = 30 + idx * 12
    # draw slanted domino
    d8.polygon([(dx, dy), (dx + 70, dy + 20), (dx + 30, dy + 220), (dx - 40, dy + 200)], fill=(30, 30, 30), outline=(200, 40, 40), width=3)
    d8.text((dx, dy + 60), f"BANK {idx+1}", fill=(255, 255, 255))
d8.text((200, 1420), "FEAR OVERTAKES FUNDAMENTALS", fill=(180, 30, 30))
d8.text((200, 1500), "CHAIN REACTION ACROSS ENTIRE SECTOR", fill=(60, 60, 60))
img8.save(PLATES_DIR / "bank08_panic_dominoes.jpg", quality=95)

# 9. bank09_trust_shield.jpg
img9 = create_parchment_base(1080, 960)
d9 = ImageDraw.Draw(img9)
add_torn_paper_card(img9, 120, 120, 840, 720, bg_color=(248, 245, 235))
d9 = ImageDraw.Draw(img9)
d9.text((220, 180), "THE REAL FOUNDATION: TRUST", fill=(30, 30, 30))
# Golden Shield
d9.polygon([(540, 300), (740, 380), (700, 620), (540, 740), (380, 620), (340, 380)], fill=(235, 205, 120), outline=(160, 120, 30), width=6)
d9.text((470, 480), "TRUST\n  AND\nLIQUIDITY", fill=(50, 40, 10))
img9.save(PLATES_DIR / "bank09_trust_shield.jpg", quality=95)

# 10. bank10_follow_cta.jpg
img10 = create_parchment_base(1080, 960)
d10 = ImageDraw.Draw(img10)
add_torn_paper_card(img10, 120, 120, 840, 720, bg_color=(248, 245, 235))
d10 = ImageDraw.Draw(img10)
d10.text((200, 200), "MASTER MONEY & TRADING PSYCHOLOGY", fill=(50, 45, 40))
# Red Follow Button
d10.rectangle([300, 400, 780, 540], fill=(220, 35, 35), outline=(160, 20, 20), width=4)
d10.text((420, 450), "FOLLOW FOR MORE", fill=(255, 255, 255))
d10.text((240, 640), "SIMPLE EXPLANATIONS DAILY", fill=(100, 95, 90))
img10.save(PLATES_DIR / "bank10_follow_cta.jpg", quality=95)

print(f"Successfully generated all 10 Vox Paper Collage plates in {PLATES_DIR}!")
