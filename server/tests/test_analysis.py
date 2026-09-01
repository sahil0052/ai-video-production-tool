from pathlib import Path

import cv2
import numpy as np
import pytest

from app.editor.analysis import (
    detect_hard_cuts,
    detect_reframe_keyframes,
    probe_video,
    validate_source,
)
from app.models import VideoMetadata


def write_video(path: Path, colors: list[tuple[int, int, int]], fps: int = 10) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (180, 320),
    )
    assert writer.isOpened()
    for color in colors:
        frame = np.full((320, 180, 3), color, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_probe_and_validate_accepts_short_vertical_video(tmp_path: Path) -> None:
    source = tmp_path / "vertical.mp4"
    write_video(source, [(20, 20, 20)] * 20)

    metadata = probe_video(source)

    assert metadata.width == 180
    assert metadata.height == 320
    assert metadata.duration_seconds == pytest.approx(2.0, abs=0.1)
    validate_source(metadata)


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (
            VideoMetadata(
                width=1920,
                height=1080,
                fps=30,
                frame_count=900,
                duration_seconds=30,
            ),
            "portrait",
        ),
        (
            VideoMetadata(
                width=1080,
                height=1920,
                fps=30,
                frame_count=2100,
                duration_seconds=70,
            ),
            "65 seconds",
        ),
        (
            VideoMetadata(
                width=4320,
                height=7680,
                fps=30,
                frame_count=900,
                duration_seconds=30,
            ),
            "resolution",
        ),
    ],
)
def test_validate_source_rejects_unsupported_video(
    metadata: VideoMetadata, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_source(metadata)


def test_detect_hard_cuts_returns_sorted_scene_boundaries(tmp_path: Path) -> None:
    source = tmp_path / "cuts.mp4"
    write_video(
        source,
        [(10, 10, 10)] * 10
        + [(240, 240, 240)] * 10
        + [(20, 80, 220)] * 10,
    )

    cuts = detect_hard_cuts(
        source,
        threshold=25,
        sample_rate_hz=10,
        min_gap_seconds=0.5,
    )

    assert cuts == sorted(cuts)
    assert len(cuts) == 2
    assert cuts[0] == pytest.approx(1.0, abs=0.2)
    assert cuts[1] == pytest.approx(2.0, abs=0.2)


def test_detect_reframe_keyframes_falls_back_to_stable_center(
    tmp_path: Path,
) -> None:
    source = tmp_path / "no-face.mp4"
    write_video(source, [(30, 30, 30)] * 20)

    keyframes = detect_reframe_keyframes(source, sample_rate_hz=2)

    assert len(keyframes) >= 2
    assert keyframes[0].time_ms == 0
    assert keyframes[-1].time_ms >= 1500
    assert all(keyframe.x == pytest.approx(0.5) for keyframe in keyframes)
    assert all(keyframe.y == pytest.approx(0.42) for keyframe in keyframes)
