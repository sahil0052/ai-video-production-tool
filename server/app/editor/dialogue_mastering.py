from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any, Iterable, Sequence

from imageio_ffmpeg import get_ffmpeg_exe


@dataclass(frozen=True)
class DialoguePolicy:
    speech_playback_rate: float = 1.0
    collapse_gap_over_ms: int = 120
    replacement_gap_ms: int = 70
    edit_crossfade_ms: int = 12
    preserve_channels: int = 2
    ending_pad_ms: int = 450


@dataclass(frozen=True)
class DialogueSegment:
    id: str
    source_start_ms: int
    source_end_ms: int
    output_start_ms: int
    output_end_ms: int
    playback_rate: float = 1.0

    def to_dict(self) -> dict[str, int | float | str | bool]:
        return {
            "id": self.id,
            "source_start_ms": self.source_start_ms,
            "source_end_ms": self.source_end_ms,
            "output_start_ms": self.output_start_ms,
            "output_end_ms": self.output_end_ms,
            "playback_rate": self.playback_rate,
            "preserve_pitch": True,
        }


@dataclass(frozen=True)
class DialoguePlan:
    source: Path
    segments: tuple[DialogueSegment, ...]
    output_duration_ms: int
    channels: int
    policy: DialoguePolicy


@dataclass(frozen=True)
class AudioSelection:
    dialogue_asset_id: str
    untouched_dialogue_asset_id: str


@dataclass(frozen=True)
class DialogueAssets:
    untouched: Path
    edited: Path
    processed: Path
    presenter: Path
    comparison: Path
    plan: DialoguePlan


def _word_time_ms(word: dict[str, Any], key: str) -> int:
    millisecond_key = f"{key}_ms"
    if millisecond_key in word:
        return round(float(word[millisecond_key]))
    if key in word:
        return round(float(word[key]) * 1000)
    raise ValueError(f"Transcript word is missing {key} timing")


def build_dialogue_plan(
    *,
    source: Path,
    words: Sequence[dict[str, Any]],
    policy: DialoguePolicy | None = None,
) -> DialoguePlan:
    resolved = policy or DialoguePolicy()
    if resolved.speech_playback_rate != 1.0:
        raise ValueError("V8 dialogue speech must remain at exactly 1.00x")
    if not words:
        raise ValueError("Dialogue planning requires word timestamps")

    normalized = [
        (
            _word_time_ms(word, "start"),
            _word_time_ms(word, "end"),
        )
        for word in words
    ]
    if any(end <= start for start, end in normalized):
        raise ValueError("Dialogue words require positive duration")
    if any(
        right_start < left_start
        for (left_start, _), (right_start, _) in zip(
            normalized,
            normalized[1:],
        )
    ):
        raise ValueError("Dialogue words must be ordered")

    source_segments: list[tuple[int, int]] = []
    segment_start = normalized[0][0]
    for (_, left_end), (right_start, _) in zip(
        normalized,
        normalized[1:],
    ):
        gap_ms = max(0, right_start - left_end)
        if gap_ms > resolved.collapse_gap_over_ms:
            segment_end = min(
                right_start,
                left_end + resolved.replacement_gap_ms,
            )
            source_segments.append((segment_start, segment_end))
            segment_start = right_start
    source_segments.append((segment_start, normalized[-1][1]))

    output_cursor = 0
    segments: list[DialogueSegment] = []
    for index, (source_start, source_end) in enumerate(source_segments):
        duration = source_end - source_start
        segment = DialogueSegment(
            id=f"dialogue-{index:03d}",
            source_start_ms=source_start,
            source_end_ms=source_end,
            output_start_ms=output_cursor,
            output_end_ms=output_cursor + duration,
            playback_rate=1.0,
        )
        segments.append(segment)
        output_cursor = segment.output_end_ms

    return DialoguePlan(
        source=source,
        segments=tuple(segments),
        output_duration_ms=output_cursor,
        channels=resolved.preserve_channels,
        policy=resolved,
    )


def build_dialogue_plan_from_ranges(
    *,
    source: Path,
    source_ranges: Sequence[tuple[int, int]],
    target_output_ms: int,
    policy: DialoguePolicy | None = None,
) -> DialoguePlan:
    resolved = policy or DialoguePolicy()
    if resolved.speech_playback_rate != 1.0:
        raise ValueError("V8 dialogue speech must remain at exactly 1.00x")
    if not source_ranges:
        raise ValueError("Dialogue source ranges are required")
    normalized = [list(item) for item in source_ranges]
    if any(end <= start for start, end in normalized):
        raise ValueError("Dialogue source ranges require positive duration")
    if any(
        right_start < left_end
        for (_, left_end), (right_start, _) in zip(
            normalized,
            normalized[1:],
        )
    ):
        raise ValueError("Dialogue source ranges must be ordered")

    base_duration = sum(end - start for start, end in normalized)
    extra_needed = target_output_ms - base_duration
    if extra_needed < 0:
        raise ValueError(
            "Target duration cannot be shorter than locked source speech"
        )
    for index in range(len(normalized) - 1):
        if extra_needed <= 0:
            break
        available = normalized[index + 1][0] - normalized[index][1]
        extension = min(available, extra_needed)
        normalized[index][1] += extension
        extra_needed -= extension
    if extra_needed:
        raise ValueError(
            "Target duration needs more pause than the source provides"
        )

    output_cursor = 0
    segments: list[DialogueSegment] = []
    for index, (source_start, source_end) in enumerate(normalized):
        duration = source_end - source_start
        segments.append(
            DialogueSegment(
                id=f"dialogue-{index:03d}",
                source_start_ms=source_start,
                source_end_ms=source_end,
                output_start_ms=output_cursor,
                output_end_ms=output_cursor + duration,
                playback_rate=1.0,
            )
        )
        output_cursor += duration
    return DialoguePlan(
        source=source,
        segments=tuple(segments),
        output_duration_ms=output_cursor,
        channels=resolved.preserve_channels,
        policy=resolved,
    )


def build_audio_plan(assets: Iterable[dict[str, Any]]) -> AudioSelection:
    asset_ids = {
        str(asset["id"])
        for asset in assets
        if asset.get("kind") == "audio"
    }
    required = {
        "dialogue-source-untouched",
        "dialogue-processed",
    }
    missing = sorted(required - asset_ids)
    if missing:
        raise ValueError(
            "V8 audio assets are missing: " + ", ".join(missing)
        )
    return AudioSelection(
        dialogue_asset_id="dialogue-processed",
        untouched_dialogue_asset_id="dialogue-source-untouched",
    )


def dialogue_filter_chain() -> str:
    return (
        "highpass=f=72,"
        "afftdn=nr=7:nf=-32:tn=1,"
        "deesser=i=0.10:m=0.25:f=0.48,"
        "acompressor=threshold=-20dB:ratio=2:"
        "attack=12:release=140:makeup=1.5"
    )


def build_stereo_master_command(
    *,
    ffmpeg: Path,
    silent_video: Path,
    dialogue: Path,
    music: Path,
    output: Path,
    duration_ms: int,
    music_gain_db: float = -28.0,
) -> list[str]:
    duration_seconds = duration_ms / 1000
    return [
        str(ffmpeg),
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(dialogue),
        "-stream_loop",
        "-1",
        "-i",
        str(music),
        "-filter_complex",
        (
            f"[2:a]atrim=0:{duration_seconds:.3f},"
            f"volume={music_gain_db}dB[music];"
            "[1:a][music]amix=inputs=2:duration=first:"
            "dropout_transition=0,alimiter=limit=0.891251[master]"
        ),
        "-map",
        "0:v:0",
        "-map",
        "[master]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-b:a",
        "256k",
        "-t",
        f"{duration_seconds:.3f}",
        "-movflags",
        "+faststart",
        str(output),
    ]


def _run(command: Sequence[str]) -> None:
    completed = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "FFmpeg dialogue operation failed:\n"
            + completed.stderr[-4000:]
        )


def _trim_filter(
    *,
    stream: str,
    segment: DialogueSegment,
    media_kind: str,
) -> str:
    start = segment.source_start_ms / 1000
    end = segment.source_end_ms / 1000
    if media_kind == "audio":
        return (
            f"[{stream}]atrim=start={start:.6f}:end={end:.6f},"
            "asetpts=PTS-STARTPTS"
        )
    return (
        f"[{stream}]trim=start={start:.6f}:end={end:.6f},"
        "setpts=PTS-STARTPTS"
    )


def materialize_dialogue_assets(
    *,
    source: Path,
    output_dir: Path,
    words: Sequence[dict[str, Any]],
    policy: DialoguePolicy | None = None,
    ffmpeg: Path | None = None,
    dialogue_plan: DialoguePlan | None = None,
    ending_pad_ms: int | None = None,
) -> DialogueAssets:
    resolved_ffmpeg = ffmpeg or Path(get_ffmpeg_exe())
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = dialogue_plan or build_dialogue_plan(
        source=source,
        words=words,
        policy=policy,
    )
    resolved_ending_pad_ms = (
        plan.policy.ending_pad_ms
        if ending_pad_ms is None
        else ending_pad_ms
    )
    untouched = output_dir / "dialogue-source-untouched.wav"
    edited = output_dir / "dialogue-edited.wav"
    processed = output_dir / "dialogue-processed.wav"
    presenter = output_dir / "presenter-edited.mp4"
    comparison = output_dir / "dialogue-ab.wav"

    _run(
        [
            str(resolved_ffmpeg),
            "-y",
            "-i",
            str(source),
            "-vn",
            "-map",
            "0:a:0",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(untouched),
        ]
    )

    audio_split = "".join(
        f"[a{index}]" for index in range(len(plan.segments))
    )
    audio_filters = [
        f"[0:a]asplit={len(plan.segments)}{audio_split}"
    ]
    for index, segment in enumerate(plan.segments):
        audio_filters.append(
            _trim_filter(
                stream=f"a{index}",
                segment=segment,
                media_kind="audio",
            )
            + f"[at{index}]"
        )
    if len(plan.segments) == 1:
        audio_filters.append("[at0]anull[edited]")
    else:
        previous = "at0"
        for index in range(1, len(plan.segments)):
            output_label = (
                "edited"
                if index == len(plan.segments) - 1
                else f"ax{index}"
            )
            audio_filters.append(
                f"[{previous}][at{index}]"
                f"acrossfade=d={plan.policy.edit_crossfade_ms / 1000:.3f}:"
                f"o=0:c1=qsin:c2=qsin[{output_label}]"
            )
            previous = output_label
    _run(
        [
            str(resolved_ffmpeg),
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(audio_filters)
            + (
                f";[edited]apad=pad_dur="
                f"{resolved_ending_pad_ms / 1000:.3f}[padded]"
            ),
            "-map",
            "[padded]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(edited),
        ]
    )

    _run(
        [
            str(resolved_ffmpeg),
            "-y",
            "-i",
            str(edited),
            "-af",
            dialogue_filter_chain(),
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(processed),
        ]
    )

    video_split = "".join(
        f"[v{index}]" for index in range(len(plan.segments))
    )
    video_filters = [
        f"[0:v]split={len(plan.segments)}{video_split}"
    ]
    video_labels: list[str] = []
    for index, segment in enumerate(plan.segments):
        label = f"vt{index}"
        video_filters.append(
            _trim_filter(
                stream=f"v{index}",
                segment=segment,
                media_kind="video",
            )
            + f"[{label}]"
        )
        video_labels.append(f"[{label}]")
    video_filters.append(
        "".join(video_labels)
        + f"concat=n={len(video_labels)}:v=1:a=0[presenter]"
    )
    video_filters.append(
        f"[presenter]tpad=stop_mode=clone:stop_duration="
        f"{resolved_ending_pad_ms / 1000:.3f}[presenter-padded]"
    )
    _run(
        [
            str(resolved_ffmpeg),
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(video_filters),
            "-map",
            "[presenter-padded]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(presenter),
        ]
    )

    excerpt_seconds = min(10.0, plan.output_duration_ms / 1000)
    _run(
        [
            str(resolved_ffmpeg),
            "-y",
            "-i",
            str(untouched),
            "-i",
            str(edited),
            "-i",
            str(processed),
            "-filter_complex",
            (
                f"[0:a]atrim=0:{excerpt_seconds:.3f},"
                "asetpts=PTS-STARTPTS[a0];"
                f"[1:a]atrim=0:{excerpt_seconds:.3f},"
                "asetpts=PTS-STARTPTS[a1];"
                f"[2:a]atrim=0:{excerpt_seconds:.3f},"
                "asetpts=PTS-STARTPTS[a2];"
                "[a0][a1][a2]concat=n=3:v=0:a=1[ab]"
            ),
            "-map",
            "[ab]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(comparison),
        ]
    )

    return DialogueAssets(
        untouched=untouched,
        edited=edited,
        processed=processed,
        presenter=presenter,
        comparison=comparison,
        plan=plan,
    )
