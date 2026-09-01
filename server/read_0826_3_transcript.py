import json
from pathlib import Path

with open(r"storage/0826_3_transcript.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total Duration: {data['duration']}s")
print(f"Total Segments: {len(data['segments'])}")
print("\n--- SEGMENTS TIMELINE ---")

for i, s in enumerate(data['segments']):
    # print start, end, and duration
    dur = s['end'] - s['start']
    w_count = len(s.get('words', []))
    print(f"Segment {i+1:02d}: {s['start']:05.2f}s -> {s['end']:05.2f}s ({dur:04.2f}s, {w_count} words)")
