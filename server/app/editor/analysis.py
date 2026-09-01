from pathlib import Path

import cv2
import numpy as np

from app.models import ReframeKeyframe, VideoMetadata


def probe_video(path: Path) -> VideoMetadata:
    if not path.is_file():
        raise ValueError("Video file does not exist")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Video could not be opened")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        capture.release()

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise ValueError("Video metadata is invalid")

    return VideoMetadata(
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=frame_count / fps,
    )


def validate_source(metadata: VideoMetadata) -> None:
    if metadata.height <= metadata.width:
        raise ValueError("Source video must use portrait orientation")
    if metadata.duration_seconds <= 0:
        raise ValueError("Source video duration must be positive")
    if metadata.duration_seconds > 65:
        raise ValueError("Source video must be 65 seconds or shorter")
    if metadata.fps < 5 or metadata.fps > 120:
        raise ValueError("Source video frame rate is unsupported")
    if metadata.width > 2160 or metadata.height > 3840:
        raise ValueError("Source video resolution must not exceed 2160x3840")


def detect_hard_cuts(
    path: Path,
    *,
    threshold: float = 30,
    sample_rate_hz: float = 5,
    min_gap_seconds: float = 0.8,
) -> list[float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Video could not be opened")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    sample_every = max(1, round(fps / sample_rate_hz))
    previous: np.ndarray | None = None
    cuts: list[float] = []
    frame_index = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            gray = cv2.cvtColor(cv2.resize(frame, (160, 284)), cv2.COLOR_BGR2GRAY)
            if previous is not None:
                difference = float(np.mean(cv2.absdiff(gray, previous)))
                timestamp = frame_index / fps
                if difference >= threshold and (
                    not cuts or timestamp - cuts[-1] >= min_gap_seconds
                ):
                    cuts.append(round(timestamp, 3))
            previous = gray
            frame_index += 1
    finally:
        capture.release()

    return cuts


def detect_reframe_keyframes(
    path: Path,
    *,
    sample_rate_hz: float = 3,
    smoothing: float = 0.35,
) -> list[ReframeKeyframe]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Video could not be opened")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    sample_every = max(1, round(fps / sample_rate_hz))
    cascade = cv2.CascadeClassifier(
        str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
    )
    keyframes: list[ReframeKeyframe] = []
    frame_index = 0
    smoothed_x = 0.5
    smoothed_y = 0.42

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            height, width = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.12,
                minNeighbors=5,
                minSize=(max(24, width // 16), max(24, height // 16)),
            )
            if len(faces):
                x, y, face_width, face_height = max(
                    faces,
                    key=lambda face: int(face[2]) * int(face[3]),
                )
                detected_x = (x + face_width / 2) / width
                detected_y = max(0.2, min(0.65, (y + face_height * 0.42) / height))
                smoothed_x = (
                    smoothing * detected_x + (1 - smoothing) * smoothed_x
                )
                smoothed_y = (
                    smoothing * detected_y + (1 - smoothing) * smoothed_y
                )

            keyframes.append(
                ReframeKeyframe(
                    time_ms=round(frame_index / fps * 1000),
                    x=round(smoothed_x, 4),
                    y=round(smoothed_y, 4),
                    scale=1.12,
                )
            )
            frame_index += 1
    finally:
        capture.release()

    if not keyframes:
        raise ValueError("Video contains no readable frames")
    return keyframes
