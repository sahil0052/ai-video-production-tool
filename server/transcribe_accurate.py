import sys, json
from pathlib import Path
from faster_whisper import WhisperModel

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
audio_path = work_dir / "raw_audio.wav"

# Using small or medium model for crystal clear accuracy
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_path), beam_size=5)

transcript_clean = []
print(f"Detected language: {info.language} with probability {info.language_probability}")

for s in segments:
    line = f"[{s.start:05.2f}s - {s.end:05.2f}s] {s.text.strip()}"
    transcript_clean.append({
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip()
    })
    print(line)

with open(work_dir / "transcript_clean.json", "w", encoding="utf-8") as f:
    json.dump(transcript_clean, f, ensure_ascii=False, indent=2)

with open(work_dir / "transcript_clean.txt", "w", encoding="utf-8") as f:
    for item in transcript_clean:
        f.write(f"[{item['start']}s - {item['end']}s] {item['text']}\n")
