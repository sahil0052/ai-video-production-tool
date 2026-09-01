from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from app.editor.flow_candidate import (
    _material_ocr_tokens,
    build_accepted_clip_command,
    build_candidate_proxy_command,
    build_selected_candidate_proxy_command,
    evaluate_candidate_metrics,
    inspect_candidate_frames,
    prepare_flow_candidate,
    prepare_flow_candidate_selection,
)
from app.production_models import (
    CropSpec,
    FlowGenerationAttempt,
    FlowShotSpec,
)


def _write_motion_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        30,
        (180, 320),
    )
    assert writer.isOpened()
    for index in range(90):
        frame = np.full((320, 180, 3), (28, 34, 36), dtype=np.uint8)
        x = 15 + index
        cv2.circle(frame, (min(x, 165), 150), 18, (120, 190, 170), -1)
        writer.write(frame)
    writer.release()


def _shot(tmp_path: Path) -> FlowShotSpec:
    for name in ("start.png", "end.png"):
        (tmp_path / name).write_bytes(b"plate")
    return FlowShotSpec(
        id="flow-test",
        start_ms=1000,
        end_ms=3000,
        editorial_role="physical-risk-metaphor",
        prompt=(
            "A balanced physical mechanism moves in one shot. "
            "No text, no UI, no code, no chart, no document."
        ),
        mode="i2v",
        model="veo-lite",
        input_plates=[
            str(tmp_path / "start.png"),
            str(tmp_path / "end.png"),
        ],
        requested_content=["physical-metaphor"],
        constraints=["No readable text", "Single shot"],
    )


def test_candidate_commands_strip_audio_and_lock_delivery_format(
    tmp_path: Path,
) -> None:
    proxy = build_candidate_proxy_command(
        executable=Path("ffmpeg.exe"),
        source=tmp_path / "raw.mp4",
        output=tmp_path / "proxy.mp4",
    )
    assert "-an" in proxy
    assert "1080:1920" in " ".join(proxy)
    assert proxy[proxy.index("-r") + 1] == "30"
    assert proxy[proxy.index("-pix_fmt") + 1] == "yuv420p"

    accepted = build_accepted_clip_command(
        executable=Path("ffmpeg.exe"),
        source=tmp_path / "proxy.mp4",
        output=tmp_path / "accepted.mp4",
        start_ms=700,
        end_ms=2200,
        speed=1,
    )
    assert accepted[accepted.index("-ss") + 1] == "0.700"
    assert accepted[accepted.index("-t") + 1] == "1.500"
    assert "-an" in accepted


def test_selected_candidate_command_applies_window_and_crop_before_scaling(
    tmp_path: Path,
) -> None:
    command = build_selected_candidate_proxy_command(
        executable=Path("ffmpeg.exe"),
        source=tmp_path / "proxy.mp4",
        output=tmp_path / "selection.mp4",
        start_ms=3350,
        end_ms=5550,
        speed=1,
        crop=CropSpec(x=0, y=0, width=1, height=0.82),
    )

    assert command[command.index("-ss") + 1] == "3.350"
    assert command[command.index("-t") + 1] == "2.200"
    filters = command[command.index("-vf") + 1]
    assert "crop=iw*1:ih*0.82:iw*0:ih*0" in filters
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in filters
    assert filters.index("crop=iw*1") < filters.index("scale=1080:1920")
    assert "-an" in command


def test_candidate_gate_evaluation_blocks_corruption_text_and_internal_cuts() -> None:
    clean = evaluate_candidate_metrics(
        {
            "decoded_frames": 120,
            "duration_ms": 4000,
            "max_black_run_frames": 0,
            "max_frozen_run_frames": 2,
            "internal_cut_count": 0,
            "unsafe_border_ratio": 0.01,
            "ocr_token_count": 0,
        },
        fps=30,
    )
    assert all(clean.model_dump().values())

    dirty = evaluate_candidate_metrics(
        {
            "decoded_frames": 120,
            "duration_ms": 4000,
            "max_black_run_frames": 20,
            "max_frozen_run_frames": 40,
            "internal_cut_count": 3,
            "unsafe_border_ratio": 0.35,
            "ocr_token_count": 4,
        },
        fps=30,
    )
    assert dirty.no_black_sequence is False
    assert dirty.no_frozen_sequence is False
    assert dirty.single_continuous_shot is False
    assert dirty.safe_framing is False
    assert dirty.no_generated_text is False


def test_candidate_gate_rejects_even_one_generated_text_token() -> None:
    gates = evaluate_candidate_metrics(
        {
            "decoded_frames": 120,
            "duration_ms": 4000,
            "max_black_run_frames": 0,
            "max_frozen_run_frames": 2,
            "internal_cut_count": 0,
            "unsafe_border_ratio": 0.01,
            "ocr_token_count": 1,
        },
        fps=30,
    )

    assert gates.no_generated_text is False


def test_candidate_ocr_ignores_short_shape_hallucinations_but_keeps_watermarks():
    shape_tokens = [
        {"frame": 19, "text": "SS", "left": 462, "top": 634},
        {"frame": 20, "text": "SS", "left": 433, "top": 657},
        {"frame": 48, "text": "OF", "left": 180, "top": 165},
        {"frame": 39, "text": "Wie", "left": 479, "top": 702},
        {"frame": 40, "text": "Wie", "left": 479, "top": 703},
    ]
    watermark = {
        "frame": 2,
        "text": "Veo",
        "left": 1024,
        "top": 1882,
    }

    assert _material_ocr_tokens(shape_tokens) == []
    assert _material_ocr_tokens([*shape_tokens, watermark]) == [watermark]


def test_candidate_gate_uses_material_text_count_when_available() -> None:
    gates = evaluate_candidate_metrics(
        {
            "decoded_frames": 66,
            "duration_ms": 2200,
            "max_black_run_frames": 0,
            "max_frozen_run_frames": 1,
            "internal_cut_count": 0,
            "unsafe_border_ratio": 0,
            "ocr_token_count": 9,
            "generated_text_token_count": 0,
        },
        fps=30,
        duration_bounds_ms=(700, 2200),
    )

    assert gates.no_generated_text is True


def test_selected_candidate_gate_accepts_editorial_window_duration() -> None:
    gates = evaluate_candidate_metrics(
        {
            "decoded_frames": 54,
            "duration_ms": 1800,
            "max_black_run_frames": 0,
            "max_frozen_run_frames": 2,
            "internal_cut_count": 0,
            "unsafe_border_ratio": 0.01,
            "ocr_token_count": 0,
        },
        fps=30,
        duration_bounds_ms=(700, 2200),
    )

    assert all(gates.model_dump().values())


def test_prepare_candidate_inspects_every_frame_and_creates_eight_frame_sheet(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw.mp4"
    _write_motion_video(raw)
    shot = _shot(tmp_path)
    attempt = FlowGenerationAttempt(
        attempt=1,
        command=["uv", "run", "gflow"],
        project_id="project",
        media_id="media",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        result_json={"status": "ok"},
        untouched_path=str(raw),
        checksum_sha256="a" * 64,
    )

    result = prepare_flow_candidate(
        output_dir=tmp_path / "production",
        shot=shot,
        attempt=attempt,
        candidate_path=raw,
        tesseract_executable=None,
    )

    assert Path(result["proxy_path"]).is_file()
    assert Path(result["contact_sheet_path"]).is_file()
    assert result["metrics"]["decoded_frames"] == 90
    sheet = cv2.imread(result["contact_sheet_path"])
    assert sheet is not None
    assert sheet.shape[1] > sheet.shape[0]

    direct = inspect_candidate_frames(
        Path(result["proxy_path"]),
        tesseract_executable=None,
    )
    assert direct["decoded_frames"] == result["metrics"]["decoded_frames"]


def test_prepare_selection_reviews_only_the_selected_crop_and_window(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw.mp4"
    _write_motion_video(raw)
    shot = _shot(tmp_path)
    attempt = FlowGenerationAttempt(
        attempt=1,
        command=["uv", "run", "gflow"],
        project_id="project",
        media_id="media",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        result_json={"status": "ok"},
        untouched_path=str(raw),
        checksum_sha256="a" * 64,
    )

    report = prepare_flow_candidate_selection(
        output_dir=tmp_path / "production",
        shot=shot,
        attempt=attempt,
        proxy_path=raw,
        start_ms=700,
        end_ms=2200,
        crop=CropSpec(x=0, y=0, width=1, height=0.82),
        tesseract_executable=None,
    )

    assert report["selection"]["start_ms"] == 700
    assert report["selection"]["end_ms"] == 2200
    assert report["selection"]["crop"]["height"] == 0.82
    assert report["metrics"]["duration_ms"] == 1500
    assert report["metrics"]["ocr_requested_frame_count"] == (
        report["metrics"]["decoded_frames"]
    )
    assert report["metrics"]["ocr_frame_count"] == 0
    assert report["hard_gate_passed"] is True
    assert Path(report["proxy_path"]).is_file()
    assert Path(report["contact_sheet_path"]).is_file()
    assert Path(report["report_path"]).is_file()
