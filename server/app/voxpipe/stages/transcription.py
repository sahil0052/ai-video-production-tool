from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from imageio_ffmpeg import get_ffmpeg_exe

from app.models import TranscriptSegment, TranscriptWord
from app.editor.transcript import repair_nonpositive_word_durations

logger = logging.getLogger("voxpipe.transcription")
FFMPEG = get_ffmpeg_exe()


def extract_audio_for_transcription(video_path: Path, output_wav: Path) -> Path:
    """Extracts 16kHz mono audio from input video for Whisper transcription."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_wav


def transcribe_video_whisper(
    video_path: Path,
    cache_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """Transcribes video using Whisper with English/Latin script enforcement (Zero Urdu script)."""
    if cache_json and cache_json.exists():
        logger.info(f"Loading cached transcription: {cache_json}")
        with open(cache_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Verify cache does not contain Urdu/Arabic characters
            first_text = data.get("segments", [{}])[0].get("text", "")
            has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in first_text)
            if not has_arabic:
                return data
            logger.info("Cached transcription contains Urdu script — re-transcribing with English Latin script...")

    logger.info(f"Transcribing and translating video with Whisper: {video_path}")
    ffmpeg_dir = str(Path(FFMPEG).parent)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    import whisper

    model = whisper.load_model("base")
    # task="translate" ensures clean Latin/English subtitles with zero Arabic/Urdu characters
    result = model.transcribe(str(video_path), task="translate", word_timestamps=True, verbose=False)

    cleaned_segments = []
    for s in result.get("segments", []):
        words = []
        for w in s.get("words", []):
            words.append(TranscriptWord(
                start=round(float(w["start"]), 3),
                end=round(float(w["end"]), 3),
                text=w["word"].strip(),
                confidence=round(float(w.get("probability", 1.0)), 2),
            ))
        cleaned_segments.append(TranscriptSegment(
            start=round(float(s["start"]), 3),
            end=round(float(s["end"]), 3),
            text=s["text"].strip(),
            words=words,
        ))

    stabilized = repair_nonpositive_word_durations(cleaned_segments)

    out_data = {
        "duration": float(result.get("duration", cleaned_segments[-1].end if cleaned_segments else 0.0)),
        "language": "en",
        "segments": [s.model_dump() for s in stabilized],
    }

    if cache_json:
        cache_json.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_json, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2, ensure_ascii=False)

    return out_data
