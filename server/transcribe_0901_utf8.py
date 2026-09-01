import sys, json
from pathlib import Path

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
audio_path = work_dir / "raw_audio.wav"

from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_path), language="hi", word_timestamps=True)

transcript_data = []
full_text_list = []

for segment in segments:
    seg_dict = {
        "start": round(segment.start, 2),
        "end": round(segment.end, 2),
        "text": segment.text.strip(),
        "words": [
            {"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)}
            for w in segment.words
        ] if segment.words else []
    }
    transcript_data.append(seg_dict)
    full_text_list.append(f"[{seg_dict['start']}s - {seg_dict['end']}s] {seg_dict['text']}")

with open(work_dir / "transcript.json", "w", encoding="utf-8") as f:
    json.dump(transcript_data, f, ensure_ascii=False, indent=2)

with open(work_dir / "transcript.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(full_text_list))

print("Transcript saved successfully with", len(transcript_data), "segments!")
