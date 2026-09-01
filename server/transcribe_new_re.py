import os, json
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
import whisper

ffmpeg_exe = get_ffmpeg_exe()
ffmpeg_dir = str(Path(ffmpeg_exe).parent)
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

vid_path = r"D:\Downloads\0830 (2)(1).mp4"
wav_path = r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0830_2_realestate\audio_new.wav"

import subprocess
cmd = [ffmpeg_exe, "-y", "-i", vid_path, "-vn", "-ac", "1", "-ar", "16000", wav_path]
subprocess.run(cmd, check=True)

print("Loading Whisper model...")
model = whisper.load_model("base")

print("Transcribing Hindi...")
result_hi = model.transcribe(wav_path, language="hi", word_timestamps=True)
Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0830_2_realestate\transcript_hi_new.json").write_text(
    json.dumps(result_hi, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("Segments breakdown:")
for s in result_hi.get("segments", []):
    print(f"{s['start']:.2f}s - {s['end']:.2f}s: {s['text']}")
