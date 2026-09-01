import sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
audio_path = work_dir / "raw_audio.wav"

from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_path), word_timestamps=True, beam_size=5)

all_words = []
for s in segments:
    for w in s.words:
        all_words.append({
            "word": w.word.strip(),
            "start": round(w.start, 2),
            "end": round(w.end, 2),
            "prob": round(w.probability, 2)
        })

with open(work_dir / "word_timestamps.json", "w", encoding="utf-8") as f:
    json.dump(all_words, f, ensure_ascii=False, indent=2)

print("Saved", len(all_words), "words with timestamps!")
