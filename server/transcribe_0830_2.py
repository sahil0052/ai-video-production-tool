import os, json, sys
from pathlib import Path
import whisper
from imageio_ffmpeg import get_ffmpeg_exe

sys.stdout.reconfigure(encoding='utf-8')

ffmpeg_dir = str(Path(get_ffmpeg_exe()).parent)
os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')

model = whisper.load_model('base')
res_en = model.transcribe(r'D:\Downloads\0830 (2).mp4', task='translate', word_timestamps=True, verbose=False)
res_hi = model.transcribe(r'D:\Downloads\0830 (2).mp4', language='hi', verbose=False)

out_dir = Path(r'storage/deliverables/voxpipe_0830_2_realestate')
out_dir.mkdir(parents=True, exist_ok=True)

with open(out_dir / 'transcript_en.json', 'w', encoding='utf-8') as f:
    json.dump(res_en, f, indent=2, ensure_ascii=False)

with open(out_dir / 'transcript_hi.json', 'w', encoding='utf-8') as f:
    json.dump(res_hi, f, indent=2, ensure_ascii=False)

print('--- ENGLISH TRANSLATION ---')
for s in res_en.get('segments', []):
    print(f"{s['start']:.2f} - {s['end']:.2f}: {s['text']}")

print('\n--- HINDI ORIGINAL ---')
for s in res_hi.get('segments', []):
    print(f"{s['start']:.2f} - {s['end']:.2f}: {s['text']}")
