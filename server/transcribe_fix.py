import sys, json
from pathlib import Path

# Force UTF-8 on stdout and stderr
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
audio_path = work_dir / "raw_audio.wav"

from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_path), beam_size=5)

transcript_clean = []
for s in segments:
    transcript_clean.append({
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip()
    })

with open(work_dir / "transcript_clean.json", "w", encoding="utf-8") as f:
    json.dump(transcript_clean, f, ensure_ascii=False, indent=2)

with open(work_dir / "transcript_clean.txt", "w", encoding="utf-8") as f:
    for item in transcript_clean:
        f.write(f"[{item['start']:05.2f}s - {item['end']:05.2f}s] {item['text']}\n")

print("SUCCESS: Transcript written with", len(transcript_clean), "segments!")
