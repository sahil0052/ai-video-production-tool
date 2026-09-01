import json
with open('storage/deliverables/voxpipe_0831_1_nishahomes/transcript_en.json', encoding='utf-8') as f:
    data = json.load(f)
for s in data['segments']:
    print(f"{s['start']:.2f}s - {s['end']:.2f}s: {s['text']}")
