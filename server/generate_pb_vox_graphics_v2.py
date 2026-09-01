import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
asset_dir = work_dir / "assets"
asset_dir.mkdir(parents=True, exist_ok=True)

def get_font(size, bold=True):
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
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

w_split, h_split = 1080, 960
w_full, h_full = 1080, 1920

# ----------------------------------------------------
# 1. ASSET: Beat 2 - Gold vs Rupee (1080x960)
# ----------------------------------------------------
img1 = Image.new("RGBA", (w_split, h_split), (248, 246, 240, 255))
draw1 = ImageDraw.Draw(img1)
for x in range(0, w_split, 40):
    draw1.line([(x, 0), (x, h_split)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_split, 40):
    draw1.line([(0, y), (w_split, y)], fill=(232, 228, 218, 255), width=1)

draw1.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw1.text((540, 85), "THE GOLD PARADOX: STRENGTH VS WEAKNESS", fill=(255, 215, 0, 255), font=get_font(38, bold=True), anchor="mm")

# Left Card: Gold
draw1.rounded_rectangle([(80, 180), (510, 880)], radius=20, fill=(255, 255, 255, 255), outline=(218, 165, 32, 255), width=4)
draw1.rectangle([(80, 180), (510, 260)], fill=(255, 215, 0, 255))
draw1.text((295, 220), "GLOBAL GOLD (XAU)", fill=(24, 28, 36, 255), font=get_font(32, bold=True), anchor="mm")
draw1.text((295, 380), "[ GOLD INGOT ]", fill=(180, 130, 0, 255), font=get_font(36, bold=True), anchor="mm")
draw1.text((295, 520), "$2,700 / oz", fill=(24, 28, 36, 255), font=get_font(52, bold=True), anchor="mm")
draw1.text((295, 600), "CONSTANT PRICE", fill=(100, 100, 100, 255), font=get_font(32, bold=True), anchor="mm")
draw1.rounded_rectangle([(120, 700), (470, 800)], radius=12, fill=(235, 245, 255, 255))
draw1.text((295, 750), "FLAT GLOBAL MARKET", fill=(40, 90, 180, 255), font=get_font(28, bold=True), anchor="mm")

# Right Card: Rupee
draw1.rounded_rectangle([(570, 180), (1000, 880)], radius=20, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=4)
draw1.rectangle([(570, 180), (1000, 260)], fill=(220, 50, 50, 255))
draw1.text((785, 220), "INDIAN RUPEE (INR)", fill=(255, 255, 255, 255), font=get_font(32, bold=True), anchor="mm")
draw1.text((785, 380), "[ DEPRECIATING ]", fill=(200, 30, 30, 255), font=get_font(36, bold=True), anchor="mm")
draw1.text((785, 520), "Rs 84.50 / $1", fill=(220, 30, 30, 255), font=get_font(52, bold=True), anchor="mm")
draw1.text((785, 600), "RUPEE WEAKENING", fill=(220, 50, 50, 255), font=get_font(32, bold=True), anchor="mm")
draw1.rounded_rectangle([(610, 700), (960, 800)], radius=12, fill=(255, 235, 235, 255))
draw1.text((785, 750), "IMPORT COST SURGES", fill=(200, 30, 30, 255), font=get_font(28, bold=True), anchor="mm")

img1.save(asset_dir / "beat2_gold_vs_rupee.png")

# ----------------------------------------------------
# 2. ASSET: Beat 3 - Global Dollar Flow (1080x1920)
# ----------------------------------------------------
img2 = Image.new("RGBA", (w_full, h_full), (248, 246, 240, 255))
draw2 = ImageDraw.Draw(img2)
for x in range(0, w_full, 40):
    draw2.line([(x, 0), (x, h_full)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_full, 40):
    draw2.line([(0, y), (w_full, y)], fill=(232, 228, 218, 255), width=1)

draw2.rounded_rectangle([(80, 100), (1000, 220)], radius=18, fill=(24, 28, 36, 255))
draw2.text((540, 160), "WHY DOLLAR MAKES GOLD MEHENGA", fill=(255, 215, 0, 255), font=get_font(42, bold=True), anchor="mm")

# Case 1
draw2.rounded_rectangle([(80, 280), (1000, 640)], radius=20, fill=(255, 255, 255, 255), outline=(200, 200, 200, 255), width=3)
draw2.rectangle([(80, 280), (1000, 350)], fill=(40, 120, 220, 255))
draw2.text((540, 315), "CASE 1: BASELINE EXCHANGE RATE", fill=(255, 255, 255, 255), font=get_font(32, bold=True), anchor="mm")
draw2.text((120, 420), "• Global Gold Price: $2,500 / oz", fill=(40, 40, 40, 255), font=get_font(34, bold=False))
draw2.text((120, 480), "• USD / INR Exchange: $1 = Rs 80", fill=(40, 40, 40, 255), font=get_font(34, bold=False))
draw2.rounded_rectangle([(120, 540), (960, 610)], radius=10, fill=(235, 245, 255, 255))
draw2.text((540, 575), "INDIA LANDED COST = Rs 2,00,000", fill=(20, 90, 180, 255), font=get_font(32, bold=True), anchor="mm")

# Case 2
draw2.rounded_rectangle([(80, 700), (1000, 1100)], radius=20, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=3)
draw2.rectangle([(80, 700), (1000, 770)], fill=(220, 50, 50, 255))
draw2.text((540, 735), "CASE 2: DOLLAR SURGES (RUPEE WEAKENS)", fill=(255, 255, 255, 255), font=get_font(32, bold=True), anchor="mm")
draw2.text((120, 840), "• Global Gold Price: $2,500 / oz (EXACTLY SAME!)", fill=(40, 40, 40, 255), font=get_font(34, bold=True))
draw2.text((120, 900), "• USD / INR Exchange: $1 = Rs 90 (+12.5% SURGE)", fill=(200, 30, 30, 255), font=get_font(34, bold=True))
draw2.rounded_rectangle([(120, 960), (960, 1060)], radius=10, fill=(255, 235, 235, 255))
draw2.text((540, 1010), "INDIA LANDED COST = Rs 2,25,000 (+Rs 25,000 EXTRA!)", fill=(200, 30, 30, 255), font=get_font(30, bold=True), anchor="mm")

# Key takeaway
draw2.rounded_rectangle([(80, 1180), (1000, 1720)], radius=24, fill=(24, 28, 36, 255))
draw2.text((540, 1260), "CRITICAL MARKET TAKEAWAY", fill=(255, 215, 0, 255), font=get_font(38, bold=True), anchor="mm")
draw2.text((540, 1370), "Gold price did NOT rise in USA...", fill=(200, 200, 200, 255), font=get_font(34, bold=False), anchor="mm")
draw2.text((540, 1460), "India paid more simply because", fill=(255, 255, 255, 255), font=get_font(36, bold=True), anchor="mm")
draw2.text((540, 1550), "THE RUPEE LOST PURCHASING POWER!", fill=(255, 80, 80, 255), font=get_font(40, bold=True), anchor="mm")
draw2.rounded_rectangle([(140, 1630), (940, 1690)], radius=8, fill=(40, 48, 62, 255))
draw2.text((540, 1660), "Currency Depreciation = Domestic Price Explosion", fill=(255, 215, 0, 255), font=get_font(26, bold=True), anchor="mm")

img2.save(asset_dir / "beat3_global_dollar_flow.png")

# ----------------------------------------------------
# 3. ASSET: Beat 4 - The 2-Variable Formula (1080x960)
# ----------------------------------------------------
img3 = Image.new("RGBA", (w_split, h_split), (248, 246, 240, 255))
draw3 = ImageDraw.Draw(img3)
for x in range(0, w_split, 40):
    draw3.line([(x, 0), (x, h_split)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_split, 40):
    draw3.line([(0, y), (w_split, y)], fill=(232, 228, 218, 255), width=1)

draw3.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw3.text((540, 85), "THE 2 ENGINES OF INDIAN GOLD PRICE", fill=(255, 215, 0, 255), font=get_font(38, bold=True), anchor="mm")

draw3.rounded_rectangle([(80, 170), (1000, 380)], radius=20, fill=(255, 255, 255, 255), outline=(24, 28, 36, 255), width=3)
draw3.text((540, 230), "INDIA GOLD PRICE (Rs) = ", fill=(24, 28, 36, 255), font=get_font(32, bold=True), anchor="mm")
draw3.text((540, 310), "GLOBAL GOLD ($)  x  USD/INR FOREX (Rs)", fill=(200, 130, 0, 255), font=get_font(38, bold=True), anchor="mm")

# Engine 1
draw3.rounded_rectangle([(80, 430), (510, 880)], radius=18, fill=(255, 255, 255, 255), outline=(40, 120, 220, 255), width=3)
draw3.rectangle([(80, 430), (510, 500)], fill=(40, 120, 220, 255))
draw3.text((295, 465), "ENGINE 1", fill=(255, 255, 255, 255), font=get_font(30, bold=True), anchor="mm")
draw3.text((295, 560), "GLOBAL GOLD ($)", fill=(24, 28, 36, 255), font=get_font(36, bold=True), anchor="mm")
draw3.text((295, 660), "• Wars & Geopolitics", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")
draw3.text((295, 730), "• Central Bank Buying", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")
draw3.text((295, 800), "• US Fed Interest Rates", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")

# Engine 2
draw3.rounded_rectangle([(570, 430), (1000, 880)], radius=18, fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=3)
draw3.rectangle([(570, 430), (1000, 500)], fill=(220, 50, 50, 255))
draw3.text((785, 465), "ENGINE 2", fill=(255, 255, 255, 255), font=get_font(30, bold=True), anchor="mm")
draw3.text((785, 560), "USD/INR FOREX (Rs)", fill=(220, 30, 30, 255), font=get_font(36, bold=True), anchor="mm")
draw3.text((785, 660), "• Rupee Depreciation", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")
draw3.text((785, 730), "• Import Deficits", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")
draw3.text((785, 800), "• FII Capital Outflows", fill=(60, 60, 60, 255), font=get_font(28, bold=False), anchor="mm")

img3.save(asset_dir / "beat4_formula_breakdown.png")

# ----------------------------------------------------
# 4. ASSET: Beat 5 - The 3 Scenarios (1080x1920)
# ----------------------------------------------------
img4 = Image.new("RGBA", (w_full, h_full), (248, 246, 240, 255))
draw4 = ImageDraw.Draw(img4)
for x in range(0, w_full, 40):
    draw4.line([(x, 0), (x, h_full)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_full, 40):
    draw4.line([(0, y), (w_full, y)], fill=(232, 228, 218, 255), width=1)

draw4.rounded_rectangle([(80, 80), (1000, 200)], radius=18, fill=(24, 28, 36, 255))
draw4.text((540, 140), "THE 3 GOLD PRICE SCENARIOS", fill=(255, 215, 0, 255), font=get_font(42, bold=True), anchor="mm")

# Scenario 1
draw4.rounded_rectangle([(80, 250), (1000, 590)], radius=20, fill=(255, 255, 255, 255), outline=(180, 180, 180, 255), width=3)
draw4.rectangle([(80, 250), (1000, 320)], fill=(24, 28, 36, 255))
draw4.text((540, 285), "SCENARIO 1: ONLY RUPEE DROPS", fill=(255, 215, 0, 255), font=get_font(30, bold=True), anchor="mm")
draw4.text((120, 380), "• Global Gold: Flat ($2,500)", fill=(60, 60, 60, 255), font=get_font(32))
draw4.text((120, 440), "• Rupee: Weakens (Rs 82 -> Rs 86)", fill=(200, 30, 30, 255), font=get_font(32, bold=True))
draw4.rounded_rectangle([(120, 500), (960, 565)], radius=10, fill=(245, 245, 245, 255))
draw4.text((540, 532), "RESULT: India Price Rises (Moderate Rise)", fill=(24, 28, 36, 255), font=get_font(28, bold=True), anchor="mm")

# Scenario 2
draw4.rounded_rectangle([(80, 640), (1000, 980)], radius=20, fill=(255, 255, 255, 255), outline=(180, 180, 180, 255), width=3)
draw4.rectangle([(80, 640), (1000, 710)], fill=(40, 120, 220, 255))
draw4.text((540, 675), "SCENARIO 2: ONLY GLOBAL GOLD RISES", fill=(255, 255, 255, 255), font=get_font(30, bold=True), anchor="mm")
draw4.text((120, 770), "• Global Gold: Surges ($2,500 -> $2,800)", fill=(40, 120, 220, 255), font=get_font(32, bold=True))
draw4.text((120, 830), "• Rupee: Stable (Rs 83)", fill=(60, 60, 60, 255), font=get_font(32))
draw4.rounded_rectangle([(120, 890), (960, 955)], radius=10, fill=(235, 245, 255, 255))
draw4.text((540, 922), "RESULT: India Price Rises (Strong Rise)", fill=(20, 90, 180, 255), font=get_font(28, bold=True), anchor="mm")

# Scenario 3: Double Whammy
draw4.rounded_rectangle([(80, 1030), (1000, 1600)], radius=24, fill=(255, 255, 255, 255), outline=(220, 30, 30, 255), width=5)
draw4.rectangle([(80, 1030), (1000, 1110)], fill=(220, 30, 30, 255))
draw4.text((540, 1070), "SCENARIO 3: THE DOUBLE WHAMMY", fill=(255, 255, 255, 255), font=get_font(34, bold=True), anchor="mm")
draw4.text((120, 1180), "• Global Gold: Surges Rapidly ($2,800+)", fill=(180, 120, 0, 255), font=get_font(34, bold=True))
draw4.text((120, 1250), "• AND Rupee: Crashes Steeply (Rs 86+)", fill=(200, 30, 30, 255), font=get_font(34, bold=True))
draw4.rounded_rectangle([(120, 1340), (960, 1540)], radius=16, fill=(24, 28, 36, 255))
draw4.text((540, 1400), "EXPLOSIVE SUPER SPIKE!", fill=(255, 215, 0, 255), font=get_font(42, bold=True), anchor="mm")
draw4.text((540, 1480), "Gold reaches Rs 1.5 Lakh+ all-time high!", fill=(255, 255, 255, 255), font=get_font(30, bold=False), anchor="mm")

img4.save(asset_dir / "beat5_scenario_matrix.png")

# ----------------------------------------------------
# 5. ASSET: Beat 7 - Checklist (1080x960)
# ----------------------------------------------------
img5 = Image.new("RGBA", (w_split, h_split), (248, 246, 240, 255))
draw5 = ImageDraw.Draw(img5)
for x in range(0, w_split, 40):
    draw5.line([(x, 0), (x, h_split)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_split, 40):
    draw5.line([(0, y), (w_split, y)], fill=(232, 228, 218, 255), width=1)

draw5.rounded_rectangle([(60, 40), (1020, 130)], radius=16, fill=(24, 28, 36, 255))
draw5.text((540, 85), "NEXT TIME GOLD PRICES SURGE, CHECK:", fill=(255, 215, 0, 255), font=get_font(38, bold=True), anchor="mm")

items = [
    ("1. Check Global Gold (XAU/USD)", "Did spot gold jump in international markets?", (40, 140, 60, 255)),
    ("2. Check USD/INR Exchange Rate", "Did the Indian Rupee weaken against the Dollar?", (200, 40, 40, 255)),
    ("3. Identify Double Whammy", "Are both engines firing simultaneously?", (220, 140, 0, 255))
]

y_pos = 180
for title, desc, col in items:
    draw5.rounded_rectangle([(80, y_pos), (1000, y_pos + 200)], radius=16, fill=(255, 255, 255, 255), outline=col, width=3)
    draw5.rounded_rectangle([(100, y_pos + 30), (160, y_pos + 90)], radius=8, fill=col)
    draw5.text((130, y_pos + 60), "[X]", fill=(255, 255, 255, 255), font=get_font(28, bold=True), anchor="mm")
    draw5.text((190, y_pos + 60), title, fill=(24, 28, 36, 255), font=get_font(32, bold=True))
    draw5.text((190, y_pos + 120), desc, fill=(90, 90, 90, 255), font=get_font(26, bold=False))
    y_pos += 230

img5.save(asset_dir / "beat7_checklist.png")

# ----------------------------------------------------
# 6. ASSET: Beat 8 - Profit Bricks Brand Outro (1080x1920)
# ----------------------------------------------------
img6 = Image.new("RGBA", (w_full, h_full), (248, 246, 240, 255))
draw6 = ImageDraw.Draw(img6)
for x in range(0, w_full, 40):
    draw6.line([(x, 0), (x, h_full)], fill=(232, 228, 218, 255), width=1)
for y in range(0, h_full, 40):
    draw6.line([(0, y), (w_full, y)], fill=(232, 228, 218, 255), width=1)

draw6.rounded_rectangle([(80, 280), (1000, 1620)], radius=32, fill=(255, 255, 255, 255), outline=(24, 28, 36, 255), width=4)

pb_logo = Image.open(asset_dir / "profit_bricks_logo.png").convert("RGBA")
logo_w, logo_h = pb_logo.size
target_w = 680
target_h = int(logo_h * (target_w / logo_w))
pb_logo_resized = pb_logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
img6.paste(pb_logo_resized, ((w_full - target_w) // 2, 420), pb_logo_resized)

draw6.rounded_rectangle([(140, 1060), (940, 1220)], radius=16, fill=(24, 28, 36, 255))
draw6.text((540, 1115), "MARKET INTELLIGENCE & TRADING SOLUTIONS", fill=(255, 215, 0, 255), font=get_font(28, bold=True), anchor="mm")
draw6.text((540, 1170), "Master Financial Economics in Simple Hindi", fill=(240, 240, 240, 255), font=get_font(30, bold=False), anchor="mm")

draw6.rounded_rectangle([(200, 1340), (880, 1490)], radius=75, fill=(220, 30, 30, 255))
draw6.text((540, 1415), "FOLLOW PROFIT BRICKS", fill=(255, 255, 255, 255), font=get_font(38, bold=True), anchor="mm")

img6.save(asset_dir / "beat8_outro_card.png")
print("Clean regenerated Vox Explainer graphic layers successfully!")
