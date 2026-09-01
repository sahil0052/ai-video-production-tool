from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.editor.analysis import probe_video
from app.models import (
    AssetRef,
    AudioPlan,
    EvidenceItem,
    OutputSpec,
)
from app.production_models import (
    BlueprintLayerSpec,
    EditPlanV2,
    LayerBounds,
    OpacityKeyframe,
    ProductionBlueprint,
    ProductionJobRecord,
    ProductionStateEvent,
    TransformKeyframe,
)


EXACT_REFERENCE_DURATION_MS = 34_933
EXACT_REFERENCE_CUTS_MS = [
    2_267,
    5_733,
    9_533,
    11_767,
    14_433,
    18_167,
    19_700,
    22_633,
    23_667,
    25_667,
    27_400,
    30_433,
]
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_V4_EVIDENCE_ROOT = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0806-production-v4"
)
OverlayBuilder = Callable[[Path, Path], dict[str, Path]]


def _transform(
    duration_ms: int,
    *,
    start_scale: float = 1,
    end_scale: float | None = None,
    x: float = 0,
    y: float = 0,
) -> list[TransformKeyframe]:
    return [
        TransformKeyframe(
            at_ms=0,
            x=x,
            y=y,
            scale=start_scale,
        ),
        TransformKeyframe(
            at_ms=duration_ms,
            x=x,
            y=y,
            scale=end_scale if end_scale is not None else start_scale,
        ),
    ]


def _video_layer(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    source_role: str,
    asset_id: str,
    source_start_ms: int,
    source_end_ms: int,
    playback_rate: float,
    start_scale: float = 1,
    end_scale: float | None = None,
    x: float = 0,
    y: float = 0,
    color_filter: str | None = None,
    transform_keyframes: list[TransformKeyframe] | None = None,
    z_index: int = 10,
) -> BlueprintLayerSpec:
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role=source_role,
        kind="video",
        asset_id=asset_id,
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        bounds=LayerBounds(),
        fit="cover",
        transform_keyframes=transform_keyframes
        or _transform(
            end_ms - start_ms,
            start_scale=start_scale,
            end_scale=end_scale,
            x=x,
            y=y,
        ),
        opacity_keyframes=[OpacityKeyframe(at_ms=0, value=1)],
        z_index=z_index,
        muted=True,
        playback_rate=playback_rate,
        color_filter=color_filter,
        reference_role="supporting",
    )


def _overlay_layer(
    *,
    layer_id: str,
    shot_id: str,
    asset_id: str,
    start_ms: int,
    end_ms: int,
    start_scale: float,
    start_y: float = 0,
    entrance_ms: int = 180,
    transform_keyframes: list[TransformKeyframe] | None = None,
    opacity_keyframes: list[OpacityKeyframe] | None = None,
) -> BlueprintLayerSpec:
    duration_ms = end_ms - start_ms
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="deterministic-graphic",
        kind="image",
        asset_id=asset_id,
        bounds=LayerBounds(),
        fit="fill",
        transform_keyframes=transform_keyframes
        or [
            TransformKeyframe(
                at_ms=0,
                y=start_y,
                scale=start_scale,
            ),
            TransformKeyframe(
                at_ms=min(entrance_ms, duration_ms),
                y=0,
                scale=1,
            ),
            TransformKeyframe(
                at_ms=duration_ms,
                y=0,
                scale=1,
            ),
        ],
        opacity_keyframes=opacity_keyframes
        or [
            OpacityKeyframe(at_ms=0, value=0),
            OpacityKeyframe(
                at_ms=min(100, duration_ms),
                value=1,
            ),
        ],
        z_index=100,
        muted=True,
        reference_role="supporting",
    )


def _vignette_layer(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
) -> BlueprintLayerSpec:
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="deterministic-graphic",
        kind="image",
        asset_id="overlay-presenter-vignette",
        bounds=LayerBounds(),
        fit="fill",
        transform_keyframes=[
            TransformKeyframe(at_ms=0, scale=1),
        ],
        opacity_keyframes=[OpacityKeyframe(at_ms=0, value=1)],
        z_index=50,
        muted=True,
        reference_role="supporting",
    )


def build_exact_reference_layers() -> list[BlueprintLayerSpec]:
    layers = [
        _video_layer(
            layer_id="exact-presenter-hook",
            shot_id="exact-shot-01",
            start_ms=0,
            end_ms=2_267,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=167,
            source_end_ms=2_433,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-robot",
            shot_id="exact-shot-02",
            start_ms=2_267,
            end_ms=5_733,
            source_role="licensed-context",
            asset_id="reference-master",
            source_start_ms=2_267,
            source_end_ms=5_733,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-ea",
            shot_id="exact-shot-03",
            start_ms=5_733,
            end_ms=9_533,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=7_233,
            source_end_ms=11_033,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-wrong-punch",
            shot_id="exact-shot-04",
            start_ms=9_533,
            end_ms=10_200,
            source_role="presenter",
            asset_id="reference-master",
            source_start_ms=9_533,
            source_end_ms=10_200,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-wrong",
            shot_id="exact-shot-04",
            start_ms=10_200,
            end_ms=11_767,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=13_133,
            source_end_ms=14_700,
            playback_rate=1,
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1.143),
                TransformKeyframe(at_ms=466, scale=1.166),
                TransformKeyframe(at_ms=1_200, scale=1.202),
                TransformKeyframe(at_ms=1_567, scale=1.218),
            ],
        ),
        _video_layer(
            layer_id="exact-reference-championship",
            shot_id="exact-shot-05",
            start_ms=11_767,
            end_ms=14_433,
            source_role="direct-evidence",
            asset_id="reference-master",
            source_start_ms=11_767,
            source_end_ms=14_433,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-number",
            shot_id="exact-shot-06",
            start_ms=14_433,
            end_ms=18_167,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=17_967,
            source_end_ms=21_700,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-risk-a",
            shot_id="exact-shot-07",
            start_ms=18_167,
            end_ms=18_933,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=21_867,
            source_end_ms=22_633,
            playback_rate=1,
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1),
                TransformKeyframe(at_ms=100, scale=1.056),
                TransformKeyframe(at_ms=167, scale=1.092),
                TransformKeyframe(at_ms=233, scale=1.122),
                TransformKeyframe(at_ms=300, scale=1.142),
                TransformKeyframe(at_ms=400, scale=1.156),
                TransformKeyframe(at_ms=500, scale=1.16),
                TransformKeyframe(at_ms=766, scale=1.16),
            ],
        ),
        _video_layer(
            layer_id="exact-presenter-risk-b",
            shot_id="exact-shot-07",
            start_ms=18_933,
            end_ms=19_700,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=22_900,
            source_end_ms=23_667,
            playback_rate=1,
            start_scale=1.16,
        ),
        _video_layer(
            layer_id="exact-reference-monochrome",
            shot_id="exact-shot-08",
            start_ms=19_700,
            end_ms=22_633,
            source_role="presenter",
            asset_id="reference-master",
            source_start_ms=19_700,
            source_end_ms=22_633,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-flash",
            shot_id="exact-shot-09",
            start_ms=22_633,
            end_ms=23_667,
            source_role="presenter",
            asset_id="reference-master",
            source_start_ms=22_633,
            source_end_ms=23_667,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-trader-emotion",
            shot_id="exact-shot-10",
            start_ms=23_667,
            end_ms=25_667,
            source_role="licensed-context",
            asset_id="reference-master",
            source_start_ms=23_667,
            source_end_ms=25_667,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-trader-risk",
            shot_id="exact-shot-11",
            start_ms=25_667,
            end_ms=27_400,
            source_role="licensed-context",
            asset_id="reference-master",
            source_start_ms=25_667,
            source_end_ms=27_400,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-cta",
            shot_id="exact-shot-12",
            start_ms=27_400,
            end_ms=30_433,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=33_467,
            source_end_ms=36_500,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-reference-ending-flash",
            shot_id="exact-shot-13",
            start_ms=30_433,
            end_ms=30_633,
            source_role="presenter",
            asset_id="reference-master",
            source_start_ms=30_433,
            source_end_ms=30_633,
            playback_rate=1,
        ),
        _video_layer(
            layer_id="exact-presenter-ending",
            shot_id="exact-shot-13",
            start_ms=30_633,
            end_ms=34_933,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=36_900,
            source_end_ms=41_200,
            playback_rate=1,
        ),
    ]
    layers.extend(
        [
            _video_layer(
                layer_id="exact-reference-ending-prefire",
                shot_id="exact-shot-12",
                start_ms=30_367,
                end_ms=30_433,
                source_role="deterministic-graphic",
                asset_id="reference-master",
                source_start_ms=30_367,
                source_end_ms=30_433,
                playback_rate=1,
                z_index=90,
            ),
            _vignette_layer(
                layer_id="presenter-hook-vignette",
                shot_id="exact-shot-01",
                start_ms=0,
                end_ms=2_267,
            ),
            _vignette_layer(
                layer_id="presenter-ea-vignette",
                shot_id="exact-shot-03",
                start_ms=5_733,
                end_ms=9_533,
            ),
            _vignette_layer(
                layer_id="presenter-wrong-vignette",
                shot_id="exact-shot-04",
                start_ms=10_200,
                end_ms=11_767,
            ),
            _vignette_layer(
                layer_id="presenter-number-vignette",
                shot_id="exact-shot-06",
                start_ms=14_433,
                end_ms=18_167,
            ),
            _vignette_layer(
                layer_id="presenter-risk-vignette",
                shot_id="exact-shot-07",
                start_ms=18_167,
                end_ms=19_700,
            ),
            _vignette_layer(
                layer_id="presenter-cta-vignette",
                shot_id="exact-shot-12",
                start_ms=27_400,
                end_ms=30_433,
            ),
            _vignette_layer(
                layer_id="presenter-ending-vignette",
                shot_id="exact-shot-13",
                start_ms=30_633,
                end_ms=34_933,
            ),
        ]
    )
    layers.extend(
        [
            _overlay_layer(
                layer_id="exact-hook-white",
                shot_id="exact-shot-01",
                asset_id="overlay-hook-white",
                start_ms=967,
                end_ms=2_267,
                start_scale=0.94,
                start_y=18,
            ),
            _overlay_layer(
                layer_id="exact-hook-accent",
                shot_id="exact-shot-01",
                asset_id="overlay-hook-accent",
                start_ms=867,
                end_ms=2_267,
                start_scale=0.9,
                start_y=24,
            ),
            _overlay_layer(
                layer_id="exact-ea-white",
                shot_id="exact-shot-03",
                asset_id="overlay-ea-white",
                start_ms=6_500,
                end_ms=9_533,
                start_scale=0.94,
                start_y=16,
            ),
            _overlay_layer(
                layer_id="exact-ea-accent",
                shot_id="exact-shot-03",
                asset_id="overlay-ea-accent",
                start_ms=7_550,
                end_ms=9_533,
                start_scale=0.72,
                start_y=72,
                entrance_ms=240,
            ),
            _overlay_layer(
                layer_id="exact-number-white",
                shot_id="exact-shot-06",
                asset_id="overlay-number-white",
                start_ms=14_600,
                end_ms=18_167,
                start_scale=0.94,
                start_y=16,
            ),
            _overlay_layer(
                layer_id="exact-number-accent",
                shot_id="exact-shot-06",
                asset_id="overlay-number-accent",
                start_ms=15_767,
                end_ms=18_167,
                start_scale=1,
                transform_keyframes=[
                    TransformKeyframe(at_ms=0, y=420, scale=1),
                    TransformKeyframe(at_ms=33, y=351, scale=1),
                    TransformKeyframe(at_ms=133, y=200, scale=1),
                    TransformKeyframe(at_ms=233, y=123, scale=1),
                    TransformKeyframe(at_ms=333, y=78, scale=1),
                    TransformKeyframe(at_ms=433, y=50, scale=1),
                    TransformKeyframe(at_ms=533, y=32, scale=1),
                    TransformKeyframe(at_ms=633, y=20, scale=1),
                    TransformKeyframe(at_ms=733, y=12, scale=1),
                    TransformKeyframe(at_ms=833, y=7, scale=1),
                    TransformKeyframe(at_ms=933, y=4, scale=1),
                    TransformKeyframe(at_ms=1_033, y=2, scale=1),
                    TransformKeyframe(at_ms=1_133, y=0, scale=1),
                    TransformKeyframe(at_ms=2_400, y=0, scale=1),
                ],
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=1),
                ],
            ),
        ]
    )
    return layers


def build_exact_audio_mux_command(
    *,
    executable: Path,
    rendered: Path,
    reference: Path,
    output: Path,
) -> list[str]:
    return [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(rendered),
        "-i",
        str(reference),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output),
    ]


def measure_frame_pair_similarity(
    reference: np.ndarray,
    rendered: np.ndarray,
) -> dict[str, float]:
    if reference.size == 0 or rendered.size == 0:
        raise ValueError("Frame similarity requires non-empty frames")
    if reference.shape != rendered.shape:
        rendered = cv2.resize(
            rendered,
            (reference.shape[1], reference.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    if reference.shape[1] > 270:
        target_width = 270
        target_height = round(
            reference.shape[0] * target_width / reference.shape[1]
        )
        reference = cv2.resize(
            reference,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,
        )
        rendered = cv2.resize(
            rendered,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,
        )
    reference_float = reference.astype(np.float32)
    rendered_float = rendered.astype(np.float32)
    rgb_similarity = 1 - float(
        np.mean(np.abs(reference_float - rendered_float))
    ) / 255
    reference_gray = cv2.cvtColor(
        reference,
        cv2.COLOR_BGR2GRAY,
    ).astype(np.float32)
    rendered_gray = cv2.cvtColor(
        rendered,
        cv2.COLOR_BGR2GRAY,
    ).astype(np.float32)
    constant_1 = (0.01 * 255) ** 2
    constant_2 = (0.03 * 255) ** 2
    mean_reference = cv2.GaussianBlur(
        reference_gray,
        (11, 11),
        1.5,
    )
    mean_rendered = cv2.GaussianBlur(
        rendered_gray,
        (11, 11),
        1.5,
    )
    variance_reference = (
        cv2.GaussianBlur(reference_gray * reference_gray, (11, 11), 1.5)
        - mean_reference * mean_reference
    )
    variance_rendered = (
        cv2.GaussianBlur(rendered_gray * rendered_gray, (11, 11), 1.5)
        - mean_rendered * mean_rendered
    )
    covariance = (
        cv2.GaussianBlur(reference_gray * rendered_gray, (11, 11), 1.5)
        - mean_reference * mean_rendered
    )
    numerator = (
        (2 * mean_reference * mean_rendered + constant_1)
        * (2 * covariance + constant_2)
    )
    denominator = (
        (
            mean_reference * mean_reference
            + mean_rendered * mean_rendered
            + constant_1
        )
        * (
            variance_reference
            + variance_rendered
            + constant_2
        )
    )
    ssim = float(np.mean(numerator / np.maximum(denominator, 1e-6)))
    return {
        "ssim": max(-1, min(1, ssim)),
        "rgb_similarity": max(0, min(1, rgb_similarity)),
    }


def measure_every_frame_similarity(
    *,
    reference: Path,
    rendered: Path,
) -> dict[str, Any]:
    reference_capture = cv2.VideoCapture(str(reference))
    rendered_capture = cv2.VideoCapture(str(rendered))
    if not reference_capture.isOpened():
        raise RuntimeError(f"Unable to inspect reference video: {reference}")
    if not rendered_capture.isOpened():
        reference_capture.release()
        raise RuntimeError(f"Unable to inspect rendered video: {rendered}")
    fps = max(1.0, float(reference_capture.get(cv2.CAP_PROP_FPS)))
    expected_reference_frames = int(
        reference_capture.get(cv2.CAP_PROP_FRAME_COUNT)
    )
    expected_rendered_frames = int(
        rendered_capture.get(cv2.CAP_PROP_FRAME_COUNT)
    )
    ssim_values: list[float] = []
    rgb_values: list[float] = []
    try:
        while True:
            reference_ok, reference_frame = reference_capture.read()
            rendered_ok, rendered_frame = rendered_capture.read()
            if not reference_ok or not rendered_ok:
                break
            pair = measure_frame_pair_similarity(
                reference_frame,
                rendered_frame,
            )
            ssim_values.append(pair["ssim"])
            rgb_values.append(pair["rgb_similarity"])
    finally:
        reference_capture.release()
        rendered_capture.release()
    if not ssim_values:
        raise RuntimeError("No corresponding frames were decoded")
    worst_indices = np.argsort(np.asarray(ssim_values))[:12]
    return {
        "compared_frame_count": len(ssim_values),
        "reference_frame_count": expected_reference_frames,
        "rendered_frame_count": expected_rendered_frames,
        "frame_count_match": (
            expected_reference_frames == expected_rendered_frames
        ),
        "mean_ssim": round(float(np.mean(ssim_values)), 6),
        "p10_ssim": round(float(np.percentile(ssim_values, 10)), 6),
        "minimum_ssim": round(float(np.min(ssim_values)), 6),
        "mean_rgb_similarity": round(float(np.mean(rgb_values)), 6),
        "p10_rgb_similarity": round(
            float(np.percentile(rgb_values, 10)),
            6,
        ),
        "worst_frames": [
            {
                "frame": int(index),
                "timestamp_ms": round(index / fps * 1000),
                "ssim": round(ssim_values[index], 6),
                "rgb_similarity": round(rgb_values[index], 6),
            }
            for index in worst_indices
        ],
    }


def mux_exact_reference_audio(
    *,
    rendered: Path,
    reference: Path,
    output: Path,
) -> None:
    command = build_exact_audio_mux_command(
        executable=Path(get_ffmpeg_exe()),
        rendered=rendered,
        reference=reference,
        output=output,
    )
    _run_media_command(command, timeout=3_600)


def run_exact_reference_review(
    *,
    output_dir: Path,
    plan: Any,
    edited_exact: Path,
    edited_safe: Path,
    reference: Path,
) -> dict[str, Any]:
    from app.editor.ffmpeg import (
        measure_loudness_for_master,
        verify_render,
    )
    from app.editor.production_audit import (
        build_audio_continuity_report,
        measure_frame_audit,
    )

    exact_metadata = verify_render(
        edited_exact,
        expected_width=plan.output.width,
        expected_height=plan.output.height,
        expected_fps=plan.output.fps,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    safe_metadata = verify_render(
        edited_safe,
        expected_width=plan.output.width,
        expected_height=plan.output.height,
        expected_fps=plan.output.fps,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    reference_frame_audit = measure_frame_audit(reference)
    rendered_frame_audit = measure_frame_audit(edited_exact)
    similarity = measure_every_frame_similarity(
        reference=reference,
        rendered=edited_exact,
    )
    audio_continuity = build_audio_continuity_report(
        _extract_pcm(reference),
        _extract_pcm(edited_exact),
        sample_rate=48_000,
    )
    report = evaluate_exact_reference_match(
        reference=reference_frame_audit,
        rendered=rendered_frame_audit,
        similarity=similarity,
        audio=audio_continuity,
        metadata=exact_metadata,
    )
    safe_loudness = measure_loudness_for_master(
        edited_safe,
        clean_completed_mix=False,
    )
    safe_audio_passed = (
        -14.7 <= safe_loudness.input_i <= -13.7
        and safe_loudness.input_tp <= -1
    )
    report["checks"].append(
        _check(
            "posting-safe-audio",
            safe_audio_passed,
            {
                "integrated_lufs": safe_loudness.input_i,
                "true_peak_dbtp": safe_loudness.input_tp,
            },
            "-14.2 LUFS +/- 0.5; true peak <= -1 dBTP",
        )
    )
    report["automated_pass"] = all(
        check["passed"] for check in report["checks"]
    )
    report["posting_safe_metadata"] = safe_metadata.model_dump(mode="json")
    report["posting_safe_loudness"] = {
        "integrated_lufs": safe_loudness.input_i,
        "true_peak_dbtp": safe_loudness.input_tp,
        "loudness_range": safe_loudness.input_lra,
    }
    _write_json(
        output_dir / "frame-audit.json",
        {
            "reference": reference_frame_audit,
            "rendered": rendered_frame_audit,
            "similarity": similarity,
        },
    )
    _write_json(
        output_dir / "audio-continuity.json",
        audio_continuity,
    )
    _write_json(output_dir / "review-report.json", report)
    _create_exact_comparison_sheet(
        reference=reference,
        rendered=edited_exact,
        output=output_dir / "review" / "exact-comparison-sheet.jpg",
        frame_indices=[
            38,
            120,
            248,
            320,
            400,
            503,
            560,
            620,
            682,
            740,
            800,
            860,
            953,
        ],
    )
    _create_exact_comparison_sheet(
        reference=reference,
        rendered=edited_exact,
        output=output_dir / "review" / "worst-frame-comparison.jpg",
        frame_indices=[
            item["frame"] for item in similarity["worst_frames"][:8]
        ],
    )
    return report


def render_exact_reference_plan(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    output: Path,
) -> None:
    from app.editor.ffmpeg import probe_stream_codecs
    from app.editor.production_assembly import render_production_plan
    from app.editor.remotion import prepare_renderer_source_proxy

    presenter = next(
        asset for asset in plan.assets if asset.id == "source-presenter"
    )
    presenter_path = Path(presenter.path).expanduser().resolve()
    video_codec, _audio_codec = probe_stream_codecs(presenter_path)
    render_plan = plan
    if video_codec != "h264":
        proxy = (
            output_dir.expanduser().resolve()
            / "renderer-proxies"
            / "source-presenter-h264.mp4"
        )
        if (
            not proxy.is_file()
            or proxy.stat().st_mtime < presenter_path.stat().st_mtime
        ):
            prepare_renderer_source_proxy(
                executable=Path(get_ffmpeg_exe()),
                source=presenter_path,
                output=proxy,
                fps=plan.output.fps,
            )
        render_plan = plan.model_copy(
            update={
                "assets": [
                    (
                        asset.model_copy(update={"path": str(proxy)})
                        if asset.id == presenter.id
                        else asset
                    )
                    for asset in plan.assets
                ]
            }
        )
    render_production_plan(
        output_dir=output_dir,
        plan=render_plan,
        output=output,
    )


def assemble_exact_reference(
    *,
    output_dir: Path,
    renderer: Callable[..., None] | None = None,
    exact_muxer: Callable[..., None] | None = None,
    safe_masterer: Callable[..., None] | None = None,
    reviewer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from app.editor.production_assembly import (
        compile_production_plan,
        master_production_render,
        render_production_plan,
    )
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "blueprint-ready",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"Exact assembly is not allowed from state {record.state}"
        )
    record = store.transition(
        "assembling",
        detail="V5 exact-reference visual and audio masters are assembling.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    try:
        plan = compile_production_plan(output_dir)
        reference_asset = next(
            asset for asset in plan.assets if asset.id == "reference-master"
        )
        reference = Path(reference_asset.path).resolve()
        rendered = output_dir / "rendered-v5.mp4"
        edited_exact = output_dir / "edited-exact.mp4"
        edited_safe = output_dir / "edited.mp4"
        (renderer or render_exact_reference_plan)(
            output_dir=output_dir,
            plan=plan,
            output=rendered,
        )
        (exact_muxer or mux_exact_reference_audio)(
            rendered=rendered,
            reference=reference,
            output=edited_exact,
        )
        (safe_masterer or master_production_render)(
            rendered=edited_exact,
            output=edited_safe,
            duration_seconds=plan.duration_ms / 1000,
        )
        store.transition(
            "automated-review",
            detail="V5 masters rendered; exact-reference gates are running.",
        )
        report = (reviewer or run_exact_reference_review)(
            output_dir=output_dir,
            plan=plan,
            edited_exact=edited_exact,
            edited_safe=edited_safe,
            reference=reference,
        )
        _write_json(output_dir / "review-report.json", report)
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "blueprint-ready",
                detail=(
                    "V5 exact-reference assembly failed; blueprint and "
                    "source provenance were preserved for retry."
                ),
                updates={
                    "automated_pass": False,
                    "error": "Exact-reference assembly failed.",
                },
            )
        raise

    artifacts = {
        **record.artifacts,
        "edit_plan": "edit-plan.json",
        "rendered_video": "rendered-v5.mp4",
        "exact_video": "edited-exact.mp4",
        "edited_video": "edited.mp4",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "review_report": "review-report.json",
        "comparison_sheet": "review/exact-comparison-sheet.jpg",
    }
    if report["automated_pass"]:
        record = store.transition(
            "awaiting-final-approval",
            detail=(
                "V5 exact-reference gates passed; explicit human approval "
                "is still required."
            ),
            updates={
                "automated_pass": True,
                "human_approved": False,
                "artifacts": artifacts,
                "error": None,
            },
        )
    else:
        record = store.transition(
            "blueprint-ready",
            detail=(
                "V5 exact-reference gates blocked release; revise and "
                "rerender before human review."
            ),
            updates={
                "automated_pass": False,
                "artifacts": artifacts,
                "error": (
                    "Exact-reference automated gates failed. Review "
                    "review-report.json."
                ),
            },
        )
    return {
        **record.model_dump(mode="json"),
        "rendered_video": "rendered-v5.mp4",
        "exact_video": "edited-exact.mp4",
        "edited_video": "edited.mp4",
        "review_report": "review-report.json",
    }


def _read_frame(video: Path, timestamp_seconds: float) -> np.ndarray:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect reference video: {video}")
    try:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        raise RuntimeError(
            f"Unable to read reference frame at {timestamp_seconds:.3f}s"
        )
    return frame


def _extract_reference_overlay(
    *,
    frame: np.ndarray,
    bounds: tuple[int, int, int, int],
    mode: str,
) -> np.ndarray:
    x0, y0, x1, y1 = bounds
    crop = frame[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(np.float32)
    saturation = hsv[:, :, 1].astype(np.float32)
    value = hsv[:, :, 2].astype(np.float32)
    if mode == "white":
        alpha = np.clip((value - 145) / 90, 0, 1)
        alpha *= np.clip((145 - saturation) / 100, 0, 1)
        text_bgr = np.full_like(crop, 255)
    elif mode == "yellow":
        hue_distance = np.abs(hue - 29)
        alpha = np.clip((15 - hue_distance) / 12, 0, 1)
        alpha *= np.clip((saturation - 55) / 120, 0, 1)
        alpha *= np.clip((value - 110) / 100, 0, 1)
        text_bgr = crop
    elif mode == "green":
        hue_distance = np.abs(hue - 59)
        alpha = np.clip((24 - hue_distance) / 20, 0, 1)
        alpha *= np.clip((saturation - 40) / 100, 0, 1)
        alpha *= np.clip((value - 110) / 100, 0, 1)
        text_bgr = crop
    else:
        raise ValueError(f"Unsupported overlay extraction mode: {mode}")

    binary = (alpha >= 0.08).astype(np.uint8)
    component_count, labels, statistics, _centroids = (
        cv2.connectedComponentsWithStats(binary, 8)
    )
    retained = np.zeros_like(binary)
    for component in range(1, component_count):
        if statistics[component, cv2.CC_STAT_AREA] >= 18:
            retained[labels == component] = 1
    alpha *= retained
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.45)
    alpha = np.clip(alpha, 0, 1)

    full_alpha = np.zeros(frame.shape[:2], dtype=np.float32)
    full_alpha[y0:y1, x0:x1] = alpha
    shadow = cv2.GaussianBlur(full_alpha, (0, 0), 7)
    shadow = np.roll(shadow, 9, axis=0) * 0.82
    shadow[:9] = 0

    output = np.zeros((*frame.shape[:2], 4), dtype=np.uint8)
    output[:, :, 3] = np.round(shadow * 255).astype(np.uint8)
    text_alpha = np.round(full_alpha * 255).astype(np.uint8)
    output[y0:y1, x0:x1, :3] = text_bgr
    replace = text_alpha > 0
    output[:, :, 3][replace] = text_alpha[replace]
    return output


def build_reference_overlays(
    reference: Path,
    output_dir: Path,
    source: Path | None = None,
) -> dict[str, Path]:
    directory = output_dir / "assets" / "overlays"
    directory.mkdir(parents=True, exist_ok=True)
    if source is not None and source.is_file() and reference.is_file():
        paths = _build_matched_reference_overlays(
            reference=reference,
            source=source,
            directory=directory,
        )
    else:
        paths = _build_font_fallback_overlays(directory)
    vignette_path = directory / "overlay-presenter-vignette.png"
    _render_presenter_vignette().save(vignette_path, optimize=True)
    paths["overlay-presenter-vignette"] = vignette_path
    return paths


def _build_font_fallback_overlays(
    directory: Path,
) -> dict[str, Path]:
    specifications = {
        "overlay-hook-white": (
            "Forex Trading",
            False,
            86,
            540,
            1282,
            (255, 255, 255),
            1.28,
        ),
        "overlay-hook-accent": (
            "ROBOT",
            True,
            146,
            540,
            1402,
            (254, 238, 65),
            1.17,
        ),
        "overlay-ea-white": (
            "Expert Adviser",
            True,
            76,
            540,
            1310,
            (255, 255, 255),
            1.0,
        ),
        "overlay-ea-accent": (
            "EA",
            True,
            142,
            540,
            1570,
            (140, 253, 146),
            1.0,
        ),
        "overlay-number-white": (
            "An Expert Adviser",
            True,
            76,
            540,
            1310,
            (255, 255, 255),
            1.06,
        ),
        "overlay-number-accent": (
            "$1,10,000",
            True,
            144,
            540,
            1390,
            (135, 254, 142),
            1.07,
        ),
    }
    paths: dict[str, Path] = {}
    for asset_id, (
        text,
        bold,
        font_size,
        center_x,
        top_y,
        color,
        scale_x,
    ) in specifications.items():
        destination = directory / f"{asset_id}.png"
        overlay = _render_text_overlay(
            text=text,
            bold=bold,
            font_size=font_size,
            center_x=center_x,
            top_y=top_y,
            color=color,
            scale_x=scale_x,
        )
        if int(np.max(np.asarray(overlay.getchannel("A")))) == 0:
            raise RuntimeError(f"Extracted overlay is empty: {asset_id}")
        overlay.save(destination, optimize=True)
        paths[asset_id] = destination
    return paths


def _build_matched_reference_overlays(
    *,
    reference: Path,
    source: Path,
    directory: Path,
) -> dict[str, Path]:
    specifications = {
        "overlay-hook-white": (
            38,
            43,
            (190, 1_270, 915, 1_395),
            "white",
        ),
        "overlay-hook-accent": (
            38,
            43,
            (250, 1_390, 860, 1_535),
            "yellow",
        ),
        "overlay-ea-white": (
            248,
            293,
            (250, 1_295, 830, 1_400),
            "white",
        ),
        "overlay-ea-accent": (
            248,
            293,
            (420, 1_555, 665, 1_695),
            "green",
        ),
        "overlay-number-white": (
            503,
            609,
            (190, 1_295, 890, 1_400),
            "white",
        ),
        "overlay-number-accent": (
            503,
            609,
            (165, 1_380, 915, 1_535),
            "green",
        ),
    }
    frame_cache: dict[tuple[Path, int], np.ndarray] = {}

    def frame(path: Path, index: int) -> np.ndarray:
        key = (path, index)
        if key not in frame_cache:
            frame_cache[key] = _read_frame_index(path, index)
        return frame_cache[key]

    vignette_alpha = _presenter_vignette_alpha()[:, :, None] / 255
    paths: dict[str, Path] = {}
    for asset_id, (
        reference_frame,
        source_frame,
        bounds,
        kind,
    ) in specifications.items():
        background = np.round(
            frame(source, source_frame).astype(np.float32)
            * (1 - vignette_alpha)
        ).astype(np.uint8)
        overlay = _recover_gradient_text_overlay(
            background=background,
            reference=frame(reference, reference_frame),
            bounds=bounds,
            kind=kind,
        )
        destination = directory / f"{asset_id}.png"
        overlay.save(destination, optimize=True)
        paths[asset_id] = destination
    return paths


def _read_frame_index(video: Path, frame_index: int) -> np.ndarray:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect video: {video}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        raise RuntimeError(
            f"Unable to read video frame {frame_index}: {video}"
        )
    return frame


def _recover_gradient_text_overlay(
    *,
    background: np.ndarray,
    reference: np.ndarray,
    bounds: tuple[int, int, int, int],
    kind: str,
) -> Image.Image:
    if background.shape != reference.shape:
        raise ValueError("Matched text recovery requires equal frame sizes")
    if kind not in {"white", "yellow", "green"}:
        raise ValueError(f"Unsupported matched text kind: {kind}")
    height, width = reference.shape[:2]
    x0, y0, x1, y1 = bounds
    base = background[y0:y1, x0:x1].astype(np.float32)
    rendered = reference[y0:y1, x0:x1].astype(np.float32)
    delta = np.max(np.abs(rendered - base), axis=2)
    hsv = cv2.cvtColor(rendered.astype(np.uint8), cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)

    row_colors = np.zeros((y1 - y0, 3), dtype=np.float32)
    valid_rows = np.zeros(y1 - y0, dtype=bool)
    if kind == "white":
        row_colors[:] = 255
        valid_rows[:] = True
    else:
        for row in range(y1 - y0):
            if kind == "yellow":
                hue_match = (
                    ((hue[row] >= 15) & (hue[row] <= 45))
                    | (saturation[row] < 75)
                )
                minimum_value = 205
            else:
                hue_match = (
                    ((hue[row] >= 35) & (hue[row] <= 90))
                    | (saturation[row] < 75)
                )
                minimum_value = 185
            candidates = (
                hue_match
                & (value[row] > minimum_value)
                & (delta[row] > 15)
            )
            if int(candidates.sum()) < 3:
                continue
            values = rendered[row][candidates]
            luminance_order = np.argsort(values.max(axis=1))
            core_count = max(3, len(values) // 3)
            row_colors[row] = np.median(
                values[luminance_order[-core_count:]],
                axis=0,
            )
            valid_rows[row] = True
        valid_indices = np.where(valid_rows)[0]
        if valid_indices.size == 0:
            raise RuntimeError(
                f"Unable to recover {kind} reference typography"
            )
        for channel in range(3):
            row_colors[:, channel] = np.interp(
                np.arange(len(row_colors)),
                valid_indices,
                row_colors[valid_indices, channel],
            )

    direction = row_colors[:, None, :] - base
    difference = rendered - base
    alpha = np.clip(
        np.sum(difference * direction, axis=2)
        / (np.sum(direction * direction, axis=2) + 1e-6),
        0,
        1,
    )
    predicted = (
        base * (1 - alpha[:, :, None])
        + row_colors[:, None, :] * alpha[:, :, None]
    )
    residual = np.mean(np.abs(predicted - rendered), axis=2)
    if kind == "white":
        chroma_match = (saturation < 100) & (value > 120)
    elif kind == "yellow":
        chroma_match = (
            (
                ((hue >= 10) & (hue <= 50))
                | (saturation < 90)
            )
            & (value > 70)
        )
    else:
        chroma_match = (
            (
                ((hue >= 28) & (hue <= 100))
                | (saturation < 90)
            )
            & (value > 65)
        )
    alpha[
        (alpha < 0.03)
        | (residual > 22)
        | (delta < 6)
        | (~chroma_match)
    ] = 0
    binary = (alpha > 0.03).astype(np.uint8)
    component_count, labels, statistics, _centroids = (
        cv2.connectedComponentsWithStats(binary, 8)
    )
    retained = np.zeros_like(binary)
    for component in range(1, component_count):
        if statistics[component, cv2.CC_STAT_AREA] >= 10:
            retained[labels == component] = 1
    alpha *= retained

    text_alpha = np.zeros((height, width), dtype=np.float32)
    text_alpha[y0:y1, x0:x1] = alpha
    text_bgr = np.zeros((height, width, 3), dtype=np.float32)
    text_bgr[y0:y1, x0:x1] = row_colors[:, None, :]
    shifted = np.zeros_like(text_alpha)
    shifted[9:] = text_alpha[:-9]
    shadow_alpha = cv2.GaussianBlur(shifted, (0, 0), 7) * 0.82
    output_alpha = text_alpha + shadow_alpha * (1 - text_alpha)
    premultiplied_bgr = text_bgr * text_alpha[:, :, None]
    output_bgr = np.divide(
        premultiplied_bgr,
        output_alpha[:, :, None],
        out=np.zeros_like(premultiplied_bgr),
        where=output_alpha[:, :, None] > 1e-6,
    )
    output = np.zeros((height, width, 4), dtype=np.uint8)
    output[:, :, :3] = np.round(
        np.clip(output_bgr[:, :, ::-1], 0, 255)
    ).astype(np.uint8)
    output[:, :, 3] = np.round(
        np.clip(output_alpha * 255, 0, 255)
    ).astype(np.uint8)
    return Image.fromarray(output, mode="RGBA")


def _render_presenter_vignette() -> Image.Image:
    alpha = _presenter_vignette_alpha()
    image = Image.new("RGBA", (1_080, 1_920), (0, 0, 0, 0))
    image.putalpha(Image.fromarray(alpha, mode="L"))
    return image


def _presenter_vignette_alpha() -> np.ndarray:
    stops = np.asarray(
        [
            (0, 0),
            (1_120, 0),
            (1_200, 5),
            (1_280, 17),
            (1_360, 35),
            (1_440, 58),
            (1_520, 81),
            (1_600, 109),
            (1_680, 136),
            (1_760, 164),
            (1_840, 191),
            (1_919, 220),
        ],
        dtype=np.float32,
    )
    alpha_rows = np.interp(
        np.arange(1_920),
        stops[:, 0],
        stops[:, 1],
    )
    return np.broadcast_to(
        np.round(alpha_rows).astype(np.uint8)[:, None],
        (1_920, 1_080),
    ).copy()


def _render_text_overlay(
    *,
    text: str,
    bold: bool,
    font_size: int,
    center_x: int,
    top_y: int,
    color: tuple[int, int, int],
    scale_x: float,
) -> Image.Image:
    font = _reference_font(bold=bold, size=font_size)
    mask = Image.new("L", (1080, 1920), 0)
    draw = ImageDraw.Draw(mask)
    draw.text(
        (center_x, top_y),
        text,
        font=font,
        fill=255,
        stroke_width=1,
        stroke_fill=255,
        anchor="mt",
    )
    if scale_x != 1:
        bounding_box = mask.getbbox()
        if bounding_box is not None:
            left, top, right, bottom = bounding_box
            crop = mask.crop(bounding_box)
            resized_width = max(1, round(crop.width * scale_x))
            crop = crop.resize(
                (resized_width, crop.height),
                Image.Resampling.LANCZOS,
            )
            stretched = Image.new("L", mask.size, 0)
            stretched.paste(
                crop,
                (round(center_x - resized_width / 2), top),
            )
            mask = stretched
    shadow_mask = Image.new("L", mask.size, 0)
    shadow_mask.paste(mask, (0, 9))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(7))
    shadow_mask = shadow_mask.point(lambda value: round(value * 0.82))
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_mask)
    foreground = Image.new("RGBA", mask.size, (*color, 0))
    foreground.putalpha(mask)
    return Image.alpha_composite(shadow, foreground)


def _reference_font(*, bold: bool, size: int) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            Path(r"C:\Windows\Fonts\Roboto-Bold_2.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ]
        if bold
        else [
            Path(r"C:\Windows\Fonts\Roboto-Regular.ttf"),
            Path(r"C:\Windows\Fonts\arial.ttf"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("Reference-compatible font is unavailable")


def build_exact_reference_blueprint(
    *,
    source: Path,
    reference: Path,
    output_dir: Path,
    overlay_builder: OverlayBuilder | None = None,
) -> dict[str, str]:
    from app.editor.production_v4 import ProductionStore

    source = source.expanduser().resolve()
    reference = reference.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not reference.is_file():
        raise FileNotFoundError(reference)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_asset_path = _copy_file(
        source,
        output_dir / "assets" / "presenter" / "source-presenter.mp4",
    )
    reference_asset_path = _copy_file(
        reference,
        output_dir / "assets" / "reference" / "reference-master.mp4",
    )
    if overlay_builder is None:
        overlays = build_reference_overlays(
            reference,
            output_dir,
            source,
        )
    else:
        overlays = overlay_builder(reference, output_dir)
    assets = [
        AssetRef(
            id="source-presenter",
            kind="video",
            path=_relative(output_dir, source_asset_path),
            keywords=["presenter", "raw source"],
            provenance="user-provided",
            license="User-provided source",
        ),
        AssetRef(
            id="reference-master",
            kind="video",
            path=_relative(output_dir, reference_asset_path),
            keywords=[
                "approved reference",
                "context footage",
                "evidence animation",
                "effect source",
            ],
            provenance="user-provided-reference",
            license="User-provided approved edit",
        ),
    ]
    assets.extend(
        AssetRef(
            id=asset_id,
            kind="image",
            path=_relative(output_dir, path),
            keywords=["reference-derived typography", asset_id],
            provenance="user-provided-reference-derived-overlay",
            license="Derived from user-provided approved edit",
        )
        for asset_id, path in overlays.items()
    )
    evidence = _copy_verified_evidence(output_dir)
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=probe_video(source),
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=EXACT_REFERENCE_DURATION_MS,
        assets=assets,
        layers=build_exact_reference_layers(),
        caption_pages=[],
        audio=AudioPlan(),
        flow_shots=[],
        evidence=evidence,
    )
    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "asset_manifest": "asset-manifest.json",
        "reference_audit": "audit/reference-exact-target.json",
    }
    _write_json(
        output_dir / artifacts["blueprint"],
        blueprint.model_dump(mode="json"),
    )
    _write_json(
        output_dir / artifacts["storyboard"],
        _storyboard_from_layers(blueprint.layers),
    )
    _write_json(
        output_dir / artifacts["evidence"],
        [item.model_dump(mode="json") for item in evidence],
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "continuous_captions": False,
            "typography_layers": [
                layer.id
                for layer in blueprint.layers
                if layer.source_role == "deterministic-graphic"
            ],
        },
    )
    _write_json(
        output_dir / artifacts["asset_manifest"],
        {
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(
                        output_dir / asset.path
                    ),
                }
                for asset in assets
            ]
        },
    )
    _write_json(
        output_dir / artifacts["reference_audit"],
        {
            "reference_path": str(reference),
            "duration_ms": EXACT_REFERENCE_DURATION_MS,
            "cut_timestamps_ms": EXACT_REFERENCE_CUTS_MS,
            "presenter_ratio": 0.7176,
            "continuous_captions": False,
            "typography_sequences": 3,
        },
    )

    store = ProductionStore(output_dir)
    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id="production-0806-exact-v5",
        source_path=str(source),
        output_dir=str(output_dir),
        state="blueprint-ready",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=0,
        artifacts=artifacts,
        state_history=[
            ProductionStateEvent(
                state="analyzing",
                at=now,
                detail="Exact supplied-reference analysis completed.",
            ),
            ProductionStateEvent(
                state="blueprint-ready",
                at=now,
                detail="Exact supplied-reference blueprint persisted.",
            ),
        ],
        created_at=now,
        updated_at=now,
    )
    if store.record_path.is_file():
        store.save(record)
    else:
        store.create(record)
    return artifacts


def evaluate_exact_reference_match(
    *,
    reference: dict[str, Any],
    rendered: dict[str, Any],
    similarity: dict[str, float],
    audio: dict[str, Any],
    metadata: Any,
) -> dict[str, Any]:
    checks = [
        _check(
            "duration",
            abs(float(metadata.duration_seconds) - 34.933) <= 0.075,
            metadata.duration_seconds,
            "34.933 +/- 0.075 seconds",
        ),
        _check(
            "frame-count",
            abs(
                int(rendered["frame_count"])
                - int(reference["frame_count"])
            )
            <= 2,
            rendered["frame_count"],
            reference["frame_count"],
        ),
        _check(
            "hard-cuts",
            int(rendered["rendered_cut_count"])
            == int(reference["rendered_cut_count"]),
            rendered["rendered_cut_count"],
            reference["rendered_cut_count"],
        ),
        _check(
            "median-shot",
            abs(
                float(rendered["median_shot_ms"])
                - float(reference["median_shot_ms"])
            )
            <= 100,
            rendered["median_shot_ms"],
            reference["median_shot_ms"],
        ),
        _check(
            "motion",
            abs(
                float(rendered["motion_score"])
                - float(reference["motion_score"])
            )
            <= 0.65,
            rendered["motion_score"],
            reference["motion_score"],
        ),
        _check(
            "darkness",
            abs(
                float(rendered["dark_frame_ratio"])
                - float(reference["dark_frame_ratio"])
            )
            <= 0.06,
            rendered["dark_frame_ratio"],
            reference["dark_frame_ratio"],
        ),
        _check(
            "luminance",
            abs(
                float(rendered["mean_luminance"])
                - float(reference["mean_luminance"])
            )
            <= 4,
            rendered["mean_luminance"],
            reference["mean_luminance"],
        ),
        _check(
            "saturation",
            abs(
                float(rendered["mean_saturation"])
                - float(reference["mean_saturation"])
            )
            <= 6,
            rendered["mean_saturation"],
            reference["mean_saturation"],
        ),
        _check(
            "mean-ssim",
            float(similarity["mean_ssim"]) >= 0.72,
            similarity["mean_ssim"],
            ">= 0.72",
        ),
        _check(
            "p10-ssim",
            float(similarity["p10_ssim"]) >= 0.55,
            similarity["p10_ssim"],
            ">= 0.55",
        ),
        _check(
            "minimum-ssim",
            float(similarity["minimum_ssim"]) >= 0.70,
            similarity["minimum_ssim"],
            ">= 0.70",
        ),
        _check(
            "rgb-similarity",
            float(similarity["mean_rgb_similarity"]) >= 0.80,
            similarity["mean_rgb_similarity"],
            ">= 0.80",
        ),
        _check(
            "audio-continuity",
            bool(audio["delay_passed"])
            and bool(audio["duration_passed"])
            and bool(audio["spectral_passed"]),
            audio,
            "reference audio stream retained",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "human_approved": False,
        "checks": checks,
        "similarity": similarity,
        "reference_frame_audit": reference,
        "rendered_frame_audit": rendered,
        "audio_continuity": audio,
    }


def _check(
    name: str,
    passed: bool,
    measured: Any,
    target: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "measured": measured,
        "target": target,
    }


def _storyboard_from_layers(
    layers: list[BlueprintLayerSpec],
) -> list[dict[str, Any]]:
    shots: dict[str, dict[str, Any]] = {}
    for layer in layers:
        if layer.source_role == "deterministic-graphic":
            continue
        shot = shots.setdefault(
            layer.shot_id,
            {
                "id": layer.shot_id,
                "start_ms": layer.start_ms,
                "end_ms": layer.end_ms,
                "source_role": layer.source_role,
                "asset_id": layer.asset_id,
                "asset_ids": [],
                "layer_ids": [
                    item.id
                    for item in layers
                    if item.shot_id == layer.shot_id
                ],
            },
        )
        shot["start_ms"] = min(shot["start_ms"], layer.start_ms)
        shot["end_ms"] = max(shot["end_ms"], layer.end_ms)
        if layer.asset_id not in shot["asset_ids"]:
            shot["asset_ids"].append(layer.asset_id)
    return list(shots.values())


def _copy_verified_evidence(
    output_dir: Path,
) -> list[EvidenceItem]:
    source_path = _V4_EVIDENCE_ROOT / "evidence.json"
    if not source_path.is_file():
        return []
    evidence = [
        EvidenceItem.model_validate(item)
        for item in json.loads(source_path.read_text(encoding="utf-8"))
        if item["id"] in {
            "metaquotes-atc-history",
            "mql5-atc-2008-risk",
        }
    ]
    copied: list[EvidenceItem] = []
    for item in evidence:
        source_capture = _V4_EVIDENCE_ROOT / item.capture_path
        destination = (
            output_dir
            / "assets"
            / "evidence"
            / source_capture.name
        )
        _copy_file(source_capture, destination)
        copied.append(
            item.model_copy(
                update={"capture_path": _relative(output_dir, destination)}
            )
        )
    return copied


def _copy_file(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if (
        not destination.is_file()
        or destination.stat().st_size != source.stat().st_size
    ):
        shutil.copy2(source, destination)
    return destination


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_pcm(path: Path) -> np.ndarray:
    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        capture_output=True,
        timeout=600,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Unable to extract exact-reference audio")
    return np.frombuffer(completed.stdout, dtype=np.int16).astype(np.float64)


def _create_exact_comparison_sheet(
    *,
    reference: Path,
    rendered: Path,
    output: Path,
    frame_indices: list[int],
) -> None:
    if not frame_indices:
        return
    reference_capture = cv2.VideoCapture(str(reference))
    rendered_capture = cv2.VideoCapture(str(rendered))
    if not reference_capture.isOpened() or not rendered_capture.isOpened():
        reference_capture.release()
        rendered_capture.release()
        raise RuntimeError("Unable to create exact-reference comparison")
    cells: list[np.ndarray] = []
    try:
        for frame_index in frame_indices:
            reference_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            rendered_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            reference_ok, reference_frame = reference_capture.read()
            rendered_ok, rendered_frame = rendered_capture.read()
            if not reference_ok or not rendered_ok:
                raise RuntimeError(
                    f"Unable to compare exact frame {frame_index}"
                )
            reference_cell = cv2.resize(
                reference_frame,
                (270, 480),
                interpolation=cv2.INTER_AREA,
            )
            rendered_cell = cv2.resize(
                rendered_frame,
                (270, 480),
                interpolation=cv2.INTER_AREA,
            )
            cell = np.hstack([reference_cell, rendered_cell])
            cv2.rectangle(cell, (0, 0), (540, 34), (0, 0, 0), -1)
            cv2.putText(
                cell,
                f"FRAME {frame_index}  REFERENCE | V5",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cells.append(cell)
    finally:
        reference_capture.release()
        rendered_capture.release()
    columns = 3
    blank = np.zeros_like(cells[0])
    rows: list[np.ndarray] = []
    for index in range(0, len(cells), columns):
        row = cells[index : index + columns]
        row.extend([blank] * (columns - len(row)))
        rows.append(np.hstack(row))
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), np.vstack(rows)):
        raise RuntimeError(f"Unable to write comparison sheet: {output}")


def _run_media_command(command: list[str], *, timeout: int) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-5_000:])
    output = Path(command[-1])
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Exact-reference media command created no output")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
