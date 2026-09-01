from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
from statistics import median
import subprocess
from typing import Any

import httpx
from imageio_ffmpeg import get_ffmpeg_exe
from app.models import (
    AssetRef,
    AudioPlan,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    DialogueEditSegment,
    EffectKeyframe,
    FlowShotSpec,
    KineticTextCue,
    LayerBounds,
    MotionEventSpec,
    OpacityKeyframe,
    ProductionBlueprint,
    TransformKeyframe,
)
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


HUMAN_REFERENCE_DURATION_MS = 44_370
QUESTION_START_MS = 10_400
BOARDROOM_START_MS = 11_340
ROBOT_ACTION_START_MS = 15_900
PRESENTER_RESET_START_MS = 18_520
RISK_START_MS = 24_680
MANAGER_START_MS = 27_120
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STYLE_REFERENCE = Path(
    r"D:\Downloads\Profit Bricks_Reel 04.mp4"
)
_DEFAULT_SEED_DIR = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0810-production-v1-internet-sourced"
)
_DEFAULT_BRAND_LOGO = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "brand"
    / "profit-bricks-forex-automation.png"
)
_DEFAULT_UPI_LOGO = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "brand"
    / "upi-logo-public-domain.png"
)
_DEFAULT_UPI_LICENSE = _DEFAULT_UPI_LOGO.with_suffix(".json")
_DEFAULT_SILENCE_INTERVALS_MS = [
    (1_020, 1_154),
    (4_457, 4_969),
    (10_547, 11_163),
    (12_096, 12_489),
    (14_952, 15_116),
    (16_960, 17_266),
    (19_760, 20_532),
    (26_525, 26_923),
    (29_265, 29_819),
    (30_940, 31_259),
    (34_472, 34_603),
    (35_983, 36_548),
    (39_204, 39_571),
    (40_786, 41_055),
    (43_874, 44_415),
    (44_756, 45_071),
    (46_162, 46_635),
    (47_600, 47_715),
    (49_004, 49_505),
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _run(command: list[str], *, timeout: int = 3600) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\n"
            + completed.stdout[-4_000:]
            + "\n"
            + completed.stderr[-8_000:]
        )


def _font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _fit_font(
    text: str,
    *,
    max_width: int,
    start_size: int,
    minimum_size: int = 24,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for size in range(start_size, minimum_size - 1, -2):
        font = _font(size)
        box = probe.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return _font(minimum_size)


def build_dialogue_edl_from_silences(
    *,
    source_duration_ms: int,
    target_duration_ms: int,
    silence_intervals_ms: list[tuple[int, int]],
    minimum_retained_silence_ms: int = 100,
) -> list[DialogueEditSegment]:
    if target_duration_ms <= 0 or target_duration_ms > source_duration_ms:
        raise ValueError("Dialogue target duration is outside the source")
    normalized: list[tuple[int, int]] = []
    previous_end = 0
    for raw_start, raw_end in sorted(silence_intervals_ms):
        start = max(0, min(source_duration_ms, int(raw_start)))
        end = max(0, min(source_duration_ms, int(raw_end)))
        if end <= start or start < previous_end:
            continue
        normalized.append((start, end))
        previous_end = end

    required_removal = source_duration_ms - target_duration_ms
    removable_at_floor = sum(
        max(0, end - start - minimum_retained_silence_ms)
        for start, end in normalized
    )
    if removable_at_floor < required_removal:
        raise ValueError(
            "Detected silence cannot reach the requested duration safely"
        )

    def removal_for_keep(keep_ms: int) -> int:
        return sum(
            max(0, end - start - keep_ms)
            for start, end in normalized
        )

    lower = minimum_retained_silence_ms
    upper = max(
        [minimum_retained_silence_ms]
        + [end - start for start, end in normalized]
    )
    while lower < upper:
        midpoint = (lower + upper + 1) // 2
        if removal_for_keep(midpoint) >= required_removal:
            lower = midpoint
        else:
            upper = midpoint - 1
    uniform_keep = lower
    removals = [
        max(0, end - start - uniform_keep)
        for start, end in normalized
    ]
    excess = sum(removals) - required_removal
    for index in range(len(removals)):
        if excess <= 0:
            break
        give_back = min(excess, 1 if removals[index] else 0)
        removals[index] -= give_back
        excess -= give_back
    if excess:
        raise ValueError("Unable to distribute dialogue pause retention")

    removed_ranges: list[tuple[int, int]] = []
    for (start, end), remove_ms in zip(
        normalized,
        removals,
        strict=True,
    ):
        if remove_ms <= 0:
            continue
        retained_ms = end - start - remove_ms
        cut_start = start + retained_ms // 2
        removed_ranges.append((cut_start, cut_start + remove_ms))

    retained_ranges: list[tuple[int, int]] = []
    cursor = 0
    for cut_start, cut_end in removed_ranges:
        if cut_start > cursor:
            retained_ranges.append((cursor, cut_start))
        cursor = cut_end
    if cursor < source_duration_ms:
        retained_ranges.append((cursor, source_duration_ms))

    output_cursor = 0
    edl: list[DialogueEditSegment] = []
    for index, (source_start, source_end) in enumerate(
        retained_ranges,
        start=1,
    ):
        duration_ms = source_end - source_start
        edl.append(
            DialogueEditSegment(
                id=f"dialogue-{index:03d}",
                source_start_ms=source_start,
                source_end_ms=source_end,
                output_start_ms=output_cursor,
                output_end_ms=output_cursor + duration_ms,
                playback_rate=1,
                preserve_pitch=True,
            )
        )
        output_cursor += duration_ms
    if output_cursor != target_duration_ms:
        raise ValueError(
            f"Dialogue EDL duration mismatch: {output_cursor} ms"
        )
    return edl


def _safe_sfx_start(
    *,
    desired_ms: int,
    duration_ms: int,
    windows: list[SpeechProtectionWindow],
) -> int:
    offsets = [0]
    for delta in range(10, 801, 10):
        offsets.extend((-delta, delta))
    for offset in offsets:
        candidate = max(
            0,
            min(
                HUMAN_REFERENCE_DURATION_MS - duration_ms,
                desired_ms + offset,
            ),
        )
        if not any(
            candidate < window.end_ms
            and candidate + duration_ms > window.start_ms
            for window in windows
        ):
            return candidate
    raise ValueError(f"No speech-safe SFX window near {desired_ms} ms")


def build_social_kinetic_audio_plan(
    segments: list[TranscriptSegment],
) -> AudioPlan:
    windows = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=min(
                HUMAN_REFERENCE_DURATION_MS,
                round(word.start * 1000) + 120,
            ),
            word=word.text,
        )
        for segment in segments
        for word in segment.words
        if round(word.start * 1000) < HUMAN_REFERENCE_DURATION_MS
    ]
    candidate_cues = [
        ("sfx-hook-year", "sfx-snap", 850, 80, -16, "click", "2008 reveal"),
        ("sfx-hook-months", "sfx-snap", 1_450, 80, -16, "click", "3 months reveal"),
        ("sfx-hook-contest", "sfx-snap", 2_350, 80, -16, "click", "contest stack"),
        ("sfx-robot-enter", "sfx-whoosh", 3_400, 110, -16, "whoosh", "robot section"),
        ("sfx-proof", "sfx-click", 5_650, 90, -17, "click", "proof punch"),
        ("sfx-robot-detail", "sfx-impact", 6_450, 100, -17, "impact", "robot detail"),
        ("sfx-number", "sfx-impact", 7_550, 110, -15, "impact", "peak reveal"),
        ("sfx-question", "sfx-whoosh", QUESTION_START_MS, 110, -16, "whoosh", "question interrupt"),
        ("sfx-boardroom", "sfx-riser", BOARDROOM_START_MS, 110, -18, "riser", "future section"),
        ("sfx-upi", "sfx-click", 13_680, 90, -17, "click", "UPI PIP"),
        ("sfx-robot-action", "sfx-whoosh", ROBOT_ACTION_START_MS, 110, -17, "whoosh", "robot action"),
        ("sfx-future-reset", "sfx-snap", PRESENTER_RESET_START_MS, 80, -18, "click", "presenter reset"),
        ("sfx-risk", "sfx-impact", RISK_START_MS, 110, -17, "impact", "risk section"),
        ("sfx-monitor", "sfx-click", 25_780, 90, -18, "click", "monitor reveal"),
        ("sfx-logo", "sfx-logo", 33_270, 110, -15, "riser", "logo stinger"),
        ("sfx-zero-risk", "sfx-impact", 36_070, 100, -16, "impact", "risk correction"),
        ("sfx-cta-jump", "sfx-whoosh", 40_800, 110, -17, "whoosh", "CTA jump"),
        ("sfx-demo", "sfx-pop", 41_250, 90, -15, "notification", "Demo reveal"),
    ]
    cues = [
        SfxCue(
            id=cue_id,
            asset_id=asset_id,
            start_ms=_safe_sfx_start(
                desired_ms=desired_ms,
                duration_ms=duration_ms,
                windows=windows,
            ),
            duration_ms=duration_ms,
            volume=0.35,
            gain_db=gain_db,
            kind=kind,
            reason=reason,
        )
        for (
            cue_id,
            asset_id,
            desired_ms,
            duration_ms,
            gain_db,
            kind,
            reason,
        ) in candidate_cues
    ]
    automation = [
        GainAutomation(
            start_ms=max(0, round(segment.start * 1000) - 80),
            end_ms=min(
                HUMAN_REFERENCE_DURATION_MS,
                round(segment.end * 1000) + 120,
            ),
            gain_db=-6,
            reason="Duck music beneath narration",
        )
        for segment in segments
        if round(segment.start * 1000) < HUMAN_REFERENCE_DURATION_MS
    ]
    return AudioPlan(
        integrated_lufs=-13.5,
        true_peak_dbtp=-1.0,
        target_lra_lu=2.4,
        music_bpm=126,
        dialogue_asset_id="dialogue-processed",
        dialogue_offset_ms=0,
        music_asset_id="music-social-kinetic",
        music_duck_db=6,
        music_base_gain_db=-18,
        music_gain_automation=automation,
        speech_protection_windows=windows,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def _detect_silence_intervals(source: Path) -> list[tuple[int, int]]:
    command = [
        str(get_ffmpeg_exe()),
        "-hide_banner",
        "-i",
        str(source),
        "-af",
        "silencedetect=noise=-30dB:d=0.06",
        "-f",
        "null",
        "NUL",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    text = "\n".join((completed.stdout, completed.stderr))
    intervals: list[tuple[int, int]] = []
    start: float | None = None
    for line in text.splitlines():
        match = re.search(r"silence_start: ([0-9.]+)", line)
        if match:
            start = float(match.group(1))
            continue
        match = re.search(r"silence_end: ([0-9.]+)", line)
        if match and start is not None:
            end = float(match.group(1))
            intervals.append((round(start * 1000), round(end * 1000)))
            start = None
    if not intervals:
        raise RuntimeError("No dialogue pauses were detected")
    return intervals


def _prepare_dialogue_media(
    *,
    source: Path,
    edl: list[DialogueEditSegment],
    presenter_output: Path,
    original_audio_output: Path,
    processed_audio_output: Path,
) -> None:
    duration_seconds = edl[-1].output_end_ms / 1000
    presenter_output.parent.mkdir(parents=True, exist_ok=True)
    original_audio_output.parent.mkdir(parents=True, exist_ok=True)
    video_sources = "".join(
        f"[vsrc{index}]" for index in range(len(edl))
    )
    video_filters = [
        f"[0:v]split={len(edl)}{video_sources}"
    ]
    for index, segment in enumerate(edl):
        video_filters.append(
            f"[vsrc{index}]trim=start={segment.source_start_ms / 1000:.6f}"
            f":end={segment.source_end_ms / 1000:.6f},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
    video_filters.append(
        "".join(f"[v{index}]" for index in range(len(edl)))
        + f"concat=n={len(edl)}:v=1:a=0[vout]"
    )
    _run(
        [
            str(get_ffmpeg_exe()),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(video_filters),
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "15",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            str(presenter_output),
        ],
        timeout=3600,
    )

    audio_sources = "".join(
        f"[asrc{index}]" for index in range(len(edl))
    )
    audio_filters = [
        f"[0:a]asplit={len(edl)}{audio_sources}"
    ]
    for index, segment in enumerate(edl):
        audio_filters.append(
            f"[asrc{index}]atrim=start={segment.source_start_ms / 1000:.6f}"
            f":end={segment.source_end_ms / 1000:.6f},"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )
    audio_filters.append(
        "".join(f"[a{index}]" for index in range(len(edl)))
        + f"concat=n={len(edl)}:v=0:a=1[aout]"
    )
    _run(
        [
            str(get_ffmpeg_exe()),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(audio_filters),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(original_audio_output),
        ]
    )
    _run(
        [
            str(get_ffmpeg_exe()),
            "-hide_banner",
            "-y",
            "-i",
            str(original_audio_output),
            "-af",
            build_dialogue_processing_filter(duration_seconds),
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(processed_audio_output),
        ]
    )


def build_dialogue_processing_filter(duration_seconds: float) -> str:
    return (
        "apad=pad_dur=0.10,"
        "highpass=f=75,lowpass=f=16500,afftdn=nf=-28,"
        "deesser=i=0.22:m=0.42:f=0.5,"
        "acompressor=threshold=-18dB:ratio=2.6:"
        "attack=12:release=150:makeup=2,alimiter=limit=0.88,"
        f"atrim=start=0.030:duration={duration_seconds:.3f},"
        "asetpts=PTS-STARTPTS"
    )


def _map_source_time_ms(
    source_ms: int,
    edl: list[DialogueEditSegment],
    *,
    end_boundary: bool,
) -> int:
    for segment in edl:
        if segment.source_start_ms <= source_ms <= segment.source_end_ms:
            mapped = (
                segment.output_start_ms
                + (source_ms - segment.source_start_ms)
                / segment.playback_rate
            )
            return round(mapped)
        if source_ms < segment.source_start_ms:
            return (
                segment.output_start_ms
                if not end_boundary
                else max(0, segment.output_start_ms - 1)
            )
    return edl[-1].output_end_ms


def measure_visible_interval_duration(items: list[Any]) -> int:
    intervals = sorted(
        (int(item.start_ms), int(item.end_ms))
        for item in items
        if int(item.end_ms) > int(item.start_ms)
    )
    if not intervals:
        return 0
    total = 0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
            continue
        total += current_end - current_start
        current_start, current_end = start, end
    return total + current_end - current_start


def _remap_transcript(
    segments: list[TranscriptSegment],
    edl: list[DialogueEditSegment],
    *,
    target_duration_ms: int = HUMAN_REFERENCE_DURATION_MS,
) -> list[TranscriptSegment]:
    remapped: list[TranscriptSegment] = []
    previous_end_ms = 0
    for segment in segments:
        words: list[TranscriptWord] = []
        for word in segment.words:
            start_ms = max(
                previous_end_ms,
                _map_source_time_ms(
                    round(word.start * 1000),
                    edl,
                    end_boundary=False,
                ),
            )
            end_ms = max(
                start_ms + 40,
                _map_source_time_ms(
                    round(word.end * 1000),
                    edl,
                    end_boundary=True,
                ),
            )
            end_ms = min(target_duration_ms, end_ms)
            if end_ms <= start_ms:
                start_ms = max(
                    previous_end_ms,
                    target_duration_ms - 40,
                )
                end_ms = target_duration_ms
            words.append(
                word.model_copy(
                    update={
                        "start": start_ms / 1000,
                        "end": end_ms / 1000,
                    }
                )
            )
            previous_end_ms = end_ms
        remapped.append(
            segment.model_copy(
                update={
                    "start": words[0].start,
                    "end": words[-1].end,
                    "words": words,
                }
            )
        )
    return remapped


def _vertical_gradient(
    *,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    image = Image.new("RGB", (1_080, 1_920), top)
    pixels = image.load()
    for y in range(1_920):
        progress = y / 1_919
        color = tuple(
            round(start + (end - start) * progress)
            for start, end in zip(top, bottom, strict=True)
        )
        for x in range(1_080):
            pixels[x, y] = color
    return image


def _build_question_plate(destination: Path) -> None:
    image = _vertical_gradient(
        top=(249, 48, 38),
        bottom=(66, 0, 18),
    ).convert("RGBA")
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse(
        (120, 250, 960, 1_210),
        fill=(255, 92, 54, 115),
    )
    glow_draw.ellipse(
        (300, 520, 780, 1_020),
        fill=(255, 206, 128, 72),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    image.alpha_composite(glow)

    ribbons = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ribbons_draw = ImageDraw.Draw(ribbons, "RGBA")
    for offset, alpha in ((-260, 75), (10, 110), (280, 62)):
        ribbons_draw.arc(
            (offset, 300, offset + 1_120, 1_430),
            start=205,
            end=505,
            fill=(255, 215, 185, alpha),
            width=22,
        )
    ribbons_draw.line(
        ((-80, 1_590), (1_160, 690)),
        fill=(255, 96, 70, 92),
        width=34,
    )
    ribbons = ribbons.filter(ImageFilter.GaussianBlur(15))
    image.alpha_composite(ribbons)

    vignette = Image.new("RGBA", image.size, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette, "RGBA")
    vignette_draw.rectangle((0, 0, 1_080, 250), fill=(24, 0, 10, 42))
    vignette_draw.rectangle(
        (0, 1_420, 1_080, 1_920),
        fill=(18, 0, 10, 122),
    )
    image.alpha_composite(vignette)

    draw = ImageDraw.Draw(image, "RGBA")
    mark = "?"
    mark_font = _font(610)
    box = draw.textbbox((0, 0), mark, font=mark_font, stroke_width=8)
    draw.text(
        (
            540 - (box[2] - box[0]) / 2,
            1_030 - (box[3] - box[1]) / 2,
        ),
        mark,
        font=mark_font,
        fill=(255, 250, 236, 255),
        stroke_width=9,
        stroke_fill=(76, 0, 18, 225),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, quality=96)


def _build_market_overlay(destination: Path) -> None:
    image = Image.new("RGBA", (1_080, 1_920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    points = [
        (0, 1_245),
        (120, 1_180),
        (220, 1_265),
        (340, 1_070),
        (455, 1_145),
        (590, 925),
        (720, 1_020),
        (860, 760),
        (1_080, 850),
    ]
    draw.line(points, fill=(64, 240, 255, 165), width=12, joint="curve")
    for index, x in enumerate(range(90, 1_030, 105)):
        center = 1_300 - (index % 5) * 85
        color = (112, 255, 140, 135) if index % 2 else (255, 80, 72, 135)
        draw.line((x, center - 80, x, center + 80), fill=color, width=7)
        draw.rounded_rectangle(
            (x - 18, center - 38, x + 18, center + 38),
            radius=5,
            fill=color,
        )
    image = image.filter(ImageFilter.GaussianBlur(1.2))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def _build_robot_transition(destination: Path) -> None:
    image = _vertical_gradient(
        top=(18, 66, 92),
        bottom=(12, 8, 24),
    ).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(12):
        offset = index * 120
        draw.polygon(
            [
                (-220 + offset, 0),
                (-40 + offset, 0),
                (600 + offset, 1_920),
                (400 + offset, 1_920),
            ],
            fill=(
                28 if index % 2 else 255,
                220 if index % 2 else 55,
                255 if index % 2 else 92,
                48,
            ),
        )
    image = image.filter(ImageFilter.GaussianBlur(12))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def _build_logo_card(*, source: Path, destination: Path) -> None:
    background = _vertical_gradient(
        top=(255, 255, 253),
        bottom=(247, 245, 238),
    ).convert("RGBA")
    logo_rgb = Image.open(source).convert("RGB")
    white = Image.new("RGB", logo_rgb.size, (255, 255, 255))
    difference = ImageChops.difference(logo_rgb, white).convert("L")
    alpha = difference.point(
        lambda value: (
            0
            if value <= 2
            else min(255, round((value - 2) * 12))
        )
    )
    logo = logo_rgb.convert("RGBA")
    logo.putalpha(alpha)
    content_box = difference.point(
        lambda value: 255 if value > 12 else 0
    ).getbbox()
    if content_box is not None:
        logo = logo.crop(content_box)
    scale = min(1_010 / logo.width, 900 / logo.height)
    logo = logo.resize(
        (
            max(1, round(logo.width * scale)),
            max(1, round(logo.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )

    aura = Image.new("RGBA", background.size, (0, 0, 0, 0))
    aura_draw = ImageDraw.Draw(aura, "RGBA")
    aura_draw.ellipse(
        (70, 390, 1_010, 1_420),
        fill=(226, 194, 105, 28),
    )
    aura = aura.filter(ImageFilter.GaussianBlur(70))
    background.alpha_composite(aura)

    shadow_alpha = logo.getchannel("A").filter(
        ImageFilter.GaussianBlur(24)
    ).point(
        lambda value: round(value * 0.22)
    )
    shadow = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)
    x = (1_080 - logo.width) // 2
    y = (1_920 - logo.height) // 2 - 30
    background.alpha_composite(shadow, (x, y + 34))
    background.alpha_composite(logo, (x, y))
    destination.parent.mkdir(parents=True, exist_ok=True)
    background.convert("RGB").save(destination, quality=96)


def _build_upi_phone_card(*, source: Path, destination: Path) -> None:
    phone = Image.new("RGBA", (800, 1_000), (0, 0, 0, 0))
    shadow = Image.new("RGBA", phone.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    shadow_draw.rounded_rectangle(
        (70, 36, 730, 982),
        radius=92,
        fill=(0, 0, 0, 115),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    phone.alpha_composite(shadow, (0, 8))

    draw = ImageDraw.Draw(phone, "RGBA")
    draw.rounded_rectangle(
        (82, 24, 718, 965),
        radius=86,
        fill=(18, 21, 24, 255),
    )
    draw.rounded_rectangle(
        (112, 58, 688, 928),
        radius=62,
        fill=(251, 252, 249, 255),
    )
    draw.rounded_rectangle(
        (315, 75, 485, 91),
        radius=8,
        fill=(43, 47, 51, 255),
    )

    logo = Image.open(source).convert("RGBA")
    logo.thumbnail((480, 270), Image.Resampling.LANCZOS)
    phone.alpha_composite(
        logo,
        ((800 - logo.width) // 2, 260),
    )
    draw.ellipse(
        (284, 585, 516, 817),
        fill=(232, 255, 237, 255),
        outline=(35, 180, 92, 255),
        width=12,
    )
    draw.line(
        ((340, 700), (390, 750), (475, 645)),
        fill=(24, 162, 82, 255),
        width=26,
        joint="curve",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    phone.save(destination)


def _build_lower_vignette(destination: Path) -> None:
    image = Image.new("RGBA", (1_080, 1_920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(780, 1_920):
        progress = (y - 780) / (1_920 - 780)
        alpha = round((progress**1.45) * 205)
        draw.line((0, y, 1_080, y), fill=(2, 6, 9, alpha), width=1)
    edge = Image.new("RGBA", image.size, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge, "RGBA")
    edge_draw.rectangle((0, 0, 95, 1_920), fill=(0, 0, 0, 52))
    edge_draw.rectangle((985, 0, 1_080, 1_920), fill=(0, 0, 0, 52))
    edge = edge.filter(ImageFilter.GaussianBlur(70))
    image.alpha_composite(edge)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def _build_peak_proof_card(*, source: Path, destination: Path) -> None:
    canvas = Image.new("RGB", (1_080, 1_920), (249, 250, 247))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1_080, 245), fill=(11, 18, 27))
    draw.rectangle((0, 0, 20, 245), fill=(213, 255, 63))
    draw.text(
        (58, 50),
        "2008 CHAMPIONSHIP • OFFICIAL MQL5",
        font=_font(31, bold=True),
        fill=(213, 255, 63),
    )
    draw.text(
        (58, 112),
        "DIRECT SOURCE PROOF",
        font=_font(62, bold=True),
        fill=(255, 255, 255),
    )

    excerpt = Image.open(source).convert("RGB")
    excerpt.thumbnail((960, 260), Image.Resampling.LANCZOS)
    excerpt_x = (1_080 - excerpt.width) // 2
    excerpt_y = 355
    draw.rounded_rectangle(
        (42, 314, 1_038, 680),
        radius=30,
        fill=(255, 255, 255),
        outline=(207, 212, 204),
        width=3,
    )
    canvas.paste(excerpt, (excerpt_x, excerpt_y))
    draw.rounded_rectangle(
        (55, 704, 1_025, 1_530),
        radius=38,
        fill=(11, 18, 27),
    )
    draw.text(
        (540, 940),
        "$110,000",
        font=_fit_font("$110,000", max_width=900, start_size=176),
        fill=(255, 255, 255),
        anchor="mm",
    )
    draw.text(
        (540, 1_115),
        "AT ONE POINT",
        font=_fit_font("AT ONE POINT", max_width=850, start_size=82),
        fill=(213, 255, 63),
        anchor="mm",
    )
    draw.line(
        (140, 1_235, 940, 1_235),
        fill=(63, 76, 91),
        width=3,
    )
    draw.text(
        (540, 1_350),
        "PEAK — NOT FINAL BALANCE",
        font=_fit_font(
            "PEAK — NOT FINAL BALANCE",
            max_width=840,
            start_size=44,
        ),
        fill=(221, 226, 232),
        anchor="mm",
    )
    draw.text(
        (540, 1_735),
        "SOURCE: MQL5 / METATRADER 5",
        font=_font(26, bold=True),
        fill=(49, 58, 68),
        anchor="mm",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=96)


def _build_flow_plate(
    *,
    destination: Path,
    palette: tuple[tuple[int, int, int], tuple[int, int, int]],
    subject: str,
    end: bool,
) -> None:
    image = _vertical_gradient(top=palette[0], bottom=palette[1]).convert(
        "RGBA"
    )
    draw = ImageDraw.Draw(image, "RGBA")
    if subject == "robot":
        center_x = 610 if end else 470
        draw.ellipse(
            (center_x - 150, 320, center_x + 150, 620),
            fill=(225, 235, 240, 245),
            outline=(74, 220, 255, 255),
            width=12,
        )
        draw.rounded_rectangle(
            (center_x - 210, 610, center_x + 210, 1_380),
            radius=90,
            fill=(175, 190, 204, 245),
            outline=(32, 182, 230, 255),
            width=12,
        )
        draw.line(
            (center_x, 1_050, 870 if end else 760, 1_520),
            fill=(225, 235, 240, 255),
            width=80,
        )
    elif subject == "boardroom":
        for index, center_x in enumerate((260, 540, 820)):
            lift = 45 if end and index == 1 else 0
            draw.ellipse(
                (center_x - 90, 420 - lift, center_x + 90, 600 - lift),
                fill=(220, 232, 238, 235),
                outline=(82, 210, 235, 245),
                width=9,
            )
            draw.rounded_rectangle(
                (center_x - 120, 610 - lift, center_x + 120, 1_030 - lift),
                radius=55,
                fill=(160, 180, 196, 235),
            )
        draw.ellipse(
            (80, 1_000, 1_000, 1_610),
            fill=(200, 230, 240, 70),
            outline=(255, 255, 255, 120),
            width=8,
        )
    else:
        x = 720 if end else 420
        draw.rounded_rectangle(
            (170, 720, 900, 1_430),
            radius=60,
            fill=(24, 38, 52, 235),
            outline=(76, 222, 255, 220),
            width=12,
        )
        draw.line(
            (x, 390, x - 110, 1_050),
            fill=(210, 222, 232, 255),
            width=105,
        )
        draw.ellipse(
            (x - 190, 310, x + 70, 570),
            fill=(180, 195, 208, 255),
            outline=(255, 186, 74, 255),
            width=10,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, quality=94)


def _build_flow_plates(output_dir: Path) -> None:
    specs = [
        ("robot-trading", ((46, 132, 166), (8, 17, 35)), "robot"),
        ("robot-boardroom", ((188, 225, 236), (26, 66, 88)), "boardroom"),
        ("robot-action", ((36, 105, 130), (36, 20, 20)), "action"),
    ]
    for stem, palette, subject in specs:
        _build_flow_plate(
            destination=output_dir / "flow-plates" / f"{stem}-start.png",
            palette=palette,
            subject=subject,
            end=False,
        )
        _build_flow_plate(
            destination=output_dir / "flow-plates" / f"{stem}-end.png",
            palette=palette,
            subject=subject,
            end=True,
        )


def _copy_required(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _download_binary(url: str, destination: Path) -> Path:
    if destination.is_file() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": "Cutline/2.0 production editor"},
        follow_redirects=True,
        timeout=90,
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for chunk in response.iter_bytes(1024 * 1024):
                stream.write(chunk)
    return destination


def _archive_page(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "Cutline/2.0 production editor"},
            follow_redirects=True,
            timeout=45,
        )
        response.raise_for_status()
        destination.write_text(response.text, encoding="utf-8")
    except Exception as error:
        destination.write_text(
            f"Unable to archive {url}: {error}",
            encoding="utf-8",
        )


def _prepare_licensed_video_assets(
    *,
    output_dir: Path,
    seed_dir: Path,
) -> list[AssetRef]:
    destination = output_dir / "assets" / "licensed" / "mixkit"
    risk = _copy_required(
        seed_dir
        / "assets"
        / "licensed"
        / "mixkit"
        / "data-center-engineers-22966.mp4",
        destination / "risk-manager-22966.mp4",
    )
    license_dir = output_dir / "assets" / "licenses"
    for filename in ("22966-page.html",):
        source = (
            seed_dir
            / "assets"
            / "licensed"
            / "mixkit"
            / "licenses"
            / filename
        )
        if source.is_file():
            _copy_required(source, license_dir / filename)
    mixkit_license = (
        seed_dir
        / "assets"
        / "licensed"
        / "mixkit"
        / "licenses"
        / "mixkit-license.html"
    )
    if mixkit_license.is_file():
        _copy_required(mixkit_license, license_dir / "mixkit-license.html")
    return [
        AssetRef(
            id="licensed-risk-manager",
            kind="video",
            path=_relative(output_dir, risk),
            keywords=[
                "human engineers",
                "risk manager",
                "system monitoring",
                "licensed video",
            ],
            provenance="internet:licensed-stock-video",
            license="Mixkit Free License",
            provider="Mixkit",
            remote_id="22966",
            creator="FrameStock",
            source_url=(
                "https://mixkit.co/free-stock-video/"
                "engineers-working-in-the-data-center-22966/"
            ),
            license_url="https://mixkit.co/license/",
            search_query="human engineers monitoring systems",
        ),
    ]


def _prepare_licensed_audio_assets(
    *,
    output_dir: Path,
    seed_dir: Path,
    acquire_assets: bool,
) -> list[AssetRef]:
    audio_dir = output_dir / "assets" / "audio"
    license_dir = output_dir / "assets" / "licenses"
    music_path = audio_dir / "mixkit-minimal-techno-01-162.mp3"
    music_url = "https://assets.mixkit.co/music/162/162.mp3"
    if acquire_assets:
        _download_binary(music_url, music_path)
        _archive_page(
            "https://mixkit.co/free-stock-music/tag/technology/",
            license_dir / "mixkit-music-technology.html",
        )
        _archive_page(
            "https://mixkit.co/license/",
            license_dir / "mixkit-license.html",
        )
    else:
        candidate = (
            _WORKSPACE_ROOT
            / "storage"
            / "deliverables"
            / "0810-production-v2-human-reference"
            / "assets"
            / "audio"
            / "source-candidates"
            / "162.mp3"
        )
        fallback = (
            seed_dir
            / "assets"
            / "audio"
            / "reference-style-score.wav"
        )
        _copy_required(
            candidate if candidate.is_file() else fallback,
            music_path,
        )

    sfx_specs = [
        (
            "sfx-snap",
            "3124",
            "Modern technology select",
            "https://assets.mixkit.co/active_storage/sfx/3124/3124-preview.mp3",
            "https://mixkit.co/free-sound-effects/click/",
        ),
        (
            "sfx-click",
            "1109",
            "Select click",
            "https://assets.mixkit.co/active_storage/sfx/1109/1109-preview.mp3",
            "https://mixkit.co/free-sound-effects/click/",
        ),
        (
            "sfx-impact",
            "1143",
            "Cinematic whoosh deep impact",
            "https://assets.mixkit.co/active_storage/sfx/1143/1143-preview.mp3",
            "https://mixkit.co/free-sound-effects/impact/",
        ),
        (
            "sfx-whoosh",
            "1492",
            "Cinematic whoosh fast transition",
            "https://assets.mixkit.co/active_storage/sfx/1492/1492-preview.mp3",
            "https://mixkit.co/free-sound-effects/whoosh/",
        ),
        (
            "sfx-riser",
            "1144",
            "Short space stutter intro riser",
            "https://assets.mixkit.co/active_storage/sfx/1144/1144-preview.mp3",
            "https://mixkit.co/free-sound-effects/riser/",
        ),
        (
            "sfx-logo",
            "2902",
            "Movie impact intro presentation",
            "https://assets.mixkit.co/active_storage/sfx/2902/2902-preview.mp3",
            "https://mixkit.co/free-sound-effects/impact/",
        ),
        (
            "sfx-pop",
            "2354",
            "Message pop alert",
            "https://assets.mixkit.co/active_storage/sfx/2354/2354-preview.mp3",
            "https://mixkit.co/free-sound-effects/notification/",
        ),
    ]
    assets = [
        AssetRef(
            id="music-social-kinetic",
            kind="audio",
            path=_relative(output_dir, music_path),
            keywords=["126 BPM", "electronic", "vocal-free"],
            provenance="internet:licensed-stock-audio",
            license="Mixkit Free License",
            provider="Mixkit",
            remote_id="162",
            creator="Alejandro Magaña (A. M.)",
            source_url=(
                "https://mixkit.co/free-stock-music/tag/technology/"
            ),
            license_url="https://mixkit.co/license/",
            search_query="minimal techno technology music",
        )
    ]
    fallback_sfx = (
        seed_dir / "assets" / "audio" / "label-snap.wav"
    )
    for asset_id, remote_id, title, url, source_url in sfx_specs:
        path = audio_dir / f"{asset_id}-{remote_id}.mp3"
        if acquire_assets:
            _download_binary(url, path)
            page_name = source_url.rstrip("/").split("/")[-1]
            _archive_page(
                source_url,
                license_dir / f"mixkit-sfx-{page_name}.html",
            )
        else:
            _copy_required(fallback_sfx, path)
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=_relative(output_dir, path),
                keywords=["sound effect", title],
                provenance="internet:licensed-stock-audio",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=remote_id,
                creator="Mixkit contributor",
                source_url=source_url,
                license_url="https://mixkit.co/license/",
                search_query=title,
            )
        )
    return assets


def build_social_kinetic_schedule() -> list[dict[str, Any]]:
    specs = [
        (0, 3_400, "presenter", "hook-presenter"),
        (3_400, 5_650, "flow-illustrative", "robot-trading-wide"),
        (5_650, 6_450, "direct-evidence", "ea-proof-punch"),
        (6_450, 7_200, "flow-illustrative", "robot-trading-detail"),
        (7_200, QUESTION_START_MS, "presenter", "number-reveal"),
        (
            QUESTION_START_MS,
            BOARDROOM_START_MS,
            "deterministic-graphic",
            "question-interrupt",
        ),
        (
            BOARDROOM_START_MS,
            13_630,
            "flow-illustrative",
            "robot-boardroom",
        ),
        (13_630, ROBOT_ACTION_START_MS, "presenter", "upi-pip"),
        (
            ROBOT_ACTION_START_MS,
            PRESENTER_RESET_START_MS,
            "licensed-context",
            "robot-laptop-action",
        ),
        (
            PRESENTER_RESET_START_MS,
            RISK_START_MS,
            "presenter",
            "future-explanation",
        ),
        (
            RISK_START_MS,
            MANAGER_START_MS,
            "licensed-context",
            "risk-manager",
        ),
        (
            MANAGER_START_MS,
            33_270,
            "presenter",
            "robot-manager-explanation",
        ),
        (33_270, 36_070, "deterministic-graphic", "brand-logo"),
        (36_070, 37_370, "presenter", "zero-risk-correction"),
        (37_370, 40_800, "presenter", "cta-open"),
        (40_800, HUMAN_REFERENCE_DURATION_MS, "presenter", "cta-demo"),
    ]
    shots = [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": source_role,
            "editorial_role": editorial_role,
            "reference_role": "primary-human",
        }
        for index, (
            start_ms,
            end_ms,
            source_role,
            editorial_role,
        ) in enumerate(specs, start=1)
    ]
    durations = [
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
    ]
    if not 2_300 <= median(durations) <= 3_000:
        raise ValueError("Social-kinetic schedule drifted from reference pacing")
    return shots


def build_social_kinetic_flow_shots(
    output_dir: Path,
) -> list[FlowShotSpec]:
    plates = output_dir.expanduser().resolve() / "flow-plates"
    constraints = [
        "Single continuous portrait shot with one clear subject",
        "No readable text, symbols, logos, captions or watermarks",
        "No software UI, code, charts, numbers, currencies or documents",
        "No internal cuts, flicker, warped hands or duplicate limbs",
        "Bright exposure, clean shape separation and safe center framing",
    ]
    return [
        FlowShotSpec(
            id="flow-robot-trading",
            start_ms=3_400,
            end_ms=7_200,
            editorial_role="robot-trading-process",
            prompt=(
                "A premium cinematic portrait shot of one polished humanoid "
                "robot actively operating a modern workstation. Mechanical "
                "hands make deliberate physical control movements while "
                "abstract cyan and red light patterns move across frosted "
                "glass panels in the background. Bright commercial lighting, "
                "deep but detailed shadows, realistic materials, controlled "
                "camera push-in, no readable display content."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "robot-trading-start.png"),
                str(plates / "robot-trading-end.png"),
            ],
            requested_content=["process-illustration"],
            constraints=constraints,
        ),
        FlowShotSpec(
            id="flow-robot-boardroom",
            start_ms=BOARDROOM_START_MS,
            end_ms=13_300,
            editorial_role="robot-boardroom-question",
            prompt=(
                "A bright cinematic portrait boardroom with three elegant "
                "humanoid robots seated around a glass table and one human "
                "supervisor watching them. The robots turn toward one another "
                "as if evaluating a difficult decision. Gentle parallax, "
                "premium blue-white lighting, realistic anatomy, one "
                "continuous camera move, no readable surfaces."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "robot-boardroom-start.png"),
                str(plates / "robot-boardroom-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=constraints,
        ),
        FlowShotSpec(
            id="flow-robot-action",
            start_ms=ROBOT_ACTION_START_MS,
            end_ms=PRESENTER_RESET_START_MS,
            editorial_role="robot-action-workstation",
            prompt=(
                "A close cinematic portrait shot of a realistic robotic hand "
                "working beside a laptop and physical desk controls. The hand "
                "moves between tactile knobs and keys with purposeful speed "
                "while soft cyan and warm amber reflections travel across the "
                "metal. Shallow depth of field, bright premium commercial "
                "lighting, one continuous shot, no readable screen content."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "robot-action-start.png"),
                str(plates / "robot-action-end.png"),
            ],
            requested_content=["process-illustration"],
            constraints=constraints,
        ),
    ]


def _presenter_layer(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    start_scale: float,
    end_scale: float,
    fade_in_ms: int = 0,
) -> BlueprintLayerSpec:
    duration_ms = end_ms - start_ms
    opacity_keyframes = (
        [
            OpacityKeyframe(at_ms=0, value=0),
            OpacityKeyframe(at_ms=fade_in_ms, value=1),
        ]
        if fade_in_ms > 0
        else [OpacityKeyframe(at_ms=0, value=1)]
    )
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="presenter",
        kind="video",
        asset_id="presenter-edl",
        source_start_ms=start_ms,
        source_end_ms=end_ms,
        bounds=LayerBounds(),
        fit="cover",
        transform_keyframes=[
            TransformKeyframe(at_ms=0, scale=start_scale),
            TransformKeyframe(at_ms=duration_ms, scale=end_scale),
        ],
        opacity_keyframes=opacity_keyframes,
        effect_keyframes=[
            EffectKeyframe(
                at_ms=0,
                brightness=1.045,
                contrast=1.025,
                saturation=0.92,
            ),
            EffectKeyframe(
                at_ms=duration_ms,
                brightness=1.055,
                contrast=1.035,
                saturation=0.94,
            ),
        ],
        z_index=10,
        muted=True,
        reference_role="primary-human",
    )


def build_social_kinetic_layers() -> list[BlueprintLayerSpec]:
    layers: list[BlueprintLayerSpec] = [
        _presenter_layer(
            layer_id="layer-hook-presenter",
            shot_id="shot-01",
            start_ms=0,
            end_ms=3_400,
            start_scale=1.0,
            end_scale=1.035,
        ),
        BlueprintLayerSpec(
            id="layer-flow-robot-a",
            shot_id="shot-02",
            start_ms=3_400,
            end_ms=5_650,
            source_role="flow-illustrative",
            flow_shot_id="flow-robot-trading",
            source_start_ms=0,
            source_end_ms=2_200,
            bounds=LayerBounds(),
            crop={"x": 0, "y": 0, "width": 1, "height": 1},
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1.03),
                TransformKeyframe(at_ms=2_250, x=-22, scale=1.13),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.08,
                    contrast=1.06,
                    saturation=0.88,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-evidence-proof",
            shot_id="shot-03",
            start_ms=5_650,
            end_ms=6_450,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-mql5-110k-proof",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=16, scale=1),
                TransformKeyframe(at_ms=800, y=-18, scale=1.12),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.03,
                    contrast=1.08,
                    saturation=0.82,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="secondary-10",
        ),
        BlueprintLayerSpec(
            id="layer-flow-robot-b",
            shot_id="shot-04",
            start_ms=6_450,
            end_ms=7_200,
            source_role="flow-illustrative",
            flow_shot_id="flow-robot-trading",
            source_start_ms=1_450,
            source_end_ms=2_200,
            bounds=LayerBounds(),
            crop={"x": 0.34, "y": 0.06, "width": 0.62, "height": 0.9},
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=18, scale=1.12),
                TransformKeyframe(at_ms=750, x=-12, scale=1.2),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.1,
                    contrast=1.08,
                    saturation=0.9,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-number-presenter",
            shot_id="shot-05",
            start_ms=7_200,
            end_ms=QUESTION_START_MS,
            start_scale=1.13,
            end_scale=1.18,
        ),
        BlueprintLayerSpec(
            id="layer-question",
            shot_id="shot-06",
            start_ms=QUESTION_START_MS,
            end_ms=BOARDROOM_START_MS,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-question-plate",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1.08),
                TransformKeyframe(
                    at_ms=BOARDROOM_START_MS - QUESTION_START_MS,
                    scale=1.15,
                ),
            ],
            z_index=10,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-flow-boardroom",
            shot_id="shot-07",
            start_ms=BOARDROOM_START_MS,
            end_ms=13_630,
            source_role="flow-illustrative",
            flow_shot_id="flow-robot-boardroom",
            source_start_ms=0,
            source_end_ms=2_200,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=8, scale=1.04),
                TransformKeyframe(
                    at_ms=13_630 - BOARDROOM_START_MS,
                    y=-14,
                    scale=1.12,
                ),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.1,
                    contrast=1.04,
                    saturation=0.84,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-upi-presenter",
            shot_id="shot-08",
            start_ms=13_630,
            end_ms=ROBOT_ACTION_START_MS,
            start_scale=1.02,
            end_scale=1.055,
        ),
        BlueprintLayerSpec(
            id="layer-flow-robot-action",
            shot_id="shot-09",
            start_ms=ROBOT_ACTION_START_MS,
            end_ms=PRESENTER_RESET_START_MS,
            source_role="flow-illustrative",
            flow_shot_id="flow-robot-action",
            source_start_ms=0,
            source_end_ms=2_200,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=12, scale=1.04),
                TransformKeyframe(
                    at_ms=PRESENTER_RESET_START_MS - ROBOT_ACTION_START_MS,
                    x=-24,
                    scale=1.14,
                ),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.08,
                    contrast=1.06,
                    saturation=0.88,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-presenter-explanation",
            shot_id="shot-10",
            start_ms=PRESENTER_RESET_START_MS,
            end_ms=RISK_START_MS,
            start_scale=1.0,
            end_scale=1.055,
        ),
        BlueprintLayerSpec(
            id="layer-risk-manager",
            shot_id="shot-11",
            start_ms=RISK_START_MS,
            end_ms=MANAGER_START_MS,
            source_role="licensed-context",
            kind="video",
            asset_id="licensed-risk-manager",
            source_start_ms=3_200,
            source_end_ms=5_640,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=-16, scale=1.04),
                TransformKeyframe(
                    at_ms=MANAGER_START_MS - RISK_START_MS,
                    x=16,
                    scale=1.12,
                ),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.04,
                    contrast=1.12,
                    saturation=0.72,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-presenter-manager",
            shot_id="shot-12",
            start_ms=MANAGER_START_MS,
            end_ms=33_300,
            start_scale=1.035,
            end_scale=1.085,
        ),
        BlueprintLayerSpec(
            id="layer-logo",
            shot_id="shot-13",
            start_ms=33_300,
            end_ms=36_300,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-logo-card",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=40, scale=0.82),
                TransformKeyframe(at_ms=700, y=0, scale=1),
                TransformKeyframe(at_ms=3_000, scale=1.035),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
                OpacityKeyframe(at_ms=2_500, value=1),
                OpacityKeyframe(at_ms=3_000, value=0),
            ],
            z_index=10,
            muted=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-correction-presenter",
            shot_id="shot-14",
            start_ms=35_800,
            end_ms=37_370,
            start_scale=1.09,
            end_scale=1.12,
            fade_in_ms=500,
        ),
        _presenter_layer(
            layer_id="layer-cta-presenter",
            shot_id="shot-15",
            start_ms=37_370,
            end_ms=40_800,
            start_scale=1.12,
            end_scale=1.035,
        ),
        _presenter_layer(
            layer_id="layer-demo-presenter",
            shot_id="shot-16",
            start_ms=40_800,
            end_ms=HUMAN_REFERENCE_DURATION_MS,
            start_scale=1.13,
            end_scale=1.17,
        ),
        BlueprintLayerSpec(
            id="layer-upi-pip",
            shot_id="shot-08",
            start_ms=13_820,
            end_ms=15_570,
            source_role="licensed-context",
            kind="image",
            asset_id="graphic-upi-phone",
            bounds=LayerBounds(x=340, y=1_210, width=400, height=470),
            fit="contain",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=30, scale=0.88),
                TransformKeyframe(at_ms=220, y=0, scale=1),
                TransformKeyframe(at_ms=1_750, scale=1.04),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=150, value=1),
            ],
            border_radius=28,
            z_index=30,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-hook-vignette",
            shot_id="shot-01",
            start_ms=0,
            end_ms=3_000,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-lower-vignette",
            bounds=LayerBounds(),
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=1),
                OpacityKeyframe(at_ms=2_600, value=1),
                OpacityKeyframe(at_ms=3_000, value=0),
            ],
            z_index=20,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-correction-vignette",
            shot_id="shot-14",
            start_ms=36_070,
            end_ms=37_370,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-lower-vignette",
            bounds=LayerBounds(),
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=300, value=1),
                OpacityKeyframe(at_ms=900, value=1),
                OpacityKeyframe(at_ms=1_300, value=0),
            ],
            z_index=20,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-cta-vignette",
            shot_id="shot-16",
            start_ms=40_800,
            end_ms=43_800,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-lower-vignette",
            bounds=LayerBounds(),
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=1),
                OpacityKeyframe(at_ms=2_500, value=1),
                OpacityKeyframe(at_ms=3_000, value=0),
            ],
            z_index=20,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-market-overlay-a",
            shot_id="shot-02",
            start_ms=3_400,
            end_ms=5_650,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-market-overlay",
            bounds=LayerBounds(),
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0.48),
                OpacityKeyframe(at_ms=2_250, value=0.68),
            ],
            blend_mode="screen",
            z_index=22,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-market-overlay-b",
            shot_id="shot-04",
            start_ms=6_450,
            end_ms=7_200,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="graphic-market-overlay",
            bounds=LayerBounds(),
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0.42),
                OpacityKeyframe(at_ms=750, value=0.7),
            ],
            blend_mode="screen",
            z_index=22,
            muted=True,
            reference_role="primary-human",
        ),
    ]
    return layers


def build_social_kinetic_text_cues() -> list[KineticTextCue]:
    return [
        KineticTextCue(
            id="text-hook-year",
            start_ms=180,
            end_ms=880,
            text="2008",
            family="hero-condensed",
            x=540,
            y=1_340,
            max_width=880,
            animation="slam",
        ),
        KineticTextCue(
            id="text-hook-months",
            start_ms=1_060,
            end_ms=3_350,
            text="3 MONTHS",
            family="hero-condensed",
            x=540,
            y=1_245,
            max_width=960,
            animation="slam",
        ),
        KineticTextCue(
            id="text-hook-automated",
            start_ms=1_720,
            end_ms=3_350,
            text="AUTOMATED",
            family="cyan-secondary",
            x=540,
            y=1_390,
            max_width=900,
            animation="rise",
        ),
        KineticTextCue(
            id="text-hook-trading",
            start_ms=2_020,
            end_ms=3_350,
            text="TRADING",
            family="hero-condensed",
            x=540,
            y=1_530,
            max_width=920,
            animation="slam",
        ),
        KineticTextCue(
            id="text-hook-contest",
            start_ms=2_320,
            end_ms=3_350,
            text="CONTEST",
            family="cyan-secondary",
            x=650,
            y=1_675,
            max_width=620,
            animation="rise",
        ),
        KineticTextCue(
            id="text-ea-title",
            start_ms=4_050,
            end_ms=5_200,
            text="FOREX ROBOT",
            family="outlined-stack",
            x=540,
            y=1_420,
            max_width=940,
            animation="stack",
        ),
        KineticTextCue(
            id="text-proof-source",
            start_ms=5_700,
            end_ms=6_450,
            text="MQL5 • VERIFIED PEAK EVIDENCE",
            family="micro-source",
            x=540,
            y=1_720,
            max_width=940,
            animation="hard-cut",
        ),
        KineticTextCue(
            id="text-number-peak",
            start_ms=7_550,
            end_ms=9_050,
            text="$110K PEAK",
            family="gradient-number",
            x=540,
            y=365,
            max_width=940,
            animation="glow",
        ),
        KineticTextCue(
            id="text-future",
            start_ms=11_750,
            end_ms=12_450,
            text="THE FUTURE?",
            family="cyan-secondary",
            x=540,
            y=1_485,
            max_width=900,
            animation="rise",
        ),
        KineticTextCue(
            id="text-upi",
            start_ms=14_250,
            end_ms=14_950,
            text="UPI",
            family="outlined-stack",
            x=780,
            y=1_430,
            max_width=420,
            animation="quote-pop",
        ),
        KineticTextCue(
            id="text-risk-limits",
            start_ms=24_720,
            end_ms=25_520,
            text="RISK LIMITS",
            family="outlined-stack",
            x=540,
            y=1_420,
            max_width=920,
            animation="stack",
        ),
        KineticTextCue(
            id="text-monitor",
            start_ms=25_780,
            end_ms=26_480,
            text="MONITOR",
            family="outlined-stack",
            x=540,
            y=1_430,
            max_width=900,
            animation="hard-cut",
        ),
        KineticTextCue(
            id="text-zero-risk",
            start_ms=36_150,
            end_ms=37_150,
            text="ZERO RISK",
            secondary_text="✕  ↓",
            family="correction-symbol",
            x=540,
            y=1_460,
            max_width=940,
            animation="draw",
        ),
        KineticTextCue(
            id="text-demo",
            start_ms=41_250,
            end_ms=43_050,
            text='"Demo"',
            family="cta-quote",
            x=540,
            y=1_535,
            max_width=920,
            animation="quote-pop",
        ),
    ]


def build_social_kinetic_motion_events() -> list[MotionEventSpec]:
    events = [
        MotionEventSpec(
            id=f"motion-{cue.id}",
            start_ms=cue.start_ms,
            end_ms=min(cue.end_ms, cue.start_ms + 240),
            kind="text-reveal",
            target_id=cue.id,
            intensity=0.62,
        )
        for cue in build_social_kinetic_text_cues()
    ]
    events.extend(
        [
            MotionEventSpec(
                id="motion-hook-punch",
                start_ms=0,
                end_ms=260,
                kind="punch-crop",
                target_id="layer-hook-presenter",
                intensity=0.5,
            ),
            MotionEventSpec(
                id="motion-flow-robot-push",
                start_ms=3_400,
                end_ms=3_760,
                kind="directional-jump",
                target_id="layer-flow-robot-a",
                intensity=0.7,
                direction="left",
            ),
            MotionEventSpec(
                id="motion-flow-robot-scan",
                start_ms=4_620,
                end_ms=5_180,
                kind="highlight-sweep",
                target_id="layer-flow-robot-a",
                intensity=0.55,
                direction="right",
            ),
            MotionEventSpec(
                id="motion-proof-punch",
                start_ms=5_650,
                end_ms=5_980,
                kind="proof-punch",
                target_id="layer-evidence-proof",
                intensity=0.78,
            ),
            MotionEventSpec(
                id="motion-number-punch",
                start_ms=7_200,
                end_ms=7_520,
                kind="punch-crop",
                target_id="layer-number-presenter",
                intensity=0.58,
            ),
            MotionEventSpec(
                id="motion-question-pulse",
                start_ms=QUESTION_START_MS,
                end_ms=QUESTION_START_MS + 820,
                kind="question-pulse",
                target_id="layer-question",
                intensity=0.72,
            ),
            MotionEventSpec(
                id="motion-boardroom-push",
                start_ms=BOARDROOM_START_MS,
                end_ms=BOARDROOM_START_MS + 360,
                kind="directional-jump",
                target_id="layer-flow-boardroom",
                intensity=0.66,
                direction="up",
            ),
            MotionEventSpec(
                id="motion-boardroom-symbol",
                start_ms=12_120,
                end_ms=12_720,
                kind="question-pulse",
                target_id="text-future",
                intensity=0.52,
            ),
            MotionEventSpec(
                id="motion-upi-pip",
                start_ms=13_820,
                end_ms=14_180,
                kind="pip-pop",
                target_id="layer-upi-pip",
                intensity=0.7,
            ),
            MotionEventSpec(
                id="motion-robot-action-punch",
                start_ms=ROBOT_ACTION_START_MS,
                end_ms=ROBOT_ACTION_START_MS + 350,
                kind="punch-crop",
                target_id="layer-flow-robot-action",
                intensity=0.58,
            ),
            MotionEventSpec(
                id="motion-presenter-reset",
                start_ms=20_620,
                end_ms=20_900,
                kind="punch-crop",
                target_id="layer-presenter-explanation",
                intensity=0.42,
            ),
            MotionEventSpec(
                id="motion-risk-sweep",
                start_ms=RISK_START_MS,
                end_ms=RISK_START_MS + 650,
                kind="highlight-sweep",
                target_id="layer-risk-manager",
                intensity=0.6,
                direction="right",
            ),
            MotionEventSpec(
                id="motion-risk-monitor",
                start_ms=25_620,
                end_ms=26_080,
                kind="punch-crop",
                target_id="layer-risk-manager",
                intensity=0.44,
            ),
            MotionEventSpec(
                id="motion-manager-catch",
                start_ms=29_980,
                end_ms=30_300,
                kind="punch-crop",
                target_id="layer-presenter-manager",
                intensity=0.46,
            ),
            MotionEventSpec(
                id="motion-logo-build",
                start_ms=33_270,
                end_ms=34_300,
                kind="logo-build",
                target_id="layer-logo",
                intensity=0.72,
            ),
            MotionEventSpec(
                id="motion-correction-drop",
                start_ms=36_070,
                end_ms=36_620,
                kind="impact-flash",
                target_id="layer-correction-presenter",
                intensity=0.52,
            ),
            MotionEventSpec(
                id="motion-cta-jump",
                start_ms=40_800,
                end_ms=41_140,
                kind="directional-jump",
                target_id="layer-demo-presenter",
                intensity=0.68,
                direction="right",
            ),
        ]
    )
    return events


def build_human_reference_blueprint(
    *,
    source: Path,
    output_dir: Path,
    style_reference: Path | None = None,
    flow_operation_budget: int = 8,
    seed_dir: Path | None = None,
    prepare_media: bool = True,
    acquire_assets: bool = True,
) -> dict[str, str]:
    from app.editor.analysis import probe_video
    from app.editor.internet_story_0810 import (
        build_0810_evidence_items,
        load_0810_transcript,
    )

    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    style_reference = (
        style_reference.expanduser().resolve()
        if style_reference is not None
        else _DEFAULT_STYLE_REFERENCE
    )
    seed_dir = (
        seed_dir.expanduser().resolve()
        if seed_dir is not None
        else _DEFAULT_SEED_DIR
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    if not style_reference.is_file():
        raise FileNotFoundError(style_reference)
    if not seed_dir.is_dir():
        raise FileNotFoundError(seed_dir)
    if not 0 <= flow_operation_budget <= 8:
        raise ValueError("Flow operation budget must be between zero and eight")
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename in (
        "transcript-groq-raw.json",
        "transcript-corrected-texts.json",
    ):
        _copy_required(seed_dir / filename, output_dir / filename)
    source_capture_dir = output_dir / "source-captures"
    source_capture_dir.mkdir(parents=True, exist_ok=True)
    for capture in (seed_dir / "source-captures").glob("*.png"):
        _copy_required(capture, source_capture_dir / capture.name)

    if prepare_media:
        metadata = probe_video(source)
        source_duration_ms = round(metadata.duration_seconds * 1000)
        silence_intervals = _detect_silence_intervals(source)
    else:
        metadata = VideoMetadata(
            width=1_080,
            height=1_920,
            fps=30,
            frame_count=1_485,
            duration_seconds=49.505,
        )
        source_duration_ms = 49_505
        silence_intervals = list(_DEFAULT_SILENCE_INTERVALS_MS)
    edl = build_dialogue_edl_from_silences(
        source_duration_ms=source_duration_ms,
        target_duration_ms=HUMAN_REFERENCE_DURATION_MS,
        silence_intervals_ms=silence_intervals,
        minimum_retained_silence_ms=100,
    )

    presenter = (
        output_dir / "assets" / "presenter" / "presenter-edl.mp4"
    )
    dialogue_original = (
        output_dir / "assets" / "audio" / "dialogue-original.wav"
    )
    dialogue_processed = (
        output_dir / "assets" / "audio" / "dialogue-processed.wav"
    )
    if prepare_media:
        _prepare_dialogue_media(
            source=source,
            edl=edl,
            presenter_output=presenter,
            original_audio_output=dialogue_original,
            processed_audio_output=dialogue_processed,
        )
    else:
        _copy_required(
            seed_dir / "assets" / "presenter" / "source-presenter.mp4",
            presenter,
        )
        _copy_required(
            seed_dir / "assets" / "audio" / "dialogue-original.wav",
            dialogue_original,
        )
        _copy_required(
            seed_dir / "assets" / "audio" / "dialogue-processed.wav",
            dialogue_processed,
        )

    source_segments = load_0810_transcript(output_dir)
    remapped_segments = _remap_transcript(source_segments, edl)
    _write_json(
        output_dir / "transcript-aligned.json",
        [segment.model_dump(mode="json") for segment in remapped_segments],
    )

    evidence = build_0810_evidence_items(output_dir)
    _write_json(
        output_dir / "evidence.json",
        [item.model_dump(mode="json") for item in evidence],
    )
    graphics_dir = output_dir / "assets" / "graphics"
    question = graphics_dir / "question-plate.png"
    market_overlay = graphics_dir / "market-overlay.png"
    robot_transition = graphics_dir / "robot-transition.png"
    lower_vignette = graphics_dir / "lower-vignette.png"
    peak_proof = graphics_dir / "evidence-mql5-110k-proof.jpg"
    upi_source = (
        output_dir
        / "assets"
        / "external"
        / "upi-logo-public-domain.png"
    )
    upi_card = graphics_dir / "upi-phone-card.png"
    upi_license = (
        output_dir
        / "assets"
        / "licenses"
        / "upi-logo-public-domain.json"
    )
    brand_original = (
        output_dir / "assets" / "brand" / "profit-bricks-logo.png"
    )
    logo_card = graphics_dir / "profit-bricks-logo-card.jpg"
    _copy_required(_DEFAULT_BRAND_LOGO, brand_original)
    _copy_required(_DEFAULT_UPI_LOGO, upi_source)
    _copy_required(_DEFAULT_UPI_LICENSE, upi_license)
    _build_question_plate(question)
    _build_market_overlay(market_overlay)
    _build_robot_transition(robot_transition)
    _build_lower_vignette(lower_vignette)
    _build_peak_proof_card(
        source=source_capture_dir / "mql5-110k-mobile-excerpt.png",
        destination=peak_proof,
    )
    _build_upi_phone_card(source=upi_source, destination=upi_card)
    _build_logo_card(source=brand_original, destination=logo_card)
    _build_flow_plates(output_dir)

    assets: list[AssetRef] = [
        AssetRef(
            id="presenter-edl",
            kind="video",
            path=_relative(output_dir, presenter),
            keywords=["presenter", "dialogue EDL", "source footage"],
            provenance="user-provided-edl-preserved",
            license="User-provided source footage",
        ),
        AssetRef(
            id="dialogue-original",
            kind="audio",
            path=_relative(output_dir, dialogue_original),
            keywords=["EDL dialogue baseline", "48 kHz"],
            provenance="source-dialogue-edl-master",
            license="User-provided source audio",
        ),
        AssetRef(
            id="dialogue-processed",
            kind="audio",
            path=_relative(output_dir, dialogue_processed),
            keywords=["processed dialogue", "48 kHz"],
            provenance="source-dialogue-edl-processed",
            license="User-provided source audio",
        ),
        AssetRef(
            id="evidence-mql5-110k-proof",
            kind="image",
            path=_relative(output_dir, peak_proof),
            keywords=["official evidence", "$110,000 at one point"],
            provenance="official-source-capture-derived-proof-card",
            license="Official source excerpt used as editorial evidence",
        ),
        AssetRef(
            id="graphic-question-plate",
            kind="image",
            path=_relative(output_dir, question),
            keywords=["question interrupt", "red abstract"],
            provenance="deterministic-original-graphic",
        ),
        AssetRef(
            id="graphic-market-overlay",
            kind="image",
            path=_relative(output_dir, market_overlay),
            keywords=["illustrative market motion overlay"],
            provenance="deterministic-original-graphic",
        ),
        AssetRef(
            id="graphic-robot-transition",
            kind="image",
            path=_relative(output_dir, robot_transition),
            keywords=["robot transition", "light streaks"],
            provenance="deterministic-original-graphic",
        ),
        AssetRef(
            id="graphic-lower-vignette",
            kind="image",
            path=_relative(output_dir, lower_vignette),
            keywords=["presenter lower vignette", "reference typography"],
            provenance="deterministic-original-graphic",
        ),
        AssetRef(
            id="source-upi-logo",
            kind="image",
            path=_relative(output_dir, upi_source),
            keywords=["UPI", "official payment brand mark"],
            provenance="internet:public-domain-brand-asset",
            license="Public domain",
            provider="Wikimedia Commons",
            remote_id="UPI-Logo-vector.svg",
            creator="Unknown",
            source_url=(
                "https://commons.wikimedia.org/wiki/"
                "File:UPI-Logo-vector.svg"
            ),
            license_url=(
                "https://commons.wikimedia.org/wiki/"
                "File:UPI-Logo-vector.svg"
            ),
            search_query="Unified Payments Interface logo",
        ),
        AssetRef(
            id="graphic-upi-phone",
            kind="image",
            path=_relative(output_dir, upi_card),
            keywords=["UPI", "payment phone PIP"],
            provenance="public-domain-upi-logo-derived-graphic",
            license="Public domain",
            provider="Wikimedia Commons",
            remote_id="UPI-Logo-vector.svg",
            source_url=(
                "https://commons.wikimedia.org/wiki/"
                "File:UPI-Logo-vector.svg"
            ),
            license_url=(
                "https://commons.wikimedia.org/wiki/"
                "File:UPI-Logo-vector.svg"
            ),
            search_query="Unified Payments Interface logo",
        ),
        AssetRef(
            id="brand-logo-original",
            kind="image",
            path=_relative(output_dir, brand_original),
            keywords=["Profit Bricks", "brand"],
            provenance="user-provided-brand-asset",
            license="User-provided",
        ),
        AssetRef(
            id="graphic-logo-card",
            kind="image",
            path=_relative(output_dir, logo_card),
            keywords=["Profit Bricks", "logo build"],
            provenance="user-provided-brand-derived-card",
            license="User-provided",
        ),
    ]
    assets.extend(
        _prepare_licensed_video_assets(
            output_dir=output_dir,
            seed_dir=seed_dir,
        )
    )
    assets.extend(
        _prepare_licensed_audio_assets(
            output_dir=output_dir,
            seed_dir=seed_dir,
            acquire_assets=acquire_assets,
        )
    )

    layers = build_social_kinetic_layers()
    flow_shots = build_social_kinetic_flow_shots(output_dir)
    kinetic_text = build_social_kinetic_text_cues()
    motion_events = build_social_kinetic_motion_events()
    audio = build_social_kinetic_audio_plan(remapped_segments)
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(),
        duration_ms=HUMAN_REFERENCE_DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=[],
        audio=audio,
        flow_shots=flow_shots,
        evidence=evidence,
        reference_profile="social-kinetic",
        story_profile="automation-future",
        style_reference_path=str(style_reference),
        voice_policy="reference-compressed",
        dialogue_edl=edl,
        kinetic_text_cues=kinetic_text,
        motion_events=motion_events,
    )

    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "reference_profile": "reference-profile.json",
        "dialogue_edl": "dialogue-edl.json",
        "kinetic_text_plan": "kinetic-text-plan.json",
        "motion_events": "motion-events.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "caption_plan": "caption-plan.json",
        "production_settings": "production-settings.json",
        "transcript_aligned": "transcript-aligned.json",
    }
    _write_json(
        output_dir / artifacts["blueprint"],
        blueprint.model_dump(mode="json"),
    )
    _write_json(
        output_dir / artifacts["flow_shot_plan"],
        [shot.model_dump(mode="json") for shot in flow_shots],
    )
    _write_json(
        output_dir / artifacts["dialogue_edl"],
        {
            "source_duration_ms": source_duration_ms,
            "output_duration_ms": HUMAN_REFERENCE_DURATION_MS,
            "removed_ms": source_duration_ms - HUMAN_REFERENCE_DURATION_MS,
            "playback_rate_max": max(
                segment.playback_rate for segment in edl
            ),
            "segments": [
                segment.model_dump(mode="json") for segment in edl
            ],
        },
    )
    text_visible_ms = measure_visible_interval_duration(kinetic_text)
    _write_json(
        output_dir / artifacts["kinetic_text_plan"],
        {
            "profile": "social-kinetic",
            "continuous_captions": False,
            "semantic_text_visible_ms": text_visible_ms,
            "semantic_text_ratio": round(
                text_visible_ms / HUMAN_REFERENCE_DURATION_MS,
                6,
            ),
            "cues": [
                cue.model_dump(mode="json") for cue in kinetic_text
            ],
        },
    )
    _write_json(
        output_dir / artifacts["motion_events"],
        [event.model_dump(mode="json") for event in motion_events],
    )
    _write_json(
        output_dir / artifacts["sound_cue_sheet"],
        {
            "profile": "social-kinetic",
            "music_bpm": audio.music_bpm,
            "target_lufs": audio.integrated_lufs,
            "target_true_peak_dbtp": audio.true_peak_dbtp,
            "target_lra_lu": audio.target_lra_lu,
            "cues": [
                cue.model_dump(mode="json") for cue in audio.sfx_cues
            ],
            "speech_protection_windows": [
                window.model_dump(mode="json")
                for window in audio.speech_protection_windows
            ],
        },
    )
    layer_ids_by_shot: dict[str, list[str]] = {}
    for layer in layers:
        layer_ids_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    _write_json(
        output_dir / artifacts["storyboard"],
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot.get(shot["id"], []),
                "kinetic_text_ids": [
                    cue.id
                    for cue in kinetic_text
                    if cue.start_ms < shot["end_ms"]
                    and cue.end_ms > shot["start_ms"]
                ],
                "evidence_ids": (
                    ["mql5-110k-peak"]
                    if shot["editorial_role"]
                    in {"ea-proof-punch", "number-reveal"}
                    else []
                ),
            }
            for shot in build_social_kinetic_schedule()
        ],
    )
    _write_json(
        output_dir / artifacts["reference_profile"],
        {
            "name": "social-kinetic",
            "primary_reference": {
                "path": str(style_reference),
                "checksum_sha256": _sha256(style_reference),
                "role": "typography, pacing, color, motion and sound grammar",
            },
            "secondary_reference": {
                "training_reference": 10,
                "role": "factual evidence restraint only",
            },
            "measured_primary": {
                "duration_seconds": 44.37,
                "hard_cuts": 13,
                "median_shot_seconds": 2.70,
                "dark_frame_ratio": 0.03,
                "mean_luminance": 101.4,
                "mean_saturation": 75.5,
                "cut_audio_alignment_percent": 92.3,
            },
            "targets": {
                "duration_seconds": [44.1, 44.7],
                "hard_cuts": [13, 16],
                "median_shot_seconds": [2.3, 3.0],
                "presenter_ratio": [0.58, 0.68],
                "flow_ratio_max": 0.18,
                "dark_frame_ratio_max": 0.06,
                "mean_luminance": [95, 108],
                "mean_saturation": [65, 85],
            },
        },
    )
    _write_json(
        output_dir / artifacts["flow_instructions"],
        {
            "card": [
                {
                    "text": (
                        "Premium bright portrait commercial cinematography. "
                        "One clear subject and one continuous camera move. "
                        "No readable text, UI, code, charts, numbers, "
                        "currencies, documents, captions, logos or watermarks."
                    )
                }
            ]
        },
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "profile": "social-kinetic",
            "pages": [],
            "reason": (
                "The human reference uses sparse semantic typography rather "
                "than continuous subtitles."
            ),
        },
    )
    _write_json(
        output_dir / artifacts["capture_manifest"],
        {
            "source": {
                "path": str(source),
                "checksum_sha256": _sha256(source),
                "read_only": True,
            },
            "presenter_edl": {
                "path": _relative(output_dir, presenter),
                "checksum_sha256": _sha256(presenter),
                "privacy_reviewed": True,
            },
            "official_source_captures": [
                {
                    "path": _relative(output_dir, capture),
                    "checksum_sha256": _sha256(capture),
                }
                for capture in sorted(source_capture_dir.glob("*.png"))
            ],
        },
    )
    _write_json(
        output_dir / artifacts["asset_manifest"],
        {
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(output_dir / asset.path),
                }
                for asset in assets
            ]
        },
    )
    _write_json(
        output_dir / artifacts["production_settings"],
        {
            "style_reference": str(style_reference),
            "reference_profile": "social-kinetic",
            "voice_policy": "reference-compressed",
            "flow_operation_budget": flow_operation_budget,
            "maximum_attempts_per_flow_shot": 2,
            "automatic_retry": False,
            "human_final_approval_required": True,
        },
    )
    return artifacts
