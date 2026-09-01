from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import imageio_ffmpeg

from app.models import TranscriptSegment, TranscriptWord
from app.editor.production_assembly import (
    compile_production_plan,
    run_automated_production_review,
)


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "deliverables"
    / "0813-production-v1"
)


def _env_value(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    env_path = OUTPUT_DIR.parents[2] / ".env"
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, candidate = line.split("=", 1)
        if key.strip() == name:
            return candidate.strip().strip("\"'")
    raise RuntimeError(f"{name} is not configured")


def _segments_from_deepgram(payload: dict) -> list[TranscriptSegment]:
    results = payload["results"]
    utterances = results.get("utterances") or []
    if utterances:
        raw_segments = utterances
    else:
        alternative = results["channels"][0]["alternatives"][0]
        raw_segments = [
            {
                "start": alternative["words"][0]["start"],
                "end": alternative["words"][-1]["end"],
                "transcript": alternative["transcript"],
                "words": alternative["words"],
            }
        ]
    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        words = [
            TranscriptWord(
                start=float(word["start"]),
                end=float(word["end"]),
                text=str(
                    word.get("punctuated_word") or word["word"]
                ).strip(),
                confidence=word.get("confidence"),
            )
            for word in raw_segment.get("words", [])
            if str(word.get("word", "")).strip()
        ]
        if not words:
            continue
        segments.append(
            TranscriptSegment(
                start=float(raw_segment.get("start", words[0].start)),
                end=float(raw_segment.get("end", words[-1].end)),
                text=str(raw_segment.get("transcript", "")).strip()
                or " ".join(word.text for word in words),
                words=words,
            )
        )
    return segments


def _deepgram_transcriber(path: Path) -> list[TranscriptSegment]:
    cached_source = (
        OUTPUT_DIR / "analysis" / "transcript-deepgram-raw.json"
    )
    if path.name == "dialogue-original.wav" and cached_source.is_file():
        return _segments_from_deepgram(
            json.loads(cached_source.read_text(encoding="utf-8"))
        )

    review_audio = OUTPUT_DIR / "analysis" / "final-review-audio.wav"
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(review_audio),
        ],
        check=True,
        shell=False,
    )
    cache = (
        OUTPUT_DIR / "analysis" / "transcript-final-deepgram-raw.json"
    )
    if cache.is_file() and cache.stat().st_mtime >= path.stat().st_mtime:
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        query = urlencode(
            {
                "model": "nova-3",
                "language": "multi",
                "smart_format": "true",
                "punctuate": "true",
                "utterances": "true",
            }
        )
        request = Request(
            f"https://api.deepgram.com/v1/listen?{query}",
            data=review_audio.read_bytes(),
            headers={
                "Authorization": f"Token {_env_value('DEEPGRAM_API_KEY')}",
                "Content-Type": "audio/wav",
            },
            method="POST",
        )
        with urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
        cache.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return _segments_from_deepgram(payload)


def main() -> int:
    plan = compile_production_plan(OUTPUT_DIR)
    report = run_automated_production_review(
        output_dir=OUTPUT_DIR,
        plan=plan,
        edited=OUTPUT_DIR / "edited.mp4",
        transcriber=_deepgram_transcriber,
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
