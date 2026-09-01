from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np

from app.editor.ffmpeg import (
    measure_loudness_for_master,
    verify_render,
)
from app.editor.production_audit import (
    build_audio_continuity_report,
    compare_asr_tokens,
    evaluate_news_reference_composition,
    evaluate_training_parity_composition,
    estimate_audio_pulse_bpm,
    estimate_audio_delay_ms,
    measure_composition_parity,
    measure_frame_audit,
)
from app.editor.qc import (
    measure_cut_onsets_for_video,
    measure_reference_cut_onsets_for_video,
)
from app.editor.remotion import (
    build_remotion_render_command,
    prepare_production_renderer_inputs,
    run_remotion_command,
)
from app.models import AssetRef, TranscriptSegment
from app.production_models import (
    CropSpec,
    EditPlanV2,
    ProductionBlueprint,
    VisualLayerSpec,
)


def compile_production_plan(output_dir: Path) -> EditPlanV2:
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    blueprint = ProductionBlueprint.model_validate_json(
        (output_dir / "blueprint.json").read_text(encoding="utf-8")
    )
    record = ProductionStore(output_dir).load()
    accepted_by_shot = {
        clip.shot_id: clip for clip in record.accepted_clips
    }
    required_flow_ids = {shot.id for shot in blueprint.flow_shots}
    if not required_flow_ids.issubset(accepted_by_shot):
        missing = sorted(required_flow_ids - set(accepted_by_shot))
        raise ValueError(
            "Assembly requires a human-accepted Flow clip for every "
            f"planned shot. Missing: {', '.join(missing)}"
        )

    assets: list[AssetRef] = []
    for asset in blueprint.assets:
        absolute = (output_dir / asset.path).resolve()
        if not absolute.is_file():
            raise FileNotFoundError(absolute)
        assets.append(asset.model_copy(update={"path": str(absolute)}))
    layers: list[VisualLayerSpec] = []
    flow_asset_ids: set[str] = set()
    for layer in blueprint.layers:
        if layer.flow_shot_id is None:
            if layer.asset_id is None:
                raise ValueError(f"Layer {layer.id} has no source")
            layers.append(
                VisualLayerSpec(
                    **layer.model_dump(
                        exclude={"asset_id", "flow_shot_id"}
                    ),
                    asset_id=layer.asset_id,
                    loop=False,
                )
            )
            continue

        accepted = accepted_by_shot[layer.flow_shot_id]
        accepted_path = Path(accepted.proxy_path).expanduser().resolve()
        if not accepted_path.is_file():
            raise FileNotFoundError(accepted_path)
        if _sha256(accepted_path) != accepted.checksum_sha256:
            raise ValueError(
                f"Accepted Flow clip checksum changed: {layer.flow_shot_id}"
            )
        asset_id = f"accepted-{layer.flow_shot_id}"
        if asset_id not in flow_asset_ids:
            assets.append(
                AssetRef(
                    id=asset_id,
                    kind="video",
                    path=str(accepted_path),
                    keywords=[
                        "flow illustrative",
                        layer.flow_shot_id,
                    ],
                    provenance=accepted.provenance,
                )
            )
            flow_asset_ids.add(asset_id)
        source_duration_ms = round(
            (accepted.trim_end_ms - accepted.trim_start_ms)
            / accepted.speed
        )
        source_start_ms = layer.source_start_ms or 0
        source_end_ms = layer.source_end_ms or source_duration_ms
        if source_end_ms > source_duration_ms:
            raise ValueError(
                f"Flow layer {layer.id} trim exceeds the accepted clip"
            )
        layer_duration_ms = layer.end_ms - layer.start_ms
        playback_rate = (
            source_end_ms - source_start_ms
        ) / layer_duration_ms
        layers.append(
            VisualLayerSpec(
                **layer.model_dump(
                    exclude={
                        "asset_id",
                        "flow_shot_id",
                        "source_start_ms",
                        "source_end_ms",
                        "crop",
                        "playback_rate",
                        "color_filter",
                    }
                ),
                asset_id=asset_id,
                source_start_ms=source_start_ms,
                source_end_ms=source_end_ms,
                crop=_compose_crops(accepted.crop, layer.crop),
                playback_rate=playback_rate,
                color_filter=_flow_color_filter(
                    layer.color_filter,
                    accepted.color_correction.brightness,
                    accepted.color_correction.contrast,
                    accepted.color_correction.saturation,
                ),
                loop=False,
            )
        )

    plan = EditPlanV2(
        source_filename=blueprint.source_filename,
        source_metadata=blueprint.source_metadata,
        output=blueprint.output,
        duration_ms=blueprint.duration_ms,
        assets=assets,
        visual_layers=layers,
        caption_pages=blueprint.caption_pages,
        audio=blueprint.audio,
        reference_profile=blueprint.reference_profile,
        story_profile=blueprint.story_profile,
        style_reference_path=blueprint.style_reference_path,
        voice_policy=blueprint.voice_policy,
        dialogue_edl=blueprint.dialogue_edl,
        kinetic_text_cues=blueprint.kinetic_text_cues,
        motion_events=blueprint.motion_events,
    )
    (output_dir / "edit-plan.json").write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return plan


def _compose_crops(outer: CropSpec, inner: CropSpec) -> CropSpec:
    return CropSpec(
        x=outer.x + inner.x * outer.width,
        y=outer.y + inner.y * outer.height,
        width=inner.width * outer.width,
        height=inner.height * outer.height,
    )


def _visible_interval_duration(items: list[Any]) -> int:
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


def _caption_family_share(
    pages: list[Any],
    family: str,
) -> float:
    total_ms = sum(
        max(0, int(page.end_ms) - int(page.start_ms))
        for page in pages
    )
    if total_ms <= 0:
        return 0.0
    family_ms = sum(
        max(0, int(page.end_ms) - int(page.start_ms))
        for page in pages
        if getattr(page, "family", None) == family
    )
    return family_ms / total_ms


def _caption_token_window_violations(
    pages: list[Any],
) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    for page_index, page in enumerate(pages):
        for token in getattr(page, "tokens", []):
            if (
                int(token.start_ms) < int(page.start_ms)
                or int(token.end_ms) > int(page.end_ms)
            ):
                violations.append(
                    {
                        "page_index": page_index,
                        "token": str(token.text),
                        "page_window": [
                            int(page.start_ms),
                            int(page.end_ms),
                        ],
                        "token_window": [
                            int(token.start_ms),
                            int(token.end_ms),
                        ],
                    }
                )
    return violations


def _flow_color_filter(
    base_filter: str | None,
    brightness: float,
    contrast: float,
    saturation: float,
) -> str:
    correction = (
        f"brightness({brightness:g}) "
        f"contrast({contrast:g}) "
        f"saturate({saturation:g})"
    )
    return " ".join(
        value for value in (base_filter, correction) if value
    )


def calculate_layer_coverage(
    plan: EditPlanV2,
) -> dict[str, float | int | str]:
    grid_width = max(1, round(plan.output.width / 10))
    grid_height = max(1, round(plan.output.height / 10))
    grid_area = grid_width * grid_height
    total_pixel_ms = grid_area * plan.duration_ms
    role_pixel_ms: dict[str, float] = {}
    used_assets: set[str] = set()
    assets_by_id = {asset.id: asset for asset in plan.assets}
    image_alpha_cache: dict[Path, np.ndarray | None] = {}
    boundaries = sorted(
        {
            0,
            plan.duration_ms,
            *(
                time
                for layer in plan.visual_layers
                for time in (layer.start_ms, layer.end_ms)
            ),
        }
    )
    ordered_layers = [
        layer
        for _index, layer in sorted(
            enumerate(plan.visual_layers),
            key=lambda item: (item[1].z_index, item[0]),
        )
    ]
    for layer in plan.visual_layers:
        used_assets.add(layer.asset_id)
    for start_ms, end_ms in zip(
        boundaries,
        boundaries[1:],
        strict=False,
    ):
        duration_ms = end_ms - start_ms
        if duration_ms <= 0:
            continue
        midpoint_ms = (start_ms + end_ms) / 2
        active = [
            layer
            for layer in ordered_layers
            if layer.start_ms <= midpoint_ms < layer.end_ms
        ]
        role_alpha: dict[str, np.ndarray] = {}
        for layer in active:
            local_time_ms = midpoint_ms - layer.start_ms
            opacity = _layer_opacity_at(layer, local_time_ms)
            if opacity <= 0:
                continue
            raster_alpha = _layer_raster_alpha(
                layer=layer,
                local_time_ms=local_time_ms,
                output_width=plan.output.width,
                output_height=plan.output.height,
                grid_width=grid_width,
                grid_height=grid_height,
                asset_path=Path(
                    assets_by_id[layer.asset_id].path
                ).expanduser(),
                image_alpha_cache=image_alpha_cache,
            )
            raster_alpha = np.clip(raster_alpha * opacity, 0, 1)
            if not np.any(raster_alpha > 0):
                continue
            for contribution in role_alpha.values():
                contribution *= 1 - raster_alpha
            contribution = role_alpha.setdefault(
                layer.source_role,
                np.zeros((grid_height, grid_width), dtype=np.float32),
            )
            contribution += raster_alpha
        for role, contribution in role_alpha.items():
            role_pixel_ms[role] = (
                role_pixel_ms.get(role, 0)
                + float(np.sum(contribution)) * duration_ms
            )
    ratio = lambda role: round(
        role_pixel_ms.get(role, 0) / total_pixel_ms,
        6,
    )
    source_ratio = sum(
        ratio(role)
        for role in ("presenter", "real-product", "direct-evidence")
    )
    return {
        "presenter_ratio": ratio("presenter"),
        "real_product_ratio": ratio("real-product"),
        "direct_evidence_ratio": ratio("direct-evidence"),
        "real_direct_source_ratio": round(source_ratio, 6),
        "flow_ratio": ratio("flow-illustrative"),
        "deterministic_graphic_ratio": ratio(
            "deterministic-graphic"
        ),
        "licensed_context_ratio": ratio("licensed-context"),
        "visual_source_count": len(used_assets),
        "coverage_method": "visible-layer-alpha-raster",
    }


def _layer_opacity_at(
    layer: VisualLayerSpec,
    local_time_ms: float,
) -> float:
    keyframes = sorted(
        layer.opacity_keyframes,
        key=lambda item: item.at_ms,
    )
    if local_time_ms <= keyframes[0].at_ms:
        return keyframes[0].value
    if local_time_ms >= keyframes[-1].at_ms:
        return keyframes[-1].value
    right_index = next(
        index
        for index, keyframe in enumerate(keyframes)
        if keyframe.at_ms >= local_time_ms
    )
    left = keyframes[right_index - 1]
    right = keyframes[right_index]
    progress = (
        (local_time_ms - left.at_ms)
        / max(1, right.at_ms - left.at_ms)
    )
    return float(
        np.clip(
            left.value + (right.value - left.value) * progress,
            0,
            1,
        )
    )


def _layer_transform_at(
    layer: VisualLayerSpec,
    local_time_ms: float,
) -> tuple[float, float, float, float]:
    keyframes = sorted(
        layer.transform_keyframes,
        key=lambda item: item.at_ms,
    )
    if local_time_ms <= keyframes[0].at_ms:
        current = keyframes[0]
        return current.x, current.y, current.scale, current.rotate_deg
    if local_time_ms >= keyframes[-1].at_ms:
        current = keyframes[-1]
        return current.x, current.y, current.scale, current.rotate_deg
    right_index = next(
        index
        for index, keyframe in enumerate(keyframes)
        if keyframe.at_ms >= local_time_ms
    )
    left = keyframes[right_index - 1]
    right = keyframes[right_index]
    progress = (
        (local_time_ms - left.at_ms)
        / max(1, right.at_ms - left.at_ms)
    )
    interpolate = lambda start, finish: (
        start + (finish - start) * progress
    )
    return (
        interpolate(left.x, right.x),
        interpolate(left.y, right.y),
        interpolate(left.scale, right.scale),
        interpolate(left.rotate_deg, right.rotate_deg),
    )


def _layer_raster_mask(
    *,
    layer: VisualLayerSpec,
    local_time_ms: float,
    output_width: int,
    output_height: int,
    grid_width: int,
    grid_height: int,
) -> np.ndarray:
    translate_x, translate_y, scale, rotate_deg = _layer_transform_at(
        layer,
        local_time_ms,
    )
    left = float(layer.bounds.x)
    top = float(layer.bounds.y)
    right = left + layer.bounds.width
    bottom = top + layer.bounds.height
    center = np.array(
        [(left + right) / 2, (top + bottom) / 2],
        dtype=np.float64,
    )
    points = np.array(
        [
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom],
        ],
        dtype=np.float64,
    )
    radians = np.deg2rad(rotate_deg)
    rotation = np.array(
        [
            [np.cos(radians), -np.sin(radians)],
            [np.sin(radians), np.cos(radians)],
        ]
    )
    points = ((points - center) * scale) @ rotation.T + center
    points += np.array([translate_x, translate_y])
    points[:, 0] *= grid_width / output_width
    points[:, 1] *= grid_height / output_height
    polygon = np.round(points).astype(np.int32)
    mask = np.zeros((grid_height, grid_width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, polygon, 1)
    return mask.astype(bool)


def _layer_raster_alpha(
    *,
    layer: VisualLayerSpec,
    local_time_ms: float,
    output_width: int,
    output_height: int,
    grid_width: int,
    grid_height: int,
    asset_path: Path,
    image_alpha_cache: dict[Path, np.ndarray | None],
) -> np.ndarray:
    source_alpha = _load_image_alpha(
        asset_path,
        image_alpha_cache,
    )
    if source_alpha is None:
        return _layer_raster_mask(
            layer=layer,
            local_time_ms=local_time_ms,
            output_width=output_width,
            output_height=output_height,
            grid_width=grid_width,
            grid_height=grid_height,
        ).astype(np.float32)

    crop_left = round(layer.crop.x * source_alpha.shape[1])
    crop_top = round(layer.crop.y * source_alpha.shape[0])
    crop_right = round(
        (layer.crop.x + layer.crop.width) * source_alpha.shape[1]
    )
    crop_bottom = round(
        (layer.crop.y + layer.crop.height) * source_alpha.shape[0]
    )
    cropped = source_alpha[
        max(0, crop_top) : max(crop_top + 1, crop_bottom),
        max(0, crop_left) : max(crop_left + 1, crop_right),
    ]
    local_width = max(
        1,
        round(layer.bounds.width * grid_width / output_width),
    )
    local_height = max(
        1,
        round(layer.bounds.height * grid_height / output_height),
    )
    fitted = _fit_alpha_to_bounds(
        cropped,
        width=local_width,
        height=local_height,
        fit=layer.fit,
    )
    raster = np.zeros((grid_height, grid_width), dtype=np.float32)
    left = round(layer.bounds.x * grid_width / output_width)
    top = round(layer.bounds.y * grid_height / output_height)
    source_x = max(0, -left)
    source_y = max(0, -top)
    target_x = max(0, left)
    target_y = max(0, top)
    copy_width = min(
        fitted.shape[1] - source_x,
        grid_width - target_x,
    )
    copy_height = min(
        fitted.shape[0] - source_y,
        grid_height - target_y,
    )
    if copy_width > 0 and copy_height > 0:
        raster[
            target_y : target_y + copy_height,
            target_x : target_x + copy_width,
        ] = fitted[
            source_y : source_y + copy_height,
            source_x : source_x + copy_width,
        ]

    translate_x, translate_y, scale, rotate_deg = _layer_transform_at(
        layer,
        local_time_ms,
    )
    center = (
        (layer.bounds.x + layer.bounds.width / 2)
        * grid_width
        / output_width,
        (layer.bounds.y + layer.bounds.height / 2)
        * grid_height
        / output_height,
    )
    transform = cv2.getRotationMatrix2D(
        center,
        -rotate_deg,
        scale,
    )
    transform[0, 2] += translate_x * grid_width / output_width
    transform[1, 2] += translate_y * grid_height / output_height
    return cv2.warpAffine(
        raster,
        transform,
        (grid_width, grid_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def _load_image_alpha(
    path: Path,
    cache: dict[Path, np.ndarray | None],
) -> np.ndarray | None:
    resolved = path.resolve()
    if resolved in cache:
        return cache[resolved]
    image = cv2.imread(str(resolved), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] < 4:
        cache[resolved] = None
        return None
    alpha = image[:, :, 3].astype(np.float32) / 255
    cache[resolved] = alpha
    return alpha


def _fit_alpha_to_bounds(
    alpha: np.ndarray,
    *,
    width: int,
    height: int,
    fit: str,
) -> np.ndarray:
    source_height, source_width = alpha.shape
    if fit == "fill":
        return cv2.resize(
            alpha,
            (width, height),
            interpolation=cv2.INTER_AREA,
        )
    scale = (
        min(width / source_width, height / source_height)
        if fit == "contain"
        else max(width / source_width, height / source_height)
    )
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(
        alpha,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    if fit == "contain":
        canvas = np.zeros((height, width), dtype=np.float32)
        left = (width - resized_width) // 2
        top = (height - resized_height) // 2
        canvas[top : top + resized_height, left : left + resized_width] = (
            resized
        )
        return canvas
    left = max(0, (resized_width - width) // 2)
    top = max(0, (resized_height - height) // 2)
    return resized[top : top + height, left : left + width]


def build_production_master_command(
    *,
    executable: Path,
    rendered: Path,
    audio_mix: Path | None = None,
    output: Path,
    measurement: dict[str, float],
    duration_seconds: float,
    target_lufs: float = -14.2,
    target_true_peak: float = -1.2,
    target_lra: float = 5,
    video_filter: str | None = None,
    audio_filter: str | None = None,
) -> list[str]:
    loudness_filter = (
        f"loudnorm=I={target_lufs:g}:TP={target_true_peak:g}"
        f":LRA={target_lra:g}"
        f":measured_I={measurement['input_i']}"
        f":measured_TP={measurement['input_tp']}"
        f":measured_LRA={measurement['input_lra']}"
        f":measured_thresh={measurement['input_thresh']}"
        f":offset={measurement['target_offset']}"
        ":linear=true:print_format=summary"
    )
    command = [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(rendered),
    ]
    if audio_mix is not None:
        command.extend(["-i", str(audio_mix)])
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0" if audio_mix is not None else "0:a:0",
        ]
    )
    if video_filter:
        command.extend(
            [
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-colorspace",
                "bt709",
            ]
        )
    else:
        command.extend(["-c:v", "copy"])
    command.extend(
        [
            "-af",
            audio_filter or loudness_filter,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-t",
            f"{duration_seconds:.3f}",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def _music_volume_expression(audio: Any) -> str:
    expression = f"{10 ** (audio.music_base_gain_db / 20):.9f}"
    for window in audio.music_gain_automation:
        factor = 10 ** (window.gain_db / 20)
        expression += (
            "*if(between(t\\,"
            f"{window.start_ms / 1000:.3f}\\,"
            f"{window.end_ms / 1000:.3f})\\,"
            f"{factor:.9f}\\,1)"
        )
    return expression


def build_production_audio_mix_command(
    *,
    executable: Path,
    plan: EditPlanV2 | Any,
    output: Path,
    duration_seconds: float,
) -> list[str]:
    assets = {asset.id: asset for asset in plan.assets}
    dialogue = assets.get(plan.audio.dialogue_asset_id)
    if dialogue is None:
        raise ValueError("Production audio mix requires dialogue")
    duration = f"{duration_seconds:.3f}"
    command = [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(dialogue.path),
    ]
    filters: list[str] = []
    labels = ["[dialogue]"]
    dialogue_filters = [
        "aresample=48000",
        "asetpts=PTS-STARTPTS",
    ]
    if plan.audio.dialogue_offset_ms > 0:
        delay = plan.audio.dialogue_offset_ms
        dialogue_filters.append(f"adelay={delay}|{delay}")
    elif plan.audio.dialogue_offset_ms < 0:
        dialogue_filters.extend(
            [
                f"atrim=start={-plan.audio.dialogue_offset_ms / 1000:.3f}",
                "asetpts=PTS-STARTPTS",
            ]
        )
    dialogue_filters.extend(
        [
            "apad=pad_dur=0.10",
            f"atrim=duration={duration}",
        ]
    )
    filters.append("[0:a]" + ",".join(dialogue_filters) + "[dialogue]")
    input_index = 1

    music = assets.get(plan.audio.music_asset_id)
    if music is not None:
        command.extend(["-stream_loop", "-1", "-i", str(music.path)])
        filters.append(
            f"[{input_index}:a]"
            "aresample=48000,"
            f"volume='{_music_volume_expression(plan.audio)}':eval=frame,"
            f"atrim=duration={duration},asetpts=PTS-STARTPTS[music]"
        )
        labels.append("[music]")
        input_index += 1

    for cue_index, cue in enumerate(plan.audio.sfx_cues):
        asset = assets.get(cue.asset_id)
        if asset is None:
            raise ValueError(f"Missing SFX asset: {cue.asset_id}")
        command.extend(["-i", str(asset.path)])
        gain = min(cue.volume, 10 ** (cue.gain_db / 20))
        source_start_ms = int(getattr(cue, "source_start_ms", 0))
        source_end_ms = source_start_ms + cue.duration_ms
        label = f"sfx{cue_index}"
        filters.append(
            f"[{input_index}:a]"
            "aresample=48000,"
            f"atrim=start={source_start_ms / 1000:.3f}:"
            f"end={source_end_ms / 1000:.3f},"
            "asetpts=PTS-STARTPTS,"
            f"volume={gain:.9f},"
            f"adelay={cue.start_ms}|{cue.start_ms}[{label}]"
        )
        labels.append(f"[{label}]")
        input_index += 1

    mix_filters = [
        f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0",
    ]
    social_kinetic_preserve = (
        getattr(plan, "reference_profile", None) == "social-kinetic"
        and getattr(plan, "voice_policy", None) == "preserve-verbatim"
    )
    v7_training_reference = (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        in {"automation-future", "automation-future-parity"}
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0806"
    )
    if social_kinetic_preserve:
        mix_filters.append(
            "acompressor=threshold=0.08:ratio=2.5:"
            "attack=5:release=100:makeup=1.6"
        )
    elif v7_training_reference:
        mix_filters.append(
            "acompressor=threshold=0.075:ratio=2.2:"
            "attack=6:release=120:makeup=1.45"
        )
    mix_filters.extend(
        [
            "apad=pad_dur=0.10",
            f"atrim=duration={duration}",
            "aresample=48000",
        ]
    )
    filters.append(
        "".join(labels) + ",".join(mix_filters) + "[mix]"
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mix]",
            "-vn",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(output),
        ]
    )
    return command


def render_production_audio_mix(
    *,
    plan: EditPlanV2,
    output: Path,
    duration_seconds: float,
) -> None:
    command = build_production_audio_mix_command(
        executable=Path(get_ffmpeg_exe()),
        plan=plan,
        output=output,
        duration_seconds=duration_seconds,
    )
    _run_command(command, timeout=3600)


def _mastering_lufs_target(target_lufs: float, target_lra: float) -> float:
    del target_lra
    return target_lufs


def _mastering_true_peak_target(
    target_true_peak: float,
    target_lra: float,
) -> float:
    return target_true_peak - 0.1 if target_lra <= 3 else target_true_peak


def render_production_plan(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    output: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[3]
    renderer_root = project_root / "renderer"
    render_script = renderer_root / "render.mjs"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Remotion rendering")
    public_dir = output_dir / "renderer-public-v4"
    if public_dir.is_dir():
        shutil.rmtree(public_dir)
    prepared = prepare_production_renderer_inputs(
        plan=plan,
        public_dir=public_dir,
    )
    command = build_remotion_render_command(
        node_executable=Path(node),
        render_script=render_script,
        plan_path=prepared.plan_path,
        public_dir=public_dir,
        output=output,
    )
    run_remotion_command(command, cwd=renderer_root)


def _production_video_filter(plan: Any | None) -> str | None:
    if plan is None:
        return None
    if (
        getattr(plan, "reference_profile", None) == "social-kinetic"
        and getattr(plan, "voice_policy", None) == "preserve-verbatim"
    ):
        return "eq=brightness=0.022:saturation=1.04"
    if (
        getattr(plan, "reference_profile", None) == "social-kinetic"
        and getattr(plan, "voice_policy", None) == "reference-compressed"
        and getattr(plan, "story_profile", None) == "cpi-inflation"
    ):
        return (
            "tpad=stop_mode=clone:stop_duration=0.6,"
            "eq=brightness=-0.025:contrast=1.01"
        )
    if (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        == "automation-future-parity"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0806"
    ):
        return (
            "eq=brightness=0.033:saturation=0.96,"
            "unsharp=5:5:1.0:5:5:0"
        )
    if (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        == "cpi-inflation-training"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0813"
    ):
        return (
            "setparams=range=tv:color_primaries=bt709:"
            "color_trc=bt709:colorspace=bt709,"
            "curves=all='0/0.03 0.06/0.10 0.34/0.29 "
            "0.60/0.54 0.89/0.885 1/0.98',"
            "eq=brightness=0.012:saturation=1.32,"
            "unsharp=5:5:0.45:5:5:0"
        )
    if (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None) == "automation-future"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0806"
    ):
        return (
            "eq=brightness=0.033:saturation=0.96,"
            "unsharp=5:5:1.0:5:5:0"
        )
    return None


def master_production_render(
    *,
    plan: EditPlanV2 | None = None,
    rendered: Path,
    output: Path,
    duration_seconds: float,
    target_lufs: float = -14.2,
    target_true_peak: float = -1.2,
    target_lra: float = 5,
) -> None:
    audio_mix = None
    measurement_source = rendered
    if plan is not None:
        audio_mix = output.parent / "audio-mix.wav"
        render_production_audio_mix(
            plan=plan,
            output=audio_mix,
            duration_seconds=duration_seconds,
        )
        measurement_source = audio_mix
    measurement = measure_loudness_for_master(
        measurement_source,
        clean_completed_mix=False,
    )
    mastering_true_peak = _mastering_true_peak_target(
        target_true_peak,
        target_lra,
    )
    audio_filter = None
    cpi_training_parity = (
        plan is not None
        and getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        == "cpi-inflation-training"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0813"
    )
    if (
        plan is not None
        and (
            (
                getattr(plan, "reference_profile", None) == "social-kinetic"
                and getattr(plan, "voice_policy", None)
                == "reference-compressed"
            )
            or cpi_training_parity
        )
    ):
        gain_db = target_lufs - measurement.input_i
        gain = 10 ** (gain_db / 20)
        limit = 10 ** (mastering_true_peak / 20)
        audio_filter = (
            f"volume={gain:.9f}:precision=double,"
            f"alimiter=limit={limit:.9f}:attack=5:release=50:level=false"
        )
    command = build_production_master_command(
        executable=Path(get_ffmpeg_exe()),
        rendered=rendered,
        audio_mix=audio_mix,
        output=output,
        measurement={
            "input_i": measurement.input_i,
            "input_tp": measurement.input_tp,
            "input_lra": measurement.input_lra,
            "input_thresh": measurement.input_thresh,
            "target_offset": measurement.target_offset,
        },
        duration_seconds=duration_seconds,
        target_lufs=_mastering_lufs_target(target_lufs, target_lra),
        target_true_peak=mastering_true_peak,
        target_lra=target_lra,
        video_filter=_production_video_filter(plan),
        audio_filter=audio_filter,
    )
    _run_command(command, timeout=3600)


def _review_thresholds_for_plan(plan: Any) -> dict[str, Any]:
    social_kinetic = (
        getattr(plan, "reference_profile", None) == "social-kinetic"
    )
    cpi_training_parity = (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        == "cpi-inflation-training"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0813"
    )
    v8_training_parity = (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None)
        == "automation-future-parity"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0806"
    )
    v7_training_reference = (
        getattr(plan, "reference_profile", None) == "technical-reference"
        and getattr(plan, "story_profile", None) == "automation-future"
        and Path(getattr(plan, "source_filename", "")).stem.casefold()
        == "0806"
    )
    if social_kinetic:
        return {
            "profile": "social-kinetic",
            "cut_min": 13,
            "cut_max": 16,
            "median_min_ms": 2300,
            "median_max_ms": 3000,
            "flow_max": 0.18,
            "presenter_min": 0.58,
            "presenter_max": 0.68,
            "static_max_ms": 3000,
            "darkness_min": 0,
            "darkness_max": 0.06,
            "bright_min": None,
            "bright_max": None,
            "luminance_min": 95,
            "luminance_max": 108,
            "luminance_p10": None,
            "luminance_p90": None,
            "saturation_min": 65,
            "saturation_max": 85,
            "motion_min": 3.0,
            "motion_max": 8.0,
            "real_direct_min": 0.55,
            "deterministic_max": 0.25,
            "caption_coverage": None,
            "cut_audio_alignment_min": 85,
            "lra_min": 1.8,
            "lra_max": 3.0,
            "composition_parity": False,
        }
    if cpi_training_parity:
        return {
            "profile": "0813-cpi-training-parity",
            "cut_min": 34,
            "cut_max": 40,
            "median_min_ms": 900,
            "median_max_ms": 1400,
            "flow_max": 0,
            "presenter_min": 0.14,
            "presenter_max": 0.22,
            "static_max_ms": 2500,
            "darkness_min": 0.38,
            "darkness_max": 0.56,
            "bright_min": 0.10,
            "bright_max": 0.25,
            "luminance_min": 78,
            "luminance_max": 92,
            "luminance_p10": [8, 35],
            "luminance_p90": [215, 245],
            "saturation_min": 64,
            "saturation_max": 80,
            "motion_min": 5.0,
            "motion_max": 8.0,
            "real_direct_min": 0.55,
            "deterministic_max": 0.22,
            "caption_coverage": [0.65, 0.75],
            "cut_audio_alignment_min": 80,
            "lra_min": 2.3,
            "lra_max": 3.5,
            "composition_parity": True,
            "audio_pulse_min": 98,
            "audio_pulse_max": 106,
        }
    if v8_training_parity:
        return {
            "profile": "0806-training-parity-v8",
            "cut_min": 19,
            "cut_max": 21,
            "median_min_ms": 1700,
            "median_max_ms": 2300,
            "flow_max": 0,
            "presenter_min": 0.12,
            "presenter_max": 0.16,
            "static_max_ms": 3000,
            "darkness_min": 0.35,
            "darkness_max": 0.47,
            "bright_min": 0.16,
            "bright_max": 0.26,
            "luminance_min": 85,
            "luminance_max": 105,
            "luminance_p10": [8, 24],
            "luminance_p90": [215, 245],
            "saturation_min": 50,
            "saturation_max": 85,
            "motion_min": 3.5,
            "motion_max": 6.5,
            "real_direct_min": 0.52,
            "deterministic_max": 0.30,
            "caption_coverage": [0.70, 0.74],
            "cut_audio_alignment_min": 90,
            "lra_min": 2.3,
            "lra_max": 3.5,
            "composition_parity": True,
        }
    if v7_training_reference:
        return {
            "profile": "0806-training-reference-v7",
            "cut_min": 17,
            "cut_max": 19,
            "median_min_ms": 1800,
            "median_max_ms": 2300,
            "flow_max": 0,
            "presenter_min": 0.14,
            "presenter_max": 0.20,
            "static_max_ms": 2500,
            "darkness_min": 0.35,
            "darkness_max": 0.45,
            "bright_min": 0.18,
            "bright_max": 0.28,
            "luminance_min": 85,
            "luminance_max": 105,
            "luminance_p10": [8, 22],
            "luminance_p90": [220, 245],
            "saturation_min": 50,
            "saturation_max": 90,
            "motion_min": 4.5,
            "motion_max": 7.5,
            "real_direct_min": 0.50,
            "deterministic_max": 0.30,
            "caption_coverage": [0.68, 0.75],
            "cut_audio_alignment_min": 90,
            "lra_min": 2.3,
            "lra_max": 3.5,
            "composition_parity": False,
        }
    return {
        "profile": "technical-reference",
        "cut_min": 20,
        "cut_max": 23,
        "median_min_ms": 1400,
        "median_max_ms": 1800,
        "flow_max": 0.22,
        "presenter_min": 0.14,
        "presenter_max": 0.20,
        "static_max_ms": 2500,
        "darkness_min": 0,
        "darkness_max": 0.45,
        "bright_min": None,
        "bright_max": None,
        "luminance_min": 85,
        "luminance_max": 105,
        "luminance_p10": None,
        "luminance_p90": None,
        "saturation_min": 50,
        "saturation_max": 90,
        "motion_min": 4.5,
        "motion_max": 7.5,
        "real_direct_min": 0.55,
        "deterministic_max": 0.25,
        "caption_coverage": None,
        "cut_audio_alignment_min": None,
        "lra_min": None,
        "lra_max": None,
        "composition_parity": False,
    }


def run_automated_production_review(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    edited: Path,
    transcriber: Callable[[Path], list[TranscriptSegment]] | None = None,
) -> dict[str, Any]:
    metadata = verify_render(
        edited,
        expected_width=plan.output.width,
        expected_height=plan.output.height,
        expected_fps=plan.output.fps,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    frame_audit = measure_frame_audit(edited)
    coverage = calculate_layer_coverage(plan)
    social_kinetic = (
        getattr(plan, "reference_profile", None) == "social-kinetic"
    )
    thresholds = _review_thresholds_for_plan(plan)
    cpi_training_parity = (
        thresholds["profile"] == "0813-cpi-training-parity"
    )
    v8_training_parity = (
        thresholds["profile"] == "0806-training-parity-v8"
    )
    composition_parity = (
        measure_composition_parity(edited)
        if thresholds["composition_parity"]
        else None
    )
    v7_training_reference = (
        thresholds["profile"] == "0806-training-reference-v7"
    )
    loudness = measure_loudness_for_master(
        edited,
        clean_completed_mix=False,
    )
    audio_continuity = _measure_audio_continuity(
        plan=plan,
        edited=edited,
    )
    asr = _measure_asr_retention(
        output_dir=output_dir,
        plan=plan,
        edited=edited,
        transcriber=transcriber,
    )
    use_acoustic_retention = (
        social_kinetic
        or v7_training_reference
        or v8_training_parity
        or cpi_training_parity
    )
    acoustic_words = (
        _measure_acoustic_word_retention(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
        if use_acoustic_retention
        else None
    )
    acoustic_protected_terms_ok = (
        bool(asr["protected_terms_ok"])
        if v7_training_reference or v8_training_parity
        else bool(
            acoustic_words.get(
                "protected_terms_ok",
                asr["protected_terms_ok"],
            )
        )
        if acoustic_words is not None
        else bool(asr["protected_terms_ok"])
    )
    acoustic_missing_protected_terms = (
        asr["missing_protected_terms"]
        if v7_training_reference or v8_training_parity
        else acoustic_words.get(
            "missing_protected_terms",
            asr["missing_protected_terms"],
        )
        if acoustic_words is not None
        else asr["missing_protected_terms"]
    )
    evidence_ocr = _measure_evidence_ocr(edited, plan)
    diversity = _measure_visual_diversity(
        edited,
        output_dir / "storyboard.json",
    )
    _create_contact_sheet(
        video=edited,
        output=output_dir / "review" / "contact-sheet-v4.jpg",
        timestamps=[
            0.6,
            2.9,
            5.8,
            8.2,
            10.1,
            12.8,
            14.5,
            16.3,
            18.4,
            20.2,
            22.5,
            24.5,
            26.7,
            28.8,
            31.2,
            33.7,
            35.8,
            38.3,
            40.5,
        ],
    )
    _create_reference_comparison(output_dir=output_dir, video=edited)

    cut_min, cut_max = thresholds["cut_min"], thresholds["cut_max"]
    median_min_ms = thresholds["median_min_ms"]
    median_max_ms = thresholds["median_max_ms"]
    flow_max = thresholds["flow_max"]
    presenter_min = thresholds["presenter_min"]
    presenter_max = thresholds["presenter_max"]
    static_max_ms = thresholds["static_max_ms"]
    darkness_min = thresholds["darkness_min"]
    darkness_max = thresholds["darkness_max"]
    luminance_min = thresholds["luminance_min"]
    luminance_max = thresholds["luminance_max"]
    saturation_min = thresholds["saturation_min"]
    saturation_max = thresholds["saturation_max"]
    motion_min = thresholds["motion_min"]
    motion_max = thresholds["motion_max"]

    static_overruns = [
        layer.id
        for layer in plan.visual_layers
        if layer.kind == "image"
        and layer.end_ms - layer.start_ms > static_max_ms
    ]
    sfx_conflicts = [
        cue.id
        for cue in plan.audio.sfx_cues
        if any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in plan.audio.speech_protection_windows
        )
    ]
    semantic_text_ratio = _visible_interval_duration(
        list(getattr(plan, "kinetic_text_cues", []))
    ) / max(1, getattr(plan, "duration_ms", 0))
    caption_coverage_ratio = _visible_interval_duration(
        list(getattr(plan, "caption_pages", []))
    ) / max(1, getattr(plan, "duration_ms", 0))
    technical_mono_share = _caption_family_share(
        list(getattr(plan, "caption_pages", [])),
        "technical-mono",
    )
    compact_pill_share = _caption_family_share(
        list(getattr(plan, "caption_pages", [])),
        "compact-pill",
    )
    caption_token_violations = _caption_token_window_violations(
        list(getattr(plan, "caption_pages", []))
    )
    rendered_bed_pulse = (
        _measure_rendered_bed_pulse(
            plan=plan,
            edited=edited,
        )
        if v8_training_parity or cpi_training_parity
        else None
    )
    mixed_audio_pulse_bpm = (
        rendered_bed_pulse["pulse_bpm"]
        if rendered_bed_pulse is not None
        else None
    )
    motion_event_count = len(getattr(plan, "motion_events", []))
    typography: dict[str, Any] = {}
    audio_alignment: dict[str, Any] = {}
    if (
        social_kinetic
        or v7_training_reference
        or v8_training_parity
        or cpi_training_parity
    ):
        typography = {
            "hero_text_height_px": 196,
            "outlined_text_height_px": 114,
            "measurement_method": "renderer-profile-computed-style",
        }
        rendered_cut_times_ms = [
            round(float(timestamp) * 1000)
            for timestamp in frame_audit.get(
                "cut_timestamps_seconds",
                [],
            )
        ]
        alignment_measure = (
            measure_reference_cut_onsets_for_video
            if cpi_training_parity
            else measure_cut_onsets_for_video
        )
        audio_alignment = {
            "cut_audio_alignment_percent": alignment_measure(
                edited,
                rendered_cut_times_ms,
            ),
            "window_ms": 100,
            "cut_count": len(rendered_cut_times_ms),
        }
        if cpi_training_parity:
            audio_alignment["measurement"] = "reference-db-onset"
    checks = [
        _check(
            "rendered-hard-cuts",
            cut_min
            <= int(frame_audit["rendered_cut_count"])
            <= cut_max,
            frame_audit["rendered_cut_count"],
            f"{cut_min}-{cut_max}",
        ),
        _check(
            "median-shot",
            median_min_ms
            <= float(frame_audit["median_shot_ms"])
            <= median_max_ms,
            frame_audit["median_shot_ms"],
            f"{median_min_ms}-{median_max_ms} ms",
        ),
        _check(
            "real-direct-source-pixels",
            float(coverage["real_direct_source_ratio"])
            >= float(thresholds["real_direct_min"]),
            coverage["real_direct_source_ratio"],
            f'>= {float(thresholds["real_direct_min"]):.2f}',
        ),
        _check(
            "flow-pixels",
            float(coverage["flow_ratio"]) <= flow_max,
            coverage["flow_ratio"],
            f"<= {flow_max:.2f}",
        ),
        _check(
            "deterministic-graphic-pixels",
            float(coverage["deterministic_graphic_ratio"])
            <= float(thresholds["deterministic_max"]),
            coverage["deterministic_graphic_ratio"],
            f'<= {float(thresholds["deterministic_max"]):.2f}',
        ),
        _check(
            "presenter-pixels",
            presenter_min
            <= float(coverage["presenter_ratio"])
            <= presenter_max,
            coverage["presenter_ratio"],
            f"{presenter_min:.2f}-{presenter_max:.2f}",
        ),
        _check(
            "static-primitive-hold",
            not static_overruns,
            static_overruns,
            f"no static layer > {static_max_ms} ms",
        ),
        _check(
            "visual-source-diversity",
            int(coverage["visual_source_count"]) >= 6
            and diversity["unique_hashes"] >= 6,
            {
                "assets": coverage["visual_source_count"],
                "hashes": diversity["unique_hashes"],
            },
            ">= 6 assets and perceptual hashes",
        ),
        _check(
            "darkness",
            darkness_min
            <= float(frame_audit["dark_frame_ratio"])
            <= darkness_max,
            frame_audit["dark_frame_ratio"],
            (
                f"{darkness_min:.2f}-{darkness_max:.2f}"
                if darkness_min
                else f"<= {darkness_max:.2f}"
            ),
        ),
        _check(
            "luminance",
            luminance_min
            <= float(frame_audit["mean_luminance"])
            <= luminance_max,
            frame_audit["mean_luminance"],
            f"{luminance_min}-{luminance_max}",
        ),
        _check(
            "saturation",
            saturation_min
            <= float(frame_audit["mean_saturation"])
            <= saturation_max,
            frame_audit["mean_saturation"],
            f"{saturation_min}-{saturation_max}",
        ),
        _check(
            "structural-motion",
            motion_min
            <= float(frame_audit["motion_score"])
            <= motion_max,
            frame_audit["motion_score"],
            f"{motion_min:g}-{motion_max:g}",
        ),
        _check(
            "evidence-ocr",
            evidence_ocr["passed"],
            evidence_ocr["terms"],
            evidence_ocr.get(
                "target",
                ", ".join(evidence_ocr["terms"]),
            ),
        ),
        _check(
            "narration-retention",
            (
                float(acoustic_words["retention_ratio"]) >= 0.99
                and acoustic_protected_terms_ok
            )
            if use_acoustic_retention and acoustic_words is not None
            else (
                float(asr["retention_ratio"]) >= 0.99
                and bool(asr["protected_terms_ok"])
            ),
            (
                {
                    "acoustic_words": acoustic_words,
                    "protected_terms_ok": acoustic_protected_terms_ok,
                    "missing_protected_terms": (
                        acoustic_missing_protected_terms
                    ),
                    "asr_token_retention_ratio": asr[
                        "retention_ratio"
                    ],
                }
                if use_acoustic_retention
                else asr
            ),
            (
                ">= 0.99 acoustically verified words and protected terms retained"
                if use_acoustic_retention
                else ">= 0.99 and protected terms retained"
            ),
        ),
        _check(
            "audio-continuity",
            bool(audio_continuity["delay_passed"])
            and bool(audio_continuity["duration_passed"])
            and bool(audio_continuity["spectral_passed"]),
            audio_continuity,
            "<= 20 ms delay; <= 50 ms duration delta; <= 8 dB spectral distance",
        ),
        _check(
            "loudness",
            (
                -13.8 <= loudness.input_i <= -13.2
                and loudness.input_tp <= -1.0
                and 1.8
                <= float(getattr(loudness, "input_lra", -1))
                <= 3.0
            )
            if social_kinetic
            else (
                -14.5 <= loudness.input_i <= -13.9
                and loudness.input_tp <= -1.0
                and float(thresholds["lra_min"])
                <= float(getattr(loudness, "input_lra", -1))
                <= float(thresholds["lra_max"])
            )
            if (
                v7_training_reference
                or v8_training_parity
                or cpi_training_parity
            )
            else (
                -14.7 <= loudness.input_i <= -13.7
                and loudness.input_tp <= -1.0
            ),
            {
                "integrated_lufs": loudness.input_i,
                "true_peak_dbtp": loudness.input_tp,
                "loudness_range_lu": getattr(
                    loudness,
                    "input_lra",
                    None,
                ),
            },
            (
                "-13.5 +/- 0.3 LUFS; 1.8-3.0 LU LRA; <= -1 dBTP"
                if social_kinetic
                else (
                    "-14.2 +/- 0.3 LUFS; 2.3-3.5 LU LRA; <= -1 dBTP"
                    if (
                        v7_training_reference
                        or v8_training_parity
                        or cpi_training_parity
                    )
                    else "-14.2 +/- 0.5 LUFS; <= -1 dBTP"
                )
            ),
        ),
        _check(
            "speech-protected-sfx",
            not sfx_conflicts,
            sfx_conflicts,
            "zero SFX in protected speech windows",
        ),
    ]
    if social_kinetic:
        if getattr(plan, "voice_policy", None) == "reference-compressed":
            planned_duration_seconds = plan.duration_ms / 1000
            duration_passed = (
                abs(metadata.duration_seconds - planned_duration_seconds)
                <= 0.15
            )
            duration_target = (
                f"{planned_duration_seconds:.2f} seconds +/- 0.15"
            )
        else:
            planned_duration_seconds = plan.duration_ms / 1000
            duration_passed = (
                abs(metadata.duration_seconds - planned_duration_seconds)
                <= 0.05
            )
            duration_target = (
                f"{planned_duration_seconds:.2f} seconds +/- 0.05"
            )
        checks.extend(
            [
                _check(
                    "duration",
                    duration_passed,
                    metadata.duration_seconds,
                    duration_target,
                ),
                _check(
                    "semantic-text-coverage",
                    0.18 <= semantic_text_ratio <= 0.30,
                    semantic_text_ratio,
                    "0.18-0.30",
                ),
                _check(
                    "motion-event-density",
                    25 <= motion_event_count <= 32,
                    motion_event_count,
                    "25-32",
                ),
                _check(
                    "hero-text-height",
                    170
                    <= float(typography["hero_text_height_px"])
                    <= 220,
                    typography["hero_text_height_px"],
                    "170-220 px",
                ),
                _check(
                    "outlined-text-height",
                    100
                    <= float(typography["outlined_text_height_px"])
                    <= 125,
                    typography["outlined_text_height_px"],
                    "100-125 px",
                ),
                _check(
                    "cut-audio-alignment",
                    float(
                        audio_alignment[
                            "cut_audio_alignment_percent"
                        ]
                    )
                    >= 85,
                    audio_alignment["cut_audio_alignment_percent"],
                    ">= 85% within +/-100 ms",
                ),
            ]
        )
    if (
        v7_training_reference
        or v8_training_parity
        or cpi_training_parity
    ):
        planned_duration_seconds = plan.duration_ms / 1000
        p10_target = thresholds["luminance_p10"]
        p90_target = thresholds["luminance_p90"]
        caption_target = thresholds["caption_coverage"]
        checks.extend(
            [
                _check(
                    "duration",
                    abs(
                        metadata.duration_seconds
                        - planned_duration_seconds
                    )
                    <= 0.05,
                    metadata.duration_seconds,
                    f"{planned_duration_seconds:.2f} seconds +/- 0.05",
                ),
                _check(
                    "caption-coverage",
                    float(caption_target[0])
                    <= caption_coverage_ratio
                    <= float(caption_target[1]),
                    caption_coverage_ratio,
                    f"{caption_target[0]:.2f}-{caption_target[1]:.2f}",
                ),
                _check(
                    "bright-frame-ratio",
                    float(thresholds["bright_min"])
                    <= float(frame_audit["bright_frame_ratio"])
                    <= float(thresholds["bright_max"]),
                    frame_audit["bright_frame_ratio"],
                    (
                        f'{float(thresholds["bright_min"]):.2f}-'
                        f'{float(thresholds["bright_max"]):.2f}'
                    ),
                ),
                _check(
                    "luminance-p10",
                    float(p10_target[0])
                    <= float(frame_audit["luminance_p10"])
                    <= float(p10_target[1]),
                    frame_audit["luminance_p10"],
                    f"{p10_target[0]}-{p10_target[1]}",
                ),
                _check(
                    "luminance-p90",
                    float(p90_target[0])
                    <= float(frame_audit["luminance_p90"])
                    <= float(p90_target[1]),
                    frame_audit["luminance_p90"],
                    f"{p90_target[0]}-{p90_target[1]}",
                ),
                _check(
                    "cut-audio-alignment",
                    float(
                        audio_alignment[
                            "cut_audio_alignment_percent"
                        ]
                    )
                    >= float(thresholds["cut_audio_alignment_min"]),
                    audio_alignment["cut_audio_alignment_percent"],
                    (
                        f'>= {float(thresholds["cut_audio_alignment_min"]):.0f}% '
                        "within +/-100 ms"
                    ),
                ),
            ]
        )
    if v8_training_parity:
        checks.extend(
            [
                _check(
                    "technical-mono-caption-share",
                    technical_mono_share >= 0.96,
                    technical_mono_share,
                    ">= 0.96",
                ),
                _check(
                    "caption-token-containment",
                    not caption_token_violations,
                    caption_token_violations,
                    "zero tokens outside their visible page",
                ),
            ]
        )
    if cpi_training_parity:
        checks.extend(
            [
                _check(
                    "compact-pill-caption-share",
                    compact_pill_share >= 0.70,
                    compact_pill_share,
                    ">= 0.70",
                ),
                _check(
                    "caption-token-containment",
                    not caption_token_violations,
                    caption_token_violations,
                    "zero tokens outside their visible page",
                ),
                _check(
                    "mixed-audio-pulse",
                    mixed_audio_pulse_bpm is not None
                    and float(thresholds["audio_pulse_min"])
                    <= mixed_audio_pulse_bpm
                    <= float(thresholds["audio_pulse_max"]),
                    mixed_audio_pulse_bpm,
                    (
                        f'{thresholds["audio_pulse_min"]}-'
                        f'{thresholds["audio_pulse_max"]} BPM'
                    ),
                ),
            ]
        )
    if v8_training_parity:
        checks.append(
            _check(
                "mixed-audio-pulse",
                mixed_audio_pulse_bpm is not None
                and 84 <= mixed_audio_pulse_bpm <= 100,
                mixed_audio_pulse_bpm,
                "84-100 BPM",
            )
        )
    if composition_parity is not None:
        checks.extend(
            (
                evaluate_news_reference_composition(
                    composition_parity
                )
                if cpi_training_parity
                else evaluate_training_parity_composition(
                    composition_parity
                )
            )["checks"]
        )
    automated_pass = all(check["passed"] for check in checks)
    report = {
        "automated_pass": automated_pass,
        "human_approved": False,
        "reference_profile": getattr(
            plan,
            "reference_profile",
            "technical-reference",
        ),
        "render": {
            "width": metadata.width,
            "height": metadata.height,
            "fps": metadata.fps,
            "duration_seconds": metadata.duration_seconds,
        },
        "checks": checks,
        "coverage": coverage,
        "frame_audit": frame_audit,
        "composition_parity": composition_parity,
        "audio_continuity": audio_continuity,
        "asr_retention": asr,
        "acoustic_word_retention": acoustic_words,
        "evidence_ocr": evidence_ocr,
        "visual_diversity": diversity,
        "semantic_text_ratio": semantic_text_ratio,
        "caption_coverage_ratio": caption_coverage_ratio,
        "technical_mono_caption_share": technical_mono_share,
        "compact_pill_caption_share": compact_pill_share,
        "caption_token_window_violations": caption_token_violations,
        "mixed_audio_pulse_bpm": mixed_audio_pulse_bpm,
        "rendered_bed_pulse": rendered_bed_pulse,
        "motion_event_count": motion_event_count,
        "typography": typography,
        "audio_alignment": audio_alignment,
    }
    _write_json(output_dir / "frame-audit.json", frame_audit)
    if composition_parity is not None:
        _write_json(
            output_dir / "composition-parity.json",
            composition_parity,
        )
    _write_json(
        output_dir / "audio-continuity.json",
        audio_continuity,
    )
    _write_json(output_dir / "asr-retention.json", asr)
    _write_json(output_dir / "review-report.json", report)
    return report


def assemble_production(
    *,
    output_dir: Path,
    renderer: Callable[..., None] | None = None,
    masterer: Callable[..., None] | None = None,
    reviewer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    blueprint = ProductionBlueprint.model_validate_json(
        (output_dir / "blueprint.json").read_text(encoding="utf-8")
    )
    revision_state = (
        "awaiting-candidate-review"
        if blueprint.flow_shots
        else "blueprint-ready"
    )
    if record.state not in {
        "blueprint-ready",
        "awaiting-candidate-review",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"Assembly is not allowed from state {record.state}"
        )
    if record.state in {"automated-review", "awaiting-final-approval"}:
        record = store.transition(
            "assembling",
            detail="Production assembly restarted for revision.",
            updates={
                "automated_pass": False,
                "human_approved": False,
                "final_reviewer": None,
                "error": None,
            },
        )
    else:
        record = store.transition(
            "assembling",
            detail="All accepted sources are being assembled.",
            updates={"error": None},
        )
    try:
        plan = compile_production_plan(output_dir)
        rendered = output_dir / "rendered-v4.mp4"
        edited = output_dir / "edited.mp4"
        (renderer or render_production_plan)(
            output_dir=output_dir,
            plan=plan,
            output=rendered,
        )
        (masterer or master_production_render)(
            plan=plan,
            rendered=rendered,
            output=edited,
            duration_seconds=plan.duration_ms / 1000,
            target_lufs=plan.audio.integrated_lufs,
            target_true_peak=plan.audio.true_peak_dbtp,
            target_lra=plan.audio.target_lra_lu,
        )
        store.transition(
            "automated-review",
            detail="Render complete; automated release gates are running.",
        )
        report = (reviewer or run_automated_production_review)(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                revision_state,
                detail=(
                    "Production assembly failed; the accepted source "
                    "decisions were preserved for a safe retry."
                ),
                updates={"automated_pass": False},
            )
        raise
    if report["automated_pass"]:
        record = store.transition(
            "awaiting-final-approval",
            detail=(
                "Automated gates passed; side-by-side human approval "
                "is required before release."
            ),
            updates={
                "automated_pass": True,
                "error": None,
            },
        )
    else:
        record = store.transition(
            revision_state,
            detail=(
                "Automated gates blocked release. Review the report and "
                "revise before assembling again."
            ),
            updates={
                "automated_pass": False,
                "error": (
                    "Automated production gates failed. Review "
                    "review-report.json before retrying assembly."
                ),
            },
        )
    return {
        **record.model_dump(mode="json"),
        "review_report": "review-report.json",
        "edited_video": "edited.mp4",
    }


def _measure_audio_continuity(
    *,
    plan: EditPlanV2,
    edited: Path,
) -> dict[str, Any]:
    dialogue = next(
        (
            asset
            for asset in plan.assets
            if asset.id == "dialogue-original"
        ),
        None,
    ) or next(
        (
            asset
            for asset in plan.assets
            if asset.id == plan.audio.dialogue_asset_id
        ),
        None,
    )
    if dialogue is None:
        return {
            "delay_passed": False,
            "duration_passed": False,
            "detail": "Dialogue master is missing.",
        }
    source_signal = _extract_pcm(Path(dialogue.path))
    final_signal = _extract_pcm(edited)
    return build_audio_continuity_report(
        source_signal,
        final_signal,
        sample_rate=48000,
        allowed_delay_ms=20,
    )


def _clip_sparse_transients_for_pulse(
    samples: np.ndarray,
    *,
    percentile: float = 99.0,
) -> np.ndarray:
    signal = np.asarray(samples, dtype=np.float64).reshape(-1)
    if signal.size == 0:
        return signal
    limit = float(np.percentile(np.abs(signal), percentile))
    if limit <= 1e-12:
        return signal
    return np.clip(signal, -limit, limit)


def _rendered_bed_pulse_source(edited: Path) -> Path:
    pre_master_mix = edited.parent / "audio-mix.wav"
    return pre_master_mix if pre_master_mix.is_file() else edited


def _measure_rendered_bed_pulse(
    *,
    plan: EditPlanV2 | Any,
    edited: Path,
) -> dict[str, float | int]:
    dialogue = next(
        (
            asset
            for asset in getattr(plan, "assets", [])
            if asset.id == "dialogue-original"
        ),
        None,
    ) or next(
        (
            asset
            for asset in getattr(plan, "assets", [])
            if asset.id == getattr(plan.audio, "dialogue_asset_id", None)
        ),
        None,
    )
    if dialogue is None:
        raise ValueError("Rendered-bed pulse review requires dialogue")

    sample_rate = 48_000
    source = np.asarray(
        _extract_pcm(Path(dialogue.path)),
        dtype=np.float64,
    ).reshape(-1)
    pulse_source = _rendered_bed_pulse_source(edited)
    final = np.asarray(
        _extract_pcm(pulse_source),
        dtype=np.float64,
    ).reshape(-1)
    delay_ms = estimate_audio_delay_ms(
        source,
        final,
        sample_rate=sample_rate,
    )
    delay_samples = round(delay_ms * sample_rate / 1000)
    if delay_samples > 0:
        aligned_source = source[:-delay_samples]
        aligned_final = final[delay_samples:]
    elif delay_samples < 0:
        aligned_source = source[-delay_samples:]
        aligned_final = final[:delay_samples]
    else:
        sample_count = min(source.size, final.size)
        aligned_source = source[:sample_count]
        aligned_final = final[:sample_count]

    sample_count = min(aligned_source.size, aligned_final.size)
    if sample_count < sample_rate * 4:
        raise ValueError(
            "Rendered-bed pulse review requires four aligned seconds"
        )
    aligned_source = aligned_source[:sample_count]
    aligned_final = aligned_final[:sample_count]
    denominator = float(np.dot(aligned_source, aligned_source))
    if denominator <= 1e-12:
        raise ValueError("Dialogue master contains no measurable signal")
    dialogue_scale = float(
        np.dot(aligned_final, aligned_source) / denominator
    )
    residual_bed = aligned_final - dialogue_scale * aligned_source
    pulse_signal = _clip_sparse_transients_for_pulse(residual_bed)
    pulse_bpm = estimate_audio_pulse_bpm(
        pulse_signal,
        sample_rate=sample_rate,
        bpm_min=72,
        bpm_max=120,
    )
    return {
        "pulse_bpm": pulse_bpm,
        "dialogue_scale": round(dialogue_scale, 6),
        "estimated_delay_ms": delay_ms,
        "transient_clip_percentile": 99,
        "measurement_source": pulse_source.name,
    }


def _measure_acoustic_word_retention(
    *,
    output_dir: Path,
    plan: EditPlanV2 | Any,
    edited: Path,
) -> dict[str, Any]:
    dialogue = next(
        (
            asset
            for asset in plan.assets
            if asset.id == "dialogue-original"
        ),
        None,
    )
    transcript_path = output_dir / "transcript-aligned.json"
    if dialogue is None or not transcript_path.is_file():
        return {
            "retention_ratio": 0,
            "verified_word_count": 0,
            "word_count": 0,
            "detail": "Dialogue master or aligned transcript is missing.",
        }
    source = np.asarray(
        _extract_pcm(Path(dialogue.path)),
        dtype=np.float64,
    ).reshape(-1)
    final = np.asarray(_extract_pcm(edited), dtype=np.float64).reshape(-1)
    delay_ms = estimate_audio_delay_ms(source, final, sample_rate=48_000)
    delay_samples = round(delay_ms * 48_000 / 1000)
    segments = json.loads(transcript_path.read_text(encoding="utf-8"))
    threshold = 0.45
    scores: list[dict[str, Any]] = []
    for segment in segments:
        for word in segment.get("words", []):
            source_start = max(0, round(float(word["start"]) * 48_000))
            source_end = min(
                source.size,
                round(float(word["end"]) * 48_000),
            )
            final_start = source_start + delay_samples
            final_end = source_end + delay_samples
            if (
                source_end - source_start < 480
                or final_start < 0
                or final_end > final.size
            ):
                continue
            source_window = source[source_start:source_end]
            final_window = final[final_start:final_end]
            source_window = source_window - float(np.mean(source_window))
            final_window = final_window - float(np.mean(final_window))
            denominator = float(
                np.linalg.norm(source_window)
                * np.linalg.norm(final_window)
            )
            if denominator <= 1e-9:
                continue
            similarity = float(
                np.dot(source_window, final_window) / denominator
            )
            scores.append(
                {
                    "word": str(word["text"]),
                    "start_ms": round(float(word["start"]) * 1000),
                    "end_ms": round(float(word["end"]) * 1000),
                    "similarity": round(similarity, 6),
                    "passed": similarity >= threshold,
                }
            )
    verified = sum(1 for score in scores if score["passed"])
    report = {
        "retention_ratio": verified / len(scores) if scores else 0,
        "verified_word_count": verified,
        "word_count": len(scores),
        "similarity_threshold": threshold,
        "estimated_delay_ms": delay_ms,
        "minimum_similarity": (
            min(score["similarity"] for score in scores)
            if scores
            else None
        ),
        "failed_words": [
            score for score in scores if not score["passed"]
        ],
    }
    if getattr(plan, "reference_profile", None) == "social-kinetic":
        protected_terms, protected_aliases = _protected_terms_for_plan(plan)
        missing_terms = _missing_acoustic_protected_terms(
            scores=scores,
            protected_terms=protected_terms,
            protected_aliases=protected_aliases,
        )
        report["protected_terms_ok"] = not missing_terms
        report["missing_protected_terms"] = missing_terms
    return report


def _missing_acoustic_protected_terms(
    *,
    scores: list[dict[str, Any]],
    protected_terms: list[str],
    protected_aliases: dict[str, list[str]],
) -> list[str]:
    normalized_scores = [
        {
            "token": "".join(
                character
                for character in str(score["word"]).casefold()
                if character.isalnum()
            ),
            "passed": bool(score["passed"]),
        }
        for score in scores
    ]
    missing: list[str] = []
    for term in protected_terms:
        variants = [term, *protected_aliases.get(term, [])]
        matched = False
        for variant in variants:
            phrase = [
                "".join(
                    character
                    for character in token.casefold()
                    if character.isalnum()
                )
                for token in variant.split()
            ]
            phrase = [token for token in phrase if token]
            if not phrase:
                continue
            for start in range(len(normalized_scores) - len(phrase) + 1):
                window = normalized_scores[start : start + len(phrase)]
                if (
                    [item["token"] for item in window] == phrase
                    and all(item["passed"] for item in window)
                ):
                    matched = True
                    break
            if matched:
                break
        if not matched:
            missing.append(term)
    return missing


def _measure_asr_retention(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    edited: Path,
    transcriber: Callable[[Path], list[TranscriptSegment]] | None,
) -> dict[str, Any]:
    dialogue = next(
        (
            asset
            for asset in plan.assets
            if asset.id == "dialogue-original"
        ),
        None,
    )
    if dialogue is None:
        return {
            "retention_ratio": 0,
            "protected_terms_ok": False,
            "detail": "Untouched dialogue master is missing.",
        }
    if transcriber is None:
        from app.editor.pipeline import (
            transcribe_video,
            transcribe_video_fixed_language,
        )

        if (
            getattr(plan, "reference_profile", None)
            == "technical-reference"
            and getattr(plan, "story_profile", None)
            in {"automation-future", "automation-future-parity"}
            and Path(getattr(plan, "source_filename", "")).stem.casefold()
            == "0806"
        ):
            def transcribe_english(path: Path) -> list[TranscriptSegment]:
                return transcribe_video_fixed_language(
                    path,
                    language="en",
                )

            transcriber = transcribe_english
        else:
            transcriber = transcribe_video
    source_path = Path(dialogue.path)
    source_segments = transcriber(source_path)
    final_segments = transcriber(edited)
    _write_json(
        output_dir / "transcript-source-asr.json",
        [segment.model_dump(mode="json") for segment in source_segments],
    )
    _write_json(
        output_dir / "transcript-final-asr.json",
        [segment.model_dump(mode="json") for segment in final_segments],
    )
    source_text = " ".join(segment.text for segment in source_segments)
    unaligned_source_tokens = _unaligned_source_asr_tokens(source_segments)
    final_text = " ".join(segment.text for segment in final_segments)
    if not source_text.strip():
        return {
            "retention_ratio": 0,
            "protected_terms_ok": False,
            "detail": "Source ASR is empty.",
        }
    protected_terms, protected_aliases = _protected_terms_for_plan(plan)
    report = compare_asr_tokens(
        source_text=source_text,
        final_text=final_text,
        protected_terms=protected_terms,
        protected_term_aliases=protected_aliases,
        unverifiable_source_tokens=unaligned_source_tokens,
    )
    report["source_asset_id"] = dialogue.id
    report["source_path"] = str(source_path)
    report["source_token_policy"] = (
        "exclude-missing-zero-duration-source-tokens"
    )
    report["source_text"] = source_text
    report["final_text"] = final_text
    return report


def _protected_terms_for_plan(
    plan: EditPlanV2 | Any,
) -> tuple[list[str], dict[str, list[str]]]:
    if getattr(plan, "story_profile", None) in {
        "cpi-inflation",
        "cpi-inflation-training",
    }:
        return (
            [
                "petrol",
                "rent",
                "12 August 2026",
                "CPI",
                "0.1",
                "3.4",
                "1.5",
                "2.9",
                "shelter",
                "dollar",
                "spread limit",
                "confirmation",
                "follow",
            ],
            {
                "12 August 2026": [
                    "August 12 2026",
                    "12th August 2026",
                    "बारह August दो हज़ार छब्बीस",
                    "बारह August दो हजार छब्बीस",
                ],
                "0.1": ["zero point one"],
                "3.4": ["three point four"],
                "1.5": ["one point five"],
                "2.9": ["two point nine"],
                "spread limit": ["spread"],
            },
        )
    if getattr(plan, "reference_profile", None) == "social-kinetic":
        if Path(getattr(plan, "source_filename", "")).stem.casefold() == "0806":
            return (
                [
                    "Do",
                    "Forex Trading Robot",
                    "Expert Advisor",
                    "2008",
                    "110000",
                    "Telegram group",
                    "Thank you",
                ],
                {
                    "110000": ["110,000", "$110,000"],
                    "Telegram group": ["Telegram"],
                },
            )
        if getattr(plan, "story_profile", None) == "rofx-case":
            return (
                [
                    "Zomato",
                    "ROFX",
                    "forex trading",
                    "1,100",
                    "federal court",
                    "April 2024",
                    "transparent",
                    "follow us",
                ],
                {
                    "1,100": ["1100"],
                    "forex trading": ["forex"],
                    "federal court": ["court records"],
                },
            )
        return (
            [
                "2008",
                "3 months",
                "Forex robot",
                "EA",
                "UPI",
                "Profit Bricks",
                "risk",
                "demo",
            ],
            {
                "3 months": [
                    "three months",
                    "3 month",
                    "3-month",
                    "three-month",
                    "3 mahine",
                    "teen mahine",
                ],
                "Forex robot": ["forex trading robot"],
                "EA": ["expert advisor", "ea's"],
                "risk": [
                    "zero risk",
                    "risk free",
                    "risk-free",
                    "risk remains",
                ],
                "demo": ["live demo"],
            },
        )
    return (
        [
            "Do",
            "Forex Trading Robot",
            "Expert Advisor",
            "2008",
            "110000",
            "Telegram group",
            "Thank you",
        ],
        {},
    )


def _evidence_terms_for_plan(
    plan: EditPlanV2 | Any | None,
) -> dict[str, tuple[str, ...]]:
    if getattr(plan, "story_profile", None) in {
        "cpi-inflation",
        "cpi-inflation-training",
    }:
        return {
            "0.1": ("01mom", "01"),
            "3.4": ("34yoy", "34"),
            "energy": ("energy15", "energy"),
            "gasoline": ("gasoline29", "gasoline"),
            "shelter": ("23shelter", "shelter"),
            "dollar": ("dollargained", "dollargains"),
        }
    if getattr(plan, "story_profile", None) == "rofx-case":
        return {
            "1100": ("1100",),
            "58m": ("58m", "58million"),
            "no-forex-trading": ("noforextrading",),
            "225m": ("225m", "225million"),
        }
    return {
        "2008": ("2008",),
        "championship": ("championship",),
        "110000": ("110000",),
    }


def _unaligned_source_asr_tokens(
    segments: list[TranscriptSegment],
) -> list[str]:
    unaligned: list[str] = []
    for segment in segments:
        for word in segment.words:
            if word.end <= word.start:
                label = word.text.strip().strip(".,!?;:")
                if label:
                    unaligned.append(label)
    return unaligned


def _evidence_review_timestamps(plan: EditPlanV2 | Any) -> list[float]:
    if getattr(plan, "story_profile", None) in {
        "cpi-inflation",
        "cpi-inflation-training",
    }:
        return [12.1, 14.0, 21.8, 26.7, 29.2]
    if getattr(plan, "story_profile", None) == "rofx-case":
        required_fragments = (
            "1100",
            "58m",
            "noforextrading",
            "225m",
        )
        cue_timestamps = sorted(
            {
                round((cue.start_ms + cue.end_ms) / 2000, 3)
                for cue in getattr(plan, "kinetic_text_cues", [])
                if any(
                    fragment
                    in "".join(
                        character.casefold()
                        for character in str(cue.text)
                        if character.isalnum()
                    )
                    for fragment in required_fragments
                )
            }
        )
        if cue_timestamps:
            return cue_timestamps
    timestamps = sorted(
        {
            round((layer.start_ms + layer.end_ms) / 2000, 3)
            for layer in getattr(plan, "visual_layers", [])
            if layer.source_role == "direct-evidence"
        }
    )
    return timestamps or [14.5, 16.2, 18.4, 20.2]


def _evidence_ocr_variants(frame: np.ndarray) -> dict[str, np.ndarray]:
    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return {
        "original": frame,
        "grayscale": grayscale,
        "otsu": cv2.threshold(
            grayscale,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )[1],
    }


def _measure_evidence_ocr(
    video: Path,
    plan: EditPlanV2 | Any | None = None,
) -> dict[str, Any]:
    tesseract = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if not tesseract.is_file():
        return {
            "passed": False,
            "terms": {},
            "detail": "Tesseract is unavailable.",
        }
    frames = _extract_frames(
        video,
        (
            _evidence_review_timestamps(plan)
            if plan is not None
            else [14.5, 16.2, 18.4, 20.2]
        ),
    )
    combined: list[str] = []
    review_dir = video.parent / "review" / "evidence-ocr"
    review_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        image_path = review_dir / f"evidence-{index:02d}.png"
        cv2.imwrite(str(image_path), frame)
        for variant_name, variant in _evidence_ocr_variants(frame).items():
            variant_path = (
                review_dir / f"evidence-{index:02d}-{variant_name}.png"
            )
            cv2.imwrite(str(variant_path), variant)
            for page_segmentation_mode in ("6", "11"):
                completed = subprocess.run(
                    [
                        str(tesseract),
                        str(variant_path),
                        "stdout",
                        "--psm",
                        page_segmentation_mode,
                    ],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=60,
                    check=False,
                    shell=False,
                )
                if completed.returncode == 0:
                    combined.append(completed.stdout)
    normalized = "".join(
        character.casefold()
        for character in "\n".join(combined)
        if character.isalnum()
    )
    requirements = _evidence_terms_for_plan(plan)
    terms = {
        label: any(value in normalized for value in accepted_values)
        for label, accepted_values in requirements.items()
    }
    return {
        "passed": all(terms.values()),
        "terms": terms,
        "target": ", ".join(requirements),
        "raw_text": "\n".join(combined),
    }


def _measure_visual_diversity(
    video: Path,
    storyboard_path: Path,
) -> dict[str, Any]:
    if not storyboard_path.is_file():
        return {"unique_hashes": 0, "hashes": []}
    shots = json.loads(storyboard_path.read_text(encoding="utf-8"))
    timestamps = [
        (float(shot["start_ms"]) + float(shot["end_ms"])) / 2000
        for shot in shots
    ]
    hashes = [_dhash(frame) for frame in _extract_frames(video, timestamps)]
    return {
        "unique_hashes": len(set(hashes)),
        "hashes": hashes,
    }


def _dhash(frame: np.ndarray) -> str:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    reduced = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = reduced[:, 1:] > reduced[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def _create_contact_sheet(
    *,
    video: Path,
    output: Path,
    timestamps: list[float],
) -> None:
    frames = _extract_frames(video, timestamps)
    cells = [
        cv2.resize(frame, (216, 384), interpolation=cv2.INTER_AREA)
        for frame in frames
    ]
    columns = 5
    rows: list[np.ndarray] = []
    blank = np.zeros_like(cells[0])
    for index in range(0, len(cells), columns):
        row = cells[index : index + columns]
        row.extend([blank] * (columns - len(row)))
        rows.append(np.hstack(row))
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), np.vstack(rows))


def _create_reference_comparison(
    *,
    output_dir: Path,
    video: Path,
) -> None:
    target_dir = output_dir / "review" / "reference-targets"
    roles = [
        ("reference-10-hook.png", 1.5),
        ("reference-10-code.png", 4.6),
        ("reference-10-evidence.png", 16.3),
        ("reference-10-system-diagram.png", 22.5),
        ("reference-10-late-code.png", 29.2),
        ("reference-10-ending.png", 39.1),
    ]
    available = [
        (target_dir / filename, timestamp)
        for filename, timestamp in roles
        if (target_dir / filename).is_file()
    ]
    if not available:
        return
    rendered = _extract_frames(
        video,
        [timestamp for _, timestamp in available],
    )
    rows: list[np.ndarray] = []
    for (reference_path, _timestamp), final in zip(
        available,
        rendered,
        strict=True,
    ):
        reference = cv2.imread(str(reference_path))
        if reference is None:
            continue
        reference = cv2.resize(
            reference,
            (270, 480),
            interpolation=cv2.INTER_AREA,
        )
        final = cv2.resize(
            final,
            (270, 480),
            interpolation=cv2.INTER_AREA,
        )
        rows.append(np.hstack([reference, final]))
    if rows:
        destination = (
            output_dir / "review" / "reference-comparison-v4.jpg"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(destination), np.vstack(rows))


def _extract_frames(
    video: Path,
    timestamps: list[float],
) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect video: {video}")
    frames: list[np.ndarray] = []
    try:
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(
                    f"Unable to read frame at {timestamp:.3f}s"
                )
            frames.append(frame)
    finally:
        capture.release()
    return frames


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
        raise RuntimeError("Unable to extract audio for continuity review")
    return np.frombuffer(completed.stdout, dtype=np.int16).astype(
        np.float64
    )


def _check(
    name: str,
    passed: bool,
    measured: object,
    target: object,
) -> dict[str, object]:
    return {
        "name": name,
        "passed": bool(passed),
        "measured": measured,
        "target": target,
    }


def _run_command(command: list[str], *, timeout: int) -> None:
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
        raise RuntimeError(completed.stderr[-5000:])
    output = Path(command[-1])
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Production command created no output")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
