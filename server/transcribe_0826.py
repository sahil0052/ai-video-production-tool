import json
from pathlib import Path
from faster_whisper import WhisperModel

audio_path = r"D:\Downloads\0826 (1).mp4"
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_path, word_timestamps=True, language="hi")

results = {"segments": []}
for s in segments:
    seg_dict = {
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip(),
        "words": [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word.strip()} for w in s.words]
    }
    results["segments"].append(seg_dict)

out_p = Path(r"storage/0826_transcript.json")
out_p.parent.mkdir(parents=True, exist_ok=True)
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Transcribed {len(results['segments'])} segments to {out_p}")
for s in results["segments"]:
    print(f"[{s['start']:05.2f}s -> {s['end']:05.2f}s] {s['text']}")
