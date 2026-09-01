from __future__ import annotations

from pathlib import Path
import json
import shutil
from uuid import uuid4

import pytest

from ffmpeg_plan_renderer import (
    ass_time,
    build_caption_burn_command,
    build_segment_command,
    build_ass_script,
    js_frame,
    layer_video_filter,
    render_plan_with_ffmpeg,
    resolve_public_asset,
    segment_frame_count,
    write_concat_manifest,
)


@pytest.fixture
def workspace_tmp() -> Path:
    parent = (Path(__file__).parent / ".tmp_ffmpeg_plan_renderer").resolve()
    root = parent / uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        resolved = root.resolve()
        if resolved.is_relative_to(parent):
            shutil.rmtree(resolved, ignore_errors=True)


def test_js_frame_matches_remotion_boundary_rounding() -> None:
    assert js_frame(0, 30) == 0
    assert js_frame(50_550, 30) == 1_517
    assert js_frame(50_680, 30) == 1_520


def test_ass_time_uses_centisecond_timestamps() -> None:
    assert ass_time(0) == "0:00:00.00"
    assert ass_time(1_234) == "0:00:01.23"
    assert ass_time(61_990) == "0:01:01.99"


def test_layer_filter_compiles_crop_zoom_pan_and_color() -> None:
    layer = {
        "crop": {"x": 0.212, "y": 0.0, "width": 0.316, "height": 1.0},
        "transform_keyframes": [
            {"at_ms": 0, "x": 23, "y": 0, "scale": 1.08, "rotate_deg": 0},
            {
                "at_ms": 1_400,
                "x": 23,
                "y": -4,
                "scale": 1.098,
                "rotate_deg": 0,
            },
        ],
        "effect_keyframes": [
            {
                "at_ms": 0,
                "brightness": 0.96,
                "contrast": 1.05,
                "saturation": 0.88,
                "blur_px": 0,
            }
        ],
    }

    compiled = layer_video_filter(layer, frame_count=42, fps=30)

    assert "crop=iw*0.316000:ih*1.000000:iw*0.212000:ih*0.000000" in compiled
    assert "zoompan=" in compiled
    assert "1.080000" in compiled
    assert "1.098000" in compiled
    assert "eq=brightness=-0.040000:contrast=1.050000:saturation=0.880000" in compiled
    assert "fps=30" in compiled


def test_ass_script_contains_reference_caption_families_and_hook() -> None:
    plan = {
        "caption_pages": [
            {
                "start_ms": 0,
                "end_ms": 900,
                "tokens": [{"text": "Do"}, {"text": "you"}, {"text": "know,"}],
                "family": "outlined-demo",
                "anchor": "center-69",
                "transition": "hard-cut",
                "max_width": 760,
            },
            {
                "start_ms": 900,
                "end_ms": 1_500,
                "tokens": [{"text": "LOT"}, {"text": "SIZE"}],
                "family": "technical-mono",
                "anchor": "center-74",
                "transition": "hard-cut",
                "max_width": 500,
            },
        ],
        "kinetic_text_cues": [
            {
                "id": "hook",
                "start_ms": 0,
                "end_ms": 2_000,
                "text": "LOT SIZE = QUANTITY",
                "family": "serif-hook",
                "x": 540,
                "y": 880,
                "max_width": 900,
                "align": "center",
                "animation": "hard-cut",
                "rotation_deg": 0,
                "z_index": 60,
            }
        ],
        "visual_layers": [
            {
                "start_ms": 2_000,
                "end_ms": 3_000,
                "illustrative_label": True,
            }
        ],
    }

    script = build_ass_script(plan)

    assert "Style: TechnicalMono" in script
    assert "Style: OutlinedDemo" in script
    assert "Style: SerifHook" in script
    assert "DO YOU KNOW," in script
    assert "LOT SIZE" in script
    assert "LOT SIZE = QUANTITY" in script
    assert "ILLUSTRATIVE" in script
    assert "\\pos(540,1325)" in script
    assert "\\pos(540,1421)" in script


def test_resolve_public_asset_rejects_path_traversal() -> None:
    public_dir = Path(__file__).parent / "fixtures" / "public"

    with pytest.raises(ValueError, match="outside renderer public directory"):
        resolve_public_asset(public_dir, "../secret.mp4")


def test_segment_frame_count_uses_global_boundaries() -> None:
    layer = {"start_ms": 1_400, "end_ms": 2_800}

    assert segment_frame_count(layer, fps=30) == 42


def test_segment_command_handles_video_trim_and_exact_frames(
    workspace_tmp: Path,
) -> None:
    public_dir = workspace_tmp / "public"
    asset = public_dir / "assets" / "clip.mp4"
    asset.parent.mkdir(parents=True)
    asset.touch()
    output = workspace_tmp / "segment.mp4"
    layer = {
        "start_ms": 0,
        "end_ms": 1_400,
        "source_start_ms": 300,
        "source_end_ms": 1_700,
        "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        "transform_keyframes": [
            {"at_ms": 0, "x": 0, "y": 0, "scale": 1, "rotate_deg": 0},
            {
                "at_ms": 1_400,
                "x": 0,
                "y": -4,
                "scale": 1.018,
                "rotate_deg": 0,
            },
        ],
        "effect_keyframes": [
            {
                "at_ms": 0,
                "brightness": 1,
                "contrast": 1,
                "saturation": 1,
                "blur_px": 0,
            }
        ],
    }

    command = build_segment_command(
        ffmpeg=Path("ffmpeg.exe"),
        asset={"kind": "video", "path": "assets/clip.mp4"},
        layer=layer,
        public_dir=public_dir,
        output=output,
        fps=30,
    )

    assert command[:4] == ["ffmpeg.exe", "-y", "-v", "error"]
    assert "-ss" in command
    assert command[command.index("-ss") + 1] == "0.300000"
    assert command[command.index("-frames:v") + 1] == "42"
    assert "-an" in command
    assert command[-1] == str(output)


def test_segment_command_loops_still_images(workspace_tmp: Path) -> None:
    public_dir = workspace_tmp / "public"
    asset = public_dir / "assets" / "graphic.png"
    asset.parent.mkdir(parents=True)
    asset.touch()
    output = workspace_tmp / "segment.mp4"
    layer = {
        "start_ms": 0,
        "end_ms": 1_000,
        "source_start_ms": None,
        "source_end_ms": None,
        "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        "transform_keyframes": [
            {"at_ms": 0, "x": 0, "y": 0, "scale": 1, "rotate_deg": 0},
            {
                "at_ms": 1_000,
                "x": 0,
                "y": -4,
                "scale": 1.018,
                "rotate_deg": 0,
            },
        ],
        "effect_keyframes": [
            {
                "at_ms": 0,
                "brightness": 1,
                "contrast": 1,
                "saturation": 1,
                "blur_px": 0,
            }
        ],
    }

    command = build_segment_command(
        ffmpeg=Path("ffmpeg.exe"),
        asset={"kind": "image", "path": "assets/graphic.png"},
        layer=layer,
        public_dir=public_dir,
        output=output,
        fps=30,
    )

    assert "-loop" in command
    assert command[command.index("-loop") + 1] == "1"
    assert "-ss" not in command
    assert command[command.index("-frames:v") + 1] == "30"


def test_concat_manifest_uses_absolute_escaped_paths(
    workspace_tmp: Path,
) -> None:
    manifest = workspace_tmp / "concat.txt"
    first = workspace_tmp / "shot-01.mp4"
    second = workspace_tmp / "shot-02.mp4"

    write_concat_manifest([first, second], manifest)

    text = manifest.read_text(encoding="utf-8")
    assert f"file '{first.resolve().as_posix()}'" in text
    assert f"file '{second.resolve().as_posix()}'" in text


def test_caption_burn_command_uses_ass_and_no_audio(
    workspace_tmp: Path,
) -> None:
    source = workspace_tmp / "base.mp4"
    ass = workspace_tmp / "captions.ass"
    output = workspace_tmp / "silent.mp4"

    command = build_caption_burn_command(
        ffmpeg=Path("ffmpeg.exe"),
        source=source,
        ass_path=ass,
        output=output,
    )

    assert "-vf" in command
    assert "ass=" in command[command.index("-vf") + 1]
    assert "fontsdir=" in command[command.index("-vf") + 1]
    assert "-an" in command
    assert command[-1] == str(output)


def test_render_plan_runs_each_layer_then_concat_and_caption_burn(
    workspace_tmp: Path,
) -> None:
    public_dir = workspace_tmp / "public"
    assets_dir = public_dir / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "first.png").touch()
    (assets_dir / "second.png").touch()
    plan_path = workspace_tmp / "render-plan.json"
    output = workspace_tmp / "rendered-silent.mp4"

    def layer(
        identifier: str,
        start_ms: int,
        end_ms: int,
        asset_id: str,
    ) -> dict:
        duration = end_ms - start_ms
        return {
            "id": identifier,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "asset_id": asset_id,
            "source_start_ms": None,
            "source_end_ms": None,
            "crop": {
                "x": 0.0,
                "y": 0.0,
                "width": 1.0,
                "height": 1.0,
            },
            "transform_keyframes": [
                {
                    "at_ms": 0,
                    "x": 0,
                    "y": 0,
                    "scale": 1,
                    "rotate_deg": 0,
                },
                {
                    "at_ms": duration,
                    "x": 0,
                    "y": -4,
                    "scale": 1.018,
                    "rotate_deg": 0,
                },
            ],
            "effect_keyframes": [
                {
                    "at_ms": 0,
                    "brightness": 1,
                    "contrast": 1,
                    "saturation": 1,
                    "blur_px": 0,
                }
            ],
            "illustrative_label": False,
        }

    plan = {
        "duration_ms": 2_000,
        "assets": [
            {"id": "first", "kind": "image", "path": "assets/first.png"},
            {"id": "second", "kind": "image", "path": "assets/second.png"},
        ],
        "visual_layers": [
            layer("layer-1", 0, 1_000, "first"),
            layer("layer-2", 1_000, 2_000, "second"),
        ],
        "caption_pages": [],
        "kinetic_text_cues": [],
    }
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        commands.append(command)
        destination = Path(command[-1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"rendered")

    result = render_plan_with_ffmpeg(
        plan_path=plan_path,
        public_dir=public_dir,
        output=output,
        ffmpeg=Path("ffmpeg.exe"),
        runner=fake_runner,
        keep_cache=True,
    )

    assert result == output
    assert output.read_bytes() == b"rendered"
    assert len(commands) == 4
    assert commands[0][commands[0].index("-frames:v") + 1] == "30"
    assert commands[1][commands[1].index("-frames:v") + 1] == "30"
    assert commands[2][commands[2].index("-f") + 1] == "concat"
    assert "ass=" in commands[3][commands[3].index("-vf") + 1]
    backend = json.loads(
        (workspace_tmp / "render-backend.json").read_text(encoding="utf-8")
    )
    assert backend["backend"] == "ffmpeg-plan"
    assert backend["layer_count"] == 2


def test_render_plan_rebuilds_a_truncated_cached_segment(
    workspace_tmp: Path,
) -> None:
    public_dir = workspace_tmp / "public"
    assets_dir = public_dir / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "still.png").touch()
    plan_path = workspace_tmp / "render-plan.json"
    output = workspace_tmp / "rendered-silent.mp4"
    plan = {
        "duration_ms": 1_000,
        "assets": [
            {"id": "still", "kind": "image", "path": "assets/still.png"}
        ],
        "visual_layers": [
            {
                "id": "layer-1",
                "start_ms": 0,
                "end_ms": 1_000,
                "asset_id": "still",
                "source_start_ms": None,
                "source_end_ms": None,
                "crop": {
                    "x": 0.0,
                    "y": 0.0,
                    "width": 1.0,
                    "height": 1.0,
                },
                "transform_keyframes": [
                    {
                        "at_ms": 0,
                        "x": 0,
                        "y": 0,
                        "scale": 1,
                        "rotate_deg": 0,
                    },
                    {
                        "at_ms": 1_000,
                        "x": 0,
                        "y": 0,
                        "scale": 1,
                        "rotate_deg": 0,
                    },
                ],
                "effect_keyframes": [
                    {
                        "at_ms": 0,
                        "brightness": 1,
                        "contrast": 1,
                        "saturation": 1,
                        "blur_px": 0,
                    }
                ],
                "illustrative_label": False,
            }
        ],
        "caption_pages": [],
        "kinetic_text_cues": [],
    }
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_runner(command: list[str]) -> None:
        commands.append(command)
        destination = Path(command[-1])
        if "-frames:v" in command:
            assert destination.suffix == ".mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"complete-render")

    render_plan_with_ffmpeg(
        plan_path=plan_path,
        public_dir=public_dir,
        output=output,
        ffmpeg=Path("ffmpeg.exe"),
        runner=fake_runner,
        keep_cache=True,
    )
    segment = next(
        (workspace_tmp / "ffmpeg-render-cache").glob("segment-*.mp4")
    )
    segment.write_bytes(b"partial")
    commands.clear()

    render_plan_with_ffmpeg(
        plan_path=plan_path,
        public_dir=public_dir,
        output=output,
        ffmpeg=Path("ffmpeg.exe"),
        runner=fake_runner,
        keep_cache=True,
    )

    assert any("-frames:v" in command for command in commands)
    assert segment.read_bytes() == b"complete-render"
