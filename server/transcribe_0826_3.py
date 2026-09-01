import json
from pathlib import Path
from faster_whisper import WhisperModel

source_video = Path(r"D:\Downloads\0826 (3).mp4")
out_json = Path(r"storage/0826_3_transcript.json")
out_json.parent.mkdir(parents=True, exist_ok=True)

print("Loading Faster-Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print(f"Transcribing {source_video} with word timestamps...")
segments, info = model.transcribe(str(source_video), word_timestamps=True)

seg_list = []
full_text = []

for s in segments:
    words = []
    for w in s.words:
        words.append({
            "word": w.word.strip(),
            "start": round(w.start, 2),
            "end": round(w.end, 2),
            "probability": round(w.probability, 2)
        })
    seg_list.append({
        "id": s.id,
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip(),
        "words": words
    })
    full_text.append(s.text.strip())

res = {
    "duration": round(info.duration, 2),
    "language": info.language,
    "language_probability": round(info.language_probability, 2),
    "full_transcript": " ".join(full_text),
    "segments": seg_list
}

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print(f"Transcription complete! ({info.duration:.2f}s, Language: {info.language})")
print(f"Saved to {out_json}")
print("\n--- Full Transcript ---")
print(res["full_transcript"])
