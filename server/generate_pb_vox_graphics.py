import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
asset_dir.mkdir(parents=True, exist_ok=True)

# Helper function to get font
def get_font(size, bold=True):
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "seguiemj.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "impact.ttf"
    ]
    for fn in font_names:
        fp = Path(r"C:\Windows\Fonts") / fn
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except:
                pass
    return ImageFont.load_default()

# ----------------------------------------------------
# 1. ASSET: Beat 2 - Gold vs Rupee Balance Scale (1080x960 for split top)
# ----------------------------------------------------
w_split, h_split = 1080, 960
img1 = Image.new("RGBA", (w_split, h_split), (245, 243, 238, 255)) # Cream paper
draw1 = ImageDraw.Draw(img1)

# Subtle grid lines for Vox paper aesthetic
for x in range(0, w_split, 40):
    draw1.line([(x, 0), (x, h_split)], fill=(230, 227, 220, 255), width=1)
for y in range(0, h_split, 40):
    draw1.line([(0, y), (w_split, y)], fill=(230, 227, 220, 255), width=1)

# Header badge
font_title = get_font(42, bold=True)
font_sub = get_font(32, bold=True)
font_num = get_font(52, bold=True)
font_small = get_font(26, bold=False)

# Draw Title Card
draw1.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw1.text((540, 85), "THE GOLD PARADOX: STRENGTH VS WEAKNESS", fill=(255, 215, 0, 255), font=font_title, anchor="mm")

# Left Card: Gold
draw1.rounded_rectangle([(80, 180), (510, 860)], radius=20, fill=(255, 255, 255, 255), outline=(218, 165, 32, 255), width=4)
draw1.rectangle([(80, 180), (510, 260)], fill=(255, 215, 0, 255))
draw1.text((295, 220), "GLOBAL GOLD (XAU)", fill=(24, 28, 36, 255), font=font_sub, anchor="mm")
draw1.text((295, 360), "🪙", font=get_font(110), anchor="mm")
draw1.text((295, 520), "$2,700 / oz", fill=(24, 28, 36, 255), font=font_num, anchor="mm")
draw1.text((295, 600), "CONSTANT PRICE", fill=(100, 100, 100, 255), font=font_sub, anchor="mm")
draw1.rounded_rectangle([(120, 680), (470, 780)], radius=12, fill=(240, 248, 255, 255))
draw1.text((295, 730), "NO MAJOR MOVE", fill=(40, 90, 180, 255), font=font_sub, anchor="mm")

# Right Card: Indian Rupee
draw1.rounded_rectangle([(570, 180), (1000, 860)], radius=20, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=4)
draw1.rectangle([(570, 180), (1000, 260)], fill=(220, 50, 50, 255))
draw1.text((785, 220), "INDIAN RUPEE (INR)", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
draw1.text((785, 360), "📉", font=get_font(110), anchor="mm")
draw1.text((785, 520), "₹84.50 / $1", fill=(220, 30, 30, 255), font=font_num, anchor="mm")
draw1.text((785, 600), "DEPRECIATING ↘", fill=(220, 50, 50, 255), font=font_sub, anchor="mm")
draw1.rounded_rectangle([(610, 680), (960, 780)], radius=12, fill=(255, 240, 240, 255))
draw1.text((785, 730), "RUPEE LOSING VALUE", fill=(200, 30, 30, 255), font=font_sub, anchor="mm")

img1.save(asset_dir / "beat2_gold_vs_rupee.png")
print("Saved beat2_gold_vs_rupee.png")

# ----------------------------------------------------
# 2. ASSET: Beat 3 - Global Dollar Flow Explainer (1080x1920 Full Canvas)
# ----------------------------------------------------
w_full, h_full = 1080, 1920
img2 = Image.new("RGBA", (w_full, h_full), (18, 22, 30, 255)) # Dark slate
draw2 = ImageDraw.Draw(img2)

# Grid lines
for x in range(0, w_full, 50):
    draw2.line([(x, 0), (x, h_full)], fill=(30, 36, 48, 255), width=1)
for y in range(0, h_full, 50):
    draw2.line([(0, y), (w_full, y)], fill=(30, 36, 48, 255), width=1)

# Header
draw2.rounded_rectangle([(80, 100), (1000, 220)], radius=18, fill=(255, 215, 0, 255))
draw2.text((540, 160), "HOW DOLLAR MAKES GOLD COSTLY", fill=(18, 22, 30, 255), font=get_font(44, bold=True), anchor="mm")

# Step 1: Base Case
draw2.rounded_rectangle([(80, 280), (1000, 640)], radius=20, fill=(28, 34, 48, 255), outline=(60, 70, 90, 255), width=2)
draw2.text((120, 340), "CASE 1: NORMAL DOLLAR", fill=(255, 215, 0, 255), font=get_font(34, bold=True))
draw2.text((120, 420), "• International Gold Price: $2,500 / oz", fill=(240, 240, 240, 255), font=get_font(32, bold=False))
draw2.text((120, 480), "• USD / INR Exchange Rate: $1 = ₹80", fill=(240, 240, 240, 255), font=get_font(32, bold=False))
draw2.rounded_rectangle([(120, 540), (960, 610)], radius=10, fill=(35, 45, 65, 255))
draw2.text((540, 575), "INDIA COST = 2,500 × 80 = ₹2,00,000", fill=(100, 220, 120, 255), font=get_font(32, bold=True), anchor="mm")

# Step 2: Dollar Surge Case
draw2.rounded_rectangle([(80, 700), (1000, 1100)], radius=20, fill=(38, 24, 28, 255), outline=(220, 60, 60, 255), width=3)
draw2.text((120, 760), "CASE 2: DOLLAR SURGES (RUPEE WEAKENS)", fill=(255, 90, 90, 255), font=get_font(34, bold=True))
draw2.text((120, 840), "• International Gold Price: $2,500 / oz (SAME!)", fill=(240, 240, 240, 255), font=get_font(32, bold=False))
draw2.text((120, 900), "• USD / INR Exchange Rate: $1 = ₹90 (SURGE ↗)", fill=(255, 200, 200, 255), font=get_font(32, bold=True))
draw2.rounded_rectangle([(120, 960), (960, 1060)], radius=10, fill=(60, 25, 30, 255))
draw2.text((540, 1010), "INDIA COST = 2,500 × 90 = ₹2,25,000 (↗ +₹25,000!)", fill=(255, 90, 90, 255), font=get_font(30, bold=True), anchor="mm")

# Callout Card
draw2.rounded_rectangle([(80, 1180), (1000, 1680)], radius=24, fill=(255, 255, 255, 255))
draw2.text((540, 1260), "💡 CRITICAL MARKET TAKEAWAY", fill=(24, 28, 36, 255), font=get_font(38, bold=True), anchor="mm")
draw2.text((540, 1360), "Gold didn't rise in America...", fill=(80, 80, 80, 255), font=get_font(34, bold=False), anchor="mm")
draw2.text((540, 1440), "India paid more simply because", fill=(24, 28, 36, 255), font=get_font(36, bold=True), anchor="mm")
draw2.text((540, 1520), "THE RUPEE LOST VALUE!", fill=(220, 30, 30, 255), font=get_font(44, bold=True), anchor="mm")
draw2.rounded_rectangle([(140, 1590), (940, 1650)], radius=8, fill=(245, 245, 245, 255))
draw2.text((540, 1620), "Currency Depreciation = Imported Inflation", fill=(100, 100, 100, 255), font=get_font(26, bold=True), anchor="mm")

img2.save(asset_dir / "beat3_global_dollar_flow.png")
print("Saved beat3_global_dollar_flow.png")

# ----------------------------------------------------
# 3. ASSET: Beat 4 - The 2-Variable Formula (1080x960 for split top)
# ----------------------------------------------------
img3 = Image.new("RGBA", (w_split, h_split), (245, 243, 238, 255))
draw3 = ImageDraw.Draw(img3)

for x in range(0, w_split, 40):
    draw3.line([(x, 0), (x, h_split)], fill=(230, 227, 220, 255), width=1)
for y in range(0, h_split, 40):
    draw3.line([(0, y), (w_split, y)], fill=(230, 227, 220, 255), width=1)

draw3.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw3.text((540, 85), "THE 2 ENGINES OF INDIAN GOLD PRICE", fill=(255, 215, 0, 255), font=font_title, anchor="mm")

# Formula Box
draw3.rounded_rectangle([(80, 180), (1000, 400)], radius=20, fill=(255, 255, 255, 255), outline=(24, 28, 36, 255), width=3)
draw3.text((540, 240), "INDIAN GOLD PRICE (₹) = ", fill=(24, 28, 36, 255), font=get_font(34, bold=True), anchor="mm")
draw3.text((540, 330), "GLOBAL GOLD ($)  ×  USD/INR RATE (₹)", fill=(218, 140, 0, 255), font=get_font(40, bold=True), anchor="mm")

# Engine 1 Box
draw3.rounded_rectangle([(80, 450), (510, 880)], radius=18, fill=(255, 255, 255, 255), outline=(40, 120, 220, 255), width=3)
draw3.rectangle([(80, 450), (510, 520)], fill=(40, 120, 220, 255))
draw3.text((295, 485), "ENGINE 1", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
draw3.text((295, 580), "GLOBAL PRICE", fill=(24, 28, 36, 255), font=font_num, anchor="mm")
draw3.text((295, 680), "• Wars & Fed Rates", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")
draw3.text((295, 750), "• Central Bank Buying", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")
draw3.text((295, 820), "• Global Inflation", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")

# Engine 2 Box
draw3.rounded_rectangle([(570, 450), (1000, 880)], radius=18, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=3)
draw3.rectangle([(570, 450), (1000, 520)], fill=(220, 50, 50, 255))
draw3.text((785, 485), "ENGINE 2", fill=(255, 255, 255, 255), font=font_sub, anchor="mm")
draw3.text((785, 580), "USD/INR FOREX", fill=(220, 30, 30, 255), font=font_num, anchor="mm")
draw3.text((785, 680), "• Rupee Depreciation", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")
draw3.text((785, 750), "• India Trade Deficit", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")
draw3.text((785, 820), "• FII Capital Outflows", fill=(80, 80, 80, 255), font=font_sub, anchor="mm")

img3.save(asset_dir / "beat4_formula_breakdown.png")
print("Saved beat4_formula_breakdown.png")

# ----------------------------------------------------
# 4. ASSET: Beat 5 - The 3 Core Market Scenarios (1080x1920 Full Canvas)
# ----------------------------------------------------
img4 = Image.new("RGBA", (w_full, h_full), (18, 22, 30, 255))
draw4 = ImageDraw.Draw(img4)

for x in range(0, w_full, 50):
    draw4.line([(x, 0), (x, h_full)], fill=(30, 36, 48, 255), width=1)
for y in range(0, h_full, 50):
    draw4.line([(0, y), (w_full, y)], fill=(30, 36, 48, 255), width=1)

draw4.rounded_rectangle([(80, 80), (1000, 200)], radius=18, fill=(255, 215, 0, 255))
draw4.text((540, 140), "THE 3 GOLD PRICE SCENARIOS", fill=(18, 22, 30, 255), font=get_font(44, bold=True), anchor="mm")

# Scenario 1 Card
draw4.rounded_rectangle([(80, 250), (1000, 600)], radius=20, fill=(28, 34, 48, 255), outline=(80, 90, 110, 255), width=2)
draw4.text((120, 300), "SCENARIO 1: ONLY RUPEE DROPS", fill=(255, 215, 0, 255), font=get_font(34, bold=True))
draw4.text((120, 370), "• Global Gold: Flat ($2,500)", fill=(200, 200, 200, 255), font=get_font(30))
draw4.text((120, 430), "• Rupee: Drops (₹82 → ₹86)", fill=(255, 100, 100, 255), font=get_font(30))
draw4.rounded_rectangle([(120, 500), (960, 570)], radius=10, fill=(40, 50, 70, 255))
draw4.text((540, 535), "RESULT: India Price Rises (Moderate ↗)", fill=(255, 215, 0, 255), font=get_font(30, bold=True), anchor="mm")

# Scenario 2 Card
draw4.rounded_rectangle([(80, 650), (1000, 1000)], radius=20, fill=(28, 34, 48, 255), outline=(80, 90, 110, 255), width=2)
draw4.text((120, 700), "SCENARIO 2: ONLY GLOBAL GOLD RISES", fill=(100, 220, 255, 255), font=get_font(34, bold=True))
draw4.text((120, 770), "• Global Gold: Surges ($2,500 → $2,800)", fill=(100, 220, 120, 255), font=get_font(30))
draw4.text((120, 830), "• Rupee: Stable (₹83)", fill=(200, 200, 200, 255), font=get_font(30))
draw4.rounded_rectangle([(120, 900), (960, 970)], radius=10, fill=(40, 50, 70, 255))
draw4.text((540, 935), "RESULT: India Price Rises (Strong ↗↗)", fill=(100, 220, 255, 255), font=get_font(30, bold=True), anchor="mm")

# Scenario 3 Card (Double Whammy)
draw4.rounded_rectangle([(80, 1050), (1000, 1550)], radius=24, fill=(45, 20, 25, 255), outline=(255, 60, 60, 255), width=4)
draw4.text((120, 1110), "SCENARIO 3: THE DOUBLE WHAMMY ⚡", fill=(255, 80, 80, 255), font=get_font(38, bold=True))
draw4.text((120, 1190), "• Global Gold: Surges Rapidly ↗ ($2,800+)", fill=(255, 200, 100, 255), font=get_font(32, bold=True))
draw4.text((120, 1260), "• AND Rupee: Crashes Steeply ↘ (₹86+)", fill=(255, 100, 100, 255), font=get_font(32, bold=True))
draw4.rounded_rectangle([(120, 1340), (960, 1490)], radius=16, fill=(70, 25, 30, 255))
draw4.text((540, 1390), "RESULT: EXPLOSIVE SUPER SPIKE! 🚀", fill=(255, 220, 0, 255), font=get_font(36, bold=True), anchor="mm")
draw4.text((540, 1450), "Gold reaches ₹1.5 Lakh+ record levels in India!", fill=(255, 255, 255, 255), font=get_font(28, bold=False), anchor="mm")

img4.save(asset_dir / "beat5_scenario_matrix.png")
print("Saved beat5_scenario_matrix.png")

# ----------------------------------------------------
# 5. ASSET: Beat 7 - Action Checklist (1080x960 for split top)
# ----------------------------------------------------
img5 = Image.new("RGBA", (w_split, h_split), (245, 243, 238, 255))
draw5 = ImageDraw.Draw(img5)

for x in range(0, w_split, 40):
    draw5.line([(x, 0), (x, h_split)], fill=(230, 227, 220, 255), width=1)
for y in range(0, h_split, 40):
    draw5.line([(0, y), (w_split, y)], fill=(230, 227, 220, 255), width=1)

draw5.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw5.text((540, 85), "NEXT TIME GOLD PRICES SURGE, CHECK:", fill=(255, 215, 0, 255), font=font_title, anchor="mm")

items = [
    ("1. Check Global Gold (XAU/USD)", "Did spot gold actually jump in USD terms?", (40, 140, 60, 255)),
    ("2. Check USD/INR Exchange Rate", "Did the Indian Rupee weaken against the Dollar?", (200, 40, 40, 255)),
    ("3. Identify Double Whammy", "Are both engines firing simultaneously?", (220, 140, 0, 255))
]

y_pos = 180
for title, desc, col in items:
    draw5.rounded_rectangle([(80, y_pos), (1000, y_pos + 200)], radius=16, fill=(255, 255, 255, 255), outline=col, width=3)
    draw5.rounded_rectangle([(100, y_pos + 30), (160, y_pos + 90)], radius=8, fill=col)
    draw5.text((130, y_pos + 60), "✓", fill=(255, 255, 255, 255), font=get_font(34, bold=True), anchor="mm")
    draw5.text((190, y_pos + 60), title, fill=(24, 28, 36, 255), font=get_font(34, bold=True))
    draw5.text((190, y_pos + 120), desc, fill=(100, 100, 100, 255), font=get_font(28, bold=False))
    y_pos += 230

img5.save(asset_dir / "beat7_checklist.png")
print("Saved beat7_checklist.png")

# ----------------------------------------------------
# 6. ASSET: Beat 8 - Official Profit Bricks Brand Outro (1080x1920 Full Canvas)
# ----------------------------------------------------
img6 = Image.new("RGBA", (w_full, h_full), (16, 20, 28, 255))
draw6 = ImageDraw.Draw(img6)

for x in range(0, w_full, 50):
    draw6.line([(x, 0), (x, h_full)], fill=(28, 34, 46, 255), width=1)
for y in range(0, h_full, 50):
    draw6.line([(0, y), (w_full, y)], fill=(28, 34, 46, 255), width=1)

# Card Container
draw6.rounded_rectangle([(100, 320), (980, 1600)], radius=32, fill=(24, 30, 42, 255), outline=(255, 215, 0, 255), width=4)

# Place Official Logo
pb_logo = Image.open(asset_dir / "profit_bricks_logo.png").convert("RGBA")
# Resize logo keeping aspect ratio
logo_w, logo_h = pb_logo.size
target_w = 650
target_h = int(logo_h * (target_w / logo_w))
pb_logo_resized = pb_logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
img6.paste(pb_logo_resized, ((w_full - target_w) // 2, 440), pb_logo_resized)

draw6.text((540, 1080), "TRADING SOLUTIONS & MARKET INTELLIGENCE", fill=(255, 215, 0, 255), font=get_font(32, bold=True), anchor="mm")
draw6.text((540, 1160), "Master Market Economics in Simple Hindi", fill=(220, 220, 220, 255), font=get_font(34, bold=False), anchor="mm")

# Follow Button
draw6.rounded_rectangle([(240, 1280), (840, 1420)], radius=70, fill=(220, 30, 30, 255))
draw6.text((540, 1350), "🔔 FOLLOW PROFIT BRICKS", fill=(255, 255, 255, 255), font=get_font(38, bold=True), anchor="mm")

img6.save(asset_dir / "beat8_outro_card.png")
print("Saved beat8_outro_card.png")
print("All 6 Vox Explainer graphic layers generated successfully!")
