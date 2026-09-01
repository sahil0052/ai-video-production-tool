import json
from pathlib import Path

WORKSPACE = Path(r"c:\websites\ai video production tool")
OUT_DIR = WORKSPACE / "storage" / "deliverables" / "0826-certified-master"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASS_PATH = OUT_DIR / "captions.ass"

# Script segments with start/end frames
CAPTIONS = [
    (0.00, 1.30, "PROFIT KE BAAD...", "cyan"),
    (1.30, 2.96, "DIMAAG STUPID DECISIONS KYUN LETA HAI?", "red"),
    (2.96, 5.42, "KAL TAK JO TRADER ₹1,000 RISK SE DARR RAHA THA...", "none"),
    (5.42, 7.24, "AAJ ₹10,000 KI TRADE KYUN LE RAHA HAI?", "red"),
    (7.24, 10.50, "KYUNKI PROFIT KE BAAD CONFIDENCE BADHTA HAI", "cyan"),
    (10.50, 13.50, "DIMAAG KO LAGTA HAI 'MARKET SAMAJH AA GAYA'", "none"),
    (13.50, 16.50, "EK TRADE PROFIT HUA... PHIR DOOSRA", "cyan"),
    (16.50, 19.50, "TOH WOH POSITION SIZE BADHA DETA HAI", "red"),
    (19.50, 22.50, "PROBLEM TAB START HOTI HAI JAB LOSS HOTA HAI", "red"),
    (22.50, 25.50, "AUR EK LOSS RECOVER KARNE MEIN RISK AUR BADHTA HAI", "red"),
    (25.50, 28.50, "ACTUALLY PROBLEM TRADING MEIN NAHI...", "none"),
    (28.50, 31.00, "TRADER KE BEHAVIOUR MEIN HOTI HAI", "red"),
    (31.00, 33.80, "PROFITABLE TRADER BANNE KE LIYE DISCIPLINE CHAHIYE", "cyan"),
    (33.80, 36.46, "SIMPLE LANGUAGE MEIN SAMAJHNE HAIN... FOLLOW KAR LO!", "cyan"),
]

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Consolas,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,4,0,2,60,60,200,1
Style: Cyan,Consolas,46,&H00FFFF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,4,0,2,60,60,200,1
Style: Red,Consolas,46,&H004B4BFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,4,0,2,60,60,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

for start_s, end_s, text, style_type in CAPTIONS:
    st = format_ass_time(start_s)
    et = format_ass_time(end_s)
    style = "Cyan" if style_type == "cyan" else ("Red" if style_type == "red" else "Default")
    ass_content += f"Dialogue: 0,{st},{et},{style},,0,0,0,,{text}\n"

ASS_PATH.write_text(ass_content, encoding="utf-8")
print(f"Generated ASS captions at {ASS_PATH}")
