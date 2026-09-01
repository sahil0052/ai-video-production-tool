import os, json, subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
import whisper

ffmpeg_exe = get_ffmpeg_exe()
ffmpeg_dir = str(Path(ffmpeg_exe).parent)
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

vid_path = r"D:\Downloads\0831 (1).mp4"
work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes")
work_dir.mkdir(parents=True, exist_ok=True)

wav_path = str(work_dir / "audio.wav")
cmd = [ffmpeg_exe, "-y", "-i", vid_path, "-vn", "-ac", "1", "-ar", "16000", wav_path]
subprocess.run(cmd, check=True)

print("Loading Whisper base model...")
model = whisper.load_model("base")

print("Transcribing Hindi...")
result_hi = model.transcribe(wav_path, language="hi", word_timestamps=True)
(work_dir / "transcript_hi.json").write_text(
    json.dumps(result_hi, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("Transcribing English translation...")
result_en = model.transcribe(wav_path, task="translate", word_timestamps=True)
(work_dir / "transcript_en.json").write_text(
    json.dumps(result_en, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("--- TRANSCRIPTION COMPLETE ---")
