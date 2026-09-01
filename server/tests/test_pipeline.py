from pathlib import Path
import json

import cv2
import numpy as np
import pytest

from app.editor.ffmpeg import (
    LoudnessMeasurement,
    build_dialogue_extract_command,
    build_loudness_measure_command,
    build_master_command,
    build_render_command,
    verify_render,
)
from app.editor import assets as assets_module
from app.editor import ffmpeg as ffmpeg_module
from app.editor import pipeline as pipeline_module
from app.editor.pipeline import (
    _calculate_visual_coverage,
    _repair_plan_for_qc,
    run_pipeline,
)
from app.editor.planning import build_edit_plan
from app.editor.qc import evaluate_qc
from app.models import (
    AssetRef,
    QCMeasurements,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)


def write_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (180, 320),
    )
    assert writer.isOpened()
    for index in range(20):
        frame = np.full((320, 180, 3), 20 + index, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_build_render_command_uses_safe_h264_aac_arguments(tmp_path: Path) -> None:
    source = tmp_path / "raw video;not-a-command.mp4"
    output = tmp_path / "edited.mp4"

    command = build_render_command(
        executable=Path("ffmpeg"),
        source=source,
        output=output,
        subtitle_filename="captions.ass",
        width=1080,
        height=1920,
    )

    assert command[0] == "ffmpeg"
    assert str(source) in command
    assert str(output) in command
    assert "libx264" in command
    assert "aac" in command
    assert "48000" in command
    assert "+faststart" in command
    assert any("subtitles=captions.ass" in value for value in command)
    assert any("loudnorm=I=-14:TP=-1:LRA=7" in value for value in command)
    assert all("shell=True" not in value for value in command)


def test_build_master_command_targets_reference_loudness_and_color(
    tmp_path: Path,
) -> None:
    rendered = tmp_path / "rendered.mp4"
    output = tmp_path / "final.mp4"

    command = build_master_command(
        executable=Path("ffmpeg"),
        rendered=rendered,
        output=output,
    )

    assert command[0] == "ffmpeg"
    assert str(rendered) in command
    assert str(output) in command
    assert "libx264" in command
    assert "aac" in command
    assert any("loudnorm=I=-14.2:TP=-1.2:LRA=5" in value for value in command)
    assert any("deesser" in value for value in command)
    video_filter = command[command.index("-vf") + 1]
    assert "eq=contrast=" in video_filter
    assert "scale=in_range=auto:out_range=tv" in video_filter
    assert "format=yuv420p" in video_filter
    assert command[command.index("-color_range") + 1] == "tv"


def test_reference_mastering_does_not_reprocess_the_completed_mix(
    tmp_path: Path,
) -> None:
    command = build_master_command(
        executable=Path("ffmpeg"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "final.mp4",
        clean_completed_mix=False,
    )

    audio_filter = command[command.index("-af") + 1]
    assert "loudnorm=I=-14.2:TP=-1.2:LRA=5" in audio_filter
    assert "afftdn" not in audio_filter
    assert "deesser" not in audio_filter
    assert "acompressor" not in audio_filter


def test_dialogue_extract_command_processes_voice_alone_at_48khz(
    tmp_path: Path,
) -> None:
    command = build_dialogue_extract_command(
        executable=Path("ffmpeg"),
        source=tmp_path / "source.mp4",
        output=tmp_path / "dialogue-processed.wav",
        processed=True,
    )

    assert command[command.index("-ar") + 1] == "48000"
    assert command[command.index("-c:a") + 1] == "pcm_s24le"
    assert "-vn" in command
    audio_filter = command[command.index("-af") + 1]
    assert "afftdn" in audio_filter
    assert "deesser" in audio_filter
    assert "acompressor" in audio_filter

    raw_command = build_dialogue_extract_command(
        executable=Path("ffmpeg"),
        source=tmp_path / "source.mp4",
        output=tmp_path / "dialogue-original.wav",
        processed=False,
    )
    assert "-af" not in raw_command


def test_build_master_command_uses_measured_two_pass_loudness_values(
    tmp_path: Path,
) -> None:
    command = build_master_command(
        executable=Path("ffmpeg"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "final.mp4",
        loudness_measurement=LoudnessMeasurement(
            input_i=-18.2,
            input_tp=-2.1,
            input_lra=3.4,
            input_thresh=-28.5,
            target_offset=0.1,
        ),
    )

    audio_filter = next(value for value in command if "loudnorm=" in value)
    assert "measured_I=-18.2" in audio_filter
    assert "measured_TP=-2.1" in audio_filter
    assert "measured_LRA=3.4" in audio_filter
    assert "measured_thresh=-28.5" in audio_filter
    assert "offset=0.1" in audio_filter


def test_build_master_command_trims_codec_padding_to_plan_boundary(
    tmp_path: Path,
) -> None:
    command = build_master_command(
        executable=Path("ffmpeg"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "final.mp4",
        duration_seconds=41.4,
    )

    assert command[command.index("-t") + 1] == "41.400"


def test_loudness_measurement_uses_the_same_cleanup_chain_as_mastering(
    tmp_path: Path,
) -> None:
    command = build_loudness_measure_command(
        executable=Path("ffmpeg"),
        rendered=tmp_path / "rendered.mp4",
    )

    audio_filter = command[command.index("-af") + 1]
    assert "highpass=f=75" in audio_filter
    assert "afftdn=nf=-28" in audio_filter
    assert "deesser" in audio_filter
    assert "acompressor" in audio_filter
    assert "alimiter" in audio_filter
    assert "loudnorm=I=-14.2:TP=-1.2:LRA=5" in audio_filter


def test_reference_loudness_measurement_skips_completed_mix_cleanup(
    tmp_path: Path,
) -> None:
    command = build_loudness_measure_command(
        executable=Path("ffmpeg"),
        rendered=tmp_path / "rendered.mp4",
        clean_completed_mix=False,
    )

    audio_filter = command[command.index("-af") + 1]
    assert audio_filter == "loudnorm=I=-14.2:TP=-1.2:LRA=5:print_format=json"


def test_verify_render_accepts_decodable_vertical_video(tmp_path: Path) -> None:
    output = tmp_path / "output.mp4"
    write_video(output)

    metadata = verify_render(output)

    assert metadata.width == 180
    assert metadata.height == 320
    assert metadata.duration_seconds > 1.5


def test_verify_render_rejects_missing_output(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp4"

    try:
        verify_render(missing)
    except ValueError as error:
        assert "output" in str(error).lower()
    else:
        raise AssertionError("verify_render should reject a missing file")


def test_verify_render_rejects_unexpected_output_spec(tmp_path: Path) -> None:
    output = tmp_path / "output.mp4"
    write_video(output)

    with pytest.raises(ValueError, match="1080x1920"):
        verify_render(
            output,
            expected_width=1080,
            expected_height=1920,
            expected_fps=30,
        )


def test_verify_render_rejects_non_h264_or_missing_aac(tmp_path: Path) -> None:
    output = tmp_path / "output.mp4"
    write_video(output)

    with pytest.raises(ValueError, match="H.264/AAC"):
        verify_render(output, require_h264_aac=True)


def test_verify_render_rejects_full_range_yuvj420p(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "output.mp4"
    write_video(output)
    monkeypatch.setattr(
        ffmpeg_module,
        "probe_video_pixel_format",
        lambda _path: ("yuvj420p", "pc"),
        raising=False,
    )

    with pytest.raises(ValueError, match="yuv420p"):
        verify_render(output, require_yuv420p=True)


def test_run_pipeline_writes_edit_plan_qc_manifest_and_verified_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    output = tmp_path / "edited.mp4"
    write_video(source)
    stages: list[str] = []
    received_commands: list[list[str]] = []
    rendered_path = tmp_path / "rendered.mp4"

    def transcriber(_: Path) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                start=0,
                end=1,
                text="Expert Advisor",
                words=[
                    TranscriptWord(start=0, end=0.5, text="Expert"),
                    TranscriptWord(start=0.5, end=1, text="Advisor"),
                ],
            )
        ]

    def renderer_runner(**kwargs) -> None:
        assert kwargs["plan"].caption_pages
        assert kwargs["plan"].reframing
        rendered_path.write_bytes(source.read_bytes())

    def runner(command: list[str], cwd: Path) -> None:
        received_commands.append(command)
        Path(command[-1]).write_bytes(rendered_path.read_bytes())

    result = run_pipeline(
        source=source,
        output=output,
        work_dir=tmp_path,
        transcriber=transcriber,
        renderer_runner=renderer_runner,
        command_runner=runner,
        qc_measurement_provider=lambda **_kwargs: QCMeasurements(
            integrated_lufs=-14.2,
            true_peak_dbtp=-1.2,
            longest_silence_ms=80,
            black_frame_ratio=0,
            freeze_frame_ratio=0,
            cuts_per_minute=40,
            median_shot_ms=1400,
            cut_onset_percent=80,
            caption_overflow_count=0,
            meaningful_visual_coverage=0.65,
        ),
        progress=lambda stage, _percent: stages.append(stage),
    )

    assert result.caption_count == 1
    assert result.output_metadata.height == 320
    assert result.qc_passed is True
    assert result.style_score >= 80
    assert (tmp_path / "edit-plan.json").is_file()
    assert (tmp_path / "captions.json").is_file()
    assert (tmp_path / "qc-report.json").is_file()
    assert (tmp_path / "manifest.json").is_file()
    assert not rendered_path.exists()
    assert received_commands
    assert stages == [
        "analyzing",
        "transcribing",
        "cleaning",
        "planning",
        "sourcing",
        "rendering",
        "mastering",
        "quality_control",
        "verifying",
        "completed",
    ]


def test_run_pipeline_repairs_and_rerenders_failed_qc_up_to_two_times(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    output = tmp_path / "edited.mp4"
    rendered = tmp_path / "rendered.mp4"
    write_video(source)
    render_count = 0
    measure_count = 0
    rendered_plans = []

    def transcriber(_: Path) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                start=0,
                end=1,
                text="AI works",
                words=[
                    TranscriptWord(start=0, end=0.5, text="AI"),
                    TranscriptWord(start=0.5, end=1, text="works"),
                ],
            )
        ]

    def renderer_runner(**kwargs) -> None:
        nonlocal render_count
        render_count += 1
        rendered_plans.append(kwargs["plan"])
        rendered.write_bytes(source.read_bytes())

    def command_runner(command: list[str], _cwd: Path) -> None:
        Path(command[-1]).write_bytes(rendered.read_bytes())

    def measure(**_kwargs) -> QCMeasurements:
        nonlocal measure_count
        measure_count += 1
        bad = measure_count < 3
        return QCMeasurements(
            integrated_lufs=-18 if bad else -14.2,
            true_peak_dbtp=0 if bad else -1.2,
            longest_silence_ms=500 if bad else 80,
            black_frame_ratio=0.1 if bad else 0,
            freeze_frame_ratio=0,
            cuts_per_minute=10 if bad else 40,
            median_shot_ms=2500 if bad else 1400,
            cut_onset_percent=80,
            caption_overflow_count=0,
            meaningful_visual_coverage=0.65,
        )

    result = run_pipeline(
        source=source,
        output=output,
        work_dir=tmp_path,
        transcriber=transcriber,
        renderer_runner=renderer_runner,
        command_runner=command_runner,
        qc_measurement_provider=measure,
    )

    report = json.loads((tmp_path / "qc-report.json").read_text(encoding="utf-8"))
    assert render_count == 3
    assert measure_count == 3
    assert len(rendered_plans[1].scenes) > len(rendered_plans[0].scenes)
    assert report["repair_attempts"] == 2
    assert result.qc_passed is True


def test_repair_plan_reduces_visual_events_when_pacing_is_too_fast() -> None:
    transcript = [
        TranscriptSegment(
            start=0,
            end=3.5,
            text="This AI product changes how the app works today",
            words=[
                TranscriptWord(
                    start=index * 0.35,
                    end=index * 0.35 + 0.3,
                    text=word,
                    confidence=0.95,
                )
                for index, word in enumerate(
                    "This AI product changes how the app works today".split()
                )
            ],
        )
    ]
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=720,
            height=1280,
            fps=30,
            frame_count=120,
            duration_seconds=4,
        ),
        transcript=transcript,
    )
    report = evaluate_qc(
        plan,
        QCMeasurements(
            integrated_lufs=-14.2,
            true_peak_dbtp=-1.2,
            longest_silence_ms=80,
            black_frame_ratio=0,
            freeze_frame_ratio=0,
            cuts_per_minute=120,
            median_shot_ms=400,
            cut_onset_percent=80,
            caption_overflow_count=0,
            meaningful_visual_coverage=0.65,
        ),
    )

    repaired = _repair_plan_for_qc(plan, report)

    assert all(graphic.start_ms == 0 for graphic in repaired.graphics)
    target_events = max(
        1,
        round(repaired.duration_ms / 60_000 * 40),
    )
    repaired_events = {
        segment.output_start_ms for segment in repaired.timeline[1:]
    } | {scene.start_ms for scene in repaired.scenes[1:]} | {
        graphic.start_ms for graphic in repaired.graphics[1:]
    }
    assert len(repaired_events) <= target_events


def test_decorative_callouts_do_not_count_as_meaningful_visual_coverage() -> None:
    transcript = [
        TranscriptSegment(
            start=0,
            end=2,
            text="AI rules explain the system",
            words=[
                TranscriptWord(
                    start=index * 0.35,
                    end=index * 0.35 + 0.3,
                    text=word,
                    confidence=0.95,
                )
                for index, word in enumerate(
                    "AI rules explain the system".split()
                )
            ],
        )
    ]
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=720,
            height=1280,
            fps=30,
            frame_count=90,
            duration_seconds=3,
        ),
        transcript=transcript,
    )
    decorative_only = plan.model_copy(
        update={
            "assets": [],
            "graphics": [
                plan.graphics[0].model_copy(
                    update={
                        "kind": "callout",
                        "start_ms": 0,
                        "end_ms": plan.duration_ms,
                    }
                )
            ],
        }
    )

    assert _calculate_visual_coverage(decorative_only) == 0


def test_unreferenced_editorial_visuals_do_not_count_as_coverage() -> None:
    words = [
        TranscriptWord(
            start=index * 0.35,
            end=index * 0.35 + 0.3,
            text=word,
            confidence=0.95,
        )
        for index, word in enumerate(
            (
                "Forex trading robot software follows rules automatically "
                "and controls risk with an Expert Advisor"
            ).split()
        )
    ]
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=180,
            duration_seconds=6,
        ),
        transcript=[
            TranscriptSegment(
                start=words[0].start,
                end=words[-1].end,
                text=" ".join(word.text for word in words),
                words=words,
            )
        ],
    )
    presenter_only = plan.model_copy(
        update={
            "scenes": [
                scene.model_copy(
                    update={"layout": "presenter", "visual_id": None}
                )
                for scene in plan.scenes
            ],
            "graphics": [],
            "assets": [],
        }
    )

    assert plan.editorial_visuals
    assert _calculate_visual_coverage(presenter_only) == 0


def test_attach_internet_assets_schedules_real_media_on_body_scenes(
    tmp_path: Path,
) -> None:
    transcript = [
        TranscriptSegment(
            start=0,
            end=8,
            text=(
                "Forex trading robot follows rules and uses risk controls "
                "during an automated trading championship"
            ),
            words=[
                TranscriptWord(
                    start=index * 0.45,
                    end=index * 0.45 + 0.35,
                    text=word,
                    confidence=0.95,
                )
                for index, word in enumerate(
                    (
                        "Forex trading robot follows rules and uses risk "
                        "controls during an automated trading championship"
                    ).split()
                )
            ],
        )
    ]
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=300,
            duration_seconds=10,
        ),
        transcript=transcript,
    )
    image = tmp_path / "downloaded.jpg"
    image.write_bytes(b"image")
    received_requests: list[object] = []

    def discoverer(requests, _destination_dir):
        received_requests.extend(requests)
        request = requests[0]
        return [
            AssetRef(
                id="internet-asset-1",
                kind="image",
                path=str(image),
                keywords=request.keywords,
                provenance="internet:wikimedia-commons",
                license="CC BY-SA 4.0",
                provider="wikimedia-commons",
                remote_id="10",
                creator="Creator",
                source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
                license_url=(
                    "https://creativecommons.org/licenses/by-sa/4.0/"
                ),
                search_query=request.query,
                start_ms=request.start_ms,
                end_ms=request.end_ms,
            )
        ]

    assert hasattr(assets_module, "RemoteAssetRequest")
    updated = pipeline_module._attach_internet_assets(
        plan,
        tmp_path,
        discoverer=discoverer,
    )

    assert received_requests
    assert all("forex" in request.keywords for request in received_requests)
    assert updated.assets[0].provenance.startswith("internet:")
    scheduled_scene = next(
        scene
        for scene in updated.scenes
        if scene.start_ms == updated.assets[0].start_ms
    )
    assert scheduled_scene.layout in {"asset-full", "presenter-pip"}
