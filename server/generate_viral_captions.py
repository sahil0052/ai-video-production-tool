from pathlib import Path

OUT_DIR = Path(r"c:\websites\ai video production tool\storage\deliverables\0826-certified-master")
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASS_PATH = OUT_DIR / "viral_captions.ass"

# Format: (start_s, end_s, text_with_ass_tags)
# Colors in ASS &H00BBGGRR&:
# Yellow: &H0000E5FF& (RGB 255, 229, 0)
# Cyan:   &H00FFFF00& (RGB 0, 255, 255)
# Red:    &H002E2ED6& (RGB 214, 46, 46)
# Green:  &H0033E533& (RGB 51, 229, 51)
BURSTS = [
    (0.00, 1.20, r"{\c&H00FFFF00&}PROFIT{\c&H00FFFFFF&} KE BAAD..."),
    (1.20, 2.14, r"DIMAAG SUDDENLY"),
    (2.14, 2.96, r"{\c&H002E2ED6&}STUPID DECISIONS?{\c&H00FFFFFF&}"),
    (2.96, 4.30, r"KAL TAK JO TRADER"),
    (4.30, 5.42, r"{\c&H0000E5FF&}₹1,000 RISK{\c&H00FFFFFF&} SE DARR RAHA THA..."),
    (5.42, 6.64, r"AAJ {\c&H002E2ED6&}₹10,000 TRADE{\c&H00FFFFFF&}"),
    (6.64, 7.24, r"KYUN LE RAHA HAI?"),
    (7.24, 8.80, r"KYUNKI PROFIT KE BAAD"),
    (8.80, 10.50, r"{\c&H00FFFF00&}CONFIDENCE{\c&H00FFFFFF&} BADHTA HAI!"),
    (10.50, 12.00, r"DIMAAG KO LAGTA HAI"),
    (12.00, 13.50, r"{\c&H0000E5FF&}'MARKET SAMAJH AA GAYA'{\c&H00FFFFFF&}"),
    (13.50, 15.00, r"AUR YAHIN SE..."),
    (15.00, 16.50, r"{\c&H002E2ED6&}OVERCONFIDENCE START!{\c&H00FFFFFF&}"),
    (16.50, 18.00, r"EK TRADE {\c&H0033E533&}PROFIT HUA...{\c&H00FFFFFF&}"),
    (18.00, 19.50, r"PHIR {\c&H0033E533&}DOOSRA PROFIT!{\c&H00FFFFFF&}"),
    (19.50, 21.00, r"TOH WOH {\c&H0000E5FF&}POSITION SIZE{\c&H00FFFFFF&}"),
    (21.00, 22.50, r"BADHA DETA HAI!"),
    (22.50, 24.00, r"PROBLEM TAB START HOTI HAI"),
    (24.00, 25.50, r"JAB {\c&H002E2ED6&}LOSS{\c&H00FFFFFF&} HOTA HAI..."),
    (25.50, 27.00, r"AUR LOSS RECOVER KARNE MEIN"),
    (27.00, 28.50, r"{\c&H002E2ED6&}RISK AUR BADHTA HAI!{\c&H00FFFFFF&}"),
    (28.50, 30.00, r"ACTUALLY PROBLEM TRADING MEIN NAHI,"),
    (30.00, 31.50, r"{\c&H002E2ED6&}TRADER BEHAVIOUR{\c&H00FFFFFF&} MEIN HOTI HAI!"),
    (31.50, 33.00, r"OVERCONFIDENCE + {\c&H002E2ED6&}REVENGE TRADING{\c&H00FFFFFF&}"),
    (33.00, 34.20, r"ACCOUNT KO {\c&H002E2ED6&}DAMAGE{\c&H00FFFFFF&} KAR SAKTE HAIN."),
    (34.20, 35.30, r"SIRF STRATEGY NAHI, {\c&H00FFFF00&}DISCIPLINE{\c&H00FFFFFF&} BHI CHAHIYE!"),
    (35.30, 36.46, r"{\c&H0000E5FF&}FOLLOW KAR LO! 🚀{\c&H00FFFFFF&}"),
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
Style: ViralMain,Arial Black,54,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,102,102,1,0,1,6,3,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

for start_s, end_s, text in BURSTS:
    st = format_ass_time(start_s)
    et = format_ass_time(end_s)
    ass_content += f"Dialogue: 0,{st},{et},ViralMain,,0,0,0,,{text}\n"

ASS_PATH.write_text(ass_content, encoding="utf-8")
print(f"Generated Viral ASS Subtitles at: {ASS_PATH}")
