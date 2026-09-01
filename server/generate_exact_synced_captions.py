import json
from pathlib import Path

# Clean Roman words array aligned to the 146 speech units:
# The complete transcript:
# "Profit ke baad dimaag suddenly stupid decisions kyun lene lagta hai?
# Kal tak jo trader ₹1,000 risk lene se darr raha tha… aaj ₹10,000 ki trade kyun le raha hai?
# Kyuki profit ke baad confidence badhta hai. Dimaag ko lagta hai—‘Mujhe market samajh aa gaya.’ Aur yahin se overconfidence start hota hai.
# Ek trade profit hua… phir doosra. Ab trader ko lagta hai next trade bhi profit hi dega. Toh woh position size badha deta hai.
# Problem tab start hoti hai jab woh loss ke baad bhi same confidence ke saath aur bada trade le leta hai. Aur ek loss ko recover karne ke chakkar mein risk aur badhta jaata hai.
# Actually problem trading mein nahi, trader ke behaviour mein hoti hai. Profit ke baad overconfidence aur loss ke baad revenge trading… dono milke account ko damage kar sakte hain.
# Isliye profitable trader banne ke liye sirf strategy nahi, discipline bhi chahiye. Aur aise trading psychology aur EA concepts simple language mein samajhne hain, toh follow kar lo."

p = Path(r"storage/0826_transcript.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

# Collect all word timestamps
w_times = []
for s in data["segments"]:
    for w in s.get("words", []):
        w_times.append((w["start"], w["end"]))

print(f"Total word slots: {len(w_times)}")

# Let's define the precise cards with exact word indices and highlighted keywords:
# (word_start_idx, word_end_idx, text_template)
# Format tags in ASS:
# Yellow: {\c&H0000E5FF&}
# Cyan:   {\c&H00FFFF00&}
# Red:    {\c&H002E2ED6&}
# Green:  {\c&H0033E533&}
# White:  {\c&H00FFFFFF&}

CARDS_DEF = [
    # 0 - 2.96s | Hook
    (0, 2, r"{\c&H00FFFF00&}PROFIT{\c&H00FFFFFF&} KE BAAD..."),                # Profit ke baad
    (3, 4, r"DIMAAG SUDDENLY"),                                               # dimaag suddenly
    (5, 6, r"{\c&H002E2ED6&}STUPID DECISIONS?{\c&H00FFFFFF&}"),               # stupid decisions
    (7, 10, r"KYUN LENE LAGTA HAI?"),                                         # kyun lene lagta hai
    
    # 2.96 - 7.24s | Contrast
    (11, 14, r"KAL TAK JO TRADER"),                                           # kal tak jo trader
    (15, 17, r"{\c&H0000E5FF&}₹1,000 RISK{\c&H00FFFFFF&}"),                   # 1000 risk lene
    (18, 21, r"SE DARR RAHA THA..."),                                         # se darr raha tha
    (22, 25, r"AAJ {\c&H002E2ED6&}₹10,000 TRADE{\c&H00FFFFFF&}"),             # aaj 10000 trade
    (26, 29, r"KYUN LE RAHA HAI?"),                                           # kyun le raha hai
    
    # 7.24 - 13.50s | The Psychology
    (30, 33, r"KYUNKI {\c&H00FFFF00&}PROFIT{\c&H00FFFFFF&} KE BAAD"),         # kyuki profit ke baad
    (34, 36, r"{\c&H00FFFF00&}CONFIDENCE{\c&H00FFFFFF&} BADHTA HAI!"),        # confidence badhta hai
    (37, 39, r"DIMAAG KO LAGTA HAI"),                                         # dimaag ko lagta hai
    (40, 44, r"{\c&H0000E5FF&}'MARKET SAMAJH AA GAYA'{\c&H00FFFFFF&}"),       # mujhe market samajh aa gaya
    (45, 47, r"AUR YAHIN SE..."),                                             # aur yahin se
    (48, 51, r"{\c&H002E2ED6&}OVERCONFIDENCE START!{\c&H00FFFFFF&}"),         # overconfidence start hota hai
    
    # 13.50 - 19.50s | The Trap
    (52, 55, r"EK TRADE {\c&H0033E533&}PROFIT HUA...{\c&H00FFFFFF&}"),        # ek trade profit hua
    (56, 58, r"PHIR {\c&H0033E533&}DOOSRA PROFIT!{\c&H00FFFFFF&}"),          # phir doosra
    (59, 63, r"AB TRADER KO LAGTA HAI"),                                      # ab trader ko lagta hai
    (64, 69, r"NEXT TRADE BHI {\c&H0033E533&}PROFIT DEGA!{\c&H00FFFFFF&}"),   # next trade bhi profit dega
    (70, 72, r"TOH WOH {\c&H0000E5FF&}POSITION SIZE{\c&H00FFFFFF&}"),         # toh woh position size
    (73, 75, r"{\c&H002E2ED6&}BADHA DETA HAI!{\c&H00FFFFFF&}"),               # badha deta hai
    
    # 19.50 - 27.50s | The Consequence
    (76, 79, r"{\c&H002E2ED6&}PROBLEM TAB START HOTI HAI{\c&H00FFFFFF&}"),    # problem tab start hoti hai
    (80, 83, r"JAB WOH {\c&H002E2ED6&}LOSS{\c&H00FFFFFF&} KE BAAD"),          # jab woh loss ke baad
    (84, 88, r"SAME CONFIDENCE KE SAATH"),                                     # same confidence ke saath
    (89, 93, r"AUR {\c&H002E2ED6&}BADA TRADE{\c&H00FFFFFF&} LETA HAI!"),      # aur bada trade leta hai
    (94, 98, r"AUR EK LOSS RECOVER KARNE"),                                   # aur ek loss recover karne
    (99, 102, r"KE CHAKKAR MEIN..."),                                         # ke chakkar mein
    (103, 107, r"{\c&H002E2ED6&}RISK AUR BADHTA JATA HAI!{\c&H00FFFFFF&}"),   # risk aur badhta jata hai
    
    # 27.50 - 33.00s | The Real Problem
    (108, 112, r"ACTUALLY PROBLEM TRADING MEIN NAHI,"),                        # actually problem trading mein nahi
    (113, 117, r"{\c&H002E2ED6&}TRADER BEHAVIOUR{\c&H00FFFFFF&} MEIN HAI!"),  # trader ke behaviour mein hoti hai
    (118, 121, r"{\c&H002E2ED6&}OVERCONFIDENCE{\c&H00FFFFFF&} AUR"),          # profit ke baad overconfidence
    (122, 125, r"{\c&H002E2ED6&}REVENGE TRADING...{\c&H00FFFFFF&}"),          # aur loss ke baad revenge trading
    (126, 130, r"ACCOUNT KO {\c&H002E2ED6&}DAMAGE{\c&H00FFFFFF&} KARTE HAIN."), # dono milke account ko damage karte hain
    
    # 33.00 - 36.46s | Solution + CTA
    (131, 135, r"ISLIYE SIRF STRATEGY NAHI,"),                                # isliye profitable trader banne
    (136, 139, r"{\c&H00FFFF00&}DISCIPLINE{\c&H00FFFFFF&} BHI CHAHIYE!"),     # discipline bhi chahiye
    (140, 143, r"SIMPLE LANGUAGE MEIN SAMAJHNA HAI,"),                        # aur trading psychology simple language
    (144, 145, r"TOH {\c&H0000E5FF&}FOLLOW KAR LO! 🚀{\c&H00FFFFFF&}"),       # toh follow kar lo
]

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

OUT_DIR = Path(r"c:\websites\ai video production tool\storage\deliverables\0826-certified-master")
OUT_DIR.mkdir(parents=True, exist_ok=True)
ASS_PATH = OUT_DIR / "exact_synced_captions.ass"

ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralSync,Arial Black,50,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,102,102,1,0,1,6,3,2,60,60,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

for i, (w_start, w_end, text) in enumerate(CARDS_DEF):
    # Get exact start from first word and end from last word
    s_idx = min(w_start, len(w_times) - 1)
    e_idx = min(w_end, len(w_times) - 1)
    
    t_start = w_times[s_idx][0]
    t_end = w_times[e_idx][1]
    
    # If next card exists, extend until next card starts to avoid flickering
    if i < len(CARDS_DEF) - 1:
        next_s_idx = min(CARDS_DEF[i+1][0], len(w_times) - 1)
        next_t_start = w_times[next_s_idx][0]
        if next_t_start > t_start:
            t_end = next_t_start
    else:
        t_end = max(t_end, 36.46)
        
    st = format_ass_time(t_start)
    et = format_ass_time(t_end)
    ass_content += f"Dialogue: 0,{st},{et},ViralSync,,0,0,0,,{text}\n"

ASS_PATH.write_text(ass_content, encoding="utf-8")
print(f"Generated EXACT 0-latency ASS Subtitles at: {ASS_PATH}")
