import json
from pathlib import Path

with open(r"storage/0826_3_transcript.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []
for i, s in enumerate(data['segments']):
    lines.append(f"[{s['start']:05.2f}s - {s['end']:05.2f}s] {s['text']}")

out_txt = Path(r"storage/0826_3_transcript_readable.txt")
out_txt.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote readable transcript to {out_txt}")
