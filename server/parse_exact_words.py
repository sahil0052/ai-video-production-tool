import json
from pathlib import Path

p = Path(r"storage/0826_transcript.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

# Script reference segments in Hindi/English
# Segment 1: "Profit ke baad dimaag suddenly stupid decisions kyun lene lagta hai?" (0 - 2.96s)
# Segment 2: "Kal tak jo trader 1000 risk lene se darr raha tha... aaj 10,000 ki trade kyun le raha hai?" (2.96 - 7.24s)
# Segment 3: "Kyuki profit ke baad confidence badhta hai. Dimaag ko lagta hai 'Mujhe market samajh aa gaya'. Aur yahin se overconfidence start hota hai." (7.24 - 13.50s)
# Segment 4: "Ek trade profit hua... phir doosra. Ab trader ko lagta hai next trade bhi profit hi dega. Toh woh position size badha deta hai." (13.50 - 19.50s)
# Segment 5: "Problem tab start hoti hai jab woh loss ke baad bhi same confidence ke saath aur bada trade le leta hai. Aur ek loss ko recover karne ke chakkar mein risk aur badhta jaata hai." (19.50 - 27.50s)
# Segment 6: "Actually problem trading mein nahi, trader ke behaviour mein hoti hai. Profit ke baad overconfidence aur loss ke baad revenge trading... dono milke account ko damage kar sakte hain." (27.50 - 33.00s)
# Segment 7: "Isliye profitable trader banne ke liye sirf strategy nahi, discipline bhi chahiye. Aur aise trading psychology aur EA concepts simple language mein samajhne hain, toh follow kar lo." (33.00 - 36.46s)

print(f"Total whisper segments: {len(data['segments'])}")
for i, s in enumerate(data['segments']):
    text = s['text']
    w_list = [f"{w['word']} [{w['start']:.2f}-{w['end']:.2f}]" for w in s['words']]
    print(f"[{i:02d}] {s['start']:05.2f}s -> {s['end']:05.2f}s: {text}")
    print(f"     {' '.join(w_list)}")
