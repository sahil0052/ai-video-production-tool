import sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
audio_path = work_dir / "raw_audio.wav"

from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_path), language="hi", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))

lines = []
for s in segments:
    lines.append({
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip()
    })

with open(work_dir / "transcript_vad.json", "w", encoding="utf-8") as f:
    json.dump(lines, f, ensure_ascii=False, indent=2)

with open(work_dir / "transcript_vad.txt", "w", encoding="utf-8") as f:
    for item in lines:
        f.write(f"[{item['start']:05.2f}s - {item['end']:05.2f}s] {item['text']}\n")

print("VAD Transcript completed with", len(lines), "segments!")
