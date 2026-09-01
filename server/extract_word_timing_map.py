import json
from pathlib import Path

p = Path(r"storage/0826_transcript.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

# Flatten all words with start and end
all_words = []
for s in data["segments"]:
    for w in s.get("words", []):
        all_words.append({
            "start": round(w["start"], 2),
            "end": round(w["end"], 2),
            "text": w["word"]
        })

print(f"Extracted {len(all_words)} raw words. First 10 and last 10:")
for w in all_words[:10]:
    print(f"  {w['start']:05.2f}s -> {w['end']:05.2f}s")
for w in all_words[-10:]:
    print(f"  {w['start']:05.2f}s -> {w['end']:05.2f}s")
